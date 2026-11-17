// Panel admin: solo entra quien tenga rol "admin" (lo valida el gateway, no solo esta página)

const SIGUIENTE = { recibido: 'preparando', preparando: 'en_camino', en_camino: 'entregado' };
const COLOR_ESTADO = {
  recibido: 'bg-[var(--ambar)]', preparando: 'bg-[var(--purpura)] text-white',
  en_camino: 'bg-[var(--naranja)] text-white', entregado: 'bg-[var(--teal)] text-white',
  cancelado: 'bg-black/10',
};

function boton(texto, clases, alHacerClick) {
  const b = crear('button', `rounded-full text-xs font-bold px-3 py-1.5 cursor-pointer ${clases}`, texto);
  b.addEventListener('click', alHacerClick);
  return b;
}

async function cargarEstado() {
  try {
    const h = await api('/health');
    const caidos = Object.entries(h.servicios).filter(([, e]) => e !== 'ok').map(([n]) => n);
    $('estadoServicios').textContent = caidos.length ? `⚠ Caído: ${caidos.join(', ')}` : '● Todos los servicios OK';
    $('estadoServicios').className = 'text-xs font-bold ' + (caidos.length ? 'text-[var(--naranja)]' : 'text-[var(--teal)]');
  } catch {
    $('estadoServicios').textContent = '⚠ Gateway apagado';
  }
}

async function cargarResumen() {
  const r = await api('/api/resumen');
  const cont = $('resumen');
  cont.innerHTML = '';
  [
    ['Cervezas', r.cervezas_en_catalogo],
    ['Clientes', r.clientes],
    ['Pedidos', r.pedidos],
    ['Ventas', clp(r.ventas_totales)],
    ['Por reponer', r.stock_bajo.length + r.sin_stock.length],
  ].forEach(([nombre, valor]) => {
    const div = crear('div', 'bg-white rounded-2xl shadow-sm p-5');
    div.append(crear('p', 'text-sm text-[var(--tinta-suave)] font-bold', nombre), crear('p', 'font-display text-3xl', String(valor)));
    cont.appendChild(div);
  });
}

async function cargarCervezas() {
  const cervezas = await api('/api/cervezas');
  const tbody = $('tablaCervezas');
  tbody.innerHTML = '';
  cervezas.forEach((c) => {
    const tr = crear('tr', 'border-t border-black/5');
    const color = c.stock === 0 ? 'text-red-500' : c.stock <= 5 ? 'text-[var(--naranja)]' : '';
    tr.append(
      crear('td', 'py-2 font-bold', c.nombre),
      crear('td', '', c.estilo),
      crear('td', 'text-right', clp(c.precio)),
      crear('td', `text-right font-bold ${color}`, String(c.stock)),
    );
    const td = crear('td', 'text-right');
    td.appendChild(boton('+12', 'bg-[var(--crema)]', () => reponer(c, 12)));
    tr.appendChild(td);
    tbody.appendChild(tr);
  });
}

async function reponer(cerveza, cantidad) {
  // PUT al catálogo con el stock nuevo (ruta solo admin)
  await api(`/api/cervezas/${cerveza.id}`, { method: 'PUT', body: JSON.stringify({ stock: cerveza.stock + cantidad }) });
  await refrescar();
}

async function cargarPedidos() {
  const pedidos = await api('/api/pedidos');
  const cont = $('listaPedidos');
  cont.innerHTML = '';
  if (!pedidos.length) {
    cont.appendChild(crear('p', 'text-[var(--tinta-suave)]', 'Todavía no hay pedidos.'));
    return;
  }

  pedidos.reverse().forEach((p) => {
    const card = crear('article', 'rounded-2xl border-2 border-black/5 p-4');
    const top = crear('div', 'flex justify-between items-center mb-2');
    top.append(
      crear('strong', 'font-display text-lg', `#${p.id}`),
      crear('span', `text-xs font-black uppercase px-2 py-1 rounded-full ${COLOR_ESTADO[p.estado]}`, p.estado.replace('_', ' ')),
    );
    const items = crear('ul', 'text-sm text-[var(--tinta-suave)] my-2');
    p.items.forEach((i) => items.appendChild(crear('li', '', `${i.cantidad} × ${i.nombre}`)));
    const acciones = crear('div', 'flex gap-2 mt-3');
    if (SIGUIENTE[p.estado]) {
      acciones.appendChild(boton(`→ ${SIGUIENTE[p.estado].replace('_', ' ')}`, 'bg-[var(--tinta)] text-white', () => cambiarEstado(p.id, SIGUIENTE[p.estado])));
    }
    if (['recibido', 'preparando'].includes(p.estado)) {
      acciones.appendChild(boton('Cancelar', 'bg-black/5', () => cambiarEstado(p.id, 'cancelado')));
    }
    card.append(
      top,
      crear('p', 'font-bold text-sm', `${p.cliente} · ${p.correo}`),
      crear('p', 'text-xs text-[var(--tinta-suave)]', p.direccion),
      items,
      crear('p', 'font-bold', clp(p.total)),
      acciones,
    );
    cont.appendChild(card);
  });
}

async function cambiarEstado(id, estado) {
  try {
    await api(`/api/pedidos/${id}/estado`, { method: 'PATCH', body: JSON.stringify({ estado }) });
    await refrescar();
  } catch (e) {
    alert(e.message);
  }
}

$('formCerveza').addEventListener('submit', async (e) => {
  e.preventDefault();
  const f = e.target;
  const msg = $('msgCerveza');
  try {
    const nueva = await post('/api/cervezas', {
      nombre: f.nombre.value.trim(),
      estilo: f.estilo.value,
      precio: Number(f.precio.value),
      stock: Number(f.stock.value || 0),
    });
    msg.className = 'text-sm font-bold text-[var(--teal)]';
    msg.textContent = `${nueva.nombre} agregada 🍺`;
    f.reset();
    await refrescar();
  } catch (err) {
    msg.className = 'text-sm font-bold text-red-500';
    msg.textContent = err.message;
  }
});

async function refrescar() {
  await cargarEstado();
  await Promise.allSettled([cargarCervezas(), cargarPedidos(), cargarResumen()]);
}

(async () => {
  const usuario = await sesionActual();
  pintarHeader(usuario, 'admin');
  if (!usuario) return (location.href = 'cuenta.html');
  if (usuario.rol !== 'admin') {
    document.body.appendChild(crear('p', 'text-center py-20 font-display text-2xl', 'Esta sección es solo para administradores 🔒'));
    return;
  }
  $('panel').classList.remove('hidden');
  refrescar();
})();
