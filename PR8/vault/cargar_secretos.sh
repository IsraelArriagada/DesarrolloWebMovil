#!/bin/sh
# Genera secretos aleatorios y los guarda en Vault (KV v2, ruta secret/craftbeer).
# Lo ejecuta el contenedor "vault-init" de docker compose una sola vez.
set -e
export VAULT_ADDR=${VAULT_ADDR:-http://vault:8200}

echo "Esperando a Vault..."
until vault status >/dev/null 2>&1; do sleep 1; done

aleatorio() { head -c 32 /dev/urandom | base64 | tr -d '/+=' | cut -c1-40; }

vault kv put secret/craftbeer \
  TOKEN_CATALOGO="$(aleatorio)" \
  TOKEN_PEDIDOS="$(aleatorio)" \
  API_KEY_TIENDA="${API_KEY_TIENDA:-$(aleatorio)}" \
  API_KEY_ADMIN="${API_KEY_ADMIN:-$(aleatorio)}"

echo "Secretos cargados en secret/craftbeer:"
vault kv get -format=json secret/craftbeer | grep -E '"(API_KEY_[A-Z]+)"' || true
