/* Hero landscape: painterly night fjord drawn as inline SVG (owner: hero look). */
(function () {
  var host = document.querySelector('.hero-art');
  if (!host) return;

  var W = 1440, H = 1000, SEA = 790;
  var seed = 7;
  function rnd() { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; }

  // Midpoint-displacement ridge, with edges pushed up so the centre reads as a fjord opening.
  function ridge(base, amp, rough, edge, step) {
    var n = 64, pts = new Array(n + 1);
    pts[0] = 0; pts[n] = 0;
    (function split(a, b, r) {
      if (b - a < 2) return;
      var m = (a + b) >> 1;
      pts[m] = (pts[a] + pts[b]) / 2 + (rnd() - 0.5) * r;
      split(a, m, r * rough); split(m, b, r * rough);
    })(0, n, 1);
    var d = 'M0 ' + H;
    for (var i = 0; i <= n; i++) {
      var x = (i / n) * W, t = Math.abs(x - W / 2) / (W / 2);
      var y = base - amp * (0.55 + pts[i]) - edge * Math.pow(t, step);
      d += ' L' + x.toFixed(1) + ' ' + y.toFixed(1);
    }
    return d + ' L' + W + ' ' + H + 'Z';
  }

  function stars(count, cls) {
    var s = '<g class="' + cls + '" fill="#F4F1E6">';
    for (var i = 0; i < count; i++) {
      var y = Math.pow(rnd(), 1.4) * 600;
      s += '<circle cx="' + (rnd() * W).toFixed(0) + '" cy="' + y.toFixed(0) + '" r="' + (0.35 + rnd() * 1.1).toFixed(2) +
        '" opacity="' + (0.25 + rnd() * 0.7).toFixed(2) + '"/>';
    }
    return s + '</g>';
  }

  var far = ridge(650, 240, 0.6, 90, 2.2);
  var mid = ridge(735, 190, 0.56, 230, 2.6);
  var near = ridge(800, 90, 0.5, 460, 3.2);

  var moonX = 1170, moonY = 170, streak = '';
  for (var k = 0; k < 26; k++) {
    var w = 8 + rnd() * (60 - k * 1.6);
    streak += '<rect x="' + (moonX - w / 2 + (rnd() - 0.5) * (20 + k * 2)).toFixed(0) + '" y="' + (SEA + 5 + k * 7 + rnd() * 3).toFixed(0) + '" width="' + w.toFixed(0) +
      '" height="1.6" rx=".8" opacity="' + (0.42 - k * 0.014).toFixed(2) + '"/>';
  }

  host.innerHTML =
    '<svg viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="xMidYMax slice" aria-hidden="true" focusable="false">' +
    '<defs>' +
      '<linearGradient id="haSky" x1="0" y1="0" x2="0" y2="1">' +
        '<stop offset="0" stop-color="#070B15"/><stop offset=".45" stop-color="#121A30"/>' +
        '<stop offset=".72" stop-color="#26304D"/><stop offset=".8" stop-color="#3A4260"/></linearGradient>' +
      '<radialGradient id="haHorizon" cx=".5" cy="1" r=".6"><stop offset="0" stop-color="#6A6A7E" stop-opacity=".55"/>' +
        '<stop offset="1" stop-color="#6A6A7E" stop-opacity="0"/></radialGradient>' +
      '<radialGradient id="haMoon" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#F4F1E6" stop-opacity=".32"/>' +
        '<stop offset=".35" stop-color="#E8E4D2" stop-opacity=".1"/><stop offset="1" stop-color="#E8E4D2" stop-opacity="0"/></radialGradient>' +
      '<linearGradient id="haAur" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#7FC79A" stop-opacity="0"/>' +
        '<stop offset=".35" stop-color="#7FC79A" stop-opacity=".9"/><stop offset=".7" stop-color="#6FB8B0" stop-opacity=".6"/>' +
        '<stop offset="1" stop-color="#6FB8B0" stop-opacity="0"/></linearGradient>' +
      '<linearGradient id="haFar" x1="0" y1="0" x2="0" y2="1"><stop offset=".35" stop-color="#5A6484"/><stop offset=".75" stop-color="#2E3754"/></linearGradient>' +
      '<linearGradient id="haMid" x1="0" y1="0" x2="0" y2="1"><stop offset=".3" stop-color="#2F3958"/><stop offset=".8" stop-color="#1B2338"/></linearGradient>' +
      '<linearGradient id="haNear" x1="0" y1="0" x2="0" y2="1"><stop offset=".2" stop-color="#1A2236"/><stop offset=".8" stop-color="#0E1320"/></linearGradient>' +
      '<linearGradient id="haMist" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8A90A8" stop-opacity="0"/>' +
        '<stop offset=".6" stop-color="#8A90A8" stop-opacity=".22"/><stop offset="1" stop-color="#8A90A8" stop-opacity="0"/></linearGradient>' +
      '<linearGradient id="haWater" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#28314E"/><stop offset="1" stop-color="#0F1420"/></linearGradient>' +
      '<linearGradient id="haFade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0F1420" stop-opacity="0"/><stop offset="1" stop-color="#0F1420"/></linearGradient>' +
      '<filter id="haBlur" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="22"/></filter>' +
      '<filter id="haSoft"><feGaussianBlur stdDeviation="1.2"/></filter>' +
      '<filter id="haRipple" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".004 .09" numOctaves="2" seed="3"/>' +
        '<feDisplacementMap in="SourceGraphic" scale="14" xChannelSelector="R" yChannelSelector="G"/><feGaussianBlur stdDeviation="1.5"/></filter>' +
      '<clipPath id="haSea"><rect x="0" y="' + SEA + '" width="' + W + '" height="' + (H - SEA) + '"/></clipPath>' +
    '</defs>' +
    '<rect width="' + W + '" height="' + H + '" fill="url(#haSky)"/>' +
    '<rect y="380" width="' + W + '" height="420" fill="url(#haHorizon)"/>' +
    stars(150, 'ha-stars') + stars(40, 'ha-stars ha-tw1') + stars(30, 'ha-stars ha-tw2') +
    '<g class="ha-aurora" filter="url(#haBlur)" opacity=".26">' +
      '<path d="M-80 250 C 220 120, 460 330, 760 190 S 1240 120, 1540 230 L1540 300 C 1240 200, 1000 300, 760 270 S 220 220, -80 330Z" fill="url(#haAur)"/>' +
      '<path class="ha-aurora-2" d="M100 150 C 380 70, 620 210, 900 110 S 1300 80, 1500 140 L1500 175 C 1300 130, 1100 190, 900 160 S 380 130, 100 200Z" fill="url(#haAur)" opacity=".7"/>' +
    '</g>' +
    '<circle cx="' + moonX + '" cy="' + moonY + '" r="190" fill="url(#haMoon)"/>' +
    '<circle cx="' + moonX + '" cy="' + moonY + '" r="24" fill="#EDE8D6" filter="url(#haSoft)"/>' +
    '<g class="ha-land">' +
      '<path d="' + far + '" fill="url(#haFar)" stroke="#A9B0C8" stroke-opacity=".35" stroke-width="1.5"/>' +
      '<rect y="560" width="' + W + '" height="200" fill="url(#haMist)"/>' +
      '<path d="' + mid + '" fill="url(#haMid)"/>' +
      '<rect y="640" width="' + W + '" height="160" fill="url(#haMist)" opacity=".7"/>' +
      '<path d="' + near + '" fill="url(#haNear)"/>' +
    '</g>' +
    '<rect y="' + SEA + '" width="' + W + '" height="' + (H - SEA) + '" fill="url(#haWater)"/>' +
    '<g clip-path="url(#haSea)" filter="url(#haRipple)" opacity=".6">' +
      '<g transform="translate(0 ' + (2 * SEA) + ') scale(1 -1)">' +
        '<path d="' + far + '" fill="#4A5476"/><path d="' + mid + '" fill="#2A3350"/><path d="' + near + '" fill="#121828"/>' +
      '</g>' +
    '</g>' +
    '<rect y="' + SEA + '" width="' + W + '" height="1" fill="#E8E4D2" opacity=".12"/>' +
    '<g class="ha-shimmer" fill="#E8E4D2">' + streak + '</g>' +
    '<rect y="' + (H - 170) + '" width="' + W + '" height="170" fill="url(#haFade)"/>' +
    '</svg>';

  // Size the art so the water line sits just above the board; the board then floats on the water.
  var hero = host.closest('.hero'), board = hero && hero.querySelector('.board');
  function fit() {
    if (!board) { host.style.height = ''; return; }
    var top = board.getBoundingClientRect().top - hero.getBoundingClientRect().top;
    host.style.height = Math.round(top + 70) + 'px';
  }
  fit();
  if ('ResizeObserver' in window) new ResizeObserver(fit).observe(hero);
  else window.addEventListener('resize', fit);
})();
