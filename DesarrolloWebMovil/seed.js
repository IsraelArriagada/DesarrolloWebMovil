// Carga el catálogo inicial (los mismos productos del sitio)
// Uso: npm run seed
import 'dotenv/config';
import mongoose from 'mongoose';
import { Cerveza } from './models/Cerveza.js';

const MONGO_URI = process.env.MONGO_URI || 'mongodb://127.0.0.1:27017/craftbeer';

const catalogo = [
  { nombre: 'IPA Tropical',         estilo: 'IPA',     abv: 6.5, ibu: 55, precio: 3990, stock: 48, disponibleEnGrowler: true,
    descripcion: 'Notas a mango y maracuyá, lúpulo bien presente.' },
  { nombre: 'Session IPA',          estilo: 'IPA',     abv: 4.3, ibu: 40, precio: 3790, stock: 30,
    descripcion: 'Ligera y refrescante, ideal para tomar de a varias.' },
  { nombre: 'Imperial Stout',       estilo: 'STOUT',   abv: 9.0, ibu: 60, precio: 4490, stock: 12, disponibleEnGrowler: true,
    descripcion: 'Cuerpo denso, notas a chocolate y caramelo tostado.' },
  { nombre: 'Porter de Café',       estilo: 'PORTER',  abv: 5.8, ibu: 35, precio: 4290, stock: 4,
    descripcion: 'Tostado profundo con infusión de café de origen.' },
  { nombre: 'Golden Lager',         estilo: 'LAGER',   abv: 4.8, ibu: 18, precio: 3490, stock: 60,
    descripcion: 'Dorada, suave y fácil de beber.' },
  { nombre: 'Pilsner Clásica',      estilo: 'LAGER',   abv: 5.0, ibu: 32, precio: 3490, stock: 0,
    descripcion: 'Amargor limpio y final crujiente.' },
  { nombre: 'Wheat Ale de Naranja', estilo: 'WHEAT',   abv: 4.9, ibu: 15, precio: 3990, stock: 22,
    descripcion: 'Trigo con un toque cítrico, refrescante y ligera.' },
  { nombre: 'Red Ale Ámbar',        estilo: 'RED_ALE', abv: 5.5, ibu: 28, precio: 3890, stock: 3,
    descripcion: 'Maltosa y equilibrada, con notas a caramelo.' },
];

await mongoose.connect(MONGO_URI);
await Cerveza.deleteMany({});
const creadas = await Cerveza.insertMany(catalogo);
console.log(`✅ ${creadas.length} cervezas cargadas en ${MONGO_URI}`);
await mongoose.disconnect();
