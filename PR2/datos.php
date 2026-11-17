<?php
date_default_timezone_set('America/Santiago');

// Datos del sitio en un solo lugar.
// Si mañana cambia un precio, se cambia aquí y se actualiza en todas las páginas.

$categorias = [
    'todos'    => 'Todos',
    'ipa'      => 'IPA & Ales',
    'stout'    => 'Stout & Porter',
    'lager'    => 'Lager & Pilsner',
    'wheat'    => 'Wheat & Red Ale',
    'growlers' => 'Growlers',
    'packs'    => 'Packs y Promos',
];

$unsplash = 'https://images.unsplash.com/';
$params   = '?auto=format&fit=crop&w=800&q=70';

$productos = [
    ['nombre' => 'IPA Tropical',      'cat' => 'ipa',   'precio' => 3990, 'destacado' => true,
     'desc' => 'Notas a mango y maracuyá, lúpulo bien presente. Botella 355 ml.',
     'img'  => $unsplash . 'photo-1627627045944-a6171e94783a' . $params],
    ['nombre' => 'Session IPA',       'cat' => 'ipa',   'precio' => 3790, 'destacado' => false,
     'desc' => 'Ligera y refrescante, ideal para tomar de a varias. Botella 355 ml.',
     'img'  => $unsplash . 'photo-1618183479302-1e0aa382c36b' . $params],
    ['nombre' => 'Imperial Stout',    'cat' => 'stout', 'precio' => 4490, 'destacado' => true,
     'desc' => 'Cuerpo denso, notas a chocolate y caramelo tostado. Botella 355 ml.',
     'img'  => $unsplash . 'photo-1642997702017-8531db99dd77' . $params],
    ['nombre' => 'Porter de Café',    'cat' => 'stout', 'precio' => 4290, 'destacado' => false,
     'desc' => 'Tostado profundo con infusión de café de origen. Botella 355 ml.',
     'img'  => $unsplash . 'photo-1642997702017-8531db99dd77' . $params],
    ['nombre' => 'Golden Lager',      'cat' => 'lager', 'precio' => 3490, 'destacado' => false,
     'desc' => 'Dorada, suave y fácil de beber. Botella 355 ml.',
     'img'  => $unsplash . 'photo-1618183479302-1e0aa382c36b' . $params],
    ['nombre' => 'Pilsner Clásica',   'cat' => 'lager', 'precio' => 3490, 'destacado' => false,
     'desc' => 'Amargor limpio y final crujiente. Botella 355 ml.',
     'img'  => $unsplash . 'photo-1618183479302-1e0aa382c36b' . $params],
    ['nombre' => 'Wheat Ale de Naranja', 'cat' => 'wheat', 'precio' => 3990, 'destacado' => true,
     'desc' => 'Trigo con un toque cítrico, refrescante y ligera. Botella 355 ml.',
     'img'  => $unsplash . 'photo-1711335792535-acacf1727eab' . $params],
    ['nombre' => 'Red Ale Ámbar',     'cat' => 'wheat', 'precio' => 3890, 'destacado' => false,
     'desc' => 'Maltosa y equilibrada, con notas a caramelo. Botella 355 ml.',
     'img'  => $unsplash . 'photo-1711335792535-acacf1727eab' . $params],
    // Los que no tienen foto usan un ícono con fondo de color
    ['nombre' => 'Growler IPA Tropical 1L', 'cat' => 'growlers', 'precio' => 9990, 'destacado' => false,
     'desc' => 'Envase recargable, ideal para compartir. 1 litro.',
     'icono' => 'icon-jar', 'fondo' => '#CFF1EA', 'color' => 'var(--teal)'],
    ['nombre' => 'Growler Imperial Stout 1,9L', 'cat' => 'growlers', 'precio' => 16990, 'destacado' => false,
     'desc' => 'Formato grande para juntas largas. 1,9 litros.',
     'icono' => 'icon-jar', 'fondo' => '#CFF1EA', 'color' => 'var(--teal)'],
    ['nombre' => 'Pack Degustación (6 estilos)', 'cat' => 'packs', 'precio' => 21990, 'destacado' => false,
     'desc' => 'Una botella de cada estilo: IPA, Stout, Lager, Wheat y más.',
     'icono' => 'icon-gift', 'fondo' => '#FFF0CF', 'color' => 'var(--naranja)', 'etiqueta' => 'Más vendido'],
    ['nombre' => 'Suscripción Club Cervecero', 'cat' => 'packs', 'precio' => 24990, 'destacado' => false,
     'desc' => '6 cervezas sorpresa cada mes + envío gratis. Cancela cuando quieras.',
     'icono' => 'icon-package', 'fondo' => '#EEE4FB', 'color' => 'var(--purpura)', 'sufijo' => '/mes'],
];

// $3.990 en vez de 3990
function precio_clp(int $monto): string
{
    return '$' . number_format($monto, 0, ',', '.');
}

// Atajo para escapar texto antes de imprimirlo en el HTML
function e(string $texto): string
{
    return htmlspecialchars($texto, ENT_QUOTES, 'UTF-8');
}
