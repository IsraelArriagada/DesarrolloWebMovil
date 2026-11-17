// Esquema GraphQL: qué se puede pedir (Query) y qué se puede cambiar (Mutation)

export const typeDefs = `#graphql
  enum Estilo {
    IPA
    STOUT
    LAGER
    WHEAT
    RED_ALE
    PORTER
  }

  type Cerveza {
    id: ID!
    nombre: String!
    estilo: Estilo!
    abv: Float!
    ibu: Int
    precio: Int!
    precioFormateado: String!
    stock: Int!
    descripcion: String
    disponibleEnGrowler: Boolean!
    "true si quedan 5 o menos botellas"
    stockBajo: Boolean!
  }

  type ResumenEstilo {
    estilo: Estilo!
    cantidad: Int!
    precioPromedio: Float!
  }

  type Query {
    "Lista el catálogo. Todos los filtros son opcionales."
    cervezas(estilo: Estilo, precioMaximo: Int, soloConStock: Boolean): [Cerveza!]!
    cerveza(id: ID!): Cerveza
    buscarCerveza(texto: String!): [Cerveza!]!
    totalCervezas: Int!
    resumenPorEstilo: [ResumenEstilo!]!
  }

  input NuevaCerveza {
    nombre: String!
    estilo: Estilo!
    abv: Float!
    ibu: Int
    precio: Int!
    stock: Int
    descripcion: String
    disponibleEnGrowler: Boolean
  }

  input CambiosCerveza {
    nombre: String
    estilo: Estilo
    abv: Float
    ibu: Int
    precio: Int
    stock: Int
    descripcion: String
    disponibleEnGrowler: Boolean
  }

  type Mutation {
    crearCerveza(datos: NuevaCerveza!): Cerveza!
    actualizarCerveza(id: ID!, cambios: CambiosCerveza!): Cerveza
    "Suma o resta stock (ej: -3 cuando se venden 3)"
    moverStock(id: ID!, cantidad: Int!): Cerveza
    eliminarCerveza(id: ID!): Boolean!
  }
`;
