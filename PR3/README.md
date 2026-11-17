# PR 3 — JavaScript

El mismo sitio del PR 1, ahora con interacción en `js/app.js` (un solo archivo para las 3 páginas).

**Catálogo (`productos.html`)**
- Filtros por categoría: se muestran u ocultan las tarjetas según `data-categoria` (`classList.toggle`).
- Botón "+ Agregar": lee `data-nombre` y `data-precio` y suma el producto al carrito.

**Carrito (en todas las páginas)**
- Panel lateral que se abre con el botón de la bolsa y se cierra con ✕ o con `Esc`.
- Botones + / − por producto, total, barra de avance hacia el envío gratis ($25.000) y "Vaciar".
- Se guarda en `localStorage`, así no se pierde al cambiar de página o recargar.
- Los nombres se insertan con `textContent` (no `innerHTML`) para evitar inyección de HTML.

**Login (`cuenta.html`)**
- Validación con expresión regular para el correo y largo mínimo para la contraseña.
- Marca en rojo el campo con error y muestra un mensaje.

Conceptos usados: `querySelectorAll`, `addEventListener`, `dataset`, `createElement`, arrow functions, `reduce`, `find`, `filter`, template strings, `localStorage` y `JSON`.
