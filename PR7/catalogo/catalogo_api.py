"""
Microservicio CATÁLOGO — Craft & Beer (PR 7)
Maneja las cervezas y su stock. Puerto 8001.

    uvicorn catalogo_api:app --port 8001 --reload
"""
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(title="Catálogo Craft & Beer", version="1.0.0")

# "Base de datos" en memoria (en el PR 5/6 esto estaba en Mongo)
cervezas: dict[int, dict] = {
    1: {"id": 1, "nombre": "IPA Tropical",         "estilo": "IPA",     "precio": 3990, "stock": 48},
    2: {"id": 2, "nombre": "Session IPA",          "estilo": "IPA",     "precio": 3790, "stock": 30},
    3: {"id": 3, "nombre": "Imperial Stout",       "estilo": "STOUT",   "precio": 4490, "stock": 12},
    4: {"id": 4, "nombre": "Porter de Café",       "estilo": "PORTER",  "precio": 4290, "stock": 4},
    5: {"id": 5, "nombre": "Golden Lager",         "estilo": "LAGER",   "precio": 3490, "stock": 60},
    6: {"id": 6, "nombre": "Wheat Ale de Naranja", "estilo": "WHEAT",   "precio": 3990, "stock": 22},
    7: {"id": 7, "nombre": "Red Ale Ámbar",        "estilo": "RED_ALE", "precio": 3890, "stock": 3},
}
siguiente_id = 8


class CervezaNueva(BaseModel):
    nombre: str = Field(..., min_length=2)
    estilo: str = Field(..., examples=["IPA"])
    precio: int = Field(..., gt=0)
    stock: int = Field(0, ge=0)


class CervezaCambios(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2)
    estilo: Optional[str] = None
    precio: Optional[int] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)


class MovimientoStock(BaseModel):
    cantidad: int  # negativo = venta, positivo = reposición


def buscar(cerveza_id: int) -> dict:
    if cerveza_id not in cervezas:
        raise HTTPException(status_code=404, detail=f"No existe la cerveza {cerveza_id}")
    return cervezas[cerveza_id]


@app.get("/health")
def health():
    return {"servicio": "catalogo", "estado": "ok", "cervezas": len(cervezas)}


@app.get("/cervezas")
def listar(estilo: Optional[str] = None, con_stock: bool = False):
    lista = list(cervezas.values())
    if estilo:
        lista = [c for c in lista if c["estilo"].lower() == estilo.lower()]
    if con_stock:
        lista = [c for c in lista if c["stock"] > 0]
    return lista


@app.get("/cervezas/{cerveza_id}")
def obtener(cerveza_id: int):
    return buscar(cerveza_id)


@app.post("/cervezas", status_code=status.HTTP_201_CREATED)
def crear(datos: CervezaNueva):
    global siguiente_id
    if any(c["nombre"].lower() == datos.nombre.lower() for c in cervezas.values()):
        raise HTTPException(status_code=409, detail="Ya existe una cerveza con ese nombre")
    nueva = {"id": siguiente_id, **datos.model_dump()}
    cervezas[siguiente_id] = nueva
    siguiente_id += 1
    return nueva


@app.put("/cervezas/{cerveza_id}")
def actualizar(cerveza_id: int, cambios: CervezaCambios):
    cerveza = buscar(cerveza_id)
    cerveza.update(cambios.model_dump(exclude_none=True))
    return cerveza


@app.patch("/cervezas/{cerveza_id}/stock")
def mover_stock(cerveza_id: int, mov: MovimientoStock):
    cerveza = buscar(cerveza_id)
    if cerveza["stock"] + mov.cantidad < 0:
        raise HTTPException(
            status_code=409,
            detail=f"Stock insuficiente de {cerveza['nombre']}: quedan {cerveza['stock']}",
        )
    cerveza["stock"] += mov.cantidad
    return cerveza


@app.delete("/cervezas/{cerveza_id}")
def eliminar(cerveza_id: int):
    cerveza = buscar(cerveza_id)
    del cervezas[cerveza_id]
    return {"mensaje": f"{cerveza['nombre']} eliminada del catálogo"}
