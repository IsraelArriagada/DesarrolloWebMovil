"""
API GATEWAY — Craft & Beer (PR 8: seguridad)

Qué cambió respecto a el PR 7:
  * Los clientes se identifican con una API key en el header X-API-Key.
    Hay 2 roles: "tienda" (ver catálogo y crear pedidos) y "admin" (todo lo demás).
  * El gateway habla con cada microservicio usando un token Bearer distinto.
  * Todos los secretos se leen desde Vault (o .env en desarrollo).
  * Límite de peticiones por IP, headers de seguridad y CORS cerrado.

    uvicorn gateway:app --port 8000 --reload
"""
import asyncio
import os
import time
from collections import defaultdict, deque
from typing import Any, Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from secretos import iguales, secreto

CATALOGO_URL = os.getenv("CATALOGO_URL", "http://127.0.0.1:8001")
PEDIDOS_URL = os.getenv("PEDIDOS_URL", "http://127.0.0.1:8002")
TIMEOUT = 5.0

# Secretos (se leen una vez al arrancar; si falta alguno, el gateway no parte)
TOKEN_CATALOGO = secreto("TOKEN_CATALOGO")
TOKEN_PEDIDOS = secreto("TOKEN_PEDIDOS")
API_KEYS = {
    "tienda": secreto("API_KEY_TIENDA"),
    "admin": secreto("API_KEY_ADMIN"),
}
TOKENS = {CATALOGO_URL: TOKEN_CATALOGO, PEDIDOS_URL: TOKEN_PEDIDOS}

LIMITE_PETICIONES = int(os.getenv("LIMITE_PETICIONES", "60"))  # por minuto y por IP

app = FastAPI(title="Gateway Craft & Beer (seguro)", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ORIGENES_PERMITIDOS", "http://127.0.0.1:5500,http://localhost:5500").split(","),
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key"],
)


# ---------- Middlewares ----------

_historial: dict[str, deque] = defaultdict(deque)


@app.middleware("http")
async def limitar_y_proteger(request: Request, call_next):
    # 1) Rate limit simple: ventana deslizante de 60 s por IP
    ip = request.client.host if request.client else "desconocida"
    ahora = time.monotonic()
    cola = _historial[ip]
    while cola and ahora - cola[0] > 60:
        cola.popleft()
    if len(cola) >= LIMITE_PETICIONES:
        return JSONResponse({"detail": "Demasiadas peticiones, espera un minuto 🍺"}, status_code=429)
    cola.append(ahora)

    # 2) Headers de seguridad en todas las respuestas
    respuesta = await call_next(request)
    respuesta.headers["X-Content-Type-Options"] = "nosniff"
    respuesta.headers["X-Frame-Options"] = "DENY"
    respuesta.headers["Referrer-Policy"] = "no-referrer"
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


# ---------- Control de acceso ----------

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def rol_actual(api_key: Optional[str] = Security(api_key_header)) -> str:
    if not api_key:
        raise HTTPException(status_code=401, detail="Falta la API key (header X-API-Key)")
    for rol, clave in API_KEYS.items():
        if iguales(api_key, clave):
            return rol
    raise HTTPException(status_code=401, detail="API key inválida")


def requiere(*roles: str):
    """Uso: dependencies=[Depends(requiere("admin"))]"""
    def verificar(rol: str = Depends(rol_actual)) -> str:
        if rol not in roles:
            raise HTTPException(status_code=403, detail=f"Tu rol ({rol}) no puede hacer esto")
        return rol
    return verificar


cualquiera = Depends(requiere("tienda", "admin"))
solo_admin = Depends(requiere("admin"))


# ---------- Llamadas a microservicios ----------

async def llamar(base: str, metodo: str, ruta: str, *, json: Any = None, params: Optional[dict] = None) -> Any:
    headers = {"Authorization": f"Bearer {TOKENS[base]}"}
    try:
        async with httpx.AsyncClient(base_url=base, timeout=TIMEOUT) as cliente:
            r = await cliente.request(metodo, ruta, json=json, params=params, headers=headers)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Un servicio tardó demasiado en responder")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Servicio no disponible")

    if r.status_code == 401:
        # Si el servicio rechaza al gateway es un problema de configuración, no del usuario
        raise HTTPException(status_code=502, detail="El gateway no está autorizado ante un servicio interno")
    if r.status_code >= 400:
        try:
            detalle = r.json().get("detail", "Error en servicio interno")
        except ValueError:
            detalle = "Error en servicio interno"
        raise HTTPException(status_code=r.status_code, detail=detalle)
    return r.json()


def sin_nulos(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


# ---------- Público ----------

@app.get("/health")
async def health():
    async def revisar(url: str):
        try:
            async with httpx.AsyncClient(timeout=2) as c:
                return "ok" if (await c.get(f"{url}/health")).status_code == 200 else "error"
        except httpx.RequestError:
            return "caído"

    cat, ped = await asyncio.gather(revisar(CATALOGO_URL), revisar(PEDIDOS_URL))
    return {"gateway": "ok", "servicios": {"catalogo": cat, "pedidos": ped}}


@app.get("/api/yo")
def quien_soy(rol: str = Depends(rol_actual)):
    return {"rol": rol}


# ---------- Catálogo ----------

@app.get("/api/cervezas", dependencies=[cualquiera])
async def listar_cervezas(estilo: Optional[str] = None, con_stock: bool = False):
    return await llamar(CATALOGO_URL, "GET", "/cervezas", params=sin_nulos({"estilo": estilo, "con_stock": con_stock}))


@app.get("/api/cervezas/{cerveza_id}", dependencies=[cualquiera])
async def obtener_cerveza(cerveza_id: int):
    return await llamar(CATALOGO_URL, "GET", f"/cervezas/{cerveza_id}")


@app.post("/api/cervezas", status_code=201, dependencies=[solo_admin])
async def crear_cerveza(request: Request):
    return await llamar(CATALOGO_URL, "POST", "/cervezas", json=await request.json())


@app.put("/api/cervezas/{cerveza_id}", dependencies=[solo_admin])
async def actualizar_cerveza(cerveza_id: int, request: Request):
    return await llamar(CATALOGO_URL, "PUT", f"/cervezas/{cerveza_id}", json=await request.json())


@app.delete("/api/cervezas/{cerveza_id}", dependencies=[solo_admin])
async def eliminar_cerveza(cerveza_id: int):
    return await llamar(CATALOGO_URL, "DELETE", f"/cervezas/{cerveza_id}")


# ---------- Pedidos ----------

class ItemCarrito(BaseModel):
    cerveza_id: int
    cantidad: int = Field(..., gt=0, le=48)


class PedidoDesdeCarrito(BaseModel):
    cliente: str = Field(..., min_length=2, max_length=80)
    direccion: str = Field(..., min_length=5, max_length=150)
    items: list[ItemCarrito] = Field(..., min_length=1, max_length=20)


class CambioEstado(BaseModel):
    estado: str


@app.get("/api/pedidos", dependencies=[solo_admin])
async def listar_pedidos(estado: Optional[str] = None):
    return await llamar(PEDIDOS_URL, "GET", "/pedidos", params=sin_nulos({"estado": estado}))


@app.get("/api/pedidos/{pedido_id}", dependencies=[cualquiera])
async def obtener_pedido(pedido_id: int):
    return await llamar(PEDIDOS_URL, "GET", f"/pedidos/{pedido_id}")


@app.post("/api/pedidos", status_code=201, dependencies=[cualquiera])
async def crear_pedido(pedido: PedidoDesdeCarrito):
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
        return await llamar(
            PEDIDOS_URL, "POST", "/pedidos",
            json={"cliente": pedido.cliente, "direccion": pedido.direccion, "items": items},
        )
    except HTTPException:
        for cerveza_id, cantidad in descontados:
            try:
                await llamar(CATALOGO_URL, "PATCH", f"/cervezas/{cerveza_id}/stock", json={"cantidad": cantidad})
            except HTTPException:
                pass
        raise


@app.patch("/api/pedidos/{pedido_id}/estado", dependencies=[solo_admin])
async def cambiar_estado(pedido_id: int, cambio: CambioEstado):
    pedido = await llamar(PEDIDOS_URL, "PATCH", f"/pedidos/{pedido_id}/estado", json=cambio.model_dump())
    if cambio.estado == "cancelado":
        for item in pedido["items"]:
            await llamar(CATALOGO_URL, "PATCH", f"/cervezas/{item['cerveza_id']}/stock", json={"cantidad": item["cantidad"]})
    return pedido


@app.get("/api/resumen", dependencies=[solo_admin])
async def resumen():
    cervezas, pedidos = await asyncio.gather(
        llamar(CATALOGO_URL, "GET", "/cervezas"),
        llamar(PEDIDOS_URL, "GET", "/pedidos"),
    )
    validos = [p for p in pedidos if p["estado"] != "cancelado"]
    return {
        "cervezas_en_catalogo": len(cervezas),
        "sin_stock": [c["nombre"] for c in cervezas if c["stock"] == 0],
        "stock_bajo": [c["nombre"] for c in cervezas if 0 < c["stock"] <= 5],
        "pedidos": len(pedidos),
        "ventas_totales": sum(p["total"] for p in validos),
    }
