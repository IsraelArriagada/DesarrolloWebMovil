"""
API GATEWAY — Craft & Beer (Semana 7)
Único punto de entrada para el frontend. Puerto 8000.
Reenvía a los microservicios y además "orquesta" la creación de pedidos:
revisa el catálogo, descuenta stock y recién ahí guarda el pedido.

    uvicorn gateway:app --port 8000 --reload
"""
import asyncio
import os
from typing import Any, Optional

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

CATALOGO_URL = os.getenv("CATALOGO_URL", "http://127.0.0.1:8001")
PEDIDOS_URL = os.getenv("PEDIDOS_URL", "http://127.0.0.1:8002")
TIMEOUT = 5.0

app = FastAPI(title="Gateway Craft & Beer", version="1.0.0")

# El frontend corre en otro puerto (ej. Live Server en 5500), por eso CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ORIGENES_PERMITIDOS", "http://127.0.0.1:5500,http://localhost:5500").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


async def llamar(base: str, metodo: str, ruta: str, *, json: Any = None, params: Optional[dict] = None) -> Any:
    """Hace la llamada al microservicio y traduce sus errores a errores del gateway."""
    try:
        async with httpx.AsyncClient(base_url=base, timeout=TIMEOUT) as cliente:
            r = await cliente.request(metodo, ruta, json=json, params=params)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail=f"{base} tardó demasiado en responder")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail=f"Servicio no disponible: {base}")

    if r.status_code >= 400:
        # Paso el error tal cual (404, 409, 422...) para que el frontend sepa qué pasó
        try:
            detalle = r.json().get("detail", r.text)
        except ValueError:
            detalle = r.text
        raise HTTPException(status_code=r.status_code, detail=detalle)
    return r.json()


def sin_nulos(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


# ---------- Estado ----------

@app.get("/")
def inicio():
    return {"gateway": "Craft & Beer", "rutas": ["/health", "/api/cervezas", "/api/pedidos", "/api/resumen"]}


@app.get("/health")
async def health():
    async def revisar(nombre: str, url: str):
        try:
            await llamar(url, "GET", "/health")
            return nombre, "ok"
        except HTTPException:
            return nombre, "caído"

    resultados = dict(await asyncio.gather(revisar("catalogo", CATALOGO_URL), revisar("pedidos", PEDIDOS_URL)))
    return {"gateway": "ok", "servicios": resultados}


# ---------- Catálogo (pasa directo) ----------

@app.get("/api/cervezas")
async def listar_cervezas(estilo: Optional[str] = None, con_stock: bool = False):
    return await llamar(CATALOGO_URL, "GET", "/cervezas", params=sin_nulos({"estilo": estilo, "con_stock": con_stock}))


@app.get("/api/cervezas/{cerveza_id}")
async def obtener_cerveza(cerveza_id: int):
    return await llamar(CATALOGO_URL, "GET", f"/cervezas/{cerveza_id}")


@app.post("/api/cervezas", status_code=201)
async def crear_cerveza(request: Request):
    return await llamar(CATALOGO_URL, "POST", "/cervezas", json=await request.json())


@app.put("/api/cervezas/{cerveza_id}")
async def actualizar_cerveza(cerveza_id: int, request: Request):
    return await llamar(CATALOGO_URL, "PUT", f"/cervezas/{cerveza_id}", json=await request.json())


@app.delete("/api/cervezas/{cerveza_id}")
async def eliminar_cerveza(cerveza_id: int):
    return await llamar(CATALOGO_URL, "DELETE", f"/cervezas/{cerveza_id}")


# ---------- Pedidos (con orquestación) ----------

class ItemCarrito(BaseModel):
    cerveza_id: int
    cantidad: int = Field(..., gt=0, le=48)


class PedidoDesdeCarrito(BaseModel):
    cliente: str = Field(..., min_length=2)
    direccion: str = Field(..., min_length=5)
    items: list[ItemCarrito] = Field(..., min_length=1)


class CambioEstado(BaseModel):
    estado: str


@app.get("/api/pedidos")
async def listar_pedidos(estado: Optional[str] = None):
    return await llamar(PEDIDOS_URL, "GET", "/pedidos", params=sin_nulos({"estado": estado}))


@app.get("/api/pedidos/{pedido_id}")
async def obtener_pedido(pedido_id: int):
    return await llamar(PEDIDOS_URL, "GET", f"/pedidos/{pedido_id}")


@app.post("/api/pedidos", status_code=201)
async def crear_pedido(pedido: PedidoDesdeCarrito):
    """
    1. Trae cada cerveza del catálogo (precio real, no el que mande el navegador)
    2. Descuenta el stock
    3. Guarda el pedido
    Si algo falla a la mitad, devuelve el stock que ya se había descontado.
    """
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
        # Compensación: se devuelve lo descontado
        for cerveza_id, cantidad in descontados:
            try:
                await llamar(CATALOGO_URL, "PATCH", f"/cervezas/{cerveza_id}/stock", json={"cantidad": cantidad})
            except HTTPException:
                pass
        raise


@app.patch("/api/pedidos/{pedido_id}/estado")
async def cambiar_estado(pedido_id: int, cambio: CambioEstado):
    pedido = await llamar(PEDIDOS_URL, "PATCH", f"/pedidos/{pedido_id}/estado", json=cambio.model_dump())
    # Si se canceló, las botellas vuelven al stock
    if cambio.estado == "cancelado":
        for item in pedido["items"]:
            await llamar(CATALOGO_URL, "PATCH", f"/cervezas/{item['cerveza_id']}/stock", json={"cantidad": item["cantidad"]})
    return pedido


# ---------- Datos combinados de los 2 servicios ----------

@app.get("/api/resumen")
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
