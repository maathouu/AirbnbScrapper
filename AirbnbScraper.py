#!/usr/bin/env python3
"""
airbnb_scraper.py - Récupère des infos d'annonces Airbnb et les range en fichiers .js pour index.html.

Pour chaque lien : titre, prix (total + par nuit si dates dans l'URL), voyageurs / chambres /
lits / salles de bain, description, couchages, équipements, note, photos, coordonnées GPS
et distance au centre-ville.

UTILISATION (dans un IDE, interpréteur = python.exe du Python portable) :
    1. Mets les liens Airbnb dans urls.txt (un par ligne), à côté de ce fichier.
    2. Règle la section RÉGLAGES ci-dessous (ville, options).
    3. Lance ce fichier (bouton Run). Aucun argument en ligne de commande.

Ou depuis un autre fichier / la console de l'IDE :
    import airbnb_scraper
    airbnb_scraper.run(liens=["https://www.airbnb.fr/rooms/123?check_in=...&check_out=...&adults=2"],
                       ville="Annecy, France")

SORTIE (à côté du script, lue par index.html) :
    data/villes.js            index des villes (léger)
    data/villes/<ville>.js    résumés des logements d'une ville
    data/logements/<id>.js    fiche complète d'un logement (description, équipements, photos...)
    photos/<id>/001.jpg ...   photos téléchargées

IMPORTANT : le prix total n'apparaît que si l'URL contient check_in, check_out et adults
(ex. ?check_in=2026-12-20&check_out=2026-12-27&adults=2).
"""
import html as htmllib
import json
import math
import random
import re
import sys
import time
import unicodedata
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import os

# Python portable : Chromium est cherché dans le dossier "browsers" situé à côté de python.exe,
# quelle que soit la lettre du disque. Une variable déjà définie à la main reste prioritaire.
_portable_browsers = Path(sys.executable).resolve().parent / "browsers"
if "PLAYWRIGHT_BROWSERS_PATH" not in os.environ and _portable_browsers.is_dir():
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(_portable_browsers)


# =============================== RÉGLAGES (à modifier ici) ===============================
FICHIER_LIENS = "urls.txt"        # fichier avec un lien Airbnb par ligne
VILLE = "Annecy, France"          # sert à trouver le centre-ville (None pour désactiver)
CENTRE = None                     # ou coordonnées précises, ex. (45.8992, 6.1294) ; prioritaire sur VILLE
TELECHARGER_PHOTOS = True
MAX_PHOTOS = 0                    # 0 = toutes les photos
AFFICHER_NAVIGATEUR = False       # True si Airbnb bloque le mode invisible
# =========================================================================================

# Tous les fichiers (photos, data, urls.txt) sont lus/écrits à côté de ce script
SCRIPT_DIR = Path(__file__).resolve().parent

PHOTO_DIR = SCRIPT_DIR / "data/photos"

PHOTO_RE = re.compile(r"https://a0\.muscache\.com/im/pictures/[A-Za-z0-9_\-/.]+")
PHOTO_EXCLUDE = ("/user/", "UserProfile", "AirbnbPlatformAssets", "/icons/", "/Hosting-Icon")

# Notes détaillées des avis (nom affiché -> motifs FR / EN)
RATING_LABELS = [("Propreté", r"Propreté|Cleanliness"), ("Précision", r"Précision|Accuracy"),
                 ("Arrivée", r"Arrivée|Check-?in"), ("Communication", r"Communication"),
                 ("Emplacement", r"Emplacement|Location"), ("Qualité-prix", r"Qualité[- ]prix|Value")]

MONEY = r"(?:(?P<c1>€|\$|£|CHF)\s*(?P<a1>\d[\d\s\u202f\u00a0.,]*)|(?P<a2>\d[\d\s\u202f\u00a0.,]*?)\s*(?P<c2>€|\$|£|CHF))"


# --------------------------------------------------------------------------- utilitaires
def parse_amount(s):
    s = re.sub(r"[\s\u202f\u00a0]", "", s).strip(".,")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def walk(obj):
    """Parcourt récursivement un JSON et renvoie tous les dicts."""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v)


def strip_tags(s):
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    return htmllib.unescape(s).strip()


# --------------------------------------------------------------------------- extraction (pur, testable hors-ligne)
def extract_price(text, check_in=None, check_out=None):
    """Cherche prix total et prix/nuit dans le texte du panneau de réservation."""
    res = {"price_total": None, "price_per_night": None, "currency": None, "nights": None, "price_raw": None}
    if not text:
        return res

    def amt(m):
        return parse_amount(m.group("a1") or m.group("a2")), (m.group("c1") or m.group("c2"))

    # "123 € x 7 nuits"
    m = re.search(MONEY + r"\s*[x×]\s*(?P<n>\d+)\s*(?:nuits?|nights?)", text, re.I)
    if m:
        res["price_per_night"], res["currency"] = amt(m)
        res["nights"] = int(m.group("n"))

    # "Total ... 1 234 €"
    m = re.search(r"(?:Total|au total)[^\d€$£]{0,40}?" + MONEY, text, re.I)
    if not m:
        m = re.search(MONEY + r"\s*(?:au total|total)", text, re.I)
    if m:
        res["price_total"], res["currency"] = amt(m)

    # Sans dates : on garde juste le premier prix vu (souvent "X € par nuit")
    if res["price_total"] is None and res["price_per_night"] is None:
        m = re.search(MONEY, text)
        if m:
            res["price_per_night"], res["currency"] = amt(m)

    lines = [l.strip() for l in text.splitlines() if re.search(r"[€$£]|CHF", l)]
    res["price_raw"] = " | ".join(lines[:15])
    return res


def extract_overview(text):
    def num(pattern):
        m = re.search(pattern, text, re.I)
        if not m:
            return None
        v = m.group(1).replace(",", ".")
        return float(v) if "." in v else int(v)

    return {
        "guests": num(r"(\d+)\s+(?:voyageurs?|guests?)"),
        "bedrooms": num(r"(\d+)\s+(?:chambres?|bedrooms?)"),
        "beds": num(r"(\d+)\s+(?:lits?|beds?)\b"),
        "bathrooms": num(r"(\d+(?:[.,]\d+)?)\s+(?:salles?\s+de\s+bains?|bathrooms?)"),
    }


def extract_ratings(text):
    """{'Propreté': 4.9, ...} depuis le bloc des avis (libellé suivi de la note, ex. 'Propreté 4,9')."""
    out = {}
    for nom, motif in RATING_LABELS:
        m = re.search(r"(?:%s)\s*\n?\s*(\d(?:[.,]\d)?)\b" % motif, text or "", re.I)
        if m:
            out[nom] = float(m.group(1).replace(",", "."))
    return out


def extract_rules(text):
    """Lignes du bloc « Règlement intérieur » (arrivée, départ, fêtes, animaux...)."""
    lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
    return [l for l in lines if not re.match(r"(?i)^(règlement intérieur|house rules|afficher|show|en savoir plus|learn more)", l)]


def extract_photos(blobs):
    seen, out = set(), []
    for b in blobs:
        b = b.replace("\\u002F", "/").replace("\\/", "/")
        for url in PHOTO_RE.findall(b):
            if any(x in url for x in PHOTO_EXCLUDE):
                continue
            if not re.search(r"\.(jpe?g|png|webp)$", url, re.I):
                continue
            if url not in seen:
                seen.add(url)
                out.append(url)
    return out


def extract_from_json(json_blobs):
    """json_blobs: liste de (type, texte) des <script type="application/json|ld+json">."""
    data = {"name": None, "description": None, "lat": None, "lng": None, "city": None,
            "rating": None, "reviews": None}
    parsed_ld, parsed_state = [], []
    for typ, txt in json_blobs:
        try:
            obj = json.loads(txt)
        except Exception:
            continue
        (parsed_ld if "ld+json" in (typ or "") else parsed_state).append(obj)

    # 1) JSON-LD (schema.org) : le plus stable
    for obj in parsed_ld:
        for d in walk(obj):
            if d.get("name") and not data["name"]:
                data["name"] = d["name"]
            if d.get("description") and not data["description"]:
                data["description"] = d["description"]
            if data["lat"] is None and d.get("latitude") is not None and d.get("longitude") is not None:
                try:
                    data["lat"], data["lng"] = float(d["latitude"]), float(d["longitude"])
                except (TypeError, ValueError):
                    pass
            addr = d.get("address")
            if isinstance(addr, dict) and not data["city"]:
                data["city"] = addr.get("addressLocality") or addr.get("addressRegion")
            ar = d.get("aggregateRating")
            if isinstance(ar, dict) and data["rating"] is None:
                data["rating"] = ar.get("ratingValue")
                data["reviews"] = ar.get("ratingCount") or ar.get("reviewCount")

    # 2) État JS embarqué (structure susceptible de changer)
    for obj in parsed_state:
        for d in walk(obj):
            if data["lat"] is None:
                for kl, kg in (("listingLat", "listingLng"), ("lat", "lng"), ("latitude", "longitude")):
                    if isinstance(d.get(kl), (int, float)) and isinstance(d.get(kg), (int, float)):
                        data["lat"], data["lng"] = float(d[kl]), float(d[kg])
                        break
            hd = d.get("htmlDescription")
            if isinstance(hd, dict) and hd.get("htmlText"):
                data["description"] = strip_tags(hd["htmlText"])  # description complète
            if data["rating"] is None and isinstance(d.get("guestSatisfactionOverall"), (int, float)):
                data["rating"] = d["guestSatisfactionOverall"]
            if data["reviews"] is None and isinstance(d.get("reviewsCount"), int):
                data["reviews"] = d["reviewsCount"]
    return data


# --------------------------------------------------------------------------- navigateur
# Lit la fenêtre « Ce que propose ce logement » : titres de catégories (h1-h4) + équipements (li)
JS_EQUIPEMENTS = r"""() => {
  const ds = [...document.querySelectorAll('[role="dialog"]')];
  const d = ds.sort((a, b) => b.innerText.length - a.innerText.length)[0];
  if (!d) return {groupes: [], texte: ''};
  const groupes = []; let cur = null, off = false;
  for (const el of d.querySelectorAll('h1, h2, h3, h4, [role="heading"], li, [id$="row-title"]')) {
    const t = el.innerText.trim();
    if (!t) continue;
    if (/^H\d$/.test(el.tagName) || el.getAttribute('role') === 'heading') {
      off = /non inclus|not included|indisponible/i.test(t);
      if (!cur || cur.cat !== t) { cur = {cat: t, items: []}; groupes.push(cur); }
      continue;
    }
    if (!cur || off || el.closest('del, s') || el.querySelector('del, s') || /^(non inclus|indisponible|not included)/i.test(t)) continue;
    const nom = t.split('\n')[0].trim();
    if (nom && !cur.items.includes(nom)) cur.items.push(nom);
  }
  return {groupes: groupes.filter(g => g.items.length), texte: d.innerText.slice(0, 300)};
}"""


def lire_equipements(page):
    """Ouvre la fenêtre « Ce que propose ce logement » et renvoie [{cat, items}] (liste vide si échec)."""
    groupes, texte = [], ""
    try:
        bouton = page.locator('[data-section-id="AMENITIES_DEFAULT"] button').filter(
            has_text=re.compile(r"\d+\s+(équipements|amenities)", re.I)).first
        bouton.wait_for(state="attached", timeout=5000)
        # clic JavaScript : contourne l'erreur « element is outside of the viewport »
        bouton.evaluate("b => { b.scrollIntoView({block: 'center'}); b.click(); }")
        page.wait_for_selector('[role="dialog"] li, [role="dialog"] h3', timeout=8000)
        page.wait_for_timeout(1000)
        res = page.evaluate(JS_EQUIPEMENTS)
        groupes, texte = res["groupes"], res["texte"]
    except Exception as e:
        print(f"   ! fenêtre des équipements : {str(e).splitlines()[0]}")
    if not groupes and texte:
        print(f"   ! aucune catégorie lue ; début de la fenêtre : {texte!r}")
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass
    return groupes


def scrape_page(page, url):
    import re as _re
    page.goto(url, wait_until="domcontentloaded", timeout=60000)

    # bandeau cookies / popup de traduction
    for label in (r"Tout accepter|Accepter|Accept all|OK",):
        try:
            page.get_by_role("button", name=_re.compile(label, _re.I)).first.click(timeout=3000)
        except Exception:
            pass
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass

    page.wait_for_selector("h1", timeout=30000)
    for _ in range(6):  # scroll pour déclencher le chargement des sections
        page.mouse.wheel(0, 1500)
        page.wait_for_timeout(600)
    page.wait_for_timeout(1500)

    def inner(selector):
        try:
            return page.inner_text(selector, timeout=2000)
        except Exception:
            return ""

    body = inner("body")
    booking = inner('[data-section-id="BOOK_IT_SIDEBAR"]') or inner('[data-testid="book-it-default"]') or body

    return {
        "h1": inner("h1"),
        "body_text": body,
        "booking_text": booking,
        "sleeping": inner('[data-section-id="SLEEPING_ARRANGEMENT_DEFAULT"]'),
        "amenities": inner('[data-section-id="AMENITIES_DEFAULT"]'),
        "json_blobs": page.eval_on_selector_all(
            'script[type="application/json"], script[type="application/ld+json"]',
            "els => els.map(e => [e.type, e.textContent])",
        ),
        "html": page.content(),
        "reviews_text": inner('[data-section-id="REVIEWS_DEFAULT"]'),
        "rules": inner('[data-section-id="POLICIES_DEFAULT"]'),
        "amenity_groups": lire_equipements(page),  # en dernier : ouvre puis ferme une fenêtre
    }


def build_record(url, raw):
    q = parse_qs(urlparse(url).query)
    m = re.search(r"/rooms/(?:plus/)?(\d+)", url)
    j = extract_from_json(raw["json_blobs"])
    price = extract_price(raw["booking_text"])
    overview = extract_overview(raw["body_text"][:6000])
    photos = extract_photos([raw["html"]] + [t for _, t in raw["json_blobs"]])

    groupes = raw.get("amenity_groups") or []
    amenities = [i for g in groupes for i in g["items"]] or [l.strip() for l in raw["amenities"].splitlines()
                                                    if l.strip() and not re.match(r"(?i)(ce que propose|what this place|afficher|show all)", l.strip())]
    return {
        "listing_id": m.group(1) if m else None,
        "url": url,
        "title": raw["h1"].strip() or j["name"],
        "description": j["description"],
        "check_in": (q.get("check_in") or [None])[0],
        "check_out": (q.get("check_out") or [None])[0],
        "adults": (q.get("adults") or [None])[0],
        **price,
        **overview,
        "sleeping": raw["sleeping"].strip() or None,
        "amenities": amenities,
        "amenity_groups": groupes,
        "ratings": extract_ratings(raw.get("reviews_text") or raw["body_text"]),
        "rules": extract_rules(raw.get("rules")),
        "rating": j["rating"],
        "reviews": j["reviews"],
        "lat": j["lat"],
        "lng": j["lng"],
        "city_guess": j["city"],
        "photos": photos,
        "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


# --------------------------------------------------------------------------- centre-ville
_geo_cache = {}
_geo_names = {}


def geocode(query):
    if query in _geo_cache:
        return _geo_cache[query]
    import requests
    time.sleep(1.1)  # politique Nominatim : 1 req/s
    r = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": query, "format": "json", "limit": 1},
        headers={"User-Agent": "airbnb-compare-script/1.0 (usage personnel)"},
        timeout=20,
    )
    r.raise_for_status()
    res = r.json()
    _geo_cache[query] = (float(res[0]["lat"]), float(res[0]["lon"])) if res else None
    if res:
        _geo_names[query] = res[0].get("display_name", query)
    return _geo_cache[query]


def tester_ville(ville=None):
    """Renvoie (lat, lng) du centre de la ville, ou lève une erreur si elle est introuvable.

    Exemple : tester_ville("Annecy, France")  ->  (45.8992, 6.1294)
    """
    ville = ville or VILLE
    if not ville:
        raise ValueError("Aucune ville renseignée (réglage VILLE vide).")
    try:
        coords = geocode(ville)
    except Exception as e:
        raise ConnectionError(f"Impossible d'interroger le service de géocodage (internet ?) : {e}") from e
    if coords is None:
        raise ValueError(f"Ville introuvable : {ville!r}. Essaie le format 'Ville, Pays'.")
    print(f"{ville!r} -> {_geo_names.get(ville, ville)}\n   lat={coords[0]}, lng={coords[1]}")
    return coords


def add_distance(rec, center, city):
    rec["center_lat"] = rec["center_lng"] = rec["dist_center_km"] = None
    c = center
    if c is None:
        name = city or rec.get("city_guess")
        if name:
            try:
                c = geocode(name)
            except Exception as e:
                print(f"   ! géocodage '{name}' impossible : {e}")
    if c and rec["lat"] is not None:
        rec["center_lat"], rec["center_lng"] = c
        rec["dist_center_km"] = round(haversine_km(rec["lat"], rec["lng"], *c), 2)


# --------------------------------------------------------------------------- données du site (data/*.js)
DATA_DIR = SCRIPT_DIR / "data"
LOGEMENTS_DIR = DATA_DIR / "logements"
VILLES_DIR = DATA_DIR / "villes"
ENTETE_JS = "window.AB = window.AB || {villes: [], ville: {}, logement: {}};\n"  # .js (pas .json) : marche en double-clic
CHAMPS = ["listing_id", "url", "title", "ville", "city_guess", "description", "check_in", "check_out", "adults",
          "price_total", "price_per_night", "currency", "nights", "price_raw", "guests", "bedrooms", "beds",
          "bathrooms", "sleeping", "amenities", "amenity_groups", "ratings", "rules", "rating", "reviews", "lat", "lng", "dist_center_km", "scraped_at"]
CHAMPS_CARTE = ["listing_id", "title", "price_total", "price_per_night", "currency", "nights", "adults",
                "guests", "bedrooms", "beds", "bathrooms", "rating", "reviews", "dist_center_km"]


def slug(texte):
    s = unicodedata.normalize("NFKD", texte or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "inconnue"


def ecrire_js(path, cible, cle, obj):
    """Écrit un .js qui range `obj` dans window.AB.<cible>[<cle>] (ou window.AB.<cible> si cle est None)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    acces = f"AB.{cible}" + (f"[{json.dumps(cle)}]" if cle is not None else "")
    path.write_text(ENTETE_JS + acces + " = " + json.dumps(obj, ensure_ascii=False) + ";\n", encoding="utf-8")


def lire_js(path):
    corps = path.read_text(encoding="utf-8").split("\n", 1)[1]
    return json.loads(corps.split("=", 1)[1].strip().rstrip(";"))


def photos_site(rec):
    """[{l: chemin local relatif (ou None), r: URL Airbnb}] pour chaque photo."""
    out = []
    for i, p in enumerate(rec["photos"]):
        rel = Path(PHOTO_DIR.name) / (rec["listing_id"] or "unknown") / f"{i + 1:03d}{Path(p).suffix.lower() or '.jpg'}"
        out.append({"l": rel.as_posix() if (SCRIPT_DIR / rel).is_file() else None, "r": p})
    return out


def download_photos(rec, limit):
    import requests
    folder = PHOTO_DIR / (rec["listing_id"] or "unknown")
    folder.mkdir(parents=True, exist_ok=True)
    for i, p in enumerate(rec["photos"][:limit] if limit else rec["photos"]):
        dest = folder / f"{i + 1:03d}{Path(p).suffix.lower() or '.jpg'}"
        try:
            if not dest.exists():
                r = requests.get(p + "?im_w=1200", timeout=30)
                r.raise_for_status()
                dest.write_bytes(r.content)
        except Exception as e:
            print(f"   ! photo {i + 1} : {e}")


def enregistrer_logement(rec):
    """Écrit data/logements/<id>.js (fiche complète)."""
    if not rec["listing_id"]:
        raise ValueError("identifiant du logement introuvable dans l'URL")
    fiche = {c: rec.get(c) for c in CHAMPS}
    fiche["photos"] = photos_site(rec)
    ecrire_js(LOGEMENTS_DIR / f"{rec['listing_id']}.js", "logement", rec["listing_id"], fiche)


def reconstruire_site():
    """Relit data/logements/*.js et régénère data/villes/*.js + data/villes.js.

    À lancer seul après avoir supprimé / ajouté un fichier de logement à la main."""
    groupes = {}
    for f in sorted(LOGEMENTS_DIR.glob("*.js")):
        try:
            a = lire_js(f)
        except Exception as e:
            print(f"   ! {f.name} illisible : {e}")
            continue
        nom = a.get("ville") or a.get("city_guess") or "Ville inconnue"
        groupes.setdefault(slug(nom), {"nom": nom, "items": []})["items"].append(a)

    index, gardes = [], set()
    for s, g in groupes.items():
        items = sorted(g["items"], key=lambda a: (a.get("dist_center_km") is None, a.get("dist_center_km") or 0))
        cartes = []
        for a in items:
            c = {k: a.get(k) for k in CHAMPS_CARTE}
            c["cover"] = a["photos"][0] if a.get("photos") else None
            cartes.append(c)
        ecrire_js(VILLES_DIR / f"{s}.js", "ville", s, cartes)
        gardes.add(f"{s}.js")
        prix = [a["price_total"] for a in items if a.get("price_total") is not None]
        index.append({"slug": s, "nom": g["nom"], "nb": len(items),
                      "cover": next((c["cover"] for c in cartes if c["cover"]), None),
                      "prix_min": min(prix) if prix else None, "prix_max": max(prix) if prix else None,
                      "currency": next((a["currency"] for a in items if a.get("currency")), None)})
    for f in VILLES_DIR.glob("*.js"):
        if f.name not in gardes:
            f.unlink()
    index.sort(key=lambda v: v["nom"].lower())
    ecrire_js(DATA_DIR / "villes.js", "villes", None, index)
    print(f"Site : {sum(v['nb'] for v in index)} logements, {len(index)} ville(s) -> {DATA_DIR}  (ouvre index.html)")


# --------------------------------------------------------------------------- main
def run(liens=None, fichier_liens=FICHIER_LIENS, ville=VILLE, centre=CENTRE,
        photos=TELECHARGER_PHOTOS, max_photos=MAX_PHOTOS, navigateur_visible=AFFICHER_NAVIGATEUR):
    """Lance le scraping. `liens` = liste d'URLs ; sinon on lit `fichier_liens`."""
    def chemin(p):
        p = Path(p)
        return p if p.is_absolute() else SCRIPT_DIR / p

    urls = list(liens or [])
    if not urls:
        f = chemin(fichier_liens)
        if not f.is_file():
            print(f"Fichier introuvable : {f}\nCrée-le avec un lien Airbnb par ligne.")
            return
        urls = [l.strip() for l in f.read_text(encoding="utf-8").splitlines() if l.strip().startswith("http")]
    if not urls:
        print("Aucun lien à traiter.")
        return

    if ville and not centre:
        try:
            tester_ville(ville)
        except (ValueError, ConnectionError) as e:
            print(f"ERREUR ville : {e}")
            return

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not navigateur_visible)
        ctx = browser.new_context(locale="fr-FR", viewport={"width": 1400, "height": 1000})
        page = ctx.new_page()
        for n, url in enumerate(urls, 1):
            print(f"[{n}/{len(urls)}] {url}")
            try:
                raw = scrape_page(page, url)
                rec = build_record(url, raw)
                rec["ville"] = ville
                add_distance(rec, centre, ville)
                if photos:
                    download_photos(rec, max_photos)
                enregistrer_logement(rec)
                print(f"   {rec['title']!r} | total={rec['price_total']} nuit={rec['price_per_night']} {rec['currency']}"
                      f" | {rec['bedrooms']} ch. | {len(rec['photos'])} photos | {rec['dist_center_km']} km du centre")
                if rec["lat"] is None:
                    print("   ! coordonnées introuvables")
                if rec["price_total"] is None:
                    print("   ! prix total introuvable (dates/voyageurs dans l'URL ?)")
            except Exception as e:
                print(f"   ERREUR : {e}")
            time.sleep(random.uniform(3, 7))
        browser.close()

    reconstruire_site()


if __name__ == "__main__":
    run()