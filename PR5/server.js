import 'dotenv/config';
import mongoose from 'mongoose';
import { ApolloServer } from '@apollo/server';
import { startStandaloneServer } from '@apollo/server/standalone';

import { typeDefs } from './src/schema.js';
import { resolvers } from './src/resolvers.js';
import { Cerveza } from './models/Cerveza.js';

const MONGO_URI = process.env.MONGO_URI || 'mongodb://127.0.0.1:27017/craftbeer';
const PUERTO = Number(process.env.PUERTO) || 4000;

async function iniciar() {
  await mongoose.connect(MONGO_URI);
  console.log('🍺 Conectado a MongoDB');

  const servidor = new ApolloServer({ typeDefs, resolvers });

  const { url } = await startStandaloneServer(servidor, {
    listen: { port: PUERTO },
    // Cada request recibe el modelo en el contexto
    context: async () => ({ Cerveza }),
  });

  console.log(`🚀 GraphQL listo en ${url}`);
}

iniciar().catch((err) => {
  console.error('No se pudo iniciar el servidor:', err.message);
  process.exit(1);
});
