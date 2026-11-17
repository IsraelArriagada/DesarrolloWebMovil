"""
Craft & Beer — PR 6
API REST con FastAPI + MongoDB para administrar los socios del Club Cervecero.

Correr:
    pip install -r requirements.txt
    uvicorn main:app --reload
Documentación automática en http://127.0.0.1:8000/docs
"""
import os
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from pymongo import MongoClient, ReturnDocument
from pymongo.errors import DuplicateKeyError

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
MONGO_DB = os.getenv("MONGO_DB", "craftbeer")


def conectar(cliente: Optional[MongoClient] = None):
    """Devuelve la colección de socios. Se puede pasar otro cliente (ej. en pruebas)."""
    cliente = cliente or MongoClient(MONGO_URI)
    coleccion = cliente[MONGO_DB]["socios"]
    # Un correo = un socio
    coleccion.create_index("correo", unique=True)
    return coleccion


socios = conectar()

app = FastAPI(
    title="Craft & Beer — Club Cervecero",
    description="CRUD de socios del club de suscripción mensual.",
    version="1.0.0",
)


# ---------- Modelos ----------

class Plan(str, Enum):
    lupulo = "lupulo"     # 4 cervezas
    malta = "malta"       # 6 cervezas
    barrica = "barrica"   # 10 cervezas


PRECIOS = {Plan.lupulo: 14990, Plan.malta: 24990, Plan.barrica: 39990}


class SocioNuevo(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=80, examples=["Israel Arriagada"])
    correo: EmailStr
    comuna: str = Field(..., min_length=2, examples=["Ñuñoa"])
    plan: Plan = Plan.malta
    estilos_excluidos: list[str] = Field(default_factory=list, examples=[["STOUT"]])


class SocioCambios(BaseModel):
    # Todo opcional: solo se actualiza lo que venga
    nombre: Optional[str] = Field(None, min_length=2, max_length=80)
    comuna: Optional[str] = None
    plan: Optional[Plan] = None
    estilos_excluidos: Optional[list[str]] = None
    activo: Optional[bool] = None


# ---------- Ayudantes ----------

def a_object_id(socio_id: str) -> ObjectId:
    try:
        return ObjectId(socio_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=400, detail=f"'{socio_id}' no es un id válido")


def serializar(doc: dict) -> dict:
    """Mongo guarda _id como ObjectId; para JSON lo paso a texto y agrego el precio del plan."""
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    doc["valor_mensual"] = PRECIOS[Plan(doc["plan"])]
    return doc


def buscar_o_404(socio_id: str) -> dict:
    doc = socios.find_one({"_id": a_object_id(socio_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Socio no encontrado")
    return doc


# ---------- Rutas ----------

@app.get("/", tags=["General"])
def inicio():
    return {"servicio": "Club Cervecero", "estado": "ok", "docs": "/docs"}


@app.get("/socios", tags=["Socios"])
def listar_socios(
    plan: Optional[Plan] = None,
    comuna: Optional[str] = None,
    solo_activos: bool = True,
    limite: int = Query(50, ge=1, le=200),
):
    filtro: dict = {}
    if plan:
        filtro["plan"] = plan.value
    if comuna:
        filtro["comuna"] = {"$regex": f"^{re.escape(comuna)}$", "$options": "i"}
    if solo_activos:
        filtro["activo"] = True
    return [serializar(d) for d in socios.find(filtro).sort("nombre").limit(limite)]


@app.get("/socios/resumen", tags=["Socios"])
def resumen():
    """Cuántos socios activos hay por plan y cuánto se factura al mes."""
    por_plan = {p.value: 0 for p in Plan}
    for d in socios.find({"activo": True}, {"plan": 1}):
        por_plan[d["plan"]] += 1
    ingreso = sum(PRECIOS[Plan(p)] * n for p, n in por_plan.items())
    return {"socios_activos": sum(por_plan.values()), "por_plan": por_plan, "ingreso_mensual": ingreso}


@app.get("/socios/{socio_id}", tags=["Socios"])
def obtener_socio(socio_id: str):
    return serializar(buscar_o_404(socio_id))


@app.post("/socios", status_code=status.HTTP_201_CREATED, tags=["Socios"])
def crear_socio(socio: SocioNuevo):
    doc = socio.model_dump(mode="json")
    doc["correo"] = doc["correo"].lower()
    doc["activo"] = True
    doc["fecha_ingreso"] = datetime.now(timezone.utc).isoformat()
    try:
        resultado = socios.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Ese correo ya está inscrito en el club")
    return serializar({**doc, "_id": resultado.inserted_id})


@app.put("/socios/{socio_id}", tags=["Socios"])
def actualizar_socio(socio_id: str, cambios: SocioCambios):
    datos = cambios.model_dump(mode="json", exclude_none=True)
    if not datos:
        raise HTTPException(status_code=400, detail="No enviaste nada para cambiar")
    doc = socios.find_one_and_update(
        {"_id": a_object_id(socio_id)},
        {"$set": datos},
        return_document=ReturnDocument.AFTER,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Socio no encontrado")
    return serializar(doc)


@app.delete("/socios/{socio_id}", tags=["Socios"])
def eliminar_socio(socio_id: str, definitivo: bool = False):
    """Por defecto solo da de baja (activo=false). Con ?definitivo=true borra el registro."""
    oid = a_object_id(socio_id)
    if definitivo:
        if socios.delete_one({"_id": oid}).deleted_count == 0:
            raise HTTPException(status_code=404, detail="Socio no encontrado")
        return {"mensaje": "Socio eliminado"}

    if socios.update_one({"_id": oid}, {"$set": {"activo": False}}).matched_count == 0:
        raise HTTPException(status_code=404, detail="Socio no encontrado")
    return {"mensaje": "Socio dado de baja. Puedes reactivarlo con PUT activo=true"}
