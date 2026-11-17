# PR 7 — Microservicios + API Gateway

```
frontend (panel)  →  gateway :8000  →  catalogo :8001
                                    →  pedidos  :8002
```

## Correr (3 terminales + frontend)

```bash
cd catalogo && pip install -r requirements.txt && uvicorn catalogo_api:app --port 8001 --reload
cd pedidos  && pip install -r requirements.txt && uvicorn pedidos_api:app  --port 8002 --reload
cd gateway  && pip install -r requirements.txt && uvicorn gateway:app      --port 8000 --reload
```

Después abre `frontend/index.html` con Live Server (puerto 5500).

## Servicios

- **catalogo**: CRUD de cervezas y `PATCH /cervezas/{id}/stock` para sumar o restar stock.
- **pedidos**: crea pedidos, calcula el envío (gratis sobre $25.000) y controla los estados con transiciones válidas: `recibido → preparando → en_camino → entregado`, con `cancelado` posible al inicio.
- **gateway**: único punto de entrada (CORS habilitado para el frontend). Hace tres cosas:
  - **Reenvía** las rutas `/api/cervezas` y `/api/pedidos`.
  - **Orquesta** `POST /api/pedidos`: trae el precio real desde el catálogo, descuenta stock y crea el pedido. Si algo falla a la mitad, **devuelve el stock** (compensación). Al cancelar un pedido, el stock también vuelve.
  - **Combina** `/api/resumen`, que llama a los 2 servicios en paralelo con `asyncio.gather`.
  - Si un servicio está caído responde 503, y si tarda demasiado, 504. `/health` muestra el estado de cada uno.

El precio **nunca** lo manda el navegador: el gateway lo saca del catálogo.
