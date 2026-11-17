"""
API GATEWAY — Craft & Beer (Semana 9: autenticación con cookies)

Qué cambió respecto a la semana 8:
  * Ya no hay API keys en el navegador. El usuario inicia sesión con correo y
    contraseña; el gateway le deja una cookie HttpOnly con el token de sesión.
    JavaScript no puede leer esa cookie, así que un XSS no puede robarla.
  * Roles: "cliente" (catálogo, crear pedidos, ver SUS pedidos) y "admin" (todo).
  * Protección CSRF: cookie SameSite=Lax + se revisa el header Origin en
    peticiones que modifican datos.
  * Nuevo microservicio auth (puerto 8003).

    uvicorn gateway:app --port 8000 --reload
"""
import asyncio
import os
import time
from collections import defaultdict, deque
from typing import Any, Optional

import httpx
from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from secretos import secreto

CATALOGO_URL = os.getenv("CATALOGO_URL", "http://127.0.0.1:8001")
PEDIDOS_URL = os.getenv("PEDIDOS_URL", "http://127.0.0.1:8002")
AUTH_URL = os.getenv("AUTH_URL", "http://127.0.0.1:8003")
TIMEOUT = 5.0

TOKENS = {
    CATALOGO_URL: secreto("TOKEN_CATALOGO"),
    PEDIDOS_URL: secreto("TOKEN_PEDIDOS"),
    AUTH_URL: secreto("TOKEN_AUTH"),
}

COOKIE = "cb_sesion"
# En producción (https) debe ir en true. En localhost con http tiene que ser false.
COOKIE_SEGURA = os.getenv("COOKIE_SEGURA", "false").lower() == "true"
ORIGENES = [o.strip() for o in os.getenv(
    "ORIGENES_PERMITIDOS",
    "http://127.0.0.1:5500,http://localhost:5500,http://127.0.0.1:8080,http://localhost:8080",
).split(",")]
LIMITE_PETICIONES = int(os.getenv("LIMITE_PETICIONES", "120"))

app = FastAPI(title="Gateway Craft & Beer (con sesiones)", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES,
    allow_credentials=True,  # necesario para que el navegador mande la cookie
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)


# ---------- Middlewares ----------

_historial: dict[str, deque] = defaultdict(deque)
METODOS_QUE_MODIFICAN = {"POST", "PUT", "PATCH", "DELETE"}


@app.middleware("http")
async def seguridad(request: Request, call_next):
    # 1) Rate limit por IP
    ip = request.client.host if request.client else "?"
    ahora = time.monotonic()
    cola = _historial[ip]
    while cola and ahora - cola[0] > 60:
        cola.popleft()
    if len(cola) >= LIMITE_PETICIONES:
        return JSONResponse({"detail": "Demasiadas peticiones, espera un minuto 🍺"}, status_code=429)
    cola.append(ahora)

    # 2) CSRF: si una página de otro sitio intenta un POST con la cookie del usuario,
    #    el navegador manda su Origin y aquí se rechaza.
    origen = request.headers.get("origin")
    if request.method in METODOS_QUE_MODIFICAN and origen and origen not in ORIGENES:
        return JSONResponse({"detail": "Origen no permitido"}, status_code=403)

    respuesta = await call_next(request)
    respuesta.headers["X-Content-Type-Options"] = "nosniff"
    respuesta.headers["X-Frame-Options"] = "DENY"
    respuesta.headers["Referrer-Policy"] = "no-referrer"
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


# ---------- Llamadas internas ----------

async def llamar(base: str, metodo: str, ruta: str, *, json: Any = None,
                 params: Optional[dict] = None, headers: Optional[dict] = None) -> Any:
    h = {"Authorization": f"Bearer {TOKENS[base]}", **(headers or {})}
    try:
        async with httpx.AsyncClient(base_url=base, timeout=TIMEOUT) as cliente:
            r = await cliente.request(metodo, ruta, json=json, params=params, headers=h)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Un servicio tardó demasiado en responder")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Servicio no disponible")

    if r.status_code >= 400:
        try:
            detalle = r.json().get("detail", "Error en servicio interno")
        except ValueError:
            detalle = "Error en servicio interno"
        if r.status_code == 401 and base != AUTH_URL:
            raise HTTPException(status_code=502, detail="El gateway no está autorizado ante un servicio interno")
        raise HTTPException(status_code=r.status_code, detail=detalle)
    return r.json()


def sin_nulos(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


# ---------- Sesión ----------

async def usuario_actual(cb_sesion: Optional[str] = Cookie(None)) -> dict:
    if not cb_sesion:
        raise HTTPException(status_code=401, detail="Inicia sesión para continuar")
    return await llamar(AUTH_URL, "GET", "/sesion", headers={"X-Sesion": cb_sesion})


def requiere(*roles: str):
    async def verificar(usuario: dict = Depends(usuario_actual)) -> dict:
        if usuario["rol"] not in roles:
            raise HTTPException(status_code=403, detail="No tienes permiso para esto")
        return usuario
    return verificar


cliente_o_admin = requiere("cliente", "admin")
solo_admin = requiere("admin")


class Registro(BaseModel):
    nombre: str
    correo: str
    password: str


class Login(BaseModel):
    correo: str
    password: str


@app.post("/auth/registro", status_code=201)
async def registro(datos: Registro):
    return await llamar(AUTH_URL, "POST", "/registro", json=datos.model_dump())


@app.post("/auth/login")
async def login(datos: Login, response: Response):
    sesion = await llamar(AUTH_URL, "POST", "/login", json=datos.model_dump())
    response.set_cookie(
        key=COOKIE,
        value=sesion["token"],
        max_age=sesion["expira_en"],
        httponly=True,       # JS no la puede leer
        secure=COOKIE_SEGURA,  # solo por https en producción
        samesite="lax",      # no viaja en POST desde otros sitios
        path="/",
    )
    # El token NO se devuelve en el JSON: solo vive en la cookie
    return {"usuario": sesion["usuario"]}


@app.get("/auth/me")
async def yo(usuario: dict = Depends(usuario_actual)):
    return usuario


@app.post("/auth/logout")
async def logout(response: Response, cb_sesion: Optional[str] = Cookie(None)):
    if cb_sesion:
        try:
            await llamar(AUTH_URL, "POST", "/logout", headers={"X-Sesion": cb_sesion})
        except HTTPException:
            pass
    response.delete_cookie(COOKIE, path="/")
    return {"mensaje": "Sesión cerrada. ¡Salud!"}


# ---------- Público ----------

@app.get("/health")
async def health():
    async def revisar(url: str):
        try:
            async with httpx.AsyncClient(timeout=2) as c:
                return "ok" if (await c.get(f"{url}/health")).status_code == 200 else "error"
        except httpx.RequestError:
            return "caído"

    cat, ped, aut = await asyncio.gather(revisar(CATALOGO_URL), revisar(PEDIDOS_URL), revisar(AUTH_URL))
    return {"gateway": "ok", "servicios": {"catalogo": cat, "pedidos": ped, "auth": aut}}


# El catálogo se puede ver sin iniciar sesión (es una tienda)
@app.get("/api/cervezas")
async def listar_cervezas(estilo: Optional[str] = None, con_stock: bool = False):
    return await llamar(CATALOGO_URL, "GET", "/cervezas", params=sin_nulos({"estilo": estilo, "con_stock": con_stock}))


@app.get("/api/cervezas/{cerveza_id}")
async def obtener_cerveza(cerveza_id: int):
    return await llamar(CATALOGO_URL, "GET", f"/cervezas/{cerveza_id}")


# ---------- Admin: catálogo ----------

@app.post("/api/cervezas", status_code=201, dependencies=[Depends(solo_admin)])
async def crear_cerveza(request: Request):
    return await llamar(CATALOGO_URL, "POST", "/cervezas", json=await request.json())


@app.put("/api/cervezas/{cerveza_id}", dependencies=[Depends(solo_admin)])
async def actualizar_cerveza(cerveza_id: int, request: Request):
    return await llamar(CATALOGO_URL, "PUT", f"/cervezas/{cerveza_id}", json=await request.json())


@app.delete("/api/cervezas/{cerveza_id}", dependencies=[Depends(solo_admin)])
async def eliminar_cerveza(cerveza_id: int):
    return await llamar(CATALOGO_URL, "DELETE", f"/cervezas/{cerveza_id}")


# ---------- Pedidos ----------

class ItemCarrito(BaseModel):
    cerveza_id: int
    cantidad: int = Field(..., gt=0, le=48)


class PedidoDesdeCarrito(BaseModel):
    direccion: str = Field(..., min_length=5, max_length=150)
    items: list[ItemCarrito] = Field(..., min_length=1, max_length=20)


class CambioEstado(BaseModel):
    estado: str


@app.get("/api/mis-pedidos")
async def mis_pedidos(usuario: dict = Depends(cliente_o_admin)):
    return await llamar(PEDIDOS_URL, "GET", "/pedidos", params={"correo": usuario["correo"]})


@app.get("/api/pedidos", dependencies=[Depends(solo_admin)])
async def listar_pedidos(estado: Optional[str] = None):
    return await llamar(PEDIDOS_URL, "GET", "/pedidos", params=sin_nulos({"estado": estado}))


@app.get("/api/pedidos/{pedido_id}")
async def obtener_pedido(pedido_id: int, usuario: dict = Depends(cliente_o_admin)):
    pedido = await llamar(PEDIDOS_URL, "GET", f"/pedidos/{pedido_id}")
    # Un cliente solo puede ver sus propios pedidos
    if usuario["rol"] != "admin" and pedido["correo"] != usuario["correo"]:
        raise HTTPException(status_code=404, detail=f"No existe el pedido #{pedido_id}")
    return pedido


@app.post("/api/pedidos", status_code=201)
async def crear_pedido(pedido: PedidoDesdeCarrito, usuario: dict = Depends(cliente_o_admin)):
    cervezas = await asyncio.gather(
        *(llamar(CATALOGO_URL, "GET", f"/cervezas/{i.cerveza_id}") for i in pedido.items)
    )
    descontados: list[tuple[int, int]] = []
    try:
        for item in pedido.items:
            await llamar(CATALOGO_URL, "PATCH", f"/cervezas/{item.cerveza_id}/stock", json={"cantidad": -item.cantidad})
            descontados.append((item.cerveza_id, item.cantidad))

        items = [
            {"cerveza_id": c["id"], "nombre": c["nombre"], "precio_unitario": c["precio"], "cantidad": i.cantidad}
            for c, i in zip(cervezas, pedido.items)
        ]
        return await llamar(PEDIDOS_URL, "POST", "/pedidos", json={
            "cliente": usuario["nombre"],
            "correo": usuario["correo"],  # sale de la sesión: no se puede falsificar
            "direccion": pedido.direccion,
            "items": items,
        })
    except HTTPException:
        for cerveza_id, cantidad in descontados:
            try:
                await llamar(CATALOGO_URL, "PATCH", f"/cervezas/{cerveza_id}/stock", json={"cantidad": cantidad})
            except HTTPException:
                pass
        raise


@app.patch("/api/pedidos/{pedido_id}/estado", dependencies=[Depends(solo_admin)])
async def cambiar_estado(pedido_id: int, cambio: CambioEstado):
    pedido = await llamar(PEDIDOS_URL, "PATCH", f"/pedidos/{pedido_id}/estado", json=cambio.model_dump())
    if cambio.estado == "cancelado":
        for item in pedido["items"]:
            await llamar(CATALOGO_URL, "PATCH", f"/cervezas/{item['cerveza_id']}/stock", json={"cantidad": item["cantidad"]})
    return pedido


@app.get("/api/resumen", dependencies=[Depends(solo_admin)])
async def resumen():
    cervezas, pedidos, clientes = await asyncio.gather(
        llamar(CATALOGO_URL, "GET", "/cervezas"),
        llamar(PEDIDOS_URL, "GET", "/pedidos"),
        llamar(AUTH_URL, "GET", "/usuarios", params={"rol": "cliente"}),
    )
    validos = [p for p in pedidos if p["estado"] != "cancelado"]
    return {
        "cervezas_en_catalogo": len(cervezas),
        "sin_stock": [c["nombre"] for c in cervezas if c["stock"] == 0],
        "stock_bajo": [c["nombre"] for c in cervezas if 0 < c["stock"] <= 5],
        "pedidos": len(pedidos),
        "clientes": len(clientes),
        "ventas_totales": sum(p["total"] for p in validos),
    }
