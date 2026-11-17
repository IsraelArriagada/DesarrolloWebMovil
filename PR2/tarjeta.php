<?php
// Tarjeta de un producto. Se usa dentro de un foreach que entrega $p.
// La comparten index.php (destacados) y productos.php (catálogo).
?>
<article class="bg-white rounded-2xl shadow-md hover:shadow-xl hover:-translate-y-1 transition-all overflow-hidden <?= isset($p['etiqueta']) ? 'border-2 border-[var(--ambar)]' : '' ?>">
  <?php if (isset($p['img'])): ?>
    <div class="h-44 overflow-hidden">
      <img class="producto-img" src="<?= e($p['img']) ?>" alt="<?= e($p['nombre']) ?>" loading="lazy">
    </div>
  <?php else: ?>
    <div class="h-44 flex items-center justify-center relative" style="background: <?= $p['fondo'] ?>">
      <svg class="icon icon-xl" style="color: <?= $p['color'] ?>"><use href="#<?= $p['icono'] ?>"></use></svg>
      <?php if (isset($p['etiqueta'])): ?>
        <span class="absolute top-3 right-3 bg-[var(--naranja)] text-white text-[10px] font-black uppercase px-2 py-1 rounded-full"><?= e($p['etiqueta']) ?></span>
      <?php endif; ?>
    </div>
  <?php endif; ?>

  <div class="p-5">
    <p class="text-[11px] font-black uppercase tracking-wide text-[var(--teal)] mb-1"><?= e($categorias[$p['cat']]) ?></p>
    <h2 class="font-black text-lg mb-1"><?= e($p['nombre']) ?></h2>
    <p class="text-sm text-[var(--tinta-suave)] mb-4 min-h-[40px]"><?= e($p['desc']) ?></p>
    <strong class="font-display text-lg text-[var(--naranja)]">
      <?= precio_clp($p['precio']) ?><?= $p['sufijo'] ?? '' ?>
    </strong>
  </div>
</article>
