# Semana 2 — Craft & Beer en PHP

El sitio de la semana 1 pasado a PHP. Las partes que se repetían en cada página (head, menú, footer, íconos) quedaron en `includes/`. Los productos ahora salen de un arreglo y no están escritos a mano en el HTML.

## Cómo correrlo

```bash
cd Semana_2
php -S localhost:8000
```

Después se abre `http://localhost:8000` en el navegador. También funciona con XAMPP si copias la carpeta a `htdocs/`.

## Páginas

| Archivo | Qué hace |
|---|---|
| `index.php` | Hero con un saludo que cambia según la hora, beneficios y productos destacados (`array_filter`) |
| `productos.php` | Catálogo con filtro por categoría vía `$_GET` (`productos.php?cat=stout`) |
| `club.php` | Planes de suscripción armados con `foreach` |
| `nosotros.php` | Historia con línea de tiempo y años calculados con `date()` |
| `contacto.php` | Formulario `POST` validado en el servidor (nombre, correo con `filter_var`, motivo, mensaje y mayoría de edad) |

## Includes

- `datos.php`: arreglos de productos y categorías, más las funciones `precio_clp()` y `e()` (`htmlspecialchars`)
- `header.php`: `<head>` + franja de promo + menú, con el link activo según `$pagina`
- `footer.php`: pie de página con el año automático
- `tarjeta.php`: tarjeta de producto que se reutiliza en el inicio y en el catálogo
- `iconos.php`: sprite de íconos SVG

## Seguridad básica

Todo lo que escribe el usuario se imprime con `e()` para evitar inyección de HTML. El filtro del catálogo solo acepta categorías que existen en el arreglo; cualquier otra cosa muestra "todos".
