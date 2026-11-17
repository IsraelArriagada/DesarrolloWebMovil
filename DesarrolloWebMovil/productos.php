<?php
$titulo = 'Catálogo';
$pagina = 'productos';
include 'includes/header.php';

// El filtro llega por la URL: productos.php?cat=stout
// Si viene algo raro (o nada), se muestra "todos".
$cat = $_GET['cat'] ?? 'todos';
if (!array_key_exists($cat, $categorias)) {
    $cat = 'todos';
}

$lista = ($cat === 'todos')
    ? $productos
    : array_filter($productos, fn($p) => $p['cat'] === $cat);
?>

  <main class="mx-auto max-w-[1200px] px-6 py-14">
    <div class="text-center mb-10">
      <p class="font-display text-[var(--naranja)] text-lg mb-1">CRAFT & BEER</p>
      <h1 class="font-display text-4xl mb-3">Nuestro catálogo</h1>
      <p class="text-[var(--tinta-suave)]">Botellas, growlers y packs para cada ocasión.</p>
    </div>

    <!-- Filtros: son links, el filtrado lo hace PHP en el servidor -->
    <div class="flex flex-wrap justify-center gap-2.5 mb-4">
      <?php foreach ($categorias as $clave => $nombre): ?>
        <a href="productos.php?cat=<?= $clave ?>"
           class="border-2 rounded-full px-4 py-2 text-sm font-bold transition-colors
                  <?= $clave === $cat
                        ? 'bg-[var(--tinta)] text-white border-[var(--tinta)]'
                        : 'bg-white border-[var(--tinta)]/15 hover:border-[var(--tinta)]' ?>">
          <?= e($nombre) ?>
        </a>
      <?php endforeach; ?>
    </div>

    <p class="text-center text-sm text-[var(--tinta-suave)] mb-10">
      Mostrando <strong><?= count($lista) ?></strong> de <?= count($productos) ?> productos
    </p>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-7">
      <?php foreach ($lista as $p) { include 'includes/tarjeta.php'; } ?>
    </div>
  </main>

<?php include 'includes/footer.php'; ?>
