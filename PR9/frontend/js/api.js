// Craft & Beer — PR 9
// Código compartido por las 3 páginas: llamadas al gateway, sesión y header.

// Con docker compose el frontend y el gateway quedan en el mismo origen (nginx
// reenvía /api y /auth), así que basta con rutas relativas. En desarrollo
// (Live Server en el 5500) se llama al gateway en el 8000.
const API = location.port === '8080' ? '' : `http://${location.hostname || '127.0.0.1'}:8000`;

const clp = (n) => '$' + Number(n).toLocaleString('es-CL');
const $ = (id) => document.getElementById(id);

async function api(ruta, opciones = {}) {
  const r = await fetch(API + ruta, {
    credentials: 'include', // manda la cookie de sesión (HttpOnly, JS no la ve)
    ...opciones,
    headers: { 'Content-Type': 'application/json', ...(opciones.headers || {}) },
  });
  const datos = await r.json().catch(() => ({}));
  if (!r.ok) {
    const detalle = Array.isArray(datos.detail) ? datos.detail.map((d) => d.msg).join(', ') : datos.detail;
    const error = new Error(detalle || `Error ${r.status}`);
    error.status = r.status;
    throw error;
  }
  return datos;
}

const post = (ruta, cuerpo) => api(ruta, { method: 'POST', body: JSON.stringify(cuerpo ?? {}) });

// Devuelve el usuario logueado o null
async function sesionActual() {
  try {
    return await api('/auth/me');
  } catch {
    return null;
  }
}

async function cerrarSesion() {
  await post('/auth/logout').catch(() => {});
  location.href = 'index.html';
}

function crear(tag, clases = '', texto = '') {
  const el = document.createElement(tag);
  if (clases) el.className = clases;
  if (texto !== '') el.textContent = texto;
  return el;
}

// Header común. "activa" marca la página actual.
function pintarHeader(usuario, activa) {
  const links = [['index.html', 'Tienda', 'tienda'], ['cuenta.html', usuario ? 'Mi cuenta' : 'Ingresar', 'cuenta']];
  if (usuario?.rol === 'admin') links.push(['admin.html', 'Admin', 'admin']);

  const header = $('header');
  header.className = 'w-full bg-white/90 backdrop-blur shadow-sm sticky top-0 z-50';
  header.innerHTML = `
    <div class="mx-auto max-w-[1280px] px-6 h-[70px] flex items-center justify-between gap-4">
      <a href="index.html" class="flex items-center gap-2 font-display text-xl md:text-2xl tracking-tight">
        <svg class="icon icon-lg text-[var(--naranja)]" viewBox="0 0 24 24"><path d="M5 7h10v11a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V7Z"/><path d="M15 9h2.5a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H15"/><path d="M7 7V5.5A1.5 1.5 0 0 1 8.5 4H12"/></svg>
        Craft <span class="text-[var(--naranja)]">&</span> Beer
      </a>
      <nav id="navLinks" class="flex items-center gap-5 text-sm font-bold"></nav>
    </div>`;

  const nav = $('navLinks');
  links.forEach(([url, texto, clave]) => {
    const a = crear('a', clave === activa ? 'text-[var(--naranja)]' : 'hover:text-[var(--naranja)] transition-colors', texto);
    a.href = url;
    nav.appendChild(a);
  });
  if (usuario) {
    const hola = crear('span', 'hidden md:inline text-[var(--tinta-suave)]', `Hola, ${usuario.nombre.split(' ')[0]}`);
    nav.prepend(hola);
  }
  // Las páginas que tienen carrito agregan su botón aquí
  return nav;
}
