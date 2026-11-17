// Mi cuenta: login, registro y "mis pedidos"

const ETAPAS = ['recibido', 'preparando', 'en_camino', 'entregado'];
const regexCorreo = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const volverATienda = new URLSearchParams(location.search).get('volver') === 'tienda';

function mensaje(texto, ok = false) {
  $('msgAcceso').textContent = texto;
  $('msgAcceso').className = 'mt-4 text-center font-bold text-sm ' + (ok ? 'text-[var(--teal)]' : 'text-red-500');
}

function mostrarTab(cual) {
  const login = cual === 'login';
  $('formLogin').classList.toggle('hidden', !login);
  $('formRegistro').classList.toggle('hidden', login);
  $('tabLogin').classList.toggle('tab-activa', login);
  $('tabRegistro').classList.toggle('tab-activa', !login);
  mensaje('');
}

$('tabLogin').addEventListener('click', () => mostrarTab('login'));
$('tabRegistro').addEventListener('click', () => mostrarTab('registro'));

async function entrar(correo, password) {
  await post('/auth/login', { correo, password });
  // La cookie ya quedó guardada por el navegador; JS nunca ve el token
  location.href = volverATienda ? 'index.html?checkout' : 'cuenta.html';
}

$('formLogin').addEventListener('submit', async (e) => {
  e.preventDefault();
  const correo = $('loginCorreo').value.trim();
  const password = $('loginPass').value;
  if (!regexCorreo.test(correo) || !password) return mensaje('Completa correo y contraseña.');
  try {
    await entrar(correo, password);
  } catch (err) {
    mensaje(err.message);
  }
});

$('formRegistro').addEventListener('submit', async (e) => {
  e.preventDefault();
  const nombre = $('regNombre').value.trim();
  const correo = $('regCorreo').value.trim();
  const password = $('regPass').value;

  if (nombre.length < 2) return mensaje('Escribe tu nombre.');
  if (!regexCorreo.test(correo)) return mensaje('Ese correo no parece válido.');
  if (password.length < 8) return mensaje('La contraseña debe tener al menos 8 caracteres.');
  if (!$('regEdad').checked) return mensaje('Debes ser mayor de 18 años para comprar.');

  try {
    await post('/auth/registro', { nombre, correo, password });
    mensaje('¡Cuenta creada! Entrando…', true);
    await entrar(correo, password);
  } catch (err) {
    mensaje(err.message);
  }
});

// ---------- Perfil ----------

function tarjetaPedido(p) {
  const card = crear('article', 'bg-white rounded-2xl shadow-sm p-5');
  const cabecera = crear('div', 'flex justify-between items-center mb-3');
  cabecera.append(
    crear('strong', 'font-display text-xl', `#${p.id}`),
    crear('span', 'text-sm font-bold text-[var(--naranja)]', clp(p.total)),
  );
  card.appendChild(cabecera);

  const lista = crear('ul', 'text-sm text-[var(--tinta-suave)] mb-4');
  p.items.forEach((i) => lista.appendChild(crear('li', '', `${i.cantidad} × ${i.nombre}`)));
  card.appendChild(lista);

  if (p.estado === 'cancelado') {
    card.appendChild(crear('p', 'text-sm font-bold text-[var(--tinta-suave)]', 'Pedido cancelado'));
    return card;
  }

  // Barra de seguimiento
  const paso = ETAPAS.indexOf(p.estado);
  const barra = crear('div', 'grid grid-cols-4 gap-1');
  ETAPAS.forEach((etapa, i) => {
    const col = crear('div');
    col.append(
      crear('div', `h-2 rounded-full ${i <= paso ? 'bg-[var(--teal)]' : 'bg-black/10'}`),
      crear('p', `text-[10px] mt-1 font-bold uppercase ${i === paso ? '' : 'text-[var(--tinta-suave)]'}`, etapa.replace('_', ' ')),
    );
    barra.appendChild(col);
  });
  card.appendChild(barra);
  return card;
}

async function mostrarPerfil(usuario) {
  $('vistaPerfil').classList.remove('hidden');
  $('perfilNombre').textContent = usuario.nombre;
  $('perfilCorreo').textContent = `${usuario.correo} · ${usuario.rol}`;
  $('btnSalir').addEventListener('click', cerrarSesion);

  const cont = $('misPedidos');
  try {
    const pedidos = await api('/api/mis-pedidos');
    if (!pedidos.length) {
      const vacio = crear('p', 'text-[var(--tinta-suave)]', 'Aún no tienes pedidos. ');
      const link = crear('a', 'font-bold text-[var(--naranja)]', 'Ir a la tienda →');
      link.href = 'index.html';
      vacio.appendChild(link);
      cont.appendChild(vacio);
      return;
    }
    pedidos.reverse().forEach((p) => cont.appendChild(tarjetaPedido(p)));
  } catch (err) {
    cont.appendChild(crear('p', 'text-red-500 font-bold', err.message));
  }
}

(async () => {
  const usuario = await sesionActual();
  pintarHeader(usuario, 'cuenta');
  if (usuario) {
    mostrarPerfil(usuario);
  } else {
    $('vistaAcceso').classList.remove('hidden');
    if (volverATienda) mensaje('Ingresa para terminar tu compra 🍺', true);
  }
})();
