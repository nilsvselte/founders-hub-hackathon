/* Lit windows (bg-lab): a dusk skyline whose tops sit just under the call-to-action. */
(function () {
  var host = document.querySelector('.hero-art'); if (!host) return;
  var W = 1440, H = 1200, seed = 5;
  function rnd() { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; }
  var s = '<svg viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="xMidYMin slice" aria-hidden="true">';
  var x = -20;
  while (x < W) {
    var bw = 90 + Math.round(rnd() * 150), top = 10 + Math.round(rnd() * 150);
    var nearCentre = Math.abs(x + bw / 2 - W / 2) < 140; if (nearCentre) top += 90;
    s += '<rect class="hw-b" x="' + x + '" y="' + top + '" width="' + bw + '" height="' + (H - top) + '"/>';
    for (var wy = top + 16; wy < H - 10; wy += 22) for (var wx = x + 10; wx < x + bw - 16; wx += 18) {
      var r = rnd(), c = r > 0.62 ? 'hw-w on' : r > 0.45 ? 'hw-w dim' : 'hw-w';
      s += '<rect class="' + c + '" x="' + wx + '" y="' + wy + '" width="9" height="12"/>';
    }
    x += bw + 4 + Math.round(rnd() * 14);
  }
  var city = document.createElement('div'); city.className = 'hw-city';
  city.innerHTML = s + '</svg>'; host.appendChild(city);

  // Put the rooftops just under the buttons at every width.
  var hero = document.querySelector('.hero'), cta = document.querySelector('.hero .cta-row');
  function place() { city.style.top = (cta.getBoundingClientRect().bottom - hero.getBoundingClientRect().top - 30) + 'px'; }
  place(); addEventListener('resize', place);
  if (document.fonts) document.fonts.ready.then(place);

  var lit = [].slice.call(city.querySelectorAll('.hw-w.on'));
  var top3 = lit.filter(function (w) { return +w.getAttribute('y') < 140; });
  var pool = top3.length ? top3 : lit;
  function free() { var w = pool[Math.floor(Math.random() * pool.length)]; w.classList.add('free'); setTimeout(function () { w.classList.remove('free'); }, 3000); }
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) pool[0] && pool[0].classList.add('free');
  else { free(); setInterval(free, 2200); }
})();
