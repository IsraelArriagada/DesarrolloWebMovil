<?php
$titulo = 'Club Cervecero';
$pagina = 'club';
include 'includes/header.php';

// Planes del club (equivale a la página de "servicios")
$planes = [
    ['nombre' => 'Lúpulo',   'precio' => 14990, 'cervezas' => 4,  'color' => 'var(--teal)',
     'extras' => ['Despacho gratis', 'Ficha de cata impresa']],
    ['nombre' => 'Malta',    'precio' => 24990, 'cervezas' => 6,  'color' => 'var(--naranja)', 'popular' => true,
     'extras' => ['Despacho gratis', 'Ficha de cata impresa', '1 estilo de edición limitada', '10% OFF en tienda']],
    ['nombre' => 'Barrica',  'precio' => 39990, 'cervezas' => 10, 'color' => 'var(--purpura)',
     'extras' => ['Despacho gratis', 'Ficha de cata impresa', '2 estilos de edición limitada', '15% OFF en tienda', 'Invitación a catas en la cervecería']],
];

$pasos = [
    'Eliges tu plan y los estilos que no quieres recibir.',
    'Cada mes armamos tu caja con lo más fresco del tanque.',
    'Te llega a la puerta con su ficha de cata.',
    'Pausas o cancelas cuando quieras, sin letra chica.',
];
?>

  <main class="mx-auto max-w-[1200px] px-6 py-14">
    <div class="text-center mb-12">
      <svg class="icon icon-xl text-[var(--purpura)] mb-2"><use href="#icon-package"></use></svg>
      <h1 class="font-display text-4xl mb-3">Club Cervecero</h1>
      <p class="text-[var(--tinta-suave)] max-w-xl mx-auto">Una caja sorpresa al mes con cervezas que todavía no llegan a la tienda. Elige el tamaño que te acomode.</p>
    </div>

    <!-- Planes -->
    <div class="grid gap-7 md:grid-cols-3 mb-20">
      <?php foreach ($planes as $plan): ?>
        <div class="bg-white rounded-3xl shadow-md p-7 flex flex-col relative <?= !empty($plan['popular']) ? 'ring-4 ring-[var(--ambar)] md:-translate-y-3' : '' ?>">
          <?php if (!empty($plan['popular'])): ?>
            <span class="absolute -top-3 left-1/2 -translate-x-1/2 bg-[var(--ambar)] text-[var(--tinta)] text-xs font-black uppercase px-3 py-1 rounded-full">El favorito</span>
          <?php endif; ?>
          <h2 class="font-display text-2xl mb-1" style="color: <?= $plan['color'] ?>">Plan <?= $plan['nombre'] ?></h2>
          <p class="text-[var(--tinta-suave)] mb-4"><?= $plan['cervezas'] ?> cervezas al mes</p>
          <p class="font-display text-4xl mb-6"><?= precio_clp($plan['precio']) ?><span class="text-base text-[var(--tinta-suave)]">/mes</span></p>
          <ul class="space-y-2 text-sm mb-8 flex-grow">
            <?php foreach ($plan['extras'] as $extra): ?>
              <li class="flex gap-2"><span style="color: <?= $plan['color'] ?>">✔</span> <?= $extra ?></li>
            <?php endforeach; ?>
          </ul>
          <a href="contacto.php?motivo=club" class="text-center rounded-full text-white font-bold py-3 hover:opacity-90 transition-opacity" style="background: <?= $plan['color'] ?>">Lo quiero</a>
        </div>
      <?php endforeach; ?>
    </div>

    <!-- Cómo funciona -->
    <h2 class="font-display text-3xl text-center mb-8">¿Cómo funciona?</h2>
    <ol class="grid gap-5 md:grid-cols-4">
      <?php foreach ($pasos as $i => $paso): ?>
        <li class="bg-white rounded-2xl p-6 shadow-sm">
          <span class="font-display text-4xl text-[var(--ambar)]"><?= $i + 1 ?></span>
          <p class="mt-2"><?= $paso ?></p>
        </li>
      <?php endforeach; ?>
    </ol>
  </main>

<?php include 'includes/footer.php'; ?>
