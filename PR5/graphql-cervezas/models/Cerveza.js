import mongoose from 'mongoose';

// Los estilos permitidos son los mismos filtros que tiene el catálogo del sitio
export const ESTILOS = ['IPA', 'STOUT', 'LAGER', 'WHEAT', 'RED_ALE', 'PORTER'];

const cervezaSchema = new mongoose.Schema(
  {
    nombre:      { type: String, required: true, trim: true, unique: true },
    estilo:      { type: String, required: true, enum: ESTILOS },
    abv:         { type: Number, required: true, min: 0, max: 20 },   // % de alcohol
    ibu:         { type: Number, default: 0, min: 0, max: 120 },      // amargor
    precio:      { type: Number, required: true, min: 0 },            // CLP, botella 355 ml
    stock:       { type: Number, default: 0, min: 0 },
    descripcion: { type: String, default: '' },
    disponibleEnGrowler: { type: Boolean, default: false },
  },
  { timestamps: true } // agrega createdAt y updatedAt solo
);

export const Cerveza = mongoose.model('Cerveza', cervezaSchema, 'cervezas');
