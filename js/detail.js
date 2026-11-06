// Fiche d’un logement + visionneuse de photos

async function ouvrirDetail(id) {
  const d = $('#detail');
  d.innerHTML = '<p class="sub">Chargement…</p>'; vue('detail'); scrollTo(0, 0);
  try { if (!ab().logement[id]) await charge(`https://maathouu.github.io/TempData/logements/${id}.js`); }
  catch (e) { d.innerHTML = '<button class="back" id="retour">Retour</button>' + manque(e); return; }
  const a = ab().logement[id], pp = parPers(a);
  lbPhotos = a.photos;
  const eq = [...new Set(a.amenities || [])].filter(e => !/^(ce que propose|afficher les|show all)/i.test(e));
  const dates = a.check_in && a.check_out ? `${new Date(a.check_in).toLocaleDateString('fr-FR')} → ${new Date(a.check_out).toLocaleDateString('fr-FR')}` : '';
  document.title = a.title || 'Logement';
  d.innerHTML = `<button class="back" id="retour">Retour</button>
    <h1>${esc(a.title || 'Sans titre')}</h1>
    <p class="sub">${esc(a.ville || a.city_guess || '')}${a.dist_center_km != null ? ` · à ${dec(a.dist_center_km)} km du centre` : ''} · ${noteTxt(a)}</p>
    ${a.photos[0] ? `<button class="hero" data-i="0" aria-label="Agrandir la photo">${img(a.photos[0], a.title, 1200)}</button>` : ''}
    <div class="fiche"><div>
      ${a.description ? `<h2>Description</h2><p class="desc">${esc(a.description)}</p>` : ''}
      ${a.sleeping ? `<h2>Couchages</h2><p class="desc">${esc(a.sleeping)}</p>` : ''}
      ${a.ratings && Object.keys(a.ratings).length ? `<h2>Notes détaillées</h2><ul class="notes">${Object.entries(a.ratings).map(([k, v]) => `<li><b>${dec(v)}</b>${esc(k)}</li>`).join('')}</ul>` : ''}
      ${a.rules?.length ? `<h2>Règlement intérieur</h2><ul class="rules">${a.rules.map(r => `<li>${esc(r)}</li>`).join('')}</ul>` : ''}
      ${a.amenity_groups?.length
        ? `<h2>Équipements (${eq.length})</h2>` + a.amenity_groups.map(g => `<h3 class="cat">${esc(g.cat)}</h3><ul class="equip">${g.items.map(e => `<li>${esc(e)}</li>`).join('')}</ul>`).join('')
        : eq.length ? `<h2>Équipements (${eq.length})</h2><ul class="equip">${eq.map(e => `<li>${esc(e)}</li>`).join('')}</ul>` : ''}
    </div>
    <aside class="panneau">
      <div class="prix"><b>${money(a.price_total ?? a.price_per_night, a.currency)}</b><span>${a.price_total != null ? (a.nights ? a.nights + ' ' + plur(a.nights, 'nuit', 'nuits') : 'séjour') : 'par nuit'}</span></div>
      <div class="prix"><span>${esc([nuitTxt(a), dates, pp != null ? `soit ${money(pp, a.currency)} par personne` : ''].filter(Boolean).join(' · '))}</span></div>
      <dl class="stats">${stats(a)}</dl>
      ${a.lat != null ? `<a href="https://www.openstreetmap.org/?mlat=${a.lat}&mlon=${a.lng}#map=15/${a.lat}/${a.lng}" target="_blank" rel="noopener">Voir sur la carte</a>` : ''}
      <button class="back" data-t="${esc(id)}">${btnCmp(id)}</button>
      <a href="${esc(a.url)}" target="_blank" rel="noopener">Ouvrir sur Airbnb</a>
      ${a.price_raw ? `<details><summary>Détail du prix relevé</summary><p>${esc(a.price_raw)}</p></details>` : ''}
      <small class="sub">Données relevées le ${esc(a.scraped_at || '?')}</small>
    </aside></div>
    ${a.photos.length ? `<h2 class="toutes-h">Toutes les photos (${a.photos.length})</h2>
    <div class="mosaique tout">${a.photos.map((p, i) => `<button data-i="${i}" aria-label="Agrandir la photo ${i + 1}">${img(p, 'Photo ' + (i + 1))}</button>`).join('')}</div>` : '<p class="vide">Aucune photo.</p>'}`;
}

// visionneuse
let lbPhotos = [], lbI = 0;
function lb(i) {
  lbI = (i + lbPhotos.length) % lbPhotos.length;
  const p = lbPhotos[lbI], im = $('#lbimg');
  im.dataset.r = p.r; im.dataset.w = 1200; im.src = p.l || p.r + '?im_w=1200';
  $('#lbn').textContent = `${lbI + 1} / ${lbPhotos.length}`; $('#lb').hidden = false;
}
$('#lbx').onclick = () => $('#lb').hidden = true;
$('#lbp').onclick = () => lb(lbI - 1);
$('#lbs').onclick = () => lb(lbI + 1);
addEventListener('keydown', e => {
  if ($('#lb').hidden) return;
  if (e.key === 'Escape') $('#lb').hidden = true;
  if (e.key === 'ArrowLeft') lb(lbI - 1);
  if (e.key === 'ArrowRight') lb(lbI + 1);
});
