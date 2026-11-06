// Navigation (#/logement/<id>, #/comparer/<ids>), événements, démarrage

// navigation : #/logement/<id> = fiche ; sinon retour à la liste
function route() {
  const m = location.hash.match(/^#\/logement\/(\w+)/), c = location.hash.match(/^#\/comparer\/([\w,]+)/);
  if (m || c) {
    if ($('#vue-detail').hidden && $('#vue-comparaison').hidden) scrollListe = scrollY;
    c ? ouvrirComparaison(c[1].split(',').filter(Boolean).slice(0, CMP_MAX)) : ouvrirDetail(m[1]);
  } else {
    document.title = 'Comparateur Airbnb';
    vue(liste);
    scrollTo(0, scrollListe);
  }
}
addEventListener('hashchange', route);

document.addEventListener('click', e => {
  const t = e.target;
  if (t.closest('a[href^="#/logement/"]')) venuListe = true;
  const v = t.closest('.ville');
  if (v) { const s = v.dataset.v; sel.has(s) ? sel.delete(s) : sel.add(s); v.setAttribute('aria-pressed', sel.has(s)); majBarre(); }
  const pl = t.closest('.plus');
  if (pl) afficher(pl.closest('.groupe').dataset.s);
  const ph = t.closest('button[data-i]');
  if (ph) lb(+ph.dataset.i);
  if (t.closest('#retour')) { if (venuListe) history.back(); else location.hash = ''; }
  const x = t.closest('[data-x]');
  if (x) { cmp.delete(x.dataset.x); cmp.size ? location.replace('#/comparer/' + [...cmp].join(',')) : location.hash = ''; }
  const tg = t.closest('[data-t]');
  if (tg) {
    const i = tg.dataset.t;
    if (cmp.has(i)) cmp.delete(i); else if (cmp.size < CMP_MAX) cmp.add(i); else alert(`${CMP_MAX} logements maximum dans une comparaison.`);
    tg.textContent = btnCmp(i); majCmp();
  }
});
$('#voir').onclick = ouvrirGalerie;
document.addEventListener('change', e => {
  const t = e.target;
  if (t.id === 'diff') $('#cmp-table').classList.toggle('diff-only', t.checked);
  if (!t.dataset.c) return;
  if (t.checked && cmp.size >= CMP_MAX) { t.checked = false; alert(`${CMP_MAX} logements maximum dans une comparaison.`); return; }
  t.checked ? cmp.add(t.dataset.c) : cmp.delete(t.dataset.c);
  majCmp();
});
$('#go-cmp').onclick = () => { venuListe = true; location.hash = '#/comparer/' + [...cmp].join(','); };
$('#vider').onclick = () => {
  cmp.clear();
  document.querySelectorAll('input[data-c]').forEach(i => i.checked = false);
  document.querySelectorAll('[data-t]').forEach(b => b.textContent = btnCmp(b.dataset.t));
  majCmp();
};
$('#retour-villes').onclick = () => { liste = 'villes'; vue('villes'); scrollTo(0, 0); };

renderVilles();
majBarre();
route();
