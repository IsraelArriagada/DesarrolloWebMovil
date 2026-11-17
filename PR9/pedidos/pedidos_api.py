"""
Microservicio PEDIDOS — Craft & Beer (PR 9)
Guarda los pedidos de los clientes. Puerto 8002.
No conoce el catálogo: el gateway es el que valida precios y stock antes de llamar aquí.

    uvicorn pedidos_api:app --port 8002 --reload
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from secretos import iguales, secreto

app = FastAPI(title="Pedidos Craft & Beer", version="1.0.0")

# ---------- Seguridad ----------
# Solo el gateway conoce este token. Si alguien llama directo al servicio
# (saltándose el gateway) recibe 401.
TOKEN_SERVICIO = secreto("TOKEN_PEDIDOS")
bearer = HTTPBearer(auto_error=False)


def solo_gateway(cred: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if cred is None or not iguales(cred.credentials, TOKEN_SERVICIO):
        raise HTTPException(
            status_code=401,
            detail="Token de servicio inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Todas las rutas del router exigen el token; /health queda público
router = APIRouter(dependencies=[Depends(solo_gateway)])

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
    correo: str  # dueño del pedido (viene de la sesión, no del formulario)
    direccion: str = Field(..., min_length=5)
    items: list[Item] = Field(..., min_length=1)


class CambioEstado(BaseModel):
    estado: Estado


pedidos: dict[int, dict] = {}
siguiente_id = 1001  # que los números de pedido se vean "reales"


@app.get("/health")  # público, sin datos sensibles
def health():
    return {"servicio": "pedidos", "estado": "ok"}


@router.get("/pedidos")
def listar(estado: Optional[Estado] = None, correo: Optional[str] = None):
    lista = list(pedidos.values())
    if correo:
        lista = [p for p in lista if p["correo"] == correo.lower()]
    if estado:
        lista = [p for p in lista if p["estado"] == estado]
    return lista


@router.get("/pedidos/{pedido_id}")
def obtener(pedido_id: int):
    if pedido_id not in pedidos:
        raise HTTPException(status_code=404, detail=f"No existe el pedido #{pedido_id}")
    return pedidos[pedido_id]


@router.post("/pedidos", status_code=status.HTTP_201_CREATED)
def crear(datos: PedidoNuevo):
    global siguiente_id
    subtotal = sum(i.precio_unitario * i.cantidad for i in datos.items)
    envio = 0 if subtotal >= ENVIO_GRATIS_DESDE else ENVIO

    pedido = {
        "id": siguiente_id,
        **datos.model_dump(),
        "correo": datos.correo.lower(),
        "subtotal": subtotal,
        "envio": envio,
        "total": subtotal + envio,
        "estado": Estado.recibido,
        "creado": datetime.now(timezone.utc).isoformat(),
    }
    pedidos[siguiente_id] = pedido
    siguiente_id += 1
    return pedido


@router.patch("/pedidos/{pedido_id}/estado")
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


@router.delete("/pedidos/{pedido_id}")
def eliminar(pedido_id: int):
    obtener(pedido_id)
    del pedidos[pedido_id]
    return {"mensaje": f"Pedido #{pedido_id} eliminado"}


app.include_router(router)
