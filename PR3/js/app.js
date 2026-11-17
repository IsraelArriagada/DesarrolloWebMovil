// Craft & Beer — PR 3: interacción con JavaScript
// Un solo archivo para las 3 páginas. Cada bloque revisa si existen
// sus elementos antes de hacer algo, así no se cae en las otras páginas.

const ENVIO_GRATIS_DESDE = 25000;
const CLAVE_STORAGE = 'craftbeer_carrito';

// ---------- Utilidades ----------

const formatoCLP = (monto) => '$' + monto.toLocaleString('es-CL');

function leerCarrito() {
  try {
    return JSON.parse(localStorage.getItem(CLAVE_STORAGE)) || [];
  } catch {
    return [];
  }
}

function guardarCarrito(items) {
  try {
    localStorage.setItem(CLAVE_STORAGE, JSON.stringify(items));
  } catch {
    // Si el navegador bloquea el storage, el carrito igual funciona mientras no recargues
  }
}

let carrito = leerCarrito();

// ---------- Carrito ----------

function agregarAlCarrito(nombre, precio) {
  const existente = carrito.find((item) => item.nombre === nombre);
  if (existente) {
    existente.cantidad++;
  } else {
    carrito.push({ nombre, precio, cantidad: 1 });
  }
  guardarCarrito(carrito);
  pintarCarrito();
  animarContador();
}

function cambiarCantidad(nombre, delta) {
  const item = carrito.find((i) => i.nombre === nombre);
  if (!item) return;
  item.cantidad += delta;
  if (item.cantidad <= 0) {
    carrito = carrito.filter((i) => i.nombre !== nombre);
  }
  guardarCarrito(carrito);
  pintarCarrito();
}

function vaciarCarrito() {
  carrito = [];
  guardarCarrito(carrito);
  pintarCarrito();
}

function pintarCarrito() {
  const contador = document.getElementById('contadorCarrito');
  const contenido = document.getElementById('contenidoCarrito');

  const unidades = carrito.reduce((suma, i) => suma + i.cantidad, 0);
  const total = carrito.reduce((suma, i) => suma + i.precio * i.cantidad, 0);

  if (contador) contador.textContent = unidades;
  if (!contenido) return;

  if (carrito.length === 0) {
    contenido.innerHTML = `
      <div class="text-center py-16 text-[var(--tinta-suave)]">
        <p class="font-display text-xl mb-1">Tu pedido está vacío</p>
        <p class="text-sm">Agrega alguna cerveza desde el catálogo 🍺</p>
      </div>`;
    return;
  }

  const falta = ENVIO_GRATIS_DESDE - total;
  const avance = Math.min(100, Math.round((total / ENVIO_GRATIS_DESDE) * 100));

  // Armo el HTML con createElement para los nombres (evita inyectar HTML)
  contenido.innerHTML = '';

  const barra = document.createElement('div');
  barra.className = 'mb-5 rounded-xl bg-[var(--crema)] p-3 text-sm';
  barra.innerHTML = `
    <p class="font-bold mb-2">${falta > 0 ? `Te faltan ${formatoCLP(falta)} para envío gratis` : '¡Tienes envío gratis! 🎉'}</p>
    <div class="h-2 rounded-full bg-black/10 overflow-hidden">
      <div class="h-full bg-[var(--teal)] transition-all" style="width:${avance}%"></div>
    </div>`;
  contenido.appendChild(barra);

  carrito.forEach((item) => {
    const fila = document.createElement('div');
    fila.className = 'flex items-center justify-between gap-3 py-3 border-b border-black/5';

    const info = document.createElement('div');
    const nombre = document.createElement('p');
    nombre.className = 'font-bold text-sm';
    nombre.textContent = item.nombre;
    const precio = document.createElement('p');
    precio.className = 'text-xs text-[var(--tinta-suave)]';
    precio.textContent = `${formatoCLP(item.precio)} c/u`;
    info.append(nombre, precio);

    const controles = document.createElement('div');
    controles.className = 'flex items-center gap-2';
    controles.innerHTML = `
      <button class="w-7 h-7 rounded-full bg-[var(--crema)] font-bold cursor-pointer" data-accion="restar">−</button>
      <span class="w-5 text-center font-bold">${item.cantidad}</span>
      <button class="w-7 h-7 rounded-full bg-[var(--crema)] font-bold cursor-pointer" data-accion="sumar">+</button>`;
    controles.querySelector('[data-accion="restar"]').addEventListener('click', () => cambiarCantidad(item.nombre, -1));
    controles.querySelector('[data-accion="sumar"]').addEventListener('click', () => cambiarCantidad(item.nombre, 1));

    fila.append(info, controles);
    contenido.appendChild(fila);
  });

  const pie = document.createElement('div');
  pie.className = 'pt-5';
  pie.innerHTML = `
    <div class="flex justify-between font-display text-xl mb-4">
      <span>Total</span><span class="text-[var(--naranja)]">${formatoCLP(total)}</span>
    </div>
    <button id="btnPagar" class="w-full rounded-full bg-[var(--naranja)] text-white font-bold py-3 mb-2 hover:bg-[var(--tinta)] transition-colors cursor-pointer">Ir a pagar</button>
    <button id="btnVaciar" class="w-full text-sm font-bold text-[var(--tinta-suave)] hover:text-[var(--naranja)] cursor-pointer">Vaciar pedido</button>`;
  contenido.appendChild(pie);

  pie.querySelector('#btnVaciar').addEventListener('click', vaciarCarrito);
  pie.querySelector('#btnPagar').addEventListener('click', () => {
    mostrarAviso(`Pedido de ${formatoCLP(total)} listo. ¡Salud! 🍻`);
    vaciarCarrito();
    cerrarPanel();
  });
}

function animarContador() {
  const contador = document.getElementById('contadorCarrito');
  if (!contador) return;
  contador.animate(
    [{ transform: 'scale(1)' }, { transform: 'scale(1.5)' }, { transform: 'scale(1)' }],
    { duration: 300 }
  );
}

// ---------- Panel lateral ----------

const panel = document.getElementById('carritoPanel');

function abrirPanel() { panel?.classList.add('abierto'); }
function cerrarPanel() { panel?.classList.remove('abierto'); }

document.getElementById('btnCarrito')?.addEventListener('click', abrirPanel);
document.getElementById('cerrarCarrito')?.addEventListener('click', cerrarPanel);
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') cerrarPanel(); });

// ---------- Aviso flotante (toast) ----------

function mostrarAviso(texto) {
  const aviso = document.createElement('div');
  aviso.className = 'fixed bottom-6 left-1/2 -translate-x-1/2 z-[200] rounded-full bg-[var(--tinta)] text-white font-bold px-5 py-3 shadow-xl';
  aviso.textContent = texto;
  document.body.appendChild(aviso);
  setTimeout(() => aviso.remove(), 2500);
}

// ---------- Catálogo: botones "Agregar" ----------

document.querySelectorAll('.btn-agregar').forEach((boton) => {
  boton.addEventListener('click', () => {
    const nombre = boton.dataset.nombre;
    const precio = Number(boton.dataset.precio);
    agregarAlCarrito(nombre, precio);
    mostrarAviso(`${nombre} agregada al pedido`);
  });
});

// ---------- Catálogo: filtros por categoría ----------

const botonesFiltro = document.querySelectorAll('.filtro-btn');
const tarjetas = document.querySelectorAll('.producto-card');

function aplicarFiltro(categoria) {
  tarjetas.forEach((card) => {
    const coincide = categoria === 'todos' || card.dataset.categoria === categoria;
    card.classList.toggle('oculto-filtro', !coincide);
  });

  botonesFiltro.forEach((b) => {
    const activo = b.dataset.categoria === categoria;
    b.classList.toggle('bg-[var(--tinta)]', activo);
    b.classList.toggle('text-white', activo);
    b.classList.toggle('border-[var(--tinta)]', activo);
    b.classList.toggle('bg-white', !activo);
    b.classList.toggle('border-[var(--tinta)]/15', !activo);
  });
}

botonesFiltro.forEach((boton) => {
  boton.addEventListener('click', () => aplicarFiltro(boton.dataset.categoria));
});

// ---------- Cuenta: validación del login ----------

const formLogin = document.getElementById('formLogin');

if (formLogin) {
  const correo = document.getElementById('correo');
  const password = document.getElementById('password');
  const mensaje = document.getElementById('mensajeLogin');
  const regexCorreo = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

  function marcar(input, ok) {
    input.classList.toggle('border-red-400', !ok);
    input.classList.toggle('border-black/10', ok);
  }

  formLogin.addEventListener('submit', (e) => {
    e.preventDefault();

    const correoOk = regexCorreo.test(correo.value.trim());
    const passOk = password.value.length >= 6;
    marcar(correo, correoOk);
    marcar(password, passOk);

    if (!correoOk) {
      mensaje.textContent = 'Revisa tu correo, le falta algo.';
      mensaje.className = 'mt-4 text-center font-bold text-red-500';
      return;
    }
    if (!passOk) {
      mensaje.textContent = 'La contraseña debe tener al menos 6 caracteres.';
      mensaje.className = 'mt-4 text-center font-bold text-red-500';
      return;
    }

    const nombre = correo.value.split('@')[0];
    mensaje.textContent = `¡Bienvenido de vuelta, ${nombre}! Tienes 120 CraftPoints.`;
    mensaje.className = 'mt-4 text-center font-bold text-[var(--teal)]';
    formLogin.reset();
  });
}

// Al cargar cualquier página se pinta el carrito guardado
pintarCarrito();
