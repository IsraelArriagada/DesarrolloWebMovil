<?php
$titulo = 'Inicio';
$pagina = 'inicio';
include 'includes/header.php';

// Solo los productos marcados como destacados en datos.php
$destacados = array_filter($productos, fn($p) => $p['destacado']);

// Saludo según la hora del servidor
$hora = (int) date('G');
if ($hora < 12)      { $saludo = '¡Buenos días'; }
elseif ($hora < 20)  { $saludo = '¡Buenas tardes'; }
else                 { $saludo = '¡Buenas noches'; }
?>

  <!-- Hero -->
  <section class="relative overflow-hidden bg-gradient-to-br from-[var(--ambar)] to-[var(--naranja)]">
    <span class="burbuja w-4 h-4 left-[12%]"></span>
    <span class="burbuja w-6 h-6 left-[30%]" style="animation-delay:1.5s"></span>
    <span class="burbuja w-3 h-3 left-[70%]" style="animation-delay:.8s"></span>
    <span class="burbuja w-5 h-5 left-[88%]" style="animation-delay:2.4s"></span>

    <div class="relative mx-auto max-w-[1200px] px-6 py-20 md:py-28 grid md:grid-cols-2 gap-10 items-center">
      <div>
        <p class="font-display text-white/90 text-lg mb-2"><?= $saludo ?>, cervecero!</p>
        <h1 class="font-display text-4xl md:text-6xl text-white leading-tight mb-5">
          Cerveza artesanal, <br>fresca y sin apuro.
        </h1>
        <p class="text-white/90 text-lg mb-8 max-w-md">
          Lotes chicos, recetas propias y growlers recargables. Elige tu estilo y te lo llevamos.
        </p>
        <div class="flex flex-wrap gap-3">
          <a href="productos.php" class="rounded-full bg-[var(--tinta)] text-white font-bold px-6 py-3 hover:scale-105 transition-transform">Ver catálogo</a>
          <a href="club.php" class="rounded-full bg-white/90 text-[var(--tinta)] font-bold px-6 py-3 hover:bg-white transition-colors">Únete al Club</a>
        </div>
      </div>
      <div class="hidden md:flex justify-center">
        <svg class="icon text-white animar-flotar" style="width:16rem;height:16rem;stroke-width:.9"><use href="#icon-mug"></use></svg>
      </div>
    </div>
  </section>

  <!-- Por qué elegirnos -->
  <section class="mx-auto max-w-[1200px] px-6 py-16 grid gap-6 md:grid-cols-3">
    <?php
    $beneficios = [
        ['icon-hop',     'Recetas propias',     'Cada estilo lo desarrollamos y probamos nosotros antes de embotellar.'],
        ['icon-recycle', 'Growlers recargables', 'Trae tu envase y recárgalo con 15% de descuento. Menos vidrio, más cerveza.'],
        ['icon-truck',   'Despacho rápido',      'Envío en 24–48 h en la región. Gratis sobre ' . precio_clp(25000) . '.'],
    ];
    foreach ($beneficios as [$icono, $tituloB, $texto]): ?>
      <div class="bg-white rounded-2xl p-6 shadow-sm">
        <svg class="icon icon-lg text-[var(--naranja)] mb-3"><use href="#<?= $icono ?>"></use></svg>
        <h3 class="font-display text-xl mb-1"><?= $tituloB ?></h3>
        <p class="text-[var(--tinta-suave)]"><?= $texto ?></p>
      </div>
    <?php endforeach; ?>
  </section>

  <!-- Destacados (se generan desde el arreglo de productos) -->
  <section class="mx-auto max-w-[1200px] px-6">
    <div class="flex items-end justify-between mb-8">
      <div>
        <p class="font-display text-[var(--naranja)] text-lg">Lo más pedido</p>
        <h2 class="font-display text-3xl">Destacados del mes</h2>
      </div>
      <a href="productos.php" class="font-bold text-sm hover:text-[var(--naranja)]">Ver todo →</a>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-7">
      <?php foreach ($destacados as $p) { include 'includes/tarjeta.php'; } ?>
    </div>
  </section>

<?php include 'includes/footer.php'; ?>
