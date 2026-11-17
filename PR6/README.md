# PR 6 — FastAPI + MongoDB: socios del Club Cervecero

CRUD completo con **FastAPI**, **pymongo** y validación con **Pydantic**.

## Correr

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Documentación interactiva en http://127.0.0.1:8000/docs.

## Rutas

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/socios` | Lista con filtros `?plan=malta&comuna=Ñuñoa&solo_activos=true&limite=50` |
| GET | `/socios/resumen` | Socios activos por plan e ingreso mensual |
| GET | `/socios/{id}` | Un socio |
| POST | `/socios` | Inscribe un socio (201; 409 si el correo ya existe) |
| PUT | `/socios/{id}` | Actualiza solo los campos enviados |
| DELETE | `/socios/{id}` | Baja lógica (`activo=false`); con `?definitivo=true` lo borra |

## Detalles

- El correo tiene **índice único** en Mongo, y se valida con `EmailStr`.
- Los planes son un `Enum` (`lupulo`, `malta`, `barrica`) y cada socio devuelve su `valor_mensual`.
- Un id mal formado devuelve 400 (no 500), y uno inexistente devuelve 404.
- `ObjectId` se convierte a texto antes de responder en JSON.
