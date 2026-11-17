<?php
$titulo = 'Contacto';
$pagina = 'contacto';
include 'includes/header.php';

$motivos = [
    'pedido'  => 'Consulta por un pedido',
    'club'    => 'Quiero unirme al Club Cervecero',
    'evento'  => 'Cerveza para un evento',
    'otro'    => 'Otro',
];

// Valores iniciales. "motivo" puede venir desde club.php (?motivo=club)
$datos   = ['nombre' => '', 'correo' => '', 'motivo' => $_GET['motivo'] ?? 'pedido', 'mensaje' => ''];
$errores = [];
$enviado = false;

// Solo se valida cuando el formulario se envía (POST)
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    foreach ($datos as $campo => $_) {
        $datos[$campo] = trim($_POST[$campo] ?? '');
    }

    if (mb_strlen($datos['nombre']) < 2) {
        $errores['nombre'] = 'Escribe tu nombre.';
    }
    if (!filter_var($datos['correo'], FILTER_VALIDATE_EMAIL)) {
        $errores['correo'] = 'Ese correo no parece válido.';
    }
    if (!array_key_exists($datos['motivo'], $motivos)) {
        $errores['motivo'] = 'Elige un motivo de la lista.';
    }
    if (mb_strlen($datos['mensaje']) < 10) {
        $errores['mensaje'] = 'Cuéntanos un poco más (mínimo 10 caracteres).';
    }
    if (empty($_POST['mayor_edad'])) {
        $errores['mayor_edad'] = 'Debes confirmar que eres mayor de 18 años.';
    }

    $enviado = empty($errores);
}

// Clase del input: borde rojo si ese campo tiene error
function clase_input(string $campo, array $errores): string
{
    $base = 'w-full rounded-xl border-2 px-4 py-2.5 outline-none transition-colors ';
    return $base . (isset($errores[$campo]) ? 'border-red-400' : 'border-black/10 focus:border-[var(--naranja)]');
}
?>

  <main class="mx-auto max-w-[1100px] px-6 py-14 grid gap-10 md:grid-cols-[1fr_1.4fr]">

    <!-- Datos de contacto -->
    <section>
      <p class="font-display text-[var(--naranja)] text-lg mb-1">Hablemos</p>
      <h1 class="font-display text-4xl mb-4">Contacto</h1>
      <p class="text-[var(--tinta-suave)] mb-8">¿Dudas con tu pedido, quieres cerveza para un cumpleaños o entrar al club? Escríbenos y te respondemos en el día.</p>

      <ul class="space-y-5">
        <li class="flex gap-3"><svg class="icon text-[var(--naranja)]"><use href="#icon-pin"></use></svg> Av. Lúpulo 1234, Santiago</li>
        <li class="flex gap-3"><svg class="icon text-[var(--naranja)]"><use href="#icon-mail"></use></svg> hola@craftandbeer.cl</li>
        <li class="flex gap-3"><svg class="icon text-[var(--naranja)]"><use href="#icon-clock"></use></svg> Lun a Vie 11:00–20:00 · Sáb 12:00–22:00</li>
      </ul>
    </section>

    <!-- Formulario -->
    <section class="bg-white rounded-3xl shadow-xl p-8">
      <?php if ($enviado): ?>
        <div class="text-center py-10">
          <svg class="icon icon-xl text-[var(--teal)] mb-3"><use href="#icon-mug"></use></svg>
          <h2 class="font-display text-3xl mb-2">¡Salud, <?= e($datos['nombre']) ?>!</h2>
          <p class="text-[var(--tinta-suave)] mb-1">Recibimos tu mensaje sobre <strong><?= e($motivos[$datos['motivo']]) ?></strong>.</p>
          <p class="text-[var(--tinta-suave)] mb-8">Te responderemos a <strong><?= e($datos['correo']) ?></strong>.</p>
          <a href="contacto.php" class="rounded-full border-2 border-[var(--tinta)] px-6 py-2.5 font-bold hover:bg-[var(--tinta)] hover:text-white transition-colors">Enviar otro mensaje</a>
        </div>
      <?php else: ?>
        <?php if ($errores): ?>
          <p class="mb-5 rounded-xl bg-red-50 text-red-600 font-bold text-sm px-4 py-3">Revisa los campos marcados en rojo.</p>
        <?php endif; ?>

        <!-- novalidate: así la validación la hace PHP y se nota en la entrega -->
        <form method="post" action="contacto.php" class="space-y-5" novalidate>
          <div>
            <label for="nombre" class="block text-sm font-bold mb-1.5">Nombre</label>
            <input id="nombre" name="nombre" value="<?= e($datos['nombre']) ?>" class="<?= clase_input('nombre', $errores) ?>">
            <?php if (isset($errores['nombre'])): ?><p class="text-red-500 text-sm mt-1"><?= $errores['nombre'] ?></p><?php endif; ?>
          </div>

          <div>
            <label for="correo" class="block text-sm font-bold mb-1.5">Correo</label>
            <input id="correo" name="correo" type="email" value="<?= e($datos['correo']) ?>" placeholder="correo@ejemplo.com" class="<?= clase_input('correo', $errores) ?>">
            <?php if (isset($errores['correo'])): ?><p class="text-red-500 text-sm mt-1"><?= $errores['correo'] ?></p><?php endif; ?>
          </div>

          <div>
            <label for="motivo" class="block text-sm font-bold mb-1.5">Motivo</label>
            <select id="motivo" name="motivo" class="<?= clase_input('motivo', $errores) ?> bg-white">
              <?php foreach ($motivos as $clave => $texto): ?>
                <option value="<?= $clave ?>" <?= $clave === $datos['motivo'] ? 'selected' : '' ?>><?= $texto ?></option>
              <?php endforeach; ?>
            </select>
          </div>

          <div>
            <label for="mensaje" class="block text-sm font-bold mb-1.5">Mensaje</label>
            <textarea id="mensaje" name="mensaje" rows="5" class="<?= clase_input('mensaje', $errores) ?>"><?= e($datos['mensaje']) ?></textarea>
            <?php if (isset($errores['mensaje'])): ?><p class="text-red-500 text-sm mt-1"><?= $errores['mensaje'] ?></p><?php endif; ?>
          </div>

          <div>
            <label class="flex items-center gap-2 text-sm font-bold">
              <input type="checkbox" name="mayor_edad" value="1" <?= !empty($_POST['mayor_edad']) ? 'checked' : '' ?> class="w-4 h-4 accent-[var(--naranja)]">
              Confirmo que soy mayor de 18 años
            </label>
            <?php if (isset($errores['mayor_edad'])): ?><p class="text-red-500 text-sm mt-1"><?= $errores['mayor_edad'] ?></p><?php endif; ?>
          </div>

          <button type="submit" class="w-full rounded-full bg-[var(--naranja)] text-white font-bold py-3 hover:bg-[var(--tinta)] transition-colors cursor-pointer">Enviar mensaje</button>
        </form>
      <?php endif; ?>
    </section>
  </main>

<?php include 'includes/footer.php'; ?>
