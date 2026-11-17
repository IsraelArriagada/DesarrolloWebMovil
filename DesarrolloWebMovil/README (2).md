# Semana 5 — API GraphQL + MongoDB

Catálogo de cervezas con **Apollo Server**, **Mongoose** y **MongoDB**.

## Correr

```bash
cd graphql-cervezas
npm install
cp .env.example .env      # ajusta MONGO_URI si tu Mongo no está en localhost
npm run seed              # carga 8 cervezas de ejemplo
npm start                 # http://localhost:4000 (abre Apollo Sandbox)
```

## Estructura

```
models/Cerveza.js   esquema Mongoose (validaciones: enum de estilos, abv 0-20, precio >= 0...)
src/schema.js       typeDefs de GraphQL
src/resolvers.js    lógica de queries y mutations
server.js           conexión a Mongo y arranque de Apollo
seed.js             datos iniciales
```

El modelo se pasa a los resolvers por el **context**. Así los resolvers no importan Mongo directamente y se pueden probar con un modelo falso.

## Ejemplos para probar en el Sandbox

```graphql
# IPAs con stock, hasta $4.000
query {
  cervezas(estilo: IPA, precioMaximo: 4000, soloConStock: true) {
    nombre abv precioFormateado stock stockBajo
  }
  totalCervezas
  resumenPorEstilo { estilo cantidad precioPromedio }
}
```

```graphql
mutation {
  crearCerveza(datos: { nombre: "Hazy IPA", estilo: IPA, abv: 6.8, ibu: 45, precio: 4190, stock: 24 }) {
    id nombre
  }
}
```

```graphql
mutation { moverStock(id: "PEGA_UN_ID", cantidad: -3) { nombre stock stockBajo } }
```

## Detalles

- `precioFormateado` y `stockBajo` son **campos calculados**: no se guardan en Mongo.
- `resumenPorEstilo` usa un **aggregate** (`$group` + `$avg`).
- `buscarCerveza` escapa el texto antes de armar la RegExp (no se puede inyectar un patrón).
- Los errores salen con códigos GraphQL (`NOT_FOUND`, `BAD_USER_INPUT`); por ejemplo, un nombre duplicado o vender más stock del que hay.
