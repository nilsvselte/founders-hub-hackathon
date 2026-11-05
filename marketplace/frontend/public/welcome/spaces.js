// Owned by the spaces/device agent: idle-time calculator and the device's Release button.

(function worth() {
  const form = document.getElementById('worth-calc');
  if (!form) return;
  const FEE = 0.15;
  const WEEKS_PER_MONTH = 52 / 12;
  const kr = n => Math.round(n).toLocaleString('nb-NO').replace(/ /g, ' ') + ' kr';
  const $ = id => document.getElementById(id);
  const total = $('w-total');

  function update() {
    const rooms = +form.rooms.value, hours = +form.hours.value, price = +form.price.value;
    $('o-rooms').textContent = rooms;
    $('o-hours').textContent = hours + ' h';
    $('o-price').textContent = price + ' kr';
    const hoursMonth = rooms * hours * WEEKS_PER_MONTH;
    const gross = hoursMonth * price;
    const fee = gross * FEE;
    $('w-hours').textContent = Math.round(hoursMonth) + ' h';
    $('w-gross').textContent = kr(gross);
    $('w-fee').textContent = '− ' + kr(fee);
    $('w-year').textContent = kr((gross - fee) * 12);
    total.textContent = kr(gross - fee);
    total.classList.add('bump');
    clearTimeout(update.t);
    update.t = setTimeout(() => total.classList.remove('bump'), 160);
  }
  form.addEventListener('input', update);
  form.addEventListener('submit', e => e.preventDefault());
  update();
})();

(function deviceButton() {
  const btn = document.getElementById('unit-release');
  if (!btn) return;
  const led = document.getElementById('unit-led');
  const screen = document.getElementById('unit-screen');
  let t = [];
  btn.addEventListener('click', () => {
    t.forEach(clearTimeout); t = [];
    btn.classList.remove('pulse'); void btn.offsetWidth; btn.classList.add('pulse');
    led.classList.remove('busy'); void led.offsetWidth; led.classList.add('busy');
    screen.textContent = 'Released. On sale until 16:00';
    // Renters page: the hero's owner dashboard (renters.js) listens for this and releases its room.
    t.push(setTimeout(() => document.dispatchEvent(new CustomEvent('ledig:release')), 700));
    const rel = document.getElementById('rel');
    if (rel) {
      t.push(setTimeout(() => {
        (rel.closest('.board') || rel).scrollIntoView({ behavior: 'smooth', block: 'center' });
        document.getElementById('rel')?.click();
      }, 700));
    }
    t.push(setTimeout(() => { led.classList.remove('busy'); screen.textContent = 'Ready'; }, 6000));
  });
})();
