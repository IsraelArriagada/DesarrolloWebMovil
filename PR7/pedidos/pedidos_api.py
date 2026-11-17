"""
Microservicio PEDIDOS — Craft & Beer (PR 7)
Guarda los pedidos de los clientes. Puerto 8002.
No conoce el catálogo: el gateway es el que valida precios y stock antes de llamar aquí.

    uvicorn pedidos_api:app --port 8002 --reload
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(title="Pedidos Craft & Beer", version="1.0.0")

ENVIO = 2990
ENVIO_GRATIS_DESDE = 25000


class Estado(str, Enum):
    recibido = "recibido"
    preparando = "preparando"
    en_camino = "en_camino"
    entregado = "entregado"
    cancelado = "cancelado"


# Desde cada estado solo se puede pasar a estos
TRANSICIONES = {
    Estado.recibido:   {Estado.preparando, Estado.cancelado},
    Estado.preparando: {Estado.en_camino, Estado.cancelado},
    Estado.en_camino:  {Estado.entregado},
    Estado.entregado:  set(),
    Estado.cancelado:  set(),
}


class Item(BaseModel):
    cerveza_id: int
    nombre: str
    precio_unitario: int = Field(..., gt=0)
    cantidad: int = Field(..., gt=0, le=48)


class PedidoNuevo(BaseModel):
    cliente: str = Field(..., min_length=2)
    direccion: str = Field(..., min_length=5)
    items: list[Item] = Field(..., min_length=1)


class CambioEstado(BaseModel):
    estado: Estado


pedidos: dict[int, dict] = {}
siguiente_id = 1001  # que los números de pedido se vean "reales"


@app.get("/health")
def health():
    return {"servicio": "pedidos", "estado": "ok", "pedidos": len(pedidos)}


@app.get("/pedidos")
def listar(estado: Optional[Estado] = None):
    lista = list(pedidos.values())
    if estado:
        lista = [p for p in lista if p["estado"] == estado]
    return lista


@app.get("/pedidos/{pedido_id}")
def obtener(pedido_id: int):
    if pedido_id not in pedidos:
        raise HTTPException(status_code=404, detail=f"No existe el pedido #{pedido_id}")
    return pedidos[pedido_id]


@app.post("/pedidos", status_code=status.HTTP_201_CREATED)
def crear(datos: PedidoNuevo):
    global siguiente_id
    subtotal = sum(i.precio_unitario * i.cantidad for i in datos.items)
    envio = 0 if subtotal >= ENVIO_GRATIS_DESDE else ENVIO

    pedido = {
        "id": siguiente_id,
        **datos.model_dump(),
        "subtotal": subtotal,
        "envio": envio,
        "total": subtotal + envio,
        "estado": Estado.recibido,
        "creado": datetime.now(timezone.utc).isoformat(),
    }
    pedidos[siguiente_id] = pedido
    siguiente_id += 1
    return pedido


@app.patch("/pedidos/{pedido_id}/estado")
def cambiar_estado(pedido_id: int, cambio: CambioEstado):
    pedido = obtener(pedido_id)
    actual = Estado(pedido["estado"])
    if cambio.estado not in TRANSICIONES[actual]:
        raise HTTPException(
            status_code=409,
            detail=f"No se puede pasar de '{actual.value}' a '{cambio.estado.value}'",
        )
    pedido["estado"] = cambio.estado
    return pedido


@app.delete("/pedidos/{pedido_id}")
def eliminar(pedido_id: int):
    obtener(pedido_id)
    del pedidos[pedido_id]
    return {"mensaje": f"Pedido #{pedido_id} eliminado"}
