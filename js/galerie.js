// Choix des villes, galerie de cartes, sélection pour la comparaison

const villes = ab().villes, sel = new Set();
let liste = 'villes', cur = 'villes', scrollListe = 0, venuListe = false;
const CMP_MAX = 4, cmp = new Set();
const btnCmp = i => cmp.has(i) ? '✓ Dans la comparaison' : '+ Ajouter à la comparaison';
function majCmp() {
  $('#bar2').hidden = !(cur === 'galerie' || cur === 'detail') || !cmp.size;
  $('#resume2').textContent = `${cmp.size}/${CMP_MAX} à comparer`;
  $('#go-cmp').disabled = cmp.size < 2;
}

function vue(nom) {
  cur = nom;
  ['villes', 'galerie', 'detail', 'comparaison'].forEach(v => $('#vue-' + v).hidden = v !== nom);
  $('#bar').hidden = nom !== 'villes' || !villes.length;
  document.querySelectorAll('input[data-c]').forEach(i => i.checked = cmp.has(i.dataset.c));
  majCmp();
}

function renderVilles() {
  if (!villes.length) { $('#villes').innerHTML = '<p class="vide">Aucune donnée. Lance le scraper : il crée le dossier data/ à côté de ce fichier.</p>'; return; }
  $('#villes').innerHTML = villes.map(v => {
    const [nom, ...reste] = v.nom.split(',');
    const f = v.prix_min == null ? '' : ` · ${money(v.prix_min, v.currency)}` + (v.prix_max > v.prix_min ? ` à ${money(v.prix_max, v.currency)}` : '');
    return `<button class="ville" data-v="${esc(v.slug)}" aria-pressed="false">${img(v.cover, nom)}<span class="ok">✓</span>
      <span class="txt"><b>${esc(nom)}</b><small>${esc(reste.join(',').trim())}${reste.length ? ' · ' : ''}${v.nb} ${plur(v.nb, 'logement', 'logements')}${esc(f)}</small></span></button>`;
  }).join('');
}

function majBarre() {
  const n = [...sel].reduce((t, s) => t + villes.find(v => v.slug === s).nb, 0);
  $('#voir').disabled = !sel.size;
  $('#resume').textContent = sel.size ? `${sel.size} ${plur(sel.size, 'ville', 'villes')} · ${n} ${plur(n, 'logement', 'logements')}` : 'Aucune ville sélectionnée';
}

const stats = a => [[a.guests, 'voyageurs'], [a.bedrooms, 'chambres'], [a.beds, 'lits'], [a.bathrooms, 'sdb']]
  .map(([v, t]) => `<div><dd>${dec(v)}</dd><dt>${t}</dt></div>`).join('');
const parPers = a => a.price_total != null && Number(a.adults) ? a.price_total / Number(a.adults) : null;
const nuitTxt = a => a.price_per_night != null ? `${money(a.price_per_night, a.currency)} / nuit` : '';
const noteTxt = a => a.rating ? '★ ' + dec(a.rating) + (a.reviews ? ` (${a.reviews})` : '') : 'Pas de note';

function carte(l) {
  const pp = parPers(l), lien = `#/logement/${esc(l.listing_id)}`;
  const sejour = [l.nights ? `${l.nights} ${plur(l.nights, 'nuit', 'nuits')}` : '', nuitTxt(l)].filter(Boolean).join(' · ');
  return `<article class="carte">
    <div class="photo"><a href="${lien}" aria-label="Voir ${esc(l.title)}">${img(l.cover, l.title)}</a>
      <label class="cmp"><input type="checkbox" data-c="${esc(l.listing_id)}" ${cmp.has(l.listing_id) ? 'checked' : ''}> Comparer</label>
      ${l.dist_center_km != null ? `<span class="km">${dec(l.dist_center_km)} km du centre</span>` : ''}</div>
    <div class="corps">
      <h3><a href="${lien}">${esc(l.title || 'Sans titre')}</a></h3>
      <div class="prix"><b>${money(l.price_total ?? l.price_per_night, l.currency)}</b><span>${l.price_total != null ? esc(sejour) : 'par nuit'}</span></div>
      ${pp != null ? `<div class="prix"><span>soit ${money(pp, l.currency)} par personne</span></div>` : ''}
      <dl class="stats">${stats(l)}</dl>
      <div class="pied"><span>${noteTxt(l)}</span><a href="${lien}">Voir le détail</a></div>
    </div></article>`;
}

// fiche de ville écrite à la main dans notes_villes.js (clé = nom du fichier data/villes/<clé>.js)
// Accepte soit un objet {resume, scores, infos, plus, moins, avis}, soit un simple texte.
const noteVille = s => {
  const n = (window.NOTES_VILLES || {})[s];
  if (!n) return '';
  if (typeof n === 'string') return n.trim() ? `<div class="note-ville note-texte">${esc(n.trim())}</div>` : '';
  const liste = (cls, titre, a) => a?.length
    ? `<div><h4>${titre}</h4><ul class="${cls}">${a.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>` : '';
  const scores = Object.entries(n.scores || {}).map(([k, v]) => {
    const p = Math.max(0, Math.min(5, Math.round(v)));
    return `<span>${esc(k)} <span class="pts" role="img" aria-label="${p} sur 5">${'●'.repeat(p)}<i>${'●'.repeat(5 - p)}</i></span></span>`;
  }).join('');
  const infos = (n.infos || []).map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join('');
  return `<div class="note-ville">
    <div class="note-tete"><p class="note-resume">${esc(n.resume || '')}</p>${scores ? `<div class="note-scores">${scores}</div>` : ''}</div>
    ${infos ? `<dl class="note-infos">${infos}</dl>` : ''}
    ${n.plus?.length || n.moins?.length ? `<div class="note-bilan">${liste('l-plus', 'Points forts', n.plus)}${liste('l-moins', 'Points faibles', n.moins)}</div>` : ''}
    ${n.avis ? `<p class="note-avis"><b>Mon avis :</b> ${esc(n.avis)}</p>` : ''}
  </div>`;
};

async function ouvrirGalerie() {
  const g = $('#galerie');
  g.innerHTML = '<p class="sub">Chargement…</p>'; liste = 'galerie'; vue('galerie'); scrollTo(0, 0);
  try { await Promise.all([...sel].filter(s => !ab().ville[s]).map(s => charge(`data/villes/${s}.js`))); }
  catch (e) { g.innerHTML = manque(e); return; }
  g.innerHTML = [...sel].map(s => {
    const v = villes.find(x => x.slug === s);
    return `<div class="groupe" data-s="${esc(s)}"><h2>${esc(v.nom)}</h2>
      ${noteVille(s)}
      <p>${v.nb} ${plur(v.nb, 'logement', 'logements')}, du plus proche au plus éloigné du centre</p>
      <div class="grille"></div><button class="back plus" hidden></button></div>`;
  }).join('');
  [...sel].forEach(s => afficher(s));
}

function afficher(s) {
  const box = document.querySelector(`.groupe[data-s="${s}"]`), items = ab().ville[s], g = box.querySelector('.grille');
  const n = g.children.length;
  g.insertAdjacentHTML('beforeend', items.slice(n, n + PAGE).map(carte).join(''));
  const reste = items.length - g.children.length, b = box.querySelector('.plus');
  b.hidden = reste <= 0; b.textContent = `Afficher plus (${reste} restants)`;
}