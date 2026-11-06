// Outils communs : accès aux données, formatage, chargement des fichiers data/

const ab = () => window.AB || {villes: [], ville: {}, logement: {}};
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = (n, c) => n == null ? '—' : Math.round(n).toLocaleString('fr-FR') + ' ' + (c || '€');
const dec = n => n == null ? '—' : String(n).replace('.', ',');
const plur = (n, a, b) => n > 1 ? b : a;
const PAGE = 60;
const charge = src => new Promise((ok, ko) => {
  const s = document.createElement('script');
  s.src = src; s.onload = ok; s.onerror = () => ko(new Error(src)); document.head.append(s);
});
// photo locale d'abord, sinon l'URL Airbnb
function fb(i) { const r = i.dataset.r; if (r && !i.src.includes(r)) i.src = r + '?im_w=' + i.dataset.w; }
const img = (p, alt, w = 720) => p
  ? `<img src="${esc(p.l || p.r + '?im_w=' + w)}" data-r="${esc(p.r)}" data-w="${w}" alt="${esc(alt)}" loading="lazy" onerror="fb(this)">` : '';
const manque = e => `<p class="vide">Fichier introuvable : ${esc(e.message)}<br>Lance le scraper pour régénérer le dossier data/.</p>`;
