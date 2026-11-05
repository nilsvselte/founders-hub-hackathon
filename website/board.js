// Hero board: editable preferences, live agent re-ranking, and simulated automatic booking.
(function board() {
  const D = window.BOARD_DATA;
  const root = document.querySelector('.board');
  const form = document.getElementById('prefs');
  const list = document.getElementById('matches');
  const log = document.getElementById('log');
  const quote = document.getElementById('quote');
  const rel = document.getElementById('rel');
  const resetBtn = document.getElementById('reset');
  const status = document.getElementById('agent-status');
  const more = document.getElementById('more');
  const sumBtn = document.getElementById('prefs-sum');
  const sumText = document.getElementById('prefs-sum-text');
  if (!D || !root || !form || !list) return;

  const SHOW = 4;
  const reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  const toMin = t => { const [h, m] = t.split(':').map(Number); return h * 60 + m; };
  const hhmm = m => String(Math.floor(m / 60)).padStart(2, '0') + ':' + String(m % 60).padStart(2, '0');
  const KIT = { screen: 'screen', whiteboard: 'whiteboard', video: 'video' };

  let prefs, released, booked, logSeq = 0, auto = null;

  /* ---------- Preferences form ---------- */
  function readForm() {
    const p = {};
    p.from = form.elements.from.value || D.defaults.from;
    p.to = form.elements.to.value || D.defaults.to;
    p.people = Number(form.querySelector('[data-people]').textContent);
    p.budget = Number(form.elements.budget.value);
    p.equip = [...form.querySelectorAll('[data-equip][aria-pressed="true"]')].map(b => b.dataset.equip);
    p.duration = Number(form.querySelector('[data-seg="duration"] [aria-pressed="true"]').dataset.v);
    p.zone = form.querySelector('[data-seg="zone"] [aria-pressed="true"]').dataset.v;
    p.flex = Number(form.querySelector('[data-seg="flex"] [aria-pressed="true"]').dataset.v);
    return p;
  }
  function writeForm(p) {
    form.elements.from.value = p.from;
    form.elements.to.value = p.to;
    form.querySelector('[data-people]').textContent = p.people;
    form.elements.budget.value = p.budget;
    form.querySelector('[data-budget-out]').textContent = p.budget + ' kr';
    form.querySelectorAll('[data-equip]').forEach(b => b.setAttribute('aria-pressed', p.equip.includes(b.dataset.equip)));
    ['duration', 'zone', 'flex'].forEach(k => {
      form.querySelectorAll(`[data-seg="${k}"] button`).forEach(b => b.setAttribute('aria-pressed', String(b.dataset.v) === String(p[k])));
    });
    paintBudget();
  }
  function paintBudget() {
    const r = form.elements.budget;
    const pct = (r.value - r.min) / (r.max - r.min) * 100;
    r.style.setProperty('--pct', pct + '%');
  }

  /* ---------- Scoring ---------- */
  function score(room, p) {
    let s = 100; const plus = [], minus = [];
    const from = toMin(p.from), to = toMin(p.to);
    const wS = from - p.flex, wE = to + p.flex;
    const rS = toMin(room.from), rE = toMin(room.to);

    if (room.seats < p.people) { s -= 30 + (p.people - room.seats) * 6; minus.push([9, `seats only ${room.seats}`]); }
    else if (room.seats > p.people * 3 && room.seats > 6) { s -= 8; minus.push([2, `big for ${p.people}`]); }
    else plus.push([5, `fits ${p.people}`]);

    const missing = p.equip.filter(e => !room.equip.includes(e));
    s -= missing.length * 14;
    if (missing.length) minus.push([6, 'no ' + missing.map(e => KIT[e]).join(' or ')]);
    else if (p.equip.length) plus.push([4, p.equip.length === 3 ? 'all your kit' : 'has ' + p.equip.map(e => KIT[e]).join(' + ')]);

    const overlap = Math.min(rE, wE) - Math.max(rS, wS);
    if (overlap < p.duration) {
      s -= Math.min(45, (p.duration - Math.max(0, overlap)) * 0.7);
      if (rE <= wS + 10 || rE < from + p.duration) minus.push([8, overlap <= 0 ? `gone by ${hhmm(rE)}` : `only free till ${hhmm(rE)}`]);
      else minus.push([7, `free from ${hhmm(rS)}`]);
    } else plus.push([rS <= D.now ? 3 : 2, rS <= D.now ? 'free now' : 'in your window']);

    const diff = p.budget - room.price;
    if (diff < 0) { s -= Math.min(30, -diff / 4); minus.push([5, `${-diff} kr over budget`]); }
    else plus.push([diff >= 40 ? 4 : 1, `${diff} kr under budget`]);

    if (p.zone !== 'any') {
      if (room.zone === p.zone) plus.push([2, p.zone === 'quiet' ? 'quiet floor' : 'by the café']);
      else { s -= 8; minus.push([3, p.zone === 'quiet' ? 'open area' : 'far from café']); }
    }

    const fit = Math.max(4, Math.min(98, Math.round(s)));
    minus.sort((a, b) => b[0] - a[0]); plus.sort((a, b) => b[0] - a[0]);
    const why = minus.length
      ? [minus[0][1], minus[1] && minus[1][1], plus[0] && plus[0][1]].filter(Boolean).slice(0, 2)
      : plus.slice(0, 3).map(x => x[1]);
    return { fit, why };
  }

  function rooms() {
    const all = D.rooms.slice();
    if (released) all.push(released);
    return all.map(r => ({ room: r, ...score(r, prefs) })).sort((a, b) => b.fit - a.fit);
  }

  /* ---------- Rendering with a FLIP reorder ---------- */
  function rowFor(id) { return list.querySelector(`[data-id="${id}"]`); }
  function makeRow(r) {
    const li = document.createElement('li');
    li.className = 'm';
    li.dataset.id = r.id;
    li.innerHTML = '<span class="rank"></span><div class="m-body"><strong></strong> <span class="slot"></span><span class="why"></span></div>' +
      '<div class="m-side"><span class="fit"></span><span class="price"></span></div><span class="bar" aria-hidden="true"><i></i></span>';
    return li;
  }
  function countTo(el, to) {
    const from = Number(el.dataset.v || to);
    el.dataset.v = to;
    if (reduce || from === to) { el.textContent = to + '%'; return; }
    const t0 = performance.now();
    (function step(t) {
      const k = Math.min(1, (t - t0) / 450);
      el.textContent = Math.round(from + (to - from) * (1 - Math.pow(1 - k, 3))) + '%';
      if (k < 1 && el.dataset.v == to) requestAnimationFrame(step);
    })(t0);
  }
  function render() {
    const ranked = rooms();
    const top = ranked.slice(0, SHOW);
    const before = new Map([...list.children].map(li => [li.dataset.id, li.getBoundingClientRect().top]));
    const oldRank = new Map([...list.children].map((li, i) => [li.dataset.id, i]));

    [...list.children].forEach(li => { if (!li.dataset.id || !top.some(x => x.room.id === li.dataset.id)) li.remove(); });
    top.forEach((x, i) => {
      let li = rowFor(x.room.id);
      const isNew = !li;
      if (isNew) li = makeRow(x.room);
      const r = x.room;
      li.querySelector('.rank').textContent = i + 1;
      li.querySelector('strong').textContent = r.name;
      li.querySelector('.slot').textContent = '· ' + r.from + '–' + r.to;
      li.querySelector('.why').textContent = x.why.join(' · ');
      li.querySelector('.price').innerHTML = r.price + ' kr <s>' + r.list + '</s>';
      li.querySelector('.bar i').style.width = x.fit + '%';
      li.classList.toggle('new', r === released);
      li.classList.toggle('low', x.fit < 50);
      if (booked && r === released) { li.classList.add('booked'); li.querySelector('.fit').textContent = 'Booked'; li.querySelector('.fit').dataset.v = x.fit; }
      else { li.classList.remove('booked'); countTo(li.querySelector('.fit'), x.fit); }
      list.appendChild(li);
      if (isNew && !reduce) { li.classList.remove('enter'); void li.offsetWidth; li.classList.add('enter'); }
      if (!isNew && oldRank.has(r.id) && oldRank.get(r.id) > i && !reduce) {
        li.classList.remove('up'); void li.offsetWidth; li.classList.add('up');
      }
    });
    if (!reduce) {
      [...list.children].forEach(li => {
        if (!before.has(li.dataset.id)) return;
        const dy = before.get(li.dataset.id) - li.getBoundingClientRect().top;
        if (!dy) return;
        li.style.transition = 'none';
        li.style.transform = `translateY(${dy}px)`;
        void li.offsetWidth;
        li.style.transition = '';
        li.style.transform = '';
      });
    }
    if (more) more.textContent = `${ranked.length - top.length} more checked, ranked lower`;
    return ranked;
  }

  /* ---------- Agent log ---------- */
  function line(text, cls) {
    const s = document.createElement('span');
    s.textContent = text;
    if (cls) s.className = cls;
    log.appendChild(s);
    while (log.children.length > 5) log.firstChild.remove();
  }
  // Stream lines one after another; a newer stream cancels an older one.
  // The release stream survives later re-ranks. Reset cancels it.
  let hardSeq = 0;
  function stream(steps, hard) {
    const seq = hard ? hardSeq : ++logSeq;
    const live = () => hard ? seq === hardSeq : seq === logSeq;
    let t = 0;
    steps.forEach(([delay, fn]) => { t += delay; setTimeout(() => { if (live()) fn(); }, t); });
  }
  function thinking(on) {
    root.classList.toggle('is-thinking', on);
    if (status) status.textContent = on ? 'Agent thinking…' : 'Agent watching';
  }

  function summary(p) {
    const kit = p.equip.length ? p.equip.join(' + ') : 'no kit';
    return `${p.people} ${p.people === 1 ? 'person' : 'people'} · ${p.duration} min · ${kit} · ≤${p.budget} kr`;
  }

  let debounce = null;
  function paintSummary() { if (sumText && prefs) sumText.textContent = summary(prefs); }
  function onChange() {
    prefs = readForm();
    paintSummary();
    clearTimeout(debounce);
    debounce = setTimeout(rerank, 180);
  }
  function rerank() {
    const prevTop = list.firstElementChild && list.firstElementChild.dataset.id;
    const count = D.rooms.length + (released ? 1 : 0);
    thinking(true);
    stream([
      [0, () => line('New brief: ' + summary(prefs))],
      [380, () => line(`Checking ${count} rooms against ${hhmm(toMin(prefs.from))}–${hhmm(toMin(prefs.to))} ±${prefs.flex}…`)],
      [420, () => {
        const ranked = render();
        const best = ranked[0];
        const moved = best.room.id !== prevTop;
        line(`${moved ? 'New #1' : 'Still #1'}: ${best.room.name} · ${best.fit}% fit · ${best.why[0]}`, best.fit >= 70 ? 'ok' : '');
        thinking(false);
      }]
    ]);
  }

  /* ---------- Release and automatic booking ---------- */
  function release() {
    if (released) return;
    rel.disabled = true;
    const r = Object.assign({}, D.released);
    released = r;
    const count = D.rooms.length + 1;
    thinking(true);
    stream([
      [0, () => line(`${hhmm(D.now)} Staff pressed Release on ${r.name}, free ${r.from}–${r.to}`, 'gold')],
      [700, () => line(`Scoring ${r.name} against your ${Object.keys(prefs).length} preferences…`)],
      [700, () => {
        const ranked = render();
        const me = ranked.find(x => x.room === r);
        const pos = ranked.indexOf(me) + 1;
        line(pos === 1 ? `${r.name} freed at ${hhmm(D.now)} · new best fit, ${me.fit}%` : `${r.name} ranks #${pos} of ${count} · ${me.fit}% fit`, 'ok');
      }],
      [900, () => {
        confirmRelease(r);
        thinking(false);
      }]
    ], true);
  }

  function confirmRelease(r) {
    const start = Math.max(toMin(r.from), toMin(prefs.from) - prefs.flex);
    const end = start + prefs.duration;
    const latest = Math.min(toMin(r.to), toMin(prefs.to) + prefs.flex);
    if (end > latest || r.seats < prefs.people || r.price > prefs.budget || prefs.equip.some(kit => !r.equip.includes(kit))) {
      line(`${r.name} doesn't meet your request. Still watching.`);
      return;
    }

    const time = `${hhmm(start)}–${hhmm(end)}`;
    booked = true;
    render();
    quote.querySelector('.q-room').textContent = `${r.name} · ${time}`;
    quote.querySelector('.q-price').innerHTML = `${r.price} kr <s>${r.list} kr</s>`;
    quote.hidden = false;
    line(`Confirmed. ${r.name}, ${time}, for ${r.price} kr.`, 'ok');
  }

  function reset() {
    clearTimeout(debounce);
    logSeq++; hardSeq++;
    released = null; booked = false;
    writeForm(D.defaults);
    prefs = readForm();
    paintSummary();
    list.innerHTML = '';
    log.innerHTML = '';
    line(`Agent: watching ${D.rooms.length} rooms at Digs for you…`);
    quote.hidden = true;
    rel.disabled = false;
    thinking(false);
    render();
  }

  /* ---------- Wiring ---------- */
  form.addEventListener('submit', e => e.preventDefault());
  form.addEventListener('input', e => { if (e.target.name === 'budget') { form.querySelector('[data-budget-out]').textContent = e.target.value + ' kr'; paintBudget(); } onChange(); });
  form.addEventListener('click', e => {
    const b = e.target.closest('button');
    if (!b) return;
    if (b.dataset.equip) { b.setAttribute('aria-pressed', b.getAttribute('aria-pressed') !== 'true'); onChange(); }
    else if (b.closest('[data-seg]')) { b.closest('[data-seg]').querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x === b)); onChange(); }
    else if (b.dataset.step) {
      const out = form.querySelector('[data-people]');
      out.textContent = Math.max(1, Math.min(14, Number(out.textContent) + Number(b.dataset.step)));
      onChange();
    }
  });
  if (sumBtn) sumBtn.addEventListener('click', () => {
    const open = sumBtn.getAttribute('aria-expanded') !== 'true';
    sumBtn.setAttribute('aria-expanded', String(open));
    root.classList.toggle('prefs-open', open);
  });
  rel.addEventListener('click', release);
  resetBtn.addEventListener('click', () => { stopAuto(); reset(); });

  /* ---------- Autoplay until someone touches the board ---------- */
  function stopAuto() { if (auto) { auto.forEach(clearTimeout); auto = null; } root.classList.remove('is-auto'); }
  function press(el) { el.classList.remove('auto-press'); void el.offsetWidth; el.classList.add('auto-press'); }
  function runAuto() {
    auto = [];
    root.classList.add('is-auto');
    const a = (ms, fn) => auto.push(setTimeout(fn, ms));
    a(1600, () => { const v = form.querySelector('[data-equip="video"]'); press(v); v.click(); });
    a(4200, () => { press(rel); release(); });
    a(14000, () => { reset(); runAuto(); });
  }
  ['pointerdown', 'keydown'].forEach(ev => root.addEventListener(ev, e => { if (e.isTrusted) stopAuto(); }, true));

  reset();
  if (!reduce) runAuto();
})();
