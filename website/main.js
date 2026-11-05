// Product name lives here. Change it once and every [data-product] element and the tab title follow.
const PRODUCT_NAME = 'Mesh standby';

document.title = PRODUCT_NAME;
document.querySelectorAll('[data-product]').forEach(el => { el.textContent = PRODUCT_NAME; });

// Hero board lives in board.js (data in board-data.js).

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
