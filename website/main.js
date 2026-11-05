// Product name lives here. Change it once and every [data-product] element and the tab title follow.
const PRODUCT_NAME = 'Mesh standby';

document.title = PRODUCT_NAME;
document.querySelectorAll('[data-product]').forEach(el => { el.textContent = PRODUCT_NAME; });

// Hero board: a released room jumps to #1 with a quote.
(function board() {
  const list = document.getElementById('matches');
  const log = document.getElementById('log');
  const quote = document.getElementById('quote');
  const rel = document.getElementById('rel');
  const acc = document.getElementById('accept');
  const startHTML = list.innerHTML;
  let timers = [];
  let loop = null;
  const at = (ms, fn) => timers.push(setTimeout(fn, ms));

  function line(text, ok) {
    const s = document.createElement('span');
    s.textContent = text;
    if (ok) s.className = 'ok';
    log.appendChild(s);
    while (log.children.length > 4) log.firstChild.remove();
  }
  function renumber() {
    [...list.children].forEach((li, i) => { li.querySelector('.rank').textContent = i + 1; });
  }
  function reset() {
    timers.forEach(clearTimeout); timers = [];
    list.innerHTML = startHTML;
    log.innerHTML = '<span>Agent: watching 6 rooms for you…</span>';
    quote.hidden = true;
    rel.disabled = false;
    acc.disabled = false; acc.textContent = 'Accept';
  }
  function release() {
    rel.disabled = true;
    line('15:20 Staff released Bakklandet, free 15:25–16:00');
    at(800, () => line('Scoring it against your 6 preferences…'));
    at(1700, () => {
      const li = document.createElement('li');
      li.className = 'm new enter'; li.id = 'bk';
      li.innerHTML = '<span class="rank">1</span><div><strong>Bakklandet</strong> · 15:25–16:00<span class="why">4 seats, screen, whiteboard. In your window.</span></div><span class="fit">94%</span>';
      list.prepend(li); renumber();
      line('New best fit: Bakklandet, 94%', true);
    });
    at(2600, () => { line('Quote 180 kr, inside the space’s limits. Held 2 min.'); quote.hidden = false; });
  }
  function stopLoop() { if (loop) { clearInterval(loop); loop = null; } }

  rel.addEventListener('click', () => { stopLoop(); reset(); release(); });
  document.getElementById('reset').addEventListener('click', () => { stopLoop(); reset(); });
  acc.addEventListener('click', () => {
    stopLoop();
    acc.disabled = true; acc.textContent = 'Booked';
    line('Rechecked the slot. Booking confirmed.', true);
    const b = document.getElementById('bk');
    if (b) { b.className = 'm booked'; b.querySelector('.fit').textContent = 'Booked'; }
  });

  const reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!reduce) {
    at(2200, release);
    loop = setInterval(() => { reset(); at(1200, release); }, 11000);
  }
})();

// How it works: one step open at a time.
(function steps() {
  const buttons = document.querySelectorAll('.step');
  const panels = document.querySelectorAll('.panel');
  buttons.forEach(btn => btn.addEventListener('click', () => {
    const n = btn.dataset.step;
    buttons.forEach(b => { const on = b === btn; b.classList.toggle('is-on', on); b.setAttribute('aria-pressed', on); });
    panels.forEach(p => { p.hidden = p.dataset.panel !== n; });
  }));
})();
