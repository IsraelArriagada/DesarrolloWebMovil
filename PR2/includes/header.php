<?php
// Cabecera común. Cada página define antes:
//   $titulo -> lo que sale en la pestaña del navegador
//   $pagina -> para marcar en naranjo el link activo del menú
require_once __DIR__ . '/datos.php';

$titulo = $titulo ?? 'Craft & Beer';
$pagina = $pagina ?? '';

$menu = [
    'inicio'    => ['Inicio',         'index.php'],
    'productos' => ['Productos',      'productos.php'],
    'club'      => ['Club Cervecero', 'club.php'],
    'nosotros'  => ['Nosotros',       'nosotros.php'],
    'contacto'  => ['Contacto',       'contacto.php'],
];
?>
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title><?= e($titulo) ?> — Craft & Beer</title>

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700&family=Nunito:wght@400;600;700;800&display=swap" rel="stylesheet">

  <script src="https://unpkg.com/@tailwindcss/browser@4.3.3/dist/index.global.js" crossorigin="anonymous"></script>
  <link rel="stylesheet" href="css/style.css">

  <style type="text/tailwindcss">
    @theme {
      --font-display: 'Fredoka', system-ui, sans-serif;
      --ambar: #FFB100;
      --ambar-suave: #FFE29A;
      --naranja: #FF6B4A;
      --teal: #1FAE93;
      --purpura: #8B4FE3;
      --tinta: #2B1B12;
      --tinta-suave: #7A6A5D;
      --crema: #FFF8EA;
    }
    body { background-color: var(--crema); color: var(--tinta); font-family: 'Nunito', system-ui, sans-serif; }
  </style>
</head>
<body>

<?php include __DIR__ . '/iconos.php'; ?>

  <!-- Franja de promo -->
  <div class="w-full bg-[var(--tinta)] text-center px-4 py-2">
    <p class="text-[13px] font-bold text-white flex items-center justify-center gap-1.5 flex-wrap">
      <svg class="icon icon-sm text-[var(--ambar)]"><use href="#icon-truck"></use></svg>
      Despacho gratis sobre <?= precio_clp(25000) ?> &nbsp;•&nbsp;
      <svg class="icon icon-sm text-[var(--ambar)]"><use href="#icon-recycle"></use></svg>
      Recarga tu growler con <span class="text-[var(--ambar)]">15% OFF</span>
    </p>
  </div>

  <header class="w-full bg-white/90 backdrop-blur shadow-sm sticky top-0 z-50">
    <div class="mx-auto max-w-[1280px] px-6 h-[70px] flex items-center justify-between gap-4">
      <a href="index.php" class="flex items-center gap-2 font-display text-xl md:text-2xl tracking-tight text-[var(--tinta)]">
        <svg class="icon icon-lg text-[var(--naranja)]"><use href="#icon-mug"></use></svg>
        Craft <span class="text-[var(--naranja)]">&</span> Beer
      </a>

      <nav class="hidden lg:flex items-center gap-7 text-sm font-bold">
        <?php foreach ($menu as $clave => [$texto, $url]): ?>
          <a href="<?= $url ?>"
             class="<?= $clave === $pagina ? 'text-[var(--naranja)]' : 'hover:text-[var(--naranja)] transition-colors' ?>">
            <?= $texto ?>
          </a>
        <?php endforeach; ?>
      </nav>

      <!-- Menú para celular: un <details> que se abre sin JavaScript -->
      <details class="lg:hidden relative">
        <summary class="list-none cursor-pointer font-bold text-sm px-3 py-2 rounded-full bg-[var(--crema)]">Menú ☰</summary>
        <div class="absolute right-0 mt-2 w-48 bg-white rounded-2xl shadow-xl p-3 flex flex-col gap-1">
          <?php foreach ($menu as $clave => [$texto, $url]): ?>
            <a href="<?= $url ?>" class="px-3 py-2 rounded-xl font-bold text-sm <?= $clave === $pagina ? 'bg-[var(--crema)] text-[var(--naranja)]' : 'hover:bg-[var(--crema)]' ?>"><?= $texto ?></a>
          <?php endforeach; ?>
        </div>
      </details>
    </div>
  </header>
