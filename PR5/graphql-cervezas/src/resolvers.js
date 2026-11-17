import { GraphQLError } from 'graphql';

// El modelo llega por el "context" (ver server.js). Así los resolvers no
// dependen directo de Mongo y se pueden probar con un modelo falso.

const LIMITE_STOCK_BAJO = 5;

const noEncontrada = (id) =>
  new GraphQLError(`No existe una cerveza con id ${id}`, { extensions: { code: 'NOT_FOUND' } });

// Escapa caracteres especiales para usar el texto del usuario dentro de una RegExp
const escaparRegex = (texto) => texto.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

export const resolvers = {
  Query: {
    cervezas: async (_, { estilo, precioMaximo, soloConStock }, { Cerveza }) => {
      const filtro = {};
      if (estilo) filtro.estilo = estilo;
      if (precioMaximo != null) filtro.precio = { $lte: precioMaximo };
      if (soloConStock) filtro.stock = { $gt: 0 };
      return Cerveza.find(filtro).sort({ estilo: 1, precio: 1 });
    },

    cerveza: async (_, { id }, { Cerveza }) => Cerveza.findById(id),

    buscarCerveza: async (_, { texto }, { Cerveza }) => {
      const regex = new RegExp(escaparRegex(texto.trim()), 'i');
      return Cerveza.find({ $or: [{ nombre: regex }, { descripcion: regex }] });
    },

    totalCervezas: async (_, __, { Cerveza }) => Cerveza.countDocuments(),

    resumenPorEstilo: async (_, __, { Cerveza }) => {
      const filas = await Cerveza.aggregate([
        { $group: { _id: '$estilo', cantidad: { $sum: 1 }, precioPromedio: { $avg: '$precio' } } },
        { $sort: { cantidad: -1 } },
      ]);
      return filas.map((f) => ({
        estilo: f._id,
        cantidad: f.cantidad,
        precioPromedio: Math.round(f.precioPromedio),
      }));
    },
  },

  Mutation: {
    crearCerveza: async (_, { datos }, { Cerveza }) => {
      try {
        return await Cerveza.create(datos);
      } catch (err) {
        if (err.code === 11000) {
          throw new GraphQLError(`Ya existe una cerveza llamada "${datos.nombre}"`, {
            extensions: { code: 'BAD_USER_INPUT' },
          });
        }
        throw new GraphQLError(err.message, { extensions: { code: 'BAD_USER_INPUT' } });
      }
    },

    actualizarCerveza: async (_, { id, cambios }, { Cerveza }) => {
      const cerveza = await Cerveza.findByIdAndUpdate(id, cambios, { new: true, runValidators: true });
      if (!cerveza) throw noEncontrada(id);
      return cerveza;
    },

    moverStock: async (_, { id, cantidad }, { Cerveza }) => {
      const cerveza = await Cerveza.findById(id);
      if (!cerveza) throw noEncontrada(id);

      const nuevoStock = cerveza.stock + cantidad;
      if (nuevoStock < 0) {
        throw new GraphQLError(`Solo quedan ${cerveza.stock} unidades de ${cerveza.nombre}`, {
          extensions: { code: 'BAD_USER_INPUT' },
        });
      }
      cerveza.stock = nuevoStock;
      await cerveza.save();
      return cerveza;
    },

    eliminarCerveza: async (_, { id }, { Cerveza }) => {
      const borrada = await Cerveza.findByIdAndDelete(id);
      return Boolean(borrada);
    },
  },

  // Campos calculados (no se guardan en Mongo)
  Cerveza: {
    id: (c) => String(c._id ?? c.id),
    precioFormateado: (c) => '$' + c.precio.toLocaleString('es-CL'),
    stockBajo: (c) => c.stock <= LIMITE_STOCK_BAJO,
  },
};
