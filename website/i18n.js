// NO/EN language toggle. Norwegian (Bokmål) is the default; the choice is remembered.
// The page is written in English. NO maps each English text (whitespace-collapsed) to Bokmål,
// so it keeps working when markup moves around. Text added later (the hero demo) is caught
// by a MutationObserver. ATTR covers attributes, keyed by CSS selector.
(function i18n() {
  const NO = {
    // Header / nav
    'Skip to content': 'Hopp til innholdet',
    'How it works': 'Slik virker det',
    'For spaces': 'For utleiere',
    'The button': 'Knappen',
    'Open marketplace': 'Åpne markedsplassen',

    // Hero
    'Live at Digs, Trondheim': 'Nå på Digs i Trondheim',
    'Tell it what you need.': 'Si hva du trenger.',
    'It finds the room.': 'Den finner rommet.',
    'Set your time, group size, equipment, budget and how flexible you are. An agent ranks every room at Digs against them, and books the best fit the moment one frees up.':
      'Velg tid, antall personer, utstyr, budsjett og hvor fleksibel du er. En agent rangerer alle rommene på Digs etter ønskene dine, og booker det som passer best i det øyeblikket det blir ledig.',
    'Set my preferences': 'Legg inn ønskene mine',
    'Sell idle room time': 'Selg ledig romtid',

    // Hero demo board (static + text main.js writes later)
    'Your preferences': 'Dine ønsker',
    'Demo': 'Demo',
    'When': 'Når',
    'today, 15:15–16:30': 'i dag, 15:15–16:30',
    'Length': 'Varighet',
    'People': 'Personer',
    'Needs': 'Behov',
    'screen, whiteboard': 'skjerm, tavle',
    'Budget': 'Budsjett',
    'up to 300 kr': 'opptil 300 kr',
    'Flexible': 'Fleksibel',
    'Agent: watching 6 rooms for you…': 'Agent: følger med på 6 rom for deg …',
    'Release room': 'Frigi rommet',
    'Reset': 'Nullstill',
    'Press it the way staff do when a meeting ends early.': 'Trykk slik de ansatte gjør når et møte slutter tidlig.',
    'Ranked for you': 'Rangert for deg',
    '8 seats, screen. Later than you wanted.': '8 plasser, skjerm. Senere enn du ønsket.',
    'Phone booth 2': 'Telefonboks 2',
    '· now': '· nå',
    'Free now, but seats 1.': 'Ledig nå, men bare 1 plass.',
    '4 seats, screen, whiteboard. In your window.': '4 plasser, skjerm, tavle. Innenfor tidsrommet ditt.',
    'Held for you for 2 minutes': 'Holdt av for deg i 2 minutter',
    'Accept': 'Godta',
    'Booked': 'Booket',
    '15:20 Staff released Bakklandet, free 15:25–16:00': '15:20 Ansatte frigjorde Bakklandet, ledig 15:25–16:00',
    'Scoring it against your 6 preferences…': 'Vurderer det mot de 6 ønskene dine …',
    'New best fit: Bakklandet, 94%': 'Ny beste match: Bakklandet, 94 %',
    'Quote 180 kr, inside the space’s limits. Held 2 min.': 'Tilbud 180 kr, innenfor lokalets grenser. Holdt av i 2 min.',
    'Rechecked the slot. Booking confirmed.': 'Sjekket tiden på nytt. Bookingen er bekreftet.',
    'When, today': 'Når, i dag',
    'Screen': 'Skjerm',
    'Whiteboard': 'Tavle',
    'Budget, up to': 'Budsjett, opptil',
    'Where': 'Hvor',
    'Any': 'Uansett',
    'Quiet': 'Stille',
    'Café': 'Kafé',
    'all your kit': 'alt utstyret ditt',
    'free now': 'ledig nå',
    'in your window': 'innenfor tidsrommet ditt',
    'quiet floor': 'stille etasje',
    'by the café': 'ved kafeen',
    'open area': 'åpent område',
    'far from café': 'langt fra kafeen',
    'no kit': 'uten utstyr',
    'Agent thinking…': 'Agenten tenker …',
    'Agent watching': 'Agenten følger med',
    'Held for you': 'Holdt av for deg',
    'Checking…': 'Sjekker …',
    'Confirmed': 'Bekreftet',
    'door code sent': 'dørkode sendt',

    // Problem
    'Meetings end early. The room sits empty, and the hour is gone.': 'Møter slutter tidlig. Rommet står tomt, og timen er tapt.',
    'Booked rooms at a coworking house free up all day, but nobody hears about it in time.':
      'Bookede rom i et kontorfellesskap blir ledige hele dagen, men ingen får vite det i tide.',
    'sells that time to people who are already waiting for it.': 'selger den tiden til folk som allerede venter på den.',

    // How it works
    'Standby request': 'Standby-forespørsel',
    '3 people, a screen, before 16:30, under 300 kr': '3 personer, en skjerm, før 16:30, under 300 kr',
    'Window': 'Tidsrom',
    'Duration': 'Varighet',
    'Agent log': 'Agentlogg',
    'Bakklandet released': 'Bakklandet frigjort',
    'Seats 4, screen, whiteboard': '4 plasser, skjerm, tavle',
    'fits': 'passer',
    'Inside your window': 'Innenfor tidsrommet ditt',
    'Fit score': 'Match',
    'Quote': 'Tilbud',
    'Space\'s floor': 'Lokalets minstepris',
    'List price': 'Listepris',
    'Rechecked before booking': 'Sjekket på nytt før booking',
    'yes': 'ja',
    'Tell it what you need': 'Si hva du trenger',
    'Time window, length, group size, equipment, budget and how flexible you are. Leave it once; it keeps watching.':
      'Tidsrom, varighet, antall personer, utstyr, budsjett og hvor fleksibel du er. Legg det inn én gang, så følger den med.',
    'It watches and ranks': 'Den følger med og rangerer',
    'Every free room and every early release is scored against your request, with the reason it fits or doesn\'t.':
      'Hvert ledige rom og hver tidlige frigjøring vurderes mot forespørselen din, med begrunnelse for hvorfor det passer eller ikke.',
    'It books the best fit': 'Den booker det som passer best',
    'It quotes a price inside the space\'s limits and holds the slot. You accept, it rechecks and confirms. If the slot is gone, it finds the next one.':
      'Den gir en pris innenfor lokalets grenser og holder av tiden. Du godtar, den sjekker på nytt og bekrefter. Er tiden borte, finner den neste.',

    // Two doors
    'Two sides, one button between them': 'To sider, én knapp imellom',
    'For people who need a room': 'For deg som trenger et rom',
    'An agent that finds the room that suits you.': 'En agent som finner rommet som passer deg.',
    'Tell it once what you need. When a room opens that fits, you get a quote, often well below list price, and one tap books it.':
      'Si én gang hva du trenger. Når et rom som passer blir ledig, får du et tilbud, ofte godt under listepris, og ett trykk booker det.',
    'For spaces with rooms to fill': 'For lokaler med rom å fylle',
    'Sell the hour you were going to lose.': 'Selg timen du ellers ville tapt.',
    'Staff press one button when a meeting ends early. You set the floor and ceiling price; the agent fills the gap. Free to list, with a share of each standby booking.':
      'De ansatte trykker på én knapp når et møte slutter tidlig. Du setter minste- og høyeste pris, agenten fyller hullet. Gratis å legge ut, vi tar en andel av hver standby-booking.',
    'List my rooms': 'Legg ut rommene mine',

    // Device
    'Bakklandet · 2nd floor': 'Bakklandet · 2. etasje',
    'One press when the meeting ends': 'Ett trykk når møtet er slutt',
    'A small device by the door. Staff press it when a room is ready, and the rest of the hour goes on sale.':
      'En liten enhet ved døren. De ansatte trykker når rommet er klart, og resten av timen legges ut for salg.',
    'One press': 'Ett trykk',
    'No app to open and nothing to type.': 'Ingen app å åpne og ingenting å skrive.',
    '5-minute buffer': '5 minutters buffer',
    'Time to tidy the room before the next guest arrives.': 'Tid til å rydde rommet før neste gjest kommer.',
    'No new software for staff': 'Ingen ny programvare for de ansatte',
    'Prices and limits are set once by the space.': 'Priser og grenser settes én gang av lokalet.',

    // Closing
    'Your next room is': 'Ditt neste rom er',
    'about to open.': 'snart ledig.',
    'Live at Digs, Trondheim. Leave your request now and the agent starts watching.':
      'Nå på Digs i Trondheim. Legg inn forespørselen din nå, så begynner agenten å følge med.',

    // Bookers page (index.html)
    'Find a room': 'Finn rom',
    'Rent out rooms': 'Leie ut rom',
    'Why Ledig': 'Hvorfor Ledig',
    'Open Ledig': 'Åpne Ledig',
    'See how it works': 'Se hvordan det virker',
    'Say when, how many, what kit and what you will pay. An agent ranks every room at Digs against it, and quotes you the best fit the moment one frees up, often below list price.':
      'Si når, hvor mange, hvilket utstyr og hva du vil betale. En agent rangerer alle rommene på Digs etter det, og gir deg tilbud på det som passer best i det øyeblikket det blir ledig, ofte under listepris.',
    'Edit': 'Endre',
    'Your request': 'Forespørselen din',
    'Set your needs': 'Si hva du trenger',
    'Time window, length, group size, equipment, budget and how flexible you are. Say it once; the agent keeps it.':
      'Tidsrom, varighet, antall personer, utstyr, budsjett og hvor fleksibel du er. Si det én gang, så husker agenten det.',
    'The agent watches and ranks': 'Agenten følger med og rangerer',
    'Get a quote, accept': 'Få et tilbud, godta',
    'When the best fit opens, you get a price and the slot is held for you. One tap accepts; the agent rechecks and books it.':
      'Når det som passer best blir ledig, får du en pris og tiden holdes av for deg. Ett trykk godtar; agenten sjekker på nytt og booker.',
    'Cheaper': 'Billigere',
    'Last-minute rooms, below list price.': 'Rom i siste liten, under listepris.',
    'Rooms freed by meetings that end early go at standby prices, set inside each space\'s limits.':
      'Rom som blir ledige når møter slutter tidlig, selges til standby-pris innenfor hvert lokales grenser.',
    'No hunting': 'Ingen leting',
    'No calendars to refresh.': 'Ingen kalendere å oppdatere.',
    'You say what you need once. The agent checks every room at Digs against it and tells you why each one fits or doesn\'t.':
      'Du sier hva du trenger én gang. Agenten sjekker alle rommene på Digs mot det og forteller deg hvorfor hvert rom passer eller ikke.',
    'It waits for you': 'Den venter for deg',
    'The agent does the waiting.': 'Agenten gjør ventingen.',
    'Nothing fits yet? It keeps watching, and the moment a room frees up you get a quote held just for you.':
      'Passer ingenting ennå? Den følger med, og i det øyeblikket et rom blir ledig, får du et tilbud holdt av bare for deg.',

    // Footer
    'Built at the DNB × Founders Hub hackathon, Trondheim, November 2026. All rooms, times and prices on this page are demo data.':
      'Laget under DNB × Founders Hub-hackathonet i Trondheim, november 2026. Alle rom, tider og priser på denne siden er demodata.',
  };

  // Attributes, keyed by CSS selector: [selector, attribute, Bokmål]
  const ATTR = [
    ['meta[name="description"]', 'content', 'Si hva du trenger. Den finner rommet. Møterom som blir ledige tidlig på Digs i Trondheim, matchet til deg av en agent.'],
    ['.nav nav:not(.side-switch)', 'aria-label', 'Hovedmeny'],
    ['.nav .side-switch', 'aria-label', 'Velg side'],
    ['.board', 'aria-label', 'Live demo: agenten matcher rom til en forespørsel'],
    ['#prefs', 'aria-label', 'Dine ønsker: endre hva som helst for å rangere på nytt'],
    ['#prefs input[aria-label="From"]', 'aria-label', 'Fra'],
    ['#prefs input[aria-label="To"]', 'aria-label', 'Til'],
    ['#prefs [aria-label="Fewer people"]', 'aria-label', 'Færre personer'],
    ['#prefs [aria-label="More people"]', 'aria-label', 'Flere personer'],
    ['#prefs [aria-label="Length"]', 'aria-label', 'Varighet'],
    ['#prefs [aria-label="Equipment"]', 'aria-label', 'Utstyr'],
    ['#prefs [aria-label="Where"]', 'aria-label', 'Hvor'],
    ['#prefs [aria-label="Flexibility"]', 'aria-label', 'Fleksibilitet'],
  ];

  const KEY = 'lang';
  const norm = s => s.replace(/\s+/g, ' ').trim();
  const orig = new WeakMap();   // text node -> English text
  const attrOrig = new Map();   // element -> {attr: English}
  let lang = 'no';
  try { const v = localStorage.getItem(KEY); if (v === 'en' || v === 'no') lang = v; } catch (e) {}

  // Text built from data (the hero board): [regex, replacement], tried when NO has no exact match.
  // A "·"-joined string is translated part by part.
  const KIT_NO = { screen: 'skjerm', whiteboard: 'tavle', video: 'video' };
  const KW = '(?:screen|whiteboard|video)';
  const kit = s => s.replace(/screen|whiteboard|video/g, k => KIT_NO[k]).replace(/ or /g, ' eller ');
  const PATTERNS = [
    [new RegExp(`^${KW}(?: \\+ ${KW})*$`), s => kit(s)],
    [new RegExp(`^no (${KW}(?: or ${KW})*)$`), (m, k) => 'mangler ' + kit(k)],
    [/^(\d+) people$/, '$1 personer'],
    [/^1 person$/, '1 person'],
    [new RegExp(`^has (${KW}(?: \\+ ${KW})*)$`), (m, k) => 'har ' + kit(k)],
    [/^seats only (\d+)$/, 'bare $1 plasser'],
    [/^big for (\d+)$/, 'stort for $1'],
    [/^fits (\d+)$/, 'plass til $1'],
    [/^gone by (\S+)$/, 'opptatt fra $1'],
    [/^only free till (\S+)$/, 'bare ledig til $1'],
    [/^free from (\S+)$/, 'ledig fra $1'],
    [/^(\d+) kr over budget$/, '$1 kr over budsjett'],
    [/^(\d+) kr under budget$/, '$1 kr under budsjett'],
    [/^(\d+) more checked, ranked lower$/, '$1 til sjekket, rangert lavere'],
    [/^(\d+)% fit$/, '$1 % match'],
    [/^New brief: (\d+) people$/, 'Ny forespørsel: $1 personer'],
    [/^New brief: (\d+) person$/, 'Ny forespørsel: $1 person'],
    [/^Checking (\d+) rooms against (.+)…$/, 'Sjekker $1 rom mot $2 …'],
    [/^New #1: (.+)$/, 'Ny nr. 1: $1'],
    [/^Still #1: (.+)$/, 'Fortsatt nr. 1: $1'],
    [/^(\S+) Staff pressed Release on (.+), free (\S+)$/, '$1 Ansatte trykket Frigi på $2, ledig $3'],
    [/^Scoring (.+) against your (\d+) preferences…$/, 'Vurderer $1 mot de $2 ønskene dine …'],
    [/^(.+) freed at (\S+)$/, '$1 frigjort $2'],
    [/^new best fit, (\d+)%$/, 'ny beste match, $1 %'],
    [/^(.+) ranks #(\d+) of (\d+)$/, '$1 er nr. $2 av $3'],
    [/^Quote (\d+) kr \(list (\d+)\), inside Digs' limits\. Holding 2 min\.$/, 'Tilbud $1 kr (listepris $2), innenfor grensene til Digs. Holdes av i 2 min.'],
    [/^Rechecking (.+) is still free…$/, 'Sjekker at $1 fortsatt er ledig …'],
    [/^Confirmed\. (.+) is yours, (\S+)\.$/, 'Bekreftet. $1 er ditt, $2.'],
    [/^Agent: watching (\d+) rooms at Digs for you…$/, 'Agent: følger med på $1 rom på Digs for deg …'],
  ];
  function one(s) {
    if (NO[s] !== undefined) return NO[s];
    for (const [re, rep] of PATTERNS) if (re.test(s)) return s.replace(re, rep);
    return undefined;
  }
  function lookup(s) {
    const whole = one(s);
    if (whole !== undefined || !s.includes(' · ')) return whole;
    let hit = false;
    const parts = s.split(' · ').map(p => { const t = one(p); if (t !== undefined) { hit = true; return t; } return p; });
    return hit ? parts.join(' · ') : undefined;
  }

  function skip(node) {
    const p = node.parentElement;
    return !p || p.closest('script, style, [data-product], .lang-toggle');
  }
  function doText(node) {
    if (skip(node)) return;
    const raw = node.nodeValue;
    if (lang === 'no') {
      const t = lookup(norm(raw));
      if (t === undefined) return;
      if (!orig.has(node) || norm(orig.get(node)) !== norm(raw)) orig.set(node, raw);
      const lead = raw.match(/^\s*/)[0], tail = raw.match(/\s*$/)[0];
      const next = lead + t + tail;
      if (raw !== next) node.nodeValue = next;
    } else if (orig.has(node)) {
      const en = orig.get(node);
      if (raw !== en) node.nodeValue = en;
      orig.delete(node);
    }
  }
  function walk(root) {
    if (root.nodeType === 3) return doText(root);
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let n; while ((n = w.nextNode())) doText(n);
  }
  function doAttrs() {
    ATTR.forEach(e => { if (!e[3]) e[3] = [...document.querySelectorAll(e[0])]; });
    ATTR.forEach(([sel, attr, no, els]) => els.forEach(el => {
      if (!attrOrig.has(el)) attrOrig.set(el, {});
      const store = attrOrig.get(el);
      if (!(attr in store)) store[attr] = el.getAttribute(attr);
      el.setAttribute(attr, lang === 'no' ? no : store[attr]);
    }));
  }

  // Toggle in the nav, before the main button
  const css = document.createElement('style');
  css.textContent = `
.lang-toggle { display: inline-flex; align-items: center; gap: 2px; font: 500 14px/1 var(--text); }
.lang-toggle button { font: inherit; color: var(--muted); background: none; border: 0; padding: 8px 6px; cursor: pointer; border-radius: 6px; }
.lang-toggle button:hover { color: var(--ink); }
.lang-toggle button[aria-pressed="true"] { color: var(--ink); text-decoration: underline; text-decoration-color: var(--accent); text-decoration-thickness: 2px; text-underline-offset: 6px; }
.lang-toggle .sep { color: var(--dim); }
.nav .wordmark, .nav-inner > .btn { white-space: nowrap; }
@media (max-width: 720px) { .nav-inner { gap: 12px; } .lang-toggle { margin-left: auto; } }
@media (max-width: 480px) {
  .nav-inner { gap: 8px; }
  .nav .wordmark { font-size: 20px; }
  .lang-toggle button { padding: 8px 4px; }
  .nav-inner > .btn { font-size: 13px; padding: 9px 11px; }
}
@media (max-width: 380px) { .lang-toggle .sep { display: none; } .nav-inner > .btn { font-size: 12px; padding: 8px 9px; } }`;
  document.head.appendChild(css);

  const box = document.createElement('div');
  box.className = 'lang-toggle';
  box.setAttribute('role', 'group');
  box.innerHTML = '<button type="button" data-lang="no" lang="nb" aria-label="Norsk">NO</button><span class="sep" aria-hidden="true">/</span><button type="button" data-lang="en" lang="en" aria-label="English">EN</button>';
  const navInner = document.querySelector('.nav-inner');
  if (navInner) navInner.insertBefore(box, navInner.querySelector(':scope > .btn') || null);

  function apply(next) {
    lang = next;
    document.documentElement.lang = lang === 'no' ? 'nb' : 'en';
    box.setAttribute('aria-label', lang === 'no' ? 'Språk' : 'Language');
    box.querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.lang === lang)));
    walk(document.body);
    doAttrs();
  }
  box.addEventListener('click', e => {
    const b = e.target.closest('button[data-lang]');
    if (!b || b.dataset.lang === lang) return;
    try { localStorage.setItem(KEY, b.dataset.lang); } catch (err) {}
    apply(b.dataset.lang);
  });

  // Catch text other scripts write later (the hero demo log, matches, buttons)
  new MutationObserver(muts => {
    if (lang !== 'no') return;
    muts.forEach(m => {
      if (m.type === 'characterData') doText(m.target);
      else m.addedNodes.forEach(walk);
    });
  }).observe(document.body, { subtree: true, childList: true, characterData: true });

  apply(lang);
})();
