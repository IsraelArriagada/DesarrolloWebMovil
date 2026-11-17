#!/bin/sh
# Genera secretos aleatorios y los guarda en Vault (KV v2, ruta secret/craftbeer).
# Lo ejecuta el contenedor "vault-init" de docker compose una sola vez.
set -e
export VAULT_ADDR=${VAULT_ADDR:-http://vault:8200}

echo "Esperando a Vault..."
until vault status >/dev/null 2>&1; do sleep 1; done

aleatorio() { head -c 32 /dev/urandom | base64 | tr -d '/+=' | cut -c1-40; }

ADMIN_PASSWORD=${ADMIN_PASSWORD:-$(aleatorio)}

vault kv put secret/craftbeer \
  TOKEN_CATALOGO="$(aleatorio)" \
  TOKEN_PEDIDOS="$(aleatorio)" \
  TOKEN_AUTH="$(aleatorio)" \
  ADMIN_PASSWORD="$ADMIN_PASSWORD"

echo "=============================================="
echo " Secretos cargados en Vault (secret/craftbeer)"
echo " Admin: admin@craftandbeer.cl"
echo " Clave: $ADMIN_PASSWORD"
echo "=============================================="
