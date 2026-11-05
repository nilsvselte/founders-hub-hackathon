// Renters page (utleie.html): owner-dashboard demo in the hero, and Bokmål for this page's own text.
// i18n.js owns the NO/EN toggle and sets <html lang>; this follows it.

const RENTERS_NO = {
  // Nav
  'Find a room': 'Finn rom',
  'Rent out rooms': 'Leie ut rom',
  "What it's worth": 'Hva det er verdt',
  'Pricing': 'Pris',
  'Book a demo': 'Bli utleier',
  // Hero
  'For coworking spaces, offices and venues': 'For kontorfellesskap, kontorer og lokaler',
  'Meetings end early.': 'Møtet sluttet tidlig?',
  "Your rooms shouldn't sit empty.": 'Tjen penger på ledig møteromstid.',
  "Staff press one button when a room frees up. Ledig's agent sells the rest of the hour to people nearby, at a price inside your limits, and books it for you.":
    'De ansatte trykker på én knapp når et rom blir ledig. Agenten til Ledig selger resten av timen til folk i nærheten, til en pris innenfor grensene dine, og booker den for deg.',
  'Become a host': 'Bli utleier',
  'What is my idle time worth?': 'Hva er den ledige tiden min verdt?',
  // How
  'Sell the hour you were going to lose.': 'Selg timen du ellers ville tapt.',
  'By the door': 'Ved døra',
  'One button per room': 'Én knapp per rom',
  'Setup': 'Oppsett', 'about 10 min': 'ca. 10 min',
  'Power': 'Strøm', 'USB-C or battery': 'USB-C eller batteri',
  'Staff training': 'Opplæring', 'none': 'ingen',
  'Your limits, Bakklandet': 'Dine grenser, Bakklandet',
  'Price floor': 'Minstepris', 'Price ceiling': 'Makspris', 'Turnaround buffer': 'Buffer mellom gjester',
  'On standby': 'På standby', 'Mon–Fri, 08–18': 'man–fre, 08–18',
  'Agent log': 'Agentlogg', 'Bakklandet released': 'Bakklandet frigitt', 'Best buyer fit': 'Beste kjøpertreff',
  'Quoted': 'Tilbudt', 'Booked, calendar updated': 'Booket, kalender oppdatert',
  'Put a button by the door': 'Sett en knapp ved døra',
  'A small device per room. When a meeting ends early, staff press it once. No app, nothing to type.':
    'En liten enhet per rom. Når et møte slutter tidlig, trykker de ansatte én gang. Ingen app, ingenting å skrive.',
  'Set your limits once': 'Sett grensene dine én gang',
  'A price floor and ceiling per room, a turnaround buffer for tidying, and which rooms may go on standby, and when.':
    'Minste- og makspris per rom, en buffer til rydding, og hvilke rom som kan legges ut på standby, og når.',
  'The agent sells and books': 'Agenten selger og booker',
  'It matches the freed time to people already looking, quotes inside your limits, books the slot and updates your calendar.':
    'Den matcher den ledige tiden med folk som allerede leter, gir tilbud innenfor grensene dine, booker tiden og oppdaterer kalenderen din.',
  // Control
  'You decide. The agent only sells inside your rules.': 'Du bestemmer. Agenten selger bare innenfor reglene dine.',
  'Price limits': 'Prisgrenser',
  'Floor and ceiling, per room': 'Minste- og makspris, per rom',
  'The agent never quotes below your floor or above your ceiling. Last-minute slots go nearer the floor.':
    'Agenten går aldri under minsteprisen eller over maksprisen. Tider i siste liten selges nærmere minsteprisen.',
  'Rooms and hours': 'Rom og tider',
  'Which rooms, and when': 'Hvilke rom, og når',
  'Put only some rooms on standby, only on weekdays, or never during your own peak hours.':
    'Legg bare noen rom på standby, bare på hverdager, eller aldri i dine egne travle timer.',
  'Turnaround': 'Rydding',
  'A buffer to tidy': 'En buffer til rydding',
  'Choose how many minutes stay free between guests. The agent books around it.':
    'Velg hvor mange minutter som holdes ledig mellom gjester. Agenten booker rundt det.',
  'Payouts': 'Utbetaling',
  'Paid out monthly': 'Utbetalt hver måned',
  'Every booking shows in one report, with the fee already taken off. Paid to your account each month.':
    'Alle bookinger vises i én rapport, med avgiften trukket fra. Utbetales til kontoen din hver måned.',
  // Pricing
  'You only pay when a room sells.': 'Du betaler bare når et rom blir solgt.',
  'of each standby booking': 'av hver standby-booking',
  'Taken off before payout. If nothing sells, you pay nothing.': 'Trekkes fra før utbetaling. Selges ingenting, betaler du ingenting.',
  'Monthly fee': 'Månedsavgift',
  'To list your rooms': 'For å legge ut rommene',
  'Per button, one-off': 'Per knapp, engangsbeløp',
  'estimate': 'anslag',
  'Device price is a placeholder until hardware is costed.': 'Enhetsprisen er en plassholder til maskinvaren er priset.',
  // Closing
  'Your empty rooms could': 'De tomme rommene dine kan',
  'earn today.': 'tjene penger i dag.',
  'Live at Digs, Trondheim. We set up the buttons and your limits with you in one visit.':
    'Nå på Digs i Trondheim. Vi setter opp knappene og grensene dine sammen med deg på ett besøk.',
  // Dashboard (rendered by JS)
  'Your rooms': 'Rommene dine',
  'Demo': 'Demo',
  'Agent watching': 'Agenten følger med',
  'Agent selling': 'Agenten selger',
  'In use': 'I bruk',
  'Released': 'Frigitt',
  'Sold': 'Solgt',
  'On standby': 'På standby',
  'Release room': 'Frigi rommet',
  'Reset': 'Nullstill',
  'Earned today': 'Tjent i dag',
  'from standby bookings': 'fra standby-bookinger',
  'Agent: watching 4 rooms for you…': 'Agent: følger med på 4 rom for deg …',
};

(function owner() {
  const box = document.getElementById('owner');
  if (!box) return;
  const isNo = () => document.documentElement.lang === 'nb';
  const t = s => (isNo() && RENTERS_NO[s]) || s;
  const L = (en, no) => (isNo() ? no : en);
  const kr = n => String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + ' kr';

  const BASE = 1240, SALE = 180;
  const start = () => ({
    rooms: [
      { n: 'Bakklandet', st: 'use', note: ['6 seats · until 16:00', '6 plasser · til 16:00'] },
      { n: 'Nidelva', st: 'use', note: ['8 seats · until 16:30', '8 plasser · til 16:30'] },
      { n: 'Munkholmen', st: 'sold', note: ['4 seats · 14:10–14:55 · 160 kr', '4 plasser · 14:10–14:55 · 160 kr'] },
      { n: 'Phone booth 2', st: 'free', note: ['1 seat · free now', '1 plass · ledig nå'] },
    ],
    log: [['Agent: watching 4 rooms for you…', 'Agent: følger med på 4 rom for deg …', '']],
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
    box.querySelectorAll('[data-k]').forEach(el => { el.textContent = t(el.dataset.k); });
    $('o-rooms-list').innerHTML = s.rooms.map((r, i) =>
      '<li class="room st-' + r.st + (i === s.just ? ' just' : '') + '"><div><strong>' + L(r.n, r.n === 'Phone booth 2' ? 'Telefonboks 2' : r.n) +
      '</strong><span class="note">' + L(r.note[0], r.note[1]) + '</span></div><span class="chip">' + t(chip[r.st]) + '</span></li>').join('');
    $('o-log').innerHTML = s.log.slice(-4).map(([en, no, cls]) => '<span' + (cls ? ' class="' + cls + '"' : '') + '>' + L(en, no) + '</span>').join('');
    $('o-status').textContent = t(s.busy ? 'Agent selling' : 'Agent watching');
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
    room.st = 'released'; room.note = ['Released 15:20 · 40 min left', 'Frigitt 15:20 · 40 min igjen'];
    s.log.push(['Bakklandet released by staff, 40 min left', 'Bakklandet frigitt av de ansatte, 40 min igjen', 'gold']);
    render();
    at(1000, () => { s.just = -1; s.log.push(['Matching 5 people looking for a room…', 'Matcher 5 som leter etter rom …', '']); });
    at(2000, () => s.log.push(['Best fit: 4 people, screen, 15:25–16:00 (94%)', 'Beste treff: 4 personer, skjerm, 15:25–16:00 (94 %)', '']));
    at(3000, () => s.log.push(['Quote 180 kr, inside your 150–320 kr', 'Tilbud 180 kr, innenfor dine 150–320 kr', '']));
    at(4000, () => {
      s.busy = false; s.done = true; s.just = 0;
      room.st = 'sold'; room.note = ['4 people · 15:25–16:00 · 180 kr', '4 personer · 15:25–16:00 · 180 kr'];
      s.log.push(['Booked. 5 min buffer kept before 16:00', 'Booket. 5 min buffer holdt før 16:00', 'ok']);
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
  new MutationObserver(render).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });

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

// Static text on this page that spaces.js and i18n.js don't cover: sections marked [data-r].
(function rentersNo() {
  const norm = s => s.replace(/\s+/g, ' ').trim();
  const orig = new WeakMap();
  const isNo = () => document.documentElement.lang === 'nb';
  function doText(node) {
    const raw = node.nodeValue;
    if (isNo()) {
      const tr = RENTERS_NO[norm(raw)];
      if (tr === undefined) return;
      orig.set(node, raw);
      const next = raw.match(/^\s*/)[0] + tr + raw.match(/\s*$/)[0];
      if (raw !== next) node.nodeValue = next;
    } else if (orig.has(node)) {
      node.nodeValue = orig.get(node); orig.delete(node);
    }
  }
  function run() {
    document.querySelectorAll('[data-r]').forEach(r => {
      const w = document.createTreeWalker(r, NodeFilter.SHOW_TEXT); let n;
      while ((n = w.nextNode())) doText(n);
    });
  }
  new MutationObserver(run).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });
  run();
})();
