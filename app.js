// Panel de la tienda (Semana 8): ahora cada petición lleva la API key en X-API-Key
const API = `http://${location.hostname || '127.0.0.1'}:8000`;

// La key se guarda solo en sessionStorage: se borra al cerrar la pestaña
const leerKey = () => { try { return sessionStorage.getItem('craftbeer_api_key') || ''; } catch { return ''; } };
const guardarKey = (k) => { try { sessionStorage.setItem('craftbeer_api_key', k); } catch {} };

const clp = (n) => '$' + Number(n).toLocaleString('es-CL');
const $ = (id) => document.getElementById(id);

// Siguiente estado posible para el botón de cada pedido
const SIGUIENTE = { recibido: 'preparando', preparando: 'en_camino', en_camino: 'entregado' };
const COLOR_ESTADO = {
  recibido: 'bg-[var(--ambar)]', preparando: 'bg-[var(--purpura)] text-white',
  en_camino: 'bg-[var(--naranja)] text-white', entregado: 'bg-[var(--teal)] text-white',
  cancelado: 'bg-black/10',
};

let carrito = []; // items del pedido que se está armando

async function api(ruta, opciones = {}) {
  const r = await fetch(API + ruta, {
    ...opciones,
    headers: { 'Content-Type': 'application/json', 'X-API-Key': leerKey() },
  });
  if (r.status === 401) mostrarLogin();
  const datos = await r.json().catch(() => ({}));
  if (!r.ok) {
    // FastAPI manda los errores de validación como lista
    const detalle = Array.isArray(datos.detail) ? datos.detail.map((d) => d.msg).join(', ') : datos.detail;
    throw new Error(detalle || `Error ${r.status}`);
  }
  return datos;
}

function texto(el, valor) {
  el.textContent = valor;
  return el;
}

// ---------- Pintar ----------

async function cargarEstado() {
  try {
    const h = await api('/health');
    const caidos = Object.entries(h.servicios).filter(([, e]) => e !== 'ok').map(([n]) => n);
    $('estadoServicios').textContent = caidos.length ? `⚠ Caído: ${caidos.join(', ')}` : '● Servicios OK';
    $('estadoServicios').className = 'text-xs font-bold ' + (caidos.length ? 'text-[var(--naranja)]' : 'text-[var(--teal)]');
  } catch {
    $('estadoServicios').textContent = '⚠ Gateway apagado';
    $('estadoServicios').className = 'text-xs font-bold text-[var(--naranja)]';
  }
}

async function cargarResumen() {
  try {
    const r = await api('/api/resumen');
    const tarjetas = [
      ['Cervezas', r.cervezas_en_catalogo],
      ['Pedidos', r.pedidos],
      ['Ventas', clp(r.ventas_totales)],
      ['Stock bajo', r.stock_bajo.length + r.sin_stock.length],
    ];
    $('resumen').innerHTML = '';
    tarjetas.forEach(([nombre, valor]) => {
      const div = document.createElement('div');
      div.className = 'bg-white rounded-2xl shadow-sm p-5';
      div.innerHTML = `<p class="text-sm text-[var(--tinta-suave)] font-bold"></p><p class="font-display text-3xl"></p>`;
      texto(div.children[0], nombre);
      texto(div.children[1], valor);
      $('resumen').appendChild(div);
    });
  } catch (e) {
    $('resumen').textContent = 'No se pudo cargar el resumen: ' + e.message;
  }
}

async function cargarCervezas() {
  const cervezas = await api('/api/cervezas');
  const tbody = $('tablaCervezas');
  const select = $('selCerveza');
  tbody.innerHTML = '';
  select.innerHTML = '';

  cervezas.forEach((c) => {
    const tr = document.createElement('tr');
    tr.className = 'border-t border-black/5';
    const colorStock = c.stock === 0 ? 'text-red-500' : c.stock <= 5 ? 'text-[var(--naranja)]' : '';
    tr.innerHTML = `<td class="py-2 font-bold"></td><td></td><td class="text-right"></td><td class="text-right font-bold ${colorStock}"></td>`;
    texto(tr.children[0], c.nombre);
    texto(tr.children[1], c.estilo);
    texto(tr.children[2], clp(c.precio));
    texto(tr.children[3], c.stock);
    tbody.appendChild(tr);

    const op = document.createElement('option');
    op.value = c.id;
    op.textContent = `${c.nombre} (${c.stock})`;
    op.disabled = c.stock === 0;
    select.appendChild(op);
  });
}

async function cargarPedidos() {
  const pedidos = await api('/api/pedidos');
  const cont = $('listaPedidos');
  cont.innerHTML = pedidos.length ? '' : '<p class="text-[var(--tinta-suave)]">Todavía no hay pedidos.</p>';

  pedidos.reverse().forEach((p) => {
    const card = document.createElement('article');
    card.className = 'rounded-2xl border-2 border-black/5 p-4';
    card.innerHTML = `
      <div class="flex justify-between items-center mb-2">
        <strong class="font-display text-lg">#${p.id}</strong>
        <span class="text-xs font-black uppercase px-2 py-1 rounded-full ${COLOR_ESTADO[p.estado]}">${p.estado.replace('_', ' ')}</span>
      </div>
      <p class="font-bold text-sm cliente"></p>
      <ul class="text-sm text-[var(--tinta-suave)] my-2 items"></ul>
      <p class="font-bold">${clp(p.total)} <span class="text-xs text-[var(--tinta-suave)]">${p.envio ? '(incluye envío)' : '(envío gratis)'}</span></p>
      <div class="flex gap-2 mt-3 acciones"></div>`;
    texto(card.querySelector('.cliente'), `${p.cliente} · ${p.direccion}`);
    p.items.forEach((i) => {
      card.querySelector('.items').appendChild(texto(document.createElement('li'), `${i.cantidad} × ${i.nombre}`));
    });

    const acciones = card.querySelector('.acciones');
    if (SIGUIENTE[p.estado]) {
      acciones.appendChild(boton(`→ ${SIGUIENTE[p.estado].replace('_', ' ')}`, 'bg-[var(--tinta)] text-white', () => cambiarEstado(p.id, SIGUIENTE[p.estado])));
    }
    if (['recibido', 'preparando'].includes(p.estado)) {
      acciones.appendChild(boton('Cancelar', 'bg-black/5', () => cambiarEstado(p.id, 'cancelado')));
    }
    cont.appendChild(card);
  });
}

function boton(etiqueta, clases, alHacerClick) {
  const b = document.createElement('button');
  b.className = `rounded-full text-xs font-bold px-3 py-1.5 cursor-pointer ${clases}`;
  b.textContent = etiqueta;
  b.addEventListener('click', alHacerClick);
  return b;
}

async function cambiarEstado(id, estado) {
  try {
    await api(`/api/pedidos/${id}/estado`, { method: 'PATCH', body: JSON.stringify({ estado }) });
    await refrescar();
  } catch (e) {
    alertaPedido(e.message, false);
  }
}

// ---------- Armar pedido ----------

function pintarCarrito() {
  const ul = $('itemsPedido');
  ul.innerHTML = '';
  carrito.forEach((item, i) => {
    const li = document.createElement('li');
    li.className = 'flex justify-between bg-[var(--crema)] rounded-lg px-3 py-1.5';
    li.appendChild(texto(document.createElement('span'), `${item.cantidad} × ${item.nombre}`));
    li.appendChild(boton('✕', '', () => { carrito.splice(i, 1); pintarCarrito(); }));
    ul.appendChild(li);
  });
}

$('btnAgregarItem').addEventListener('click', () => {
  const sel = $('selCerveza');
  const cantidad = Number($('cantCerveza').value);
  if (!sel.value || cantidad < 1) return;
  const nombre = sel.options[sel.selectedIndex].textContent.replace(/ \(\d+\)$/, '');
  const existente = carrito.find((i) => i.cerveza_id === Number(sel.value));
  if (existente) existente.cantidad += cantidad;
  else carrito.push({ cerveza_id: Number(sel.value), cantidad, nombre });
  pintarCarrito();
});

function alertaPedido(msg, ok) {
  $('msgPedido').textContent = msg;
  $('msgPedido').className = 'text-sm font-bold ' + (ok ? 'text-[var(--teal)]' : 'text-red-500');
}

$('formPedido').addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;
  if (!carrito.length) return alertaPedido('Agrega al menos una cerveza', false);

  try {
    const pedido = await api('/api/pedidos', {
      method: 'POST',
      body: JSON.stringify({
        cliente: form.cliente.value,
        direccion: form.direccion.value,
        items: carrito.map(({ cerveza_id, cantidad }) => ({ cerveza_id, cantidad })),
      }),
    });
    alertaPedido(`Pedido #${pedido.id} creado por ${clp(pedido.total)} 🍻`, true);
    carrito = [];
    form.reset();
    pintarCarrito();
    await refrescar();
  } catch (err) {
    alertaPedido(err.message, false);
  }
});

// ---------- API key ----------

function mostrarLogin() {
  $('panelKey').classList.remove('hidden');
}

$('formKey').addEventListener('submit', async (e) => {
  e.preventDefault();
  guardarKey($('inputKey').value.trim());
  try {
    const { rol } = await api('/api/yo');
    $('panelKey').classList.add('hidden');
    $('rolActual').textContent = `Rol: ${rol}`;
    await refrescar();
  } catch (err) {
    $('msgKey').textContent = err.message;
  }
});

$('btnSalir').addEventListener('click', () => {
  guardarKey('');
  location.reload();
});

async function refrescar() {
  await cargarEstado();
  try {
    // allSettled: si el rol "tienda" no puede ver pedidos, igual se muestra el catálogo
    await Promise.allSettled([cargarCervezas(), cargarPedidos(), cargarResumen()]);
  } catch (e) {
    alertaPedido('No hay conexión con el gateway: ' + e.message, false);
  }
}

if (leerKey()) {
  api('/api/yo').then(({ rol }) => { $('rolActual').textContent = `Rol: ${rol}`; refrescar(); }).catch(() => {});
} else {
  mostrarLogin();
  cargarEstado();
}
