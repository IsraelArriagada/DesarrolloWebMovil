# PR 9 — Autenticación con cookies + todo en Docker

```
navegador → nginx :8080 ─┬─ archivos del frontend
                         └─ /api, /auth → gateway :8000 ─┬─ catalogo :8001
                                                         ├─ pedidos  :8002
                                                         └─ auth     :8003
                                        Vault :8200 (secretos de todos)
```

## Correr

```bash
ADMIN_PASSWORD=UnaClaveLarga123 docker compose up --build
```

- Tienda en http://localhost:8080
- Admin: `admin@craftandbeer.cl` con la clave que pusiste. Si no pusiste una, aparece en el log de `vault-init`.

## Nuevo: servicio `auth`

- Registro con validación (correo válido, contraseña de mínimo 8 caracteres y no de las obvias).
- Contraseñas con **PBKDF2-SHA256** (210.000 iteraciones y sal aleatoria). Nunca se guardan en texto plano.
- La sesión es un token aleatorio. En memoria se guarda su **hash**, no el token.
- Bloqueo de 5 minutos después de 5 intentos fallidos.
- El mensaje es el mismo si el correo no existe o si la clave está mala (no revela quién tiene cuenta).

## Cambios en el gateway

- `POST /auth/login` deja una cookie `cb_sesion` con **HttpOnly** (JavaScript no la puede leer, así que un XSS no la roba), **SameSite=Lax** y **Secure** (activable con `COOKIE_SEGURA=true` en https).
- El token **no** viaja en el JSON, solo en la cookie.
- Roles **cliente** y **admin** (reemplazan las API keys del PR 8). El catálogo es público.
- El pedido se crea con el nombre y correo **de la sesión**, no del formulario. Un cliente solo ve sus pedidos; si pide el de otro, recibe 404.
- **CSRF**: además de SameSite, se rechazan los POST/PUT/PATCH/DELETE que vengan de un `Origin` no permitido.
- `/auth/logout` borra la sesión en el servidor y la cookie.

## Frontend

| Página | Qué hace |
|---|---|
| `index.html` | Tienda con stock en vivo, filtros, carrito (guardado en `localStorage`) y checkout. Si no hay sesión, manda a ingresar y vuelve al carrito |
| `cuenta.html` | Ingresar / crear cuenta. Con sesión: perfil y seguimiento de "Mis pedidos" |
| `admin.html` | Resumen, stock con botón de reponer, alta de cervezas y gestión de estados de pedidos |

`js/api.js` es compartido: hace los `fetch` con `credentials: 'include'` y pinta el header según el usuario.

## Sin Docker (desarrollo)

Exporta `TOKEN_CATALOGO`, `TOKEN_PEDIDOS`, `TOKEN_AUTH` y `ADMIN_PASSWORD` y levanta los 4 servicios:

```bash
uvicorn catalogo_api:app --port 8001
uvicorn pedidos_api:app  --port 8002
uvicorn auth_service:app --port 8003
uvicorn gateway:app      --port 8000
```

Luego sirve el frontend en el puerto 5500 (por ejemplo con `python -m http.server 5500`). Usa siempre `127.0.0.1` o siempre `localhost`, sin mezclarlos, para que la cookie funcione.
