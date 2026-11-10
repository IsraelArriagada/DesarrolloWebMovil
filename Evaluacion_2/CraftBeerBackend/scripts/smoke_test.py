#!/usr/bin/env python3
"""Pruebas de integración contra el Gateway (http://localhost:5000). Requiere `docker compose up` y .env.
Uso: set -a; . ./.env; set +a; python3 scripts/smoke_test.py   -> imprime PASS/FAIL y guarda evidencia en evidencia_pruebas.txt"""
import os, json, hmac, hashlib, urllib.request, urllib.error, datetime, sys
GW = os.environ.get("GW", "http://localhost:5000/api/v1")
SECRET = os.environ["WEBHOOK_SECRET"]
out, results = [], []

def call(method, path, body=None, token=None, headers=None, raw=None):
    h = {"Content-Type": "application/json"}
    if token: h["Authorization"] = "Bearer " + token
    h.update(headers or {})
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(GW + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r: return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read() or b"null")
        except Exception: return e.code, None

def check(name, cond, detail=""):
    results.append(cond); line = f"[{'PASS' if cond else 'FAIL'}] {name} {detail}"; print(line); out.append(line)

def webhook(order_id, tx, amount, status="APPROVED"):
    body = json.dumps({"orderId": order_id, "txId": tx, "amount": amount, "status": status}).encode()
    sig = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    return call("POST", "/payments/webhook", raw=body, headers={"X-Signature": sig})

stamp = datetime.datetime.now().strftime("%H%M%S")
def register(mail, nac="1990-01-01"):
    return call("POST", "/clients", {"nombre": "Test", "correo": mail, "password": "Clave1234", "fechaNacimiento": nac, "aceptaTerminos": True})

# 1 Registro y edad
s, _ = register(f"a{stamp}@t.cl"); check("Registro mayor de edad -> 201", s == 201)
s, _ = register(f"m{stamp}@t.cl", "2015-01-01"); check("Registro menor de edad -> 422", s == 422)
s, _ = register(f"a{stamp}@t.cl"); check("Correo duplicado -> 409", s == 409)
# 2 Login y bloqueo
s, r = call("POST", "/auth/login", {"correo": f"a{stamp}@t.cl", "password": "Clave1234"}); check("Login OK -> 200", s == 200)
tokA = r["token"]
register(f"b{stamp}@t.cl"); s, r = call("POST", "/auth/login", {"correo": f"b{stamp}@t.cl", "password": "Clave1234"}); tokB = r["token"]
# 3 Sin token / header spoofing / acceso directo
s, _ = call("POST", "/orders", {"items": []}); check("Sin token -> 401", s == 401)
s, _ = call("GET", "/reports/sales", token=tokA, headers={"X-User-Role": "ADMIN", "X-User-Id": "1"}); check("Spoof X-User-Role no eleva privilegios -> 403", s == 403)
try:
    urllib.request.urlopen("http://localhost:5103/orders/me", timeout=3); direct = 200
except urllib.error.HTTPError as e: direct = e.code
except Exception: direct = 0  # puerto no publicado
check("Acceso directo a servicio rechazado (403 o inalcanzable)", direct in (0, 403), f"(resp={direct})")
# 4 Catálogo y pedido
s, prods = call("GET", "/products"); check("Catálogo público -> 200", s == 200 and len(prods) > 0)
s, o = call("POST", "/orders", {"items": [{"idProducto": 1, "cantidad": 2}], "direccion": "Calle 1", "distanciaKm": 1, "confirmaMayorEdad": True}, tokA)
check("Crear pedido -> 201 y total = 2*3990", s == 201 and o["total"] == 7980, f"({o})")
oid = o["id"]
s, _ = call("GET", f"/orders/{oid}", token=tokB); check("Ownership: otro cliente -> 404", s == 404)
s, _ = call("GET", f"/orders/{oid}", token=tokA); check("Dueño ve su pedido -> 200", s == 200)
s, _ = call("POST", "/orders", {"items": [{"idProducto": 1, "cantidad": 99999}], "direccion": "x", "confirmaMayorEdad": True}, tokA); check("Cantidad excesiva -> 400", s == 400)
s, _ = call("POST", "/orders", {"items": [{"idProducto": 6, "cantidad": 16}], "direccion": "x", "confirmaMayorEdad": True}, tokA); check("Sin stock -> 409", s == 409)
# 5 Pagos
s, _ = webhook(oid, f"TX-{stamp}", 1, "APPROVED"); check("Webhook monto distinto -> 422", s == 422)
s, _ = call("POST", "/payments/webhook", raw=b'{"orderId":1}', headers={"X-Signature": "bad"}); check("Webhook firma inválida -> 401", s == 401)
s, r = webhook(oid, f"TX-{stamp}", 7980); check("Webhook válido -> confirmado", s == 200 and r.get("confirmado"))
s, r = webhook(oid, f"TX-{stamp}", 7980); check("Pago duplicado idempotente (no doble cobro)", s == 200 and r.get("duplicado"))
s, r = call("GET", f"/receipts/{oid}", token=tokA); check("Boleta emitida", s == 200 and r["numero"].startswith("B-"))
s, _ = call("GET", f"/receipts/{oid}", token=tokB); check("Boleta ajena -> 404", s == 404)
# 6 Anulación y recuperación de stock
s, st0 = call("GET", "/products/2"); st = st0["stock"]
s, o2 = call("POST", "/orders", {"items": [{"idProducto": 2, "cantidad": 3}], "direccion": "Calle 2", "confirmaMayorEdad": True}, tokA)
s, st1 = call("GET", "/products/2"); check("Reserva descuenta stock", st1["stock"] == st - 3)
s, _ = call("PATCH", f"/orders/{o2['id']}/cancel", {"motivo": "prueba"}, tokA); check("Anular pedido -> 200", s == 200)
s, st2 = call("GET", "/products/2"); check("Anulación recupera stock", st2["stock"] == st)
# 7 GraphQL
def gql(q, tok): return call("POST", "/graphql", {"query": q}, tok)
s, r = gql("{ resumenPedido(id:%d){ referencia total items{ cantidad producto{ nombre } } } }" % oid, tokA)
check("GraphQL resumenPedido agrega Orders+Inventory", s == 200 and r.get("data", {}).get("resumenPedido") and not r.get("errors"), f"({r})")
s, r = gql("{ resumenPedido(id:%d){ idCliente } }" % oid, tokA); check("GraphQL: campo idCliente denegado a CLIENTE", bool(r.get("errors")))
s, r = gql("{ resumenPedido(id:%d){ referencia } }" % oid, tokB); check("GraphQL: pedido ajeno -> null", s == 200 and r["data"]["resumenPedido"] is None)
deep = "{ resumenPedido(id:1){ items{ producto{ nombre " + "}"*0
s, r = gql("{ catalogo{ nodes{ id } } }", None); check("GraphQL sin token -> 401", s == 401)
bomb = "{ a:catalogo(first:20){nodes{id}} " + " ".join(f"b{i}:catalogo(first:20){{nodes{{id}}}}" for i in range(30)) + " }"
s, r = gql(bomb, tokA); check("GraphQL rechaza consulta de costo excesivo", bool(r and r.get("errors")))
s, r = gql("{ catalogo(first:500){ nodes{ id } } }", tokA); check("GraphQL limita tamaño de página", bool(r and r.get("errors")))
# 8 Roles
s, _ = call("GET", "/dispatch-orders", token=tokA); check("CLIENTE no accede a despacho -> 403", s == 403)
s, _ = call("POST", "/products", {"id": 99, "nombre": "x", "categoria": "x", "precio": 1, "stock": 1}, tokA); check("CLIENTE no crea productos -> 403", s == 403)
# 9 Despacho con edad
s, r = call("POST", "/auth/login", {"correo": "despacho@craftbeer.cl", "password": os.environ.get("SEED_ADMIN_PWD", "")}); tokD = r.get("token") if r else None
if tokD:
    s, q = call("GET", "/dispatch-orders", token=tokD); check("DESPACHO ve cola", s == 200)
    did = next((x["id"] for x in q if x["idPedido"] == oid), None)
    call("PATCH", f"/dispatch-orders/{did}/status", {"estado": "EN_PREPARACION"}, tokD); call("PATCH", f"/dispatch-orders/{did}/status", {"estado": "EN_RUTA"}, tokD)
    s, _ = call("PATCH", f"/dispatch-orders/{did}/status", {"estado": "ENTREGADO"}, tokD); check("Entrega sin verificar edad -> 422", s == 422)
    s, _ = call("PATCH", f"/dispatch-orders/{did}/status", {"estado": "ENTREGADO", "edadVerificada": True}, tokD); check("Entrega con edad verificada -> 200", s == 200)

ok = sum(results); total = len(results)
out.append(f"RESULTADO: {ok}/{total} pruebas OK  ({datetime.datetime.now().isoformat(timespec='seconds')})")
print(out[-1]); open("evidencia_pruebas.txt", "w").write("\n".join(out))
sys.exit(0 if ok == total else 1)
