"""
Microservicio AUTH — Craft & Beer (PR 9)
Registra usuarios, valida contraseñas y maneja sesiones. Puerto 8003.

  * Contraseñas guardadas con PBKDF2-SHA256 + sal aleatoria (nunca en texto plano).
  * La sesión es un token aleatorio opaco que el gateway guarda en una cookie HttpOnly.
  * Bloqueo de 5 minutos después de 5 intentos fallidos.
  * Igual que los otros servicios, solo acepta llamadas del gateway (token Bearer).

    uvicorn auth_service:app --port 8003 --reload
"""
import hashlib
import hmac
import os
import secrets
import time
from typing import Literal

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

from secretos import iguales, secreto

DURACION_SESION = int(os.getenv("DURACION_SESION", str(60 * 60 * 8)))  # 8 horas
MAX_INTENTOS = 5
BLOQUEO_SEGUNDOS = 5 * 60
ITERACIONES = 210_000

app = FastAPI(title="Auth Craft & Beer", version="1.0.0")

TOKEN_SERVICIO = secreto("TOKEN_AUTH")
bearer = HTTPBearer(auto_error=False)


def solo_gateway(cred: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if cred is None or not iguales(cred.credentials, TOKEN_SERVICIO):
        raise HTTPException(status_code=401, detail="Token de servicio inválido")


router = APIRouter(dependencies=[Depends(solo_gateway)])


# ---------- Contraseñas ----------

def hashear(password: str, sal: bytes | None = None) -> str:
    sal = sal or secrets.token_bytes(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), sal, ITERACIONES)
    return f"pbkdf2${ITERACIONES}${sal.hex()}${h.hex()}"


def verificar(password: str, guardado: str) -> bool:
    _, iteraciones, sal_hex, hash_hex = guardado.split("$")
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(sal_hex), int(iteraciones))
    return hmac.compare_digest(h.hex(), hash_hex)


# ---------- "Base de datos" en memoria ----------

usuarios: dict[str, dict] = {}       # correo -> usuario
sesiones: dict[str, dict] = {}       # hash del token -> sesión
intentos: dict[str, list[float]] = {}  # correo -> tiempos de intentos fallidos

# Hash falso para que el login tarde lo mismo exista o no el correo
_HASH_FALSO = hashear(secrets.token_urlsafe(16))


def crear_usuario(nombre: str, correo: str, password: str, rol: str = "cliente") -> dict:
    usuario = {"nombre": nombre, "correo": correo.lower(), "rol": rol, "password": hashear(password)}
    usuarios[usuario["correo"]] = usuario
    return usuario


# Admin inicial: la contraseña viene de Vault / .env
crear_usuario("Administración", os.getenv("ADMIN_CORREO", "admin@craftandbeer.cl"), secreto("ADMIN_PASSWORD"), "admin")


def publico(u: dict) -> dict:
    return {"nombre": u["nombre"], "correo": u["correo"], "rol": u["rol"]}


def hash_token(token: str) -> str:
    # En memoria guardo el hash del token, no el token: si se filtra el dict, no sirve
    return hashlib.sha256(token.encode()).hexdigest()


# ---------- Modelos ----------

class Registro(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=60)
    correo: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class Login(BaseModel):
    correo: EmailStr
    password: str = Field(..., max_length=128)


class Sesion(BaseModel):
    token: str
    expira_en: int
    usuario: dict


# ---------- Rutas ----------

@app.get("/health")
def health():
    return {"servicio": "auth", "estado": "ok"}


@router.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(datos: Registro):
    if datos.correo.lower() in usuarios:
        raise HTTPException(status_code=409, detail="Ese correo ya tiene cuenta")
    if datos.password.lower() in {"12345678", "password", "contraseña", "cerveza123"}:
        raise HTTPException(status_code=422, detail="Esa contraseña es demasiado fácil 😅")
    return publico(crear_usuario(datos.nombre, datos.correo, datos.password))


@router.post("/login", response_model=Sesion)
def login(datos: Login):
    correo = datos.correo.lower()
    ahora = time.time()

    recientes = [t for t in intentos.get(correo, []) if ahora - t < BLOQUEO_SEGUNDOS]
    intentos[correo] = recientes
    if len(recientes) >= MAX_INTENTOS:
        espera = int(BLOQUEO_SEGUNDOS - (ahora - recientes[0]))
        raise HTTPException(status_code=429, detail=f"Demasiados intentos. Prueba en {espera // 60 + 1} min.")

    usuario = usuarios.get(correo)
    ok = verificar(datos.password, usuario["password"] if usuario else _HASH_FALSO)
    if not (usuario and ok):
        intentos[correo].append(ahora)
        # Mismo mensaje para correo inexistente y clave mala (no revelar quién tiene cuenta)
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")

    intentos.pop(correo, None)
    token = secrets.token_urlsafe(32)
    sesiones[hash_token(token)] = {"correo": correo, "expira": ahora + DURACION_SESION}
    return {"token": token, "expira_en": DURACION_SESION, "usuario": publico(usuario)}


@router.get("/sesion")
def ver_sesion(x_sesion: str = Header(..., alias="X-Sesion")):
    """El gateway pregunta: ¿este token de cookie es válido? ¿de quién es?"""
    clave = hash_token(x_sesion)
    sesion = sesiones.get(clave)
    if not sesion or sesion["expira"] < time.time():
        sesiones.pop(clave, None)
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
    usuario = usuarios.get(sesion["correo"])
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuario ya no existe")
    return publico(usuario)


@router.post("/logout")
def logout(x_sesion: str = Header(..., alias="X-Sesion")):
    sesiones.pop(hash_token(x_sesion), None)
    return {"mensaje": "Sesión cerrada"}


@router.get("/usuarios")
def listar_usuarios(rol: Literal["cliente", "admin"] | None = None):
    lista = [publico(u) for u in usuarios.values()]
    return [u for u in lista if not rol or u["rol"] == rol]


app.include_router(router)
