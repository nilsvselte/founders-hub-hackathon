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

// Demo Mac: the landing page is served on :8080 and the marketplace on :3000 of the same host
// (localhost or the Tailscale IP), so phones and other laptops on the tailnet reach both.
const demoOrigin = location.port === '8080' ? `${location.protocol}//${location.hostname}:3000` : null;
// The demo Mac keeps its local marketplace; everywhere else uses the hosted one.
const configuredOrigin = document.currentScript?.dataset.marketplaceOrigin;
const marketOrigin = configuredOrigin === 'same-origin' ? null : demoOrigin || marketplaceOrigin(configuredOrigin);
if (marketOrigin) {
  document.querySelectorAll('[data-marketplace]').forEach(element => {
    const property = element.localName === 'form' ? 'action' : 'href';
    const { pathname, search, hash } = new URL(element[property]);
    element[property] = new URL(pathname + search + hash, marketOrigin).href;
  });
}

// Pages with their own SEO title opt out with <html data-keep-title>.
if (!document.documentElement.hasAttribute('data-keep-title')) document.title = PRODUCT_NAME;
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
