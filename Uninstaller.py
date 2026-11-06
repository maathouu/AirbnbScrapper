#!/usr/bin/env python3
"""
AirbnbGestionnaire.py - Supprime des logements (ou des villes) ajoutés par erreur.

UTILISATION : lance ce fichier (bouton Run), un menu s'affiche dans la console.
Il doit rester dans le même dossier que AirbnbScraper.py, data/ et photos/.

Pour chaque logement supprimé :
    - sa fiche data/logements/<id>.js est effacée
    - son dossier photos/<id>/ est effacé (au choix)
    - son lien est retiré de urls.txt s'il y figure (sinon il reviendrait au prochain scraping)
    - data/villes/*.js et data/villes.js sont régénérés (une ville vide disparaît de index.html)

Depuis un autre fichier :
    import AirbnbGestionnaire as G
    G.supprimer_logements(["1151420194207413489"])
    G.supprimer_ville("Sunny Beach, Bulgarie")
"""
import re
import shutil

import AirbnbScraper as A


# --------------------------------------------------------------------------- fonctions
def nom_ville(a):
    return a.get("ville") or a.get("city_guess") or "Ville inconnue"


def charger():
    """Toutes les fiches, triées par ville puis par distance au centre."""
    fiches = []
    for f in sorted(A.LOGEMENTS_DIR.glob("*.js")):
        try:
            a = A.lire_js(f)
        except Exception as e:
            print(f"   ! {f.name} illisible : {e}")
            a = {"title": "(fichier illisible)"}
        a["listing_id"] = f.stem
        fiches.append(a)
    fiches.sort(key=lambda a: (nom_ville(a).lower(), a.get("dist_center_km") is None, a.get("dist_center_km") or 0))
    return fiches


def retirer_des_urls(ids):
    """Retire de urls.txt les liens des logements supprimés."""
    f = A.SCRIPT_DIR / A.FICHIER_LIENS
    if not f.is_file():
        return
    lignes = f.read_text(encoding="utf-8").splitlines()
    gardees = []
    for l in lignes:
        m = re.search(r"/rooms/(?:plus/)?(\d+)", l)
        if not (m and m.group(1) in ids):
            gardees.append(l)
    if len(gardees) != len(lignes):
        f.write_text("\n".join(gardees) + "\n", encoding="utf-8")
        print(f"   {len(lignes) - len(gardees)} lien(s) retiré(s) de {f.name}")


def supprimer_logements(ids, photos=True, nettoyer_urls=True):
    """Supprime les logements dont on donne les identifiants. Renvoie le nombre supprimé."""
    ids = [str(i) for i in ids if re.fullmatch(r"\w+", str(i))]
    n = 0
    for i in ids:
        f = A.LOGEMENTS_DIR / f"{i}.js"
        if f.is_file():
            f.unlink()
            n += 1
        else:
            print(f"   ! {i} : fiche introuvable")
        if photos and (A.PHOTO_DIR / i).is_dir():
            shutil.rmtree(A.PHOTO_DIR / i)
    if nettoyer_urls:
        retirer_des_urls(set(ids))
    A.reconstruire_site()
    print(f"{n} logement(s) supprimé(s).")
    return n


def supprimer_ville(nom, photos=True, nettoyer_urls=True):
    """Supprime tous les logements d'une ville (nom ou slug, ex. 'Sunny Beach, Bulgarie')."""
    ids = [a["listing_id"] for a in charger() if A.slug(nom_ville(a)) == A.slug(nom)]
    if not ids:
        print(f"Aucun logement pour la ville {nom!r}.")
        return 0
    return supprimer_logements(ids, photos, nettoyer_urls)


def nettoyer_photos_orphelines():
    """Efface les dossiers photos/<id>/ qui n'ont plus de fiche logement."""
    if not A.PHOTO_DIR.is_dir():
        return 0
    n = 0
    for d in A.PHOTO_DIR.iterdir():
        if d.is_dir() and not (A.LOGEMENTS_DIR / f"{d.name}.js").is_file():
            shutil.rmtree(d)
            n += 1
    print(f"{n} dossier(s) de photos orphelin(s) supprimé(s).")
    return n


def tout_supprimer():
    """Efface data/ et photos/ (index.html affichera « Aucune donnée »)."""
    for d in (A.DATA_DIR, A.PHOTO_DIR):
        if d.is_dir():
            shutil.rmtree(d)
    print("data/ et photos/ supprimés.")


# --------------------------------------------------------------------------- menu interactif
def prix(a):
    p = a.get("price_total")
    return f"{p:,.0f} {a.get('currency') or '€'}".replace(",", " ") if p is not None else "prix ?"


def afficher(fiches):
    if not fiches:
        print("\nAucun logement enregistré.")
        return
    ville = None
    for n, a in enumerate(fiches, 1):
        if nom_ville(a) != ville:
            ville = nom_ville(a)
            print(f"\n== {ville} ({sum(1 for x in fiches if nom_ville(x) == ville)}) ==")
        km = a.get("dist_center_km")
        titre = (a.get("title") or "Sans titre")[:48]
        print(f"{n:>4}. {titre:<48} | {prix(a):>10} | {a.get('bedrooms') or '?'} ch. | "
              f"{str(km).replace('.', ',') + ' km' if km is not None else '? km'} | id {a['listing_id']}")


def choisir(fiches, saisie):
    """'1 3 5-7 1151420194207413489' -> liste d'identifiants."""
    connus = {a["listing_id"] for a in fiches}
    ids = []
    for t in re.split(r"[,\s;]+", saisie.strip()):
        if not t:
            continue
        m = re.fullmatch(r"(\d+)-(\d+)", t)
        if m and 1 <= int(m.group(1)) <= int(m.group(2)) <= len(fiches):
            ids += [fiches[k - 1]["listing_id"] for k in range(int(m.group(1)), int(m.group(2)) + 1)]
        elif t.isdigit() and 1 <= int(t) <= len(fiches):
            ids.append(fiches[int(t) - 1]["listing_id"])
        elif t in connus:
            ids.append(t)
        else:
            print(f"   ! {t!r} ignoré (ni numéro de la liste, ni identifiant connu)")
    return list(dict.fromkeys(ids))


def oui(question, defaut=True):
    r = input(f"{question} ({'O/n' if defaut else 'o/N'}) ").strip().lower()
    return defaut if not r else r in ("o", "oui", "y", "yes")


def menu():
    while True:
        print("\n=== Gestionnaire Airbnb ===")
        print("1. Voir les logements")
        print("2. Supprimer des logements")
        print("3. Supprimer une ville entière")
        print("4. Nettoyer les photos orphelines")
        print("5. Tout supprimer (data + photos)")
        print("0. Quitter")
        choix = input("Ton choix : ").strip()
        fiches = charger()

        if choix == "1":
            afficher(fiches)

        elif choix == "2":
            afficher(fiches)
            if not fiches:
                continue
            ids = choisir(fiches, input("\nNuméros ou identifiants à supprimer (ex : 1 3 5-7), vide = annuler : "))
            if not ids:
                continue
            titres = {a["listing_id"]: a.get("title") or "Sans titre" for a in fiches}
            print("\nÀ supprimer :")
            for i in ids:
                print(f"   - {titres[i][:70]}  (id {i})")
            if oui("Confirmer la suppression ?", defaut=False):
                supprimer_logements(ids, photos=oui("Supprimer aussi leurs photos ?"))

        elif choix == "3":
            noms = {}
            for a in fiches:
                noms[nom_ville(a)] = noms.get(nom_ville(a), 0) + 1
            if not noms:
                print("\nAucune ville enregistrée.")
                continue
            liste = list(noms)
            print()
            for n, v in enumerate(liste, 1):
                print(f"{n:>3}. {v} ({noms[v]} logement(s))")
            r = input("\nNuméro de la ville à supprimer, vide = annuler : ").strip()
            if r.isdigit() and 1 <= int(r) <= len(liste):
                v = liste[int(r) - 1]
                if oui(f"Supprimer les {noms[v]} logement(s) de {v} ?", defaut=False):
                    supprimer_ville(v, photos=oui("Supprimer aussi leurs photos ?"))

        elif choix == "4":
            nettoyer_photos_orphelines()

        elif choix == "5":
            if input("Tape SUPPRIMER pour tout effacer (data/ et photos/) : ").strip() == "SUPPRIMER":
                tout_supprimer()

        elif choix in ("0", "q", ""):
            break


if __name__ == "__main__":
    menu()