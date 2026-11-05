// Product name lives here. Change it once and every [data-product] element and the tab title follow.
const PRODUCT_NAME = 'standbyroom';

// For hosted sites, set data-marketplace-origin on the main.js script tag to the marketplace's public origin.
function marketplaceOrigin(value) {
  if (!value) return null;
  try {
    const url = new URL(value);
    return ['https:', 'http:'].includes(url.protocol) ? url.origin : null;
  } catch {
    return null;
  }
}

const marketOrigin = marketplaceOrigin(document.currentScript?.dataset.marketplaceOrigin);
if (marketOrigin) {
  document.querySelectorAll('[data-marketplace]').forEach(link => {
    const { pathname, search, hash } = new URL(link.href);
    link.href = new URL(pathname + search + hash, marketOrigin).href;
  });
}

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
