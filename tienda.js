// Tienda: catálogo en vivo desde el gateway + carrito + checkout con sesión

const ENVIO = 2990;
const ENVIO_GRATIS_DESDE = 25000;
const CLAVE_CARRITO = 'craftbeer_carrito_v2';

const ESTILOS = {
  todos: 'Todos', IPA: 'IPA', STOUT: 'Stout', PORTER: 'Porter', LAGER: 'Lager', WHEAT: 'Wheat', RED_ALE: 'Red Ale',
};
const FOTO = 'https://images.unsplash.com/photo-';
const FOTOS = {
  IPA: FOTO + '1627627045944-a6171e94783a', STOUT: FOTO + '1642997702017-8531db99dd77',
  PORTER: FOTO + '1642997702017-8531db99dd77', LAGER: FOTO + '1618183479302-1e0aa382c36b',
  WHEAT: FOTO + '1711335792535-acacf1727eab', RED_ALE: FOTO + '1711335792535-acacf1727eab',
};

let usuario = null;
let cervezas = [];
let filtro = 'todos';
let carrito = cargarCarrito(); // [{ id, cantidad }]

function cargarCarrito() {
  try { return JSON.parse(localStorage.getItem(CLAVE_CARRITO)) || []; } catch { return []; }
}
function guardarCarrito() {
  try { localStorage.setItem(CLAVE_CARRITO, JSON.stringify(carrito)); } catch {}
}

// ---------- Catálogo ----------

function pintarFiltros() {
  const cont = $('filtros');
  cont.innerHTML = '';
  Object.entries(ESTILOS).forEach(([clave, nombre]) => {
    const activo = clave === filtro;
    const b = crear('button',
      `border-2 rounded-full px-4 py-2 text-sm font-bold transition-colors cursor-pointer ${activo
        ? 'bg-[var(--tinta)] text-white border-[var(--tinta)]'
        : 'bg-white border-[var(--tinta)]/15 hover:border-[var(--tinta)]'}`, nombre);
    b.addEventListener('click', () => { filtro = clave; pintarFiltros(); pintarCatalogo(); });
    cont.appendChild(b);
  });
}

function pintarCatalogo() {
  const grid = $('gridCervezas');
  grid.innerHTML = '';
  const lista = filtro === 'todos' ? cervezas : cervezas.filter((c) => c.estilo === filtro);
  $('estadoCatalogo').textContent = lista.length ? '' : 'No hay cervezas de este estilo por ahora.';

  lista.forEach((c) => {
    const enCarrito = carrito.find((i) => i.id === c.id)?.cantidad || 0;
    const disponible = c.stock - enCarrito;

    const card = crear('article', 'bg-white rounded-2xl shadow-md hover:shadow-xl hover:-translate-y-1 transition-all overflow-hidden');
    const foto = crear('div', 'h-44 overflow-hidden relative bg-[var(--ambar-suave)]');
    if (FOTOS[c.estilo]) {
      const img = crear('img', 'producto-img');
      img.src = `${FOTOS[c.estilo]}?auto=format&fit=crop&w=800&q=70`;
      img.alt = c.nombre;
      img.loading = 'lazy';
      foto.appendChild(img);
    }
    if (c.stock <= 5) {
      foto.appendChild(crear('span',
        'absolute top-3 right-3 text-[10px] font-black uppercase px-2 py-1 rounded-full ' +
        (c.stock === 0 ? 'bg-black/70 text-white' : 'bg-[var(--naranja)] text-white'),
        c.stock === 0 ? 'Agotada' : `¡Quedan ${c.stock}!`));
    }

    const cuerpo = crear('div', 'p-5');
    cuerpo.append(
      crear('p', 'text-[11px] font-black uppercase tracking-wide text-[var(--teal)] mb-1', ESTILOS[c.estilo] || c.estilo),
      crear('h2', 'font-black text-lg mb-4', c.nombre),
    );
    const fila = crear('div', 'flex items-center justify-between');
    fila.appendChild(crear('strong', 'font-display text-lg text-[var(--naranja)]', clp(c.precio)));
    const boton = crear('button',
      'bg-[var(--naranja)] hover:bg-[var(--tinta)] text-white text-sm font-bold px-4 py-2 rounded-full transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed',
      '+ Agregar');
    boton.disabled = disponible <= 0;
    boton.addEventListener('click', () => agregar(c.id));
    fila.appendChild(boton);
    cuerpo.appendChild(fila);

    card.append(foto, cuerpo);
    grid.appendChild(card);
  });
}

async function cargarCatalogo() {
  try {
    cervezas = await api('/api/cervezas');
    // Si algo del carrito ya no existe, se saca
    carrito = carrito.filter((i) => cervezas.some((c) => c.id === i.id));
    pintarCatalogo();
    pintarCarrito();
  } catch (e) {
    $('estadoCatalogo').textContent = 'No pudimos cargar el catálogo (' + e.message + '). ¿Está corriendo el gateway?';
  }
}

// ---------- Carrito ----------

function agregar(id) {
  const item = carrito.find((i) => i.id === id);
  if (item) item.cantidad++;
  else carrito.push({ id, cantidad: 1 });
  guardarCarrito();
  pintarCarrito();
  pintarCatalogo();
}

function cambiar(id, delta) {
  const item = carrito.find((i) => i.id === id);
  const cerveza = cervezas.find((c) => c.id === id);
  if (!item) return;
  item.cantidad = Math.min(item.cantidad + delta, cerveza?.stock ?? item.cantidad);
  if (item.cantidad <= 0) carrito = carrito.filter((i) => i.id !== id);
  guardarCarrito();
  pintarCarrito();
  pintarCatalogo();
}

function pintarCarrito() {
  const unidades = carrito.reduce((s, i) => s + i.cantidad, 0);
  $('contadorCarrito').textContent = unidades;

  const cont = $('contenidoCarrito');
  cont.innerHTML = '';
  if (!carrito.length) {
    cont.appendChild(crear('p', 'text-center py-16 text-[var(--tinta-suave)]', 'Tu pedido está vacío 🍺'));
    $('formCheckout').classList.add('hidden');
    return;
  }

  let subtotal = 0;
  carrito.forEach((item) => {
    const c = cervezas.find((x) => x.id === item.id);
    if (!c) return;
    subtotal += c.precio * item.cantidad;

    const fila = crear('div', 'flex items-center justify-between gap-3 py-3 border-b border-black/5');
    const info = crear('div');
    info.append(crear('p', 'font-bold text-sm', c.nombre), crear('p', 'text-xs text-[var(--tinta-suave)]', `${clp(c.precio)} c/u`));
    const ctrl = crear('div', 'flex items-center gap-2');
    const menos = crear('button', 'w-7 h-7 rounded-full bg-[var(--crema)] font-bold cursor-pointer', '−');
    const mas = crear('button', 'w-7 h-7 rounded-full bg-[var(--crema)] font-bold cursor-pointer', '+');
    menos.addEventListener('click', () => cambiar(c.id, -1));
    mas.addEventListener('click', () => cambiar(c.id, 1));
    ctrl.append(menos, crear('span', 'w-5 text-center font-bold', item.cantidad), mas);
    fila.append(info, ctrl);
    cont.appendChild(fila);
  });

  const envio = subtotal >= ENVIO_GRATIS_DESDE ? 0 : ENVIO;
  $('totalCarrito').textContent = clp(subtotal + envio);
  $('notaEnvio').textContent = envio
    ? `Incluye envío ${clp(ENVIO)}. Te faltan ${clp(ENVIO_GRATIS_DESDE - subtotal)} para envío gratis.`
    : 'Envío gratis 🎉';
  $('formCheckout').classList.remove('hidden');
}

// ---------- Checkout ----------

$('formCheckout').addEventListener('submit', async (e) => {
  e.preventDefault();
  const msg = $('msgCheckout');

  if (!usuario) {
    msg.className = 'text-sm font-bold text-center text-[var(--naranja)]';
    msg.textContent = 'Inicia sesión para confirmar. Te llevamos…';
    setTimeout(() => (location.href = 'cuenta.html?volver=tienda'), 1200);
    return;
  }

  try {
    const pedido = await post('/api/pedidos', {
      direccion: $('direccion').value.trim(),
      items: carrito.map((i) => ({ cerveza_id: i.id, cantidad: i.cantidad })),
    });
    carrito = [];
    guardarCarrito();
    msg.className = 'text-sm font-bold text-center text-[var(--teal)]';
    msg.textContent = `¡Pedido #${pedido.id} confirmado por ${clp(pedido.total)}! 🍻`;
    await cargarCatalogo();
  } catch (err) {
    msg.className = 'text-sm font-bold text-center text-red-500';
    msg.textContent = err.message;
  }
});

// ---------- Inicio ----------

(async () => {
  usuario = await sesionActual();
  const nav = pintarHeader(usuario, 'tienda');

  const btn = crear('button', 'relative w-9 h-9 flex items-center justify-center rounded-full bg-[var(--crema)] hover:scale-105 transition-transform cursor-pointer');
  btn.setAttribute('aria-label', 'Carrito');
  btn.innerHTML = `<svg fill="none" height="18" stroke="var(--tinta)" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" viewBox="0 0 24 24" width="18"><path d="M6 2 4 6v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V6l-2-4z"/><path d="M4 6h16"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>
    <span id="contadorCarrito" class="absolute -top-1.5 -right-1.5 min-w-[18px] h-[18px] px-1 rounded-full bg-[var(--naranja)] text-white text-[10px] font-bold flex items-center justify-center">0</span>`;
  btn.addEventListener('click', () => $('carritoPanel').classList.add('abierto'));
  nav.appendChild(btn);

  $('cerrarCarrito').addEventListener('click', () => $('carritoPanel').classList.remove('abierto'));
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') $('carritoPanel').classList.remove('abierto'); });

  pintarFiltros();
  pintarCarrito();
  await cargarCatalogo();

  // Si volvió desde el login, se abre el carrito para terminar la compra
  if (usuario && carrito.length && new URLSearchParams(location.search).has('checkout')) {
    $('carritoPanel').classList.add('abierto');
  }
})();
