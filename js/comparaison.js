// Comparaison : regroupement des équipements similaires et tableau

// comparaison
const NOTES = ['Propreté', 'Précision', 'Arrivée', 'Communication', 'Emplacement', 'Qualité-prix'];
const groupes = a => a.amenity_groups?.length ? a.amenity_groups
  : a.amenities?.length ? [{cat: null, items: [...new Set(a.amenities)].filter(e => !/^(ce que propose|afficher les|show all)/i.test(e))}] : [];

// regroupement des équipements similaires : [motif sur texte sans accents, nom commun, catégorie par défaut]
const sans = t => t.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
const EQ = [
  [/vue sur la mer|vue mer|sea view|ocean view/, 'Vue sur la mer', 'Vues panoramiques'],
  [/vue sur la baie|bay view/, 'Vue sur la baie', 'Vues panoramiques'],
  [/^vue|\bview\b/, null, 'Vues panoramiques'],
  [/seche.?linge|dryer/, 'Sèche-linge', 'Chambre et linge'],
  [/lave.?linge|machine a laver|washer|washing/, 'Lave-linge', 'Chambre et linge'],
  [/lave.?vaisselle|dishwasher/, 'Lave-vaisselle', 'Cuisine et salle à manger'],
  [/television|\btv\b|netflix|hdtv|smart ?tv|chaines/, 'Télévision', 'Divertissement'],
  [/systeme audio|enceinte|sonos|bluetooth|sound/, 'Système audio', 'Divertissement'],
  [/wi-?fi|internet/, 'Wifi', 'Internet et bureau'],
  [/espace de travail|bureau|workspace/, 'Espace de travail dédié', 'Internet et bureau'],
  [/climatisation|air condition|\bclim\b/, 'Climatisation', 'Chauffage et climatisation'],
  [/chauffage|heating|radiateur/, 'Chauffage', 'Chauffage et climatisation'],
  [/piscine.*priv|priv.*piscine|private pool/, 'Piscine privée', 'Extérieur'],
  [/piscine|\bpool\b/, 'Piscine', 'Extérieur'],
  [/jacuzzi|bain a remous|hot tub|\bspa\b|sauna/, 'Jacuzzi / spa', 'Extérieur'],
  [/barbecue|\bbbq\b|\bgrill\b/, 'Barbecue', 'Extérieur'],
  [/patio|balcon|terrasse/, 'Patio ou balcon', 'Extérieur'],
  [/jardin|\bcour\b|garden|backyard/, 'Jardin', 'Extérieur'],
  [/acces a la plage|beach access|front de mer|bord de mer/, 'Accès à la plage', 'Emplacement'],
  [/stationnement|parking|garage/, 'Stationnement', 'Stationnement et installations'],
  [/ascenseur|elevator|\blift\b/, 'Ascenseur', 'Stationnement et installations'],
  [/salle de sport|\bgym\b|fitness/, 'Salle de sport', 'Stationnement et installations'],
  [/camera|surveillance/, 'Caméras de surveillance', 'Sécurité à la maison'],
  [/detecteur de fumee|smoke/, 'Détecteur de fumée', 'Sécurité à la maison'],
  [/monoxyde|carbon monoxide/, 'Détecteur de monoxyde de carbone', 'Sécurité à la maison'],
  [/extincteur|fire extinguisher/, 'Extincteur', 'Sécurité à la maison'],
  [/premiers secours|first aid/, 'Trousse de premiers secours', 'Sécurité à la maison'],
  [/coffre.?fort|\bsafe\b/, 'Coffre-fort', 'Chambre et linge'],
  [/^cuisine$|^kitchen$/, 'Cuisine', 'Cuisine et salle à manger'],
  [/refrigerateur|frigo|congelateur|fridge|freezer/, 'Réfrigérateur', 'Cuisine et salle à manger'],
  [/micro.?ondes|microwave/, 'Micro-ondes', 'Cuisine et salle à manger'],
  [/\bfour\b|\boven\b/, 'Four', 'Cuisine et salle à manger'],
  [/plaque|cuisiniere|cooktop|stove/, 'Plaques de cuisson', 'Cuisine et salle à manger'],
  [/cafetiere|machine a cafe|nespresso|coffee/, 'Cafetière', 'Cuisine et salle à manger'],
  [/bouilloire|kettle/, 'Bouilloire', 'Cuisine et salle à manger'],
  [/vaisselle|couverts|ustensiles|dishes|silverware/, 'Vaisselle et couverts', 'Cuisine et salle à manger'],
  [/seche.?cheveux|hair dryer/, 'Sèche-cheveux', 'Salle de bain'],
  [/apres.?shampoing|conditioner/, 'Après-shampoing', 'Salle de bain'],
  [/shampoing|shampoo/, 'Shampoing', 'Salle de bain'],
  [/gel douche|savon|body soap|body wash/, 'Gel douche et savon', 'Salle de bain'],
  [/produits de nettoyage|cleaning products/, 'Produits de nettoyage', 'Salle de bain'],
  [/douche exterieure|outdoor shower/, 'Douche extérieure', 'Salle de bain'],
  [/eau chaude|hot water/, 'Eau chaude', 'Salle de bain'],
  [/baignoire|bathtub/, 'Baignoire', 'Salle de bain'],
  [/bidet/, 'Bidet', 'Salle de bain'],
  [/linge de lit|draps|bed linen/, 'Linge de lit', 'Chambre et linge'],
  [/oreillers|couvertures|pillows|blankets/, 'Oreillers et couvertures supplémentaires', 'Chambre et linge'],
  [/rideaux|stores|blackout/, 'Rideaux occultants', 'Chambre et linge'],
  [/fer a repasser|\biron\b/, 'Fer à repasser', 'Chambre et linge'],
  [/etendoir|drying rack/, 'Étendoir à linge', 'Chambre et linge'],
  [/cintres|hangers/, 'Cintres', 'Chambre et linge'],
  [/moustiquaire/, 'Moustiquaire', 'Chambre et linge'],
  [/rangement pour les vetements|placard|armoire|commode|clothing storage/, 'Rangement pour vêtements', 'Chambre et linge'],
  [/produits de base|essentials/, 'Produits de base', 'Chambre et linge'],
  [/lit (pour )?bebe|lit parapluie|berceau|crib/, 'Lit bébé', 'Famille'],
  [/chaise haute|high chair/, 'Chaise haute', 'Famille'],
  [/animaux|\bpets?\b/, 'Animaux acceptés', 'Services'],
];
function canon(item) {
  const t = sans(item);
  for (const [re, nom, cat] of EQ) if (re.test(t)) return {k: nom || t, nom: nom || item, cat};
  return {k: t.replace(/\s*\(.*?\)/g, '').replace(/\s+/g, ' ').trim(), nom: item, cat: null};
}

async function ouvrirComparaison(ids) {
  const d = $('#comparaison');
  cmp.clear(); ids.forEach(i => cmp.add(i));
  d.innerHTML = '<p class="sub">Chargement…</p>'; vue('comparaison'); scrollTo(0, 0);
  try { await Promise.all(ids.filter(i => !ab().logement[i]).map(i => charge(`https://maathouu.github.io/TempData/logements/${i}.js`))); }
  catch (e) { d.innerHTML = '<button class="back" id="retour">Retour</button>' + manque(e); return; }
  const L = ids.map(i => ab().logement[i]), n = L.length;
  const sec = (t, cls = '') => `<tr class="sec ${cls}"><th colspan="${n + 1}"><span>${esc(t)}</span></th></tr>`;
  const meilleur = (vals, mode) => {
    const v = vals.filter(x => x != null && !isNaN(x));
    if (!mode || new Set(v).size < 2) return vals.map(() => false);
    const t = Math[mode](...v);
    return vals.map(x => x === t);
  };
  const ligne = (label, get, fmt, mode) => {
    const vals = L.map(a => get(a)), b = meilleur(vals, mode);
    return `<tr><th>${esc(label)}</th>${vals.map((v, i) => `<td${b[i] ? ' class="best"' : ''}>${v == null ? '—' : fmt(v, L[i])}</td>`).join('')}</tr>`;
  };
  const prix = (v, a) => money(v, a.currency);
  const tete = `<tr><th></th>${L.map(a => `<th><button class="x" data-x="${esc(a.listing_id)}" aria-label="Retirer de la comparaison">✕</button>
    <a href="#/logement/${esc(a.listing_id)}"><div class="cmp-img">${img(a.photos[0], a.title)}</div><h3>${esc(a.title || 'Sans titre')}</h3></a>
    <small>${esc(a.ville || a.city_guess || '')}</small></th>`).join('')}</tr>`;

  let h = ligne('Prix du séjour', a => a.price_total, prix, 'min')
    + ligne('Prix par nuit', a => a.price_per_night, prix, 'min')
    + ligne('Prix par personne', a => parPers(a), prix, 'min')
    + ligne('Voyageurs max', a => a.guests, dec, 'max')
    + ligne('Chambres', a => a.bedrooms, dec, 'max')
    + ligne('Lits', a => a.beds, dec, 'max')
    + ligne('Salles de bain', a => a.bathrooms, dec, 'max')
    + ligne('Distance au centre', a => a.dist_center_km, v => dec(v) + ' km', 'min')
    + ligne('Note globale', a => a.rating == null ? null : Number(a.rating), (v, a) => '★ ' + dec(v) + (a.reviews ? ` (${a.reviews} avis)` : ''), 'max');

  const notes = NOTES.filter(k => L.some(a => a.ratings?.[k] != null));
  if (notes.length) h += sec('Notes détaillées') + notes.map(k => ligne(k, a => a.ratings?.[k], v => '★ ' + dec(v), 'max')).join('');

  h += sec('Règlement et description')
    + `<tr><th>Règlement intérieur</th>${L.map(a => `<td>${a.rules?.length ? `<ul class="rules">${a.rules.map(r => `<li>${esc(r)}</li>`).join('')}</ul>` : '—'}</td>`).join('')}</tr>`
    + `<tr><th>Description</th>${L.map(a => `<td>${a.description ? `<details><summary>${esc(a.description.slice(0, 140))}…</summary><p class="desc">${esc(a.description)}</p></details>` : '—'}</td>`).join('')}</tr>`;

  h += sec('Équipements')
    + ligne('Nombre d’équipements', a => a.amenities?.length ? new Set(a.amenities).size : null, dec, 'max');
  // une entrée par équipement « commun » ; les libellés d'origine sont gardés par logement
  const parVilla = L.map(a => {
    const m = new Map();
    groupes(a).forEach(g => g.items.forEach(it => {
      const c = canon(it), e = m.get(c.k) || {nom: c.nom, def: c.cat, cat: null, orig: []};
      if (g.cat && !e.cat) e.cat = g.cat;
      if (!e.orig.includes(it)) e.orig.push(it);
      m.set(c.k, e);
    }));
    return m;
  });
  const cles = new Map();
  parVilla.forEach(m => m.forEach((e, k) => {
    const c = cles.get(k) || {nom: e.nom, real: null, def: null};
    c.real = c.real || e.cat; c.def = c.def || e.def;
    cles.set(k, c);
  }));
  const parCat = new Map();
  cles.forEach((c, k) => {
    const cat = c.real || c.def || 'Autres équipements';
    if (!parCat.has(cat)) parCat.set(cat, []);
    parCat.get(cat).push(k);
  });
  [...parCat.keys()].sort((x, y) => (x === 'Autres équipements') - (y === 'Autres équipements')).forEach(cat => {
    const rows = parCat.get(cat).map(k => {
      const es = parVilla.map(m => m.get(k));
      const origs = new Set(es.flatMap(e => e ? e.orig : []));
      const label = origs.size === 1 ? [...origs][0] : cles.get(k).nom;  // même nom partout : on garde tel quel
      const tous = es.every(Boolean) && origs.size === 1;
      const cells = es.map(e => {
        if (!e) return '<td class="non">—</td>';
        const autres = e.orig.filter(o => o !== label);
        return `<td class="oui">✓${autres.length ? `<em class="orig">Équipement original : ${esc(autres.join(' ; '))}</em>` : ''}</td>`;
      }).join('');
      return `<tr class="${tous ? 'commun' : ''}"><th>${esc(label)}</th>${cells}</tr>`;
    });
    h += sec(cat, rows.every(r => r.startsWith('<tr class="commun"')) ? 'commun' : '') + rows.join('');
  });

  document.title = 'Comparaison';
  d.innerHTML = `<button class="back" id="retour">Retour</button>
    <h1>Comparaison</h1>
    <p class="sub">${n} ${plur(n, 'logement', 'logements')}. Le ✓ marque la meilleure valeur de chaque ligne.</p>
    <label class="opts"><input type="checkbox" id="diff"> Équipements : voir seulement les différences</label>
    <div class="cmp-wrap"><table class="cmp-table" id="cmp-table"><thead>${tete}</thead><tbody>${h}</tbody></table></div>`;
}
