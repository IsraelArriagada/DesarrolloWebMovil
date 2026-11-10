# CraftBeerBackend – Craft & Beer (Caso 10)

Backend de microservicios .NET 8 + Oracle 21c XE, con API Gateway (Ocelot) y GraphQL Gateway privado.

## Requisitos
Docker Desktop y Python 3 (solo para el script de pruebas). No hace falta instalar .NET ni Oracle.

## Ejecutar
```bash
cp .env.example .env        # edita los secretos (no subir .env)
docker compose up --build   # primera vez: Oracle tarda ~2-3 min en inicializar
```
Gateway: http://localhost:5000/api/v1 · Health: http://localhost:5000/health

## Pruebas (genera evidencia)
```bash
set -a; . ./.env; set +a
python3 scripts/smoke_test.py      # guarda evidencia_pruebas.txt
```

## Servicios
| Servicio | Puerto interno | Esquema Oracle |
|---|---|---|
| ApiGateway (Ocelot) | 8080 → **5000** publicado | – |
| GraphQLGateway (privado) | 8080 | – |
| Clients (+Auth/JWT) | 8080 | CLIENTS |
| Inventory | 8080 | INVENTORY |
| Orders | 8080 | ORDERS |
| Payments | 8080 | PAYMENTS |
| Delivery | 8080 | DELIVERY |
| Notifications | 8080 | NOTIFICATIONS |

## Seguridad
JWT HS256 30 min · BCrypt costo 12 · bloqueo tras 5 intentos · el Gateway elimina X-User-*/X-Service-Key del cliente e inyecta identidad · servicios rechazan acceso directo (403) · webhook con HMAC e idempotencia · precios/totales calculados en servidor · mayoría de edad (Ley 19.925) en registro, pedido y entrega · secretos solo por variables de entorno.

## Usuarios de prueba (staff)
admin@craftbeer.cl, cajero@craftbeer.cl, despacho@craftbeer.cl, dueno@craftbeer.cl — clave = `SEED_ADMIN_PWD` de tu .env.

## Estado de verificación
Compilado y ejecutado con Docker Desktop (Windows) el 9-nov-2026. `scripts/smoke_test.py`: 33/33 pruebas OK (ver `evidencia_pruebas.txt`).
Pagos y correo funcionan con adaptadores de prueba (`PAYMENT_PROVIDER=fake`, `MAIL_PROVIDER=fake`).
