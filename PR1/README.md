# Semana 1 — Sitio estático Craft & Beer

HTML + CSS (Tailwind por CDN y un `style.css` propio para animaciones e íconos). Sin JavaScript.

| Archivo | Contenido |
|---|---|
| `index.html` | Inicio: hero con burbujas animadas, beneficios, estilos de cerveza y bloque del Club |
| `productos.html` | Catálogo de 12 productos en grilla responsiva (1 → 2 → 3 columnas) |
| `cuenta.html` | Formulario de inicio de sesión (solo maqueta) |
| `css/style.css` | Animaciones (`@keyframes`), tamaños de íconos SVG e imágenes |

Los íconos son un *sprite* SVG: se definen una vez con `<symbol>` y se reutilizan con `<use href="#icon-...">`.

Para verlo, abre `index.html` en el navegador (o usa Live Server).
