// Renters page (utleie.html): owner-dashboard demo in the hero.

(function owner() {
  const box = document.getElementById('owner');
  if (!box) return;
  const kr = n => String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + ' kr';

  const BASE = 1240, SALE = 180;
  const start = () => ({
    rooms: [
      { n: 'Bakklandet', st: 'use', note: '6 seats · until 16:00' },
      { n: 'Nidelva', st: 'use', note: '8 seats · until 16:30' },
      { n: 'Munkholmen', st: 'sold', note: '4 seats · 14:10–14:55 · 160 kr' },
      { n: 'Phone booth 2', st: 'free', note: '1 seat · free now' },
    ],
    log: [['Agent: watching 4 rooms for you…', '']],
    earned: BASE, busy: false, done: false, just: -1,
  });
  let s = start();
  let timers = [];
  const chip = { use: 'In use', released: 'Released', sold: 'Sold', free: 'On standby' };

  box.innerHTML =
    '<div class="board-col">' +
      '<div class="board-head"><h2 class="board-title" data-k="Your rooms"></h2><span class="demo-tag" data-k="Demo"></span></div>' +
      '<ul class="rooms" id="o-rooms-list"></ul>' +
      '<div class="board-btns"><button class="btn btn-gold" id="o-rel" type="button" data-k="Release room"></button>' +
      '<button class="btn btn-ghost btn-sm" id="o-reset" type="button" data-k="Reset"></button></div>' +
    '</div>' +
    '<div class="board-col">' +
      '<div class="board-head"><span></span><span class="agent-on" id="o-status" aria-live="polite"></span></div>' +
      '<div class="earn"><p data-k="Earned today"></p><p class="kr" id="o-earned"></p><p data-k="from standby bookings"></p><span class="plus" id="o-plus">+' + SALE + ' kr</span></div>' +
      '<div class="log" id="o-log" aria-live="polite"></div>' +
    '</div>';
  const $ = id => document.getElementById(id);
  const rel = $('o-rel'), reset = $('o-reset'), earnedEl = $('o-earned');

  function render() {
    box.querySelectorAll('[data-k]').forEach(el => { el.textContent = el.dataset.k; });
    $('o-rooms-list').innerHTML = s.rooms.map((r, i) =>
      '<li class="room st-' + r.st + (i === s.just ? ' just' : '') + '"><div><strong>' + r.n +
      '</strong><span class="note">' + r.note + '</span></div><span class="chip">' + chip[r.st] + '</span></li>').join('');
    $('o-log').innerHTML = s.log.slice(-4).map(([en, cls]) => '<span' + (cls ? ' class="' + cls + '"' : '') + '>' + en + '</span>').join('');
    $('o-status').textContent = s.busy ? 'Agent selling' : 'Agent watching';
    box.classList.toggle('is-busy', s.busy);
    if (!counting) earnedEl.textContent = kr(s.earned);
    rel.disabled = s.busy || s.done;
  }

  // Animates the shown number only; s.earned is already the final value.
  let counting = 0;
  function countUp(from, to) {
    const t0 = performance.now(), dur = 900, id = ++counting;
    const done = () => { if (id === counting) { counting = 0; earnedEl.textContent = kr(to); } };
    (function step(now) {
      if (id !== counting) return;
      const p = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - p, 3);
      earnedEl.textContent = kr(from + (to - from) * e);
      if (p < 1) requestAnimationFrame(step); else done();
    })(t0);
    setTimeout(done, dur + 100);
  }

  function release() {
    if (s.busy || s.done) return;
    played = true;
    const room = s.rooms[0];
    const at = (ms, fn) => timers.push(setTimeout(() => { fn(); render(); }, ms));
    s.busy = true; s.just = 0;
    room.st = 'released'; room.note = 'Released 15:20 · 40 min left';
    s.log.push(['Bakklandet released by staff, 40 min left', 'gold']);
    render();
    at(1000, () => { s.just = -1; s.log.push(['Matching 5 people looking for a room…', '']); });
    at(2000, () => s.log.push(['Best fit: 4 people, screen, 15:25–16:00 (94%)', '']));
    at(3000, () => s.log.push(['Quote 180 kr, inside your 150–320 kr', '']));
    at(4000, () => {
      s.busy = false; s.done = true; s.just = 0;
      room.st = 'sold'; room.note = '4 people · 15:25–16:00 · 180 kr';
      s.log.push(['Booked. 5 min buffer kept before 16:00', 'ok']);
      const plus = $('o-plus'); plus.classList.remove('go'); void plus.offsetWidth; plus.classList.add('go');
      s.earned = BASE + SALE;
      countUp(BASE, BASE + SALE);
    });
  }

  rel.addEventListener('click', release);
  reset.addEventListener('click', () => { counting = 0; timers.forEach(clearTimeout); timers = []; s = start(); render(); });
  // The device section's button on this page releases the room here.
  document.addEventListener('ledig:release', () => {
    box.scrollIntoView({ behavior: 'smooth', block: 'center' });
    if (s.done) { counting = 0; timers.forEach(clearTimeout); timers = []; s = start(); render(); }
    setTimeout(release, 600);
  });

  // Play once by itself the first time the dashboard is in view.
  let played = false;
  if ('IntersectionObserver' in window && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const io = new IntersectionObserver(es => {
      if (!es.some(e => e.isIntersecting)) return;
      io.disconnect();
      setTimeout(() => { if (!played) release(); }, 1400);
    }, { threshold: 0.6 });
    io.observe(box);
  }
  render();
})();
