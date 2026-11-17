<?php
$titulo = 'Nosotros';
$pagina = 'nosotros';
include 'includes/header.php';

$anioFundacion = 2021;
$anios = (int) date('Y') - $anioFundacion;

$hitos = [
    2021 => 'Primer lote de IPA en una olla de 50 litros, en un garage.',
    2022 => 'Abrimos la sala de venta y lanzamos los growlers recargables.',
    2024 => 'Nace el Club Cervecero con 40 socios.',
    2026 => 'Despacho propio y más de 12 estilos en carta.',
];

$valores = [
    ['icon-hop',     'Frescura',   'No guardamos stock por meses: lo que sale del tanque se vende en semanas.'],
    ['icon-recycle', 'Reutilizar', 'Growlers y botellas retornables antes que vidrio nuevo.'],
    ['icon-mug',     'Comunidad',  'Catas abiertas y recetas que votan los socios del club.'],
];
?>

  <main class="mx-auto max-w-[1000px] px-6 py-14">
    <div class="text-center mb-14">
      <p class="font-display text-[var(--naranja)] text-lg mb-1">Nuestra historia</p>
      <h1 class="font-display text-4xl mb-4">Somos Craft & Beer</h1>
      <p class="text-[var(--tinta-suave)] text-lg max-w-2xl mx-auto">
        Llevamos <?= $anios ?> años haciendo cerveza a nuestro ritmo: lotes chicos, ingredientes buenos
        y harta prueba y error. Partimos como un hobby entre amigos y hoy despachamos a toda la región.
      </p>
    </div>

    <!-- Línea de tiempo -->
    <div class="relative border-l-4 border-[var(--ambar)] ml-4 mb-16 space-y-8">
      <?php foreach ($hitos as $anio => $texto): ?>
        <div class="pl-8 relative">
          <span class="absolute -left-[14px] top-1 w-6 h-6 rounded-full bg-[var(--naranja)] border-4 border-[var(--crema)]"></span>
          <p class="font-display text-2xl text-[var(--naranja)]"><?= $anio ?></p>
          <p><?= $texto ?></p>
        </div>
      <?php endforeach; ?>
    </div>

    <!-- Valores -->
    <h2 class="font-display text-3xl text-center mb-8">Lo que nos importa</h2>
    <div class="grid gap-6 md:grid-cols-3">
      <?php foreach ($valores as [$icono, $nombre, $texto]): ?>
        <div class="bg-white rounded-2xl p-6 shadow-sm text-center">
          <svg class="icon icon-lg text-[var(--teal)] mb-2"><use href="#<?= $icono ?>"></use></svg>
          <h3 class="font-display text-xl mb-1"><?= $nombre ?></h3>
          <p class="text-[var(--tinta-suave)]"><?= $texto ?></p>
        </div>
      <?php endforeach; ?>
    </div>
  </main>

<?php include 'includes/footer.php'; ?>
