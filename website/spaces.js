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

// Bokmål for the text in my sections. i18n.js (another agent's file) owns the NO/EN toggle and
// sets <html lang>; this follows it for strings its dictionary doesn't have.
(function spacesNo() {
  const NO = {
    'The meeting ended early. The room is paid for, empty, and nobody knows.': 'Møtet sluttet tidlig. Rommet er betalt, står tomt, og ingen vet det.',
    '~1 in 3': '~1 av 3',
    'estimate': 'anslag',
    'booked meetings end before their slot does.': 'bookede møter slutter før tiden er ute.',
    '20–40 min': '20–40 min',
    'left over each time, too short to rebook by hand.': 'til overs hver gang, for kort til å leie ut manuelt.',
    'earned from that time today. It just disappears.': 'tjent på den tiden i dag. Den bare forsvinner.',
    'Estimates for a Digs-sized coworking house, not measured data.': 'Anslag for et kontorfellesskap på størrelse med Digs, ikke målte tall.',
    'Staff press one button when a meeting ends early. You set the floor and ceiling price; the agent fills the gap. Free to list; we keep 15% of each standby booking.':
      'De ansatte trykker på én knapp når et møte slutter tidlig. Du setter minste- og høyeste pris, agenten fyller hullet. Gratis å legge ut; vi tar 15 % av hver standby-booking.',
    'What is my idle time worth?': 'Hva er den ledige tiden min verdt?',
    'What idle time is worth': 'Hva ledig tid er verdt',
    'Time your rooms already lose each week, sold at standby prices. Move the sliders to match your space.':
      'Tid rommene dine allerede taper hver uke, solgt til standby-pris. Flytt glidebryterne så de passer ditt lokale.',
    'Meeting rooms': 'Møterom',
    'Hours freed per room, per week': 'Timer frigjort per rom, per uke',
    'Standby price per hour': 'Standby-pris per time',
    'You keep, per month': 'Du sitter igjen med, per måned',
    'from time that earns nothing today': 'fra tid som ikke tjener noe i dag',
    'Freed hours per month': 'Frigjorte timer per måned',
    'Sold at your price': 'Solgt til din pris',
    'Platform fee, 15%': 'Plattformavgift, 15 %',
    'Per year, after fee': 'Per år, etter avgift',
    'You stay in control': 'Du har kontrollen',
    'Price floor and ceiling': 'Minste- og høyeste pris',
    'The agent quotes only inside your limits, per room.': 'Agenten gir bare tilbud innenfor grensene dine, per rom.',
    'Turnaround buffer': 'Buffer mellom gjester',
    'Minutes kept free to tidy before the next guest.': 'Minutter holdt ledig til rydding før neste gjest.',
    'Rooms and hours': 'Rom og tider',
    'Choose which rooms can go on standby, and when.': 'Velg hvilke rom som kan legges ut på standby, og når.',
    'Estimate. Assumes every freed hour sells; real fill will be lower at first.': 'Anslag. Forutsetter at hver frigjorte time selges; reelt belegg blir lavere i starten.',
    'Try it: press the button.': 'Prøv: trykk på knappen.',
    'Ready': 'Klar',
    'Released. On sale until 16:00': 'Frigitt. Til salgs til 16:00',
  };
  const roots = () => document.querySelectorAll('section.problem, #spaces, #worth, #device');
  const norm = s => s.replace(/\s+/g, ' ').trim();
  const orig = new WeakMap();
  const isNo = () => document.documentElement.lang === 'nb';
  function doText(node) {
    const raw = node.nodeValue;
    if (isNo()) {
      const t = NO[norm(raw)];
      if (t === undefined) return;
      orig.set(node, raw);
      const next = raw.match(/^\s*/)[0] + t + raw.match(/\s*$/)[0];
      if (raw !== next) node.nodeValue = next;
    } else if (orig.has(node)) {
      node.nodeValue = orig.get(node); orig.delete(node);
    }
  }
  function run() {
    roots().forEach(r => { const w = document.createTreeWalker(r, NodeFilter.SHOW_TEXT); let n; while ((n = w.nextNode())) doText(n); });
    document.querySelectorAll('#o-hours, #w-hours').forEach(el => { el.textContent = el.textContent.replace(/ [ht]$/, isNo() ? ' t' : ' h'); });
  }
  new MutationObserver(run).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });
  const screen = document.getElementById('unit-screen');
  if (screen) new MutationObserver(() => { if (isNo()) doText(screen.firstChild); }).observe(screen, { childList: true });
  const form = document.getElementById('worth-calc');
  if (form) form.addEventListener('input', () => { if (isNo()) run(); });
  run();
})();
