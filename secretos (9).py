"""
Lectura de secretos — Craft & Beer (Semana 8)

Orden de búsqueda:
  1. HashiCorp Vault (si están VAULT_ADDR y VAULT_TOKEN)
  2. Variables de entorno / archivo .env (para desarrollo sin Vault)

Los secretos viven en Vault en la ruta KV v2:  secret/craftbeer
Así ningún token queda escrito en el código ni subido a GitHub.

Este archivo se copia igual en cada servicio (cada uno se despliega por separado).
"""
import logging
import os
import secrets as _secrets
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger("secretos")

RUTA_VAULT = os.getenv("VAULT_RUTA", "craftbeer")


@lru_cache
def _desde_vault() -> dict:
    addr, token = os.getenv("VAULT_ADDR"), os.getenv("VAULT_TOKEN")
    if not (addr and token):
        return {}
    try:
        import hvac

        cliente = hvac.Client(url=addr, token=token, timeout=3)
        respuesta = cliente.secrets.kv.v2.read_secret_version(path=RUTA_VAULT, raise_on_deleted_version=True)
        log.info("Secretos cargados desde Vault (%s)", addr)
        return respuesta["data"]["data"]
    except Exception as err:  # Vault caído, token malo, ruta inexistente...
        log.warning("No se pudo leer Vault (%s). Uso variables de entorno.", err)
        return {}


def secreto(nombre: str) -> str:
    """Devuelve el secreto o se cae al arrancar: mejor fallar temprano que correr sin seguridad."""
    valor = _desde_vault().get(nombre) or os.getenv(nombre)
    if not valor:
        raise RuntimeError(f"Falta el secreto {nombre}. Configúralo en Vault o en el .env")
    return valor


def iguales(a: str, b: str) -> bool:
    """Compara tokens en tiempo constante (evita ataques por tiempo de respuesta)."""
    return _secrets.compare_digest(a.encode(), b.encode())
