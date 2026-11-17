  <footer class="bg-[var(--tinta)] text-white/70 mt-20">
    <div class="mx-auto max-w-[1200px] px-6 py-12 grid gap-8 md:grid-cols-3 text-sm">
      <div>
        <p class="font-display text-xl text-white mb-2">Craft <span class="text-[var(--naranja)]">&</span> Beer</p>
        <p>Cerveza artesanal de verdad, hecha en lotes chicos y despachada fresca a tu casa.</p>
      </div>
      <div>
        <p class="font-bold text-white mb-2">Navegación</p>
        <ul class="space-y-1">
          <?php foreach ($menu as [$texto, $url]): ?>
            <li><a class="hover:text-[var(--ambar)]" href="<?= $url ?>"><?= $texto ?></a></li>
          <?php endforeach; ?>
        </ul>
      </div>
      <div>
        <p class="font-bold text-white mb-2">Horario de la tienda</p>
        <p>Lun a Vie: 11:00 – 20:00<br>Sáb: 12:00 – 22:00</p>
      </div>
    </div>
    <p class="text-center text-white/40 text-xs pb-8">
      Craft & Beer® <?= date('Y') ?> — Bebe con responsabilidad. Venta solo a mayores de 18 años.
    </p>
  </footer>

</body>
</html>
