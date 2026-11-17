# Semana 8 — Seguridad + Vault

Sobre la arquitectura de la semana 7 se agregó:

| Capa | Medida |
|---|---|
| Cliente → gateway | API key en header `X-API-Key` con **2 roles**: `tienda` (ver catálogo, crear pedidos) y `admin` (modificar catálogo, ver todos los pedidos, cambiar estados, resumen). Sin key: 401; rol insuficiente: 403 |
| Gateway → servicios | Token **Bearer distinto por servicio**. Si alguien llama directo al microservicio sin token, recibe 401 |
| Secretos | Se leen desde **HashiCorp Vault** (`secret/craftbeer`) con `hvac`; sin Vault, desde variables de entorno o `.env`. Si falta un secreto, el servicio **no arranca** |
| Comparación | `secrets.compare_digest`, en tiempo constante (evita ataques por tiempo de respuesta) |
| Abuso | Límite de 60 peticiones por minuto por IP (responde 429) |
| Respuestas | Headers `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` y `Cache-Control: no-store`. Los errores internos no se filtran al cliente |
| CORS | Solo los orígenes y headers necesarios |
| Docker | Los contenedores corren con usuario sin privilegios. Catálogo y pedidos **no exponen puerto**: solo se alcanzan por la red interna |

## Correr con Docker (recomendado)

```bash
API_KEY_ADMIN=mi-clave-admin API_KEY_TIENDA=mi-clave-tienda docker compose up --build
```

Panel en http://localhost:8080 (pide la API key) y Vault UI en http://localhost:8200 (token `root-dev-craftbeer`, **solo desarrollo**).

## Correr sin Docker

Copia `.env.example` como `.env` dentro de cada carpeta (o exporta las variables) y levanta los 3 servicios igual que en la semana 7.

`secretos.py` está repetido en cada servicio a propósito: cada uno se despliega por separado.
