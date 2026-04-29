#!/usr/bin/env python3
"""
Innhent oppføringar frå Brønnøysund sitt enhets-API, filtrer med utelatingsfrasar,
valfritt mellomrom rundt forkortingar, og valfritt mot frivillighetsregister og norsk tilhald i adresse.
Skriv éi CSV (kjelde_url = lenkje til oppslag i nettlesar).
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import date
import re
import sys
import time
from io import StringIO
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen

import trygg_nett

BRREG_ENHETAR_URL = "https://data.brreg.no/enhetsregisteret/api/enheter"
BRREG_OPPSLAG_MAL = "https://data.brreg.no/enhetsregisteret/oppslag/enheter/{orgnr}"
FRIVILLIG_TOTALBESTAND_CSV = (
    "https://data.brreg.no/frivillighetsregisteret/api/"
    "frivillige-organisasjoner/totalbestand/csv"
)


def prosjektrot() -> Path:
    return Path(__file__).resolve().parent.parent


def les_linjer(fil: Path) -> list[str]:
    ut: list[str] = []
    for linje in fil.read_text(encoding="utf-8").splitlines():
        s = linje.strip()
        if not s or s.startswith("#"):
            continue
        ut.append(s)
    return ut


# Kvar søkjefil påverkar kva verdi som vert lagt inn i CSV-kolonnen «liste», saman med komma om fleire treff.
LISTE_UNGDOMSLAG = "ungdomslag"
LISTE_GRENDELAG = "grendelag"
LISTE_BYGDELAG = "bygdelag"
LISTE_SORTERING: tuple[str, ...] = (LISTE_UNGDOMSLAG, LISTE_GRENDELAG, LISTE_BYGDELAG)
SOKJE_FIL_MED_LISTE_ID: tuple[tuple[str, str], ...] = (
    ("sokjefragment.txt", LISTE_UNGDOMSLAG),
    ("sokjefragment_bygd.txt", LISTE_BYGDELAG),
    ("sokjefragment_grende.txt", LISTE_GRENDELAG),
)


def sokjefragment_med_liste(oppsettmappe: Path) -> list[tuple[str, str]]:
    """Fragment frå sokjefragment.txt (+ valfrie bygd/grende-filer) med liste-id for CSV og nett."""
    ut: list[tuple[str, str]] = []
    for filnamn, liste_id in SOKJE_FIL_MED_LISTE_ID:
        sti = oppsettmappe / filnamn
        if filnamn == "sokjefragment.txt":
            for frag in les_linjer(sti):
                ut.append((frag, liste_id))
        elif sti.is_file():
            for frag in les_linjer(sti):
                ut.append((frag, liste_id))
    return ut


def slaa_saman_liste_tags(tag_mengd: set[str]) -> str:
    """Kommaseparerte taggar i fast rekkje."""
    prio = {n: i for i, n in enumerate(LISTE_SORTERING)}
    return ",".join(sorted(tag_mengd, key=lambda x: (prio.get(x, 99), x)))


def last_utelatingsfrasar(oppsettmappe: Path) -> list[str]:
    f = oppsettmappe / "utelatingsfrasar_i_navn.txt"
    if not f.exists():
        return []
    return [x.lower() for x in les_linjer(f)]


def i_utelatingslista(navn: str, frasar: list[str]) -> bool:
    n = navn.lower()
    return any(f in n for f in frasar)


# Treff gjevne uavhengig av korte søkjeord: treng ikkje ordskilje-sjekk for forkortingar
GODE_TREFF_SLEPP_FORKORTINGKONTROLL: tuple[str, ...] = (
    "ungdomslag",
    "ungdomsforening",
    "ungdoms- og",
    "ungdoms-",
    "ungdoms",
    "bondeungdom",
    "bondeungdomslag",
    "bygde- ungdoms",
    "bygde- og",
    "bygde-",
    "bygdelag",
    "grende",
    "grende-",
    "folkedans",
    "frikyrk",
    "friidrett",
    "idrettsforening",
    "idretts",
    "frilynde",
    "4h-lag",
    "4h",
    "4-h",
    "4 h",
)


def _mellomrom_fr_eller_etter(navn: str, start: int, end: int) -> bool:
    """Bokstavlege mellomrom rett føre, eller rett etter, forkortinga (start/end = slice i same streng)."""
    if end <= start or start < 0 or end > len(navn):
        return False
    fyre = start > 0 and navn[start - 1].isspace()
    etter = end < len(navn) and navn[end].isspace()
    return fyre or etter


def last_forkorting_krev_mellomrom(oppsettmappe: Path) -> list[str]:
    f = oppsettmappe / "forkorting_krev_mellomrom.txt"
    if not f.is_file():
        return []
    rå: list[str] = []
    for t in les_linjer(f):
        t2 = normaliser_sokjefragment(t)
        if t2:
            rå.append(t2)
    return sorted(set(rå), key=len, reverse=True)


def navn_oppfyller_krev_forkorting_mellomrom(navn: str, forkortar: list[str]) -> bool:
    """
    Dersom namnet inneheld forkortingar (t.d. BUL, UL) som delstreng, må førekomsten
    ha mellomrom føre elles etter, elles ligg inni ein lengre godkjennd forkorting
    (t.d. UL inni « BUL » når BUL ligg med mellomrom).
    Gode søkje-ordlengder i GODE_TREFF_SLEPP_FORKORTINGKONTROLL slepp sjekk.
    """
    if not forkortar:
        return True
    n0 = navn.strip()
    if not n0:
        return False
    nl = n0.lower()
    if any(s in nl for s in GODE_TREFF_SLEPP_FORKORTINGKONTROLL):
        return True

    gode_spann: list[tuple[int, int]] = []
    for f in forkortar:
        if n0.casefold() == f.casefold():
            gode_spann.append((0, len(n0)))
    for f in forkortar:
        for m in re.finditer(re.escape(f), n0, re.IGNORECASE):
            s, e = m.start(), m.end()
            if _mellomrom_fr_eller_etter(n0, s, e):
                gode_spann.append((s, e))

    def fullt_inn_i_lengre_god(s: int, e: int) -> bool:
        for gs, ge in gode_spann:
            if (ge - gs) > (e - s) and gs <= s and e <= ge:
                return True
        return False

    for f in forkortar:
        for m in re.finditer(re.escape(f), n0, re.IGNORECASE):
            s, e = m.start(), m.end()
            if n0.casefold() == f.casefold():
                continue
            if _mellomrom_fr_eller_etter(n0, s, e):
                continue
            if fullt_inn_i_lengre_god(s, e):
                continue
            return False
    return True


def brreg_enhet_har_norsk_tilhald(enhet: dict[str, Any]) -> bool:
    """
    Oppfyller «tilhøve i norsk kommune» eller «utsendings-/visings postnummer i norsk system»:
    ser på Brreg sine felt forretningsadresse eller postadresse.

    - Uttrykkelig landkode som ikkje er NO → godtek ikkje som norsk (unntak: tom tolka same som Norge).

    True viss ein av:

    - postnummer er fire tal ( norsk postnr-format, også Svalbard o.l. ),

    - kommunenummer er innsett (tal, som Brreg bruker),

    - kommune (namnet) er innsett.
    """
    a = enhet.get("forretningsadresse") or enhet.get("postadresse")
    if not isinstance(a, dict):
        return False
    lk = str(a.get("landkode") or "").strip().upper()
    if lk and lk != "NO":
        return False

    pn = str(a.get("postnummer") or "").strip().replace(" ", "").replace("\u00a0", "")
    if re.fullmatch(r"\d{4}", pn):
        return True

    kraw = str(a.get("kommunenummer") or "").strip()
    if kraw.isdigit():
        return True

    if str(a.get("kommune") or "").strip():
        return True

    return False


def adresselinjer_frå_enhet(enhet: dict[str, Any]) -> dict[str, str]:
    a = enhet.get("forretningsadresse") or enhet.get("postadresse")
    if not a:
        return {
            "kommune": "",
            "kommunenummer": "",
            "adresse": "",
            "postnummer": "",
            "poststed": "",
        }
    gater = a.get("adresse")
    if isinstance(gater, list):
        g = ", ".join(str(x) for x in gater if x)
    else:
        g = (gater or "") if isinstance(gater, str) else ""
    rå_knr = a.get("kommunenummer") if isinstance(a, dict) else None
    knr = ""
    if rå_knr is not None and str(rå_knr).strip():
        knr = str(rå_knr).strip().zfill(4)
    return {
        "kommune": (a.get("kommune") or "") if isinstance(a, dict) else "",
        "kommunenummer": knr,
        "adresse": g,
        "postnummer": str(a.get("postnummer") or "") if isinstance(a, dict) else "",
        "poststed": (a.get("poststed") or "") if isinstance(a, dict) else "",
    }


def normaliser_nettadresse(verdi: str | None) -> str:
    if not verdi or not str(verdi).strip():
        return ""
    t = str(verdi).strip()
    if t.startswith("http://") or t.startswith("https://"):
        return t
    if "://" in t:
        return t
    if t.startswith("www."):
        return f"https://{t}"
    if "." in t and " " not in t:
        return f"https://{t.lstrip('/')}"
    return t


def hent_som(url: str, tidsavbrodt: int = 60) -> dict[str, Any]:
    svar = urlopen(
        url,
        timeout=tidsavbrodt,
        context=trygg_nett.ssl_kontekst(),
    )  # noqa: S310 — stigen URL inne i skriptet
    rå = svar.read()
    return json.loads(rå.decode("utf-8"))


def hent_tekst_frå_url(url: str, tidsavbrodt: int = 120) -> str:
    svar = urlopen(
        url,
        timeout=tidsavbrodt,
        context=trygg_nett.ssl_kontekst(),
    )  # noqa: S310
    return svar.read().decode("utf-8")


def mengd_orgnr_frivillighetsregister(tidsavbrodt: int = 120) -> set[str]:
    """Les totalbestand CSV frå Brreg sitt open frivillighetsregister-API (éi førespurnad)."""
    tekst = hent_tekst_frå_url(FRIVILLIG_TOTALBESTAND_CSV, tidsavbrodt=tidsavbrodt)
    rd = csv.DictReader(StringIO(tekst))
    kol = "organisasjonsnummer"
    if not rd.fieldnames or kol not in rd.fieldnames:
        raise ValueError(f"Ventar kolonne «{kol}», fekk {rd.fieldnames!r}")
    ut: set[str] = set()
    for rad in rd:
        o = str(rad.get(kol, "") or "").strip()
        if o.isdigit() and len(o) <= 9:
            ut.add(o.zfill(9))
    return ut


def normaliser_sokjefragment(tek: str) -> str:
    """Striper, byter ut nbsp og vanlege «lure» bindestrekar slik at URL blir stø."""
    t = tek.replace("\u00a0", " ").replace("\u2009", " ").replace("\u2007", " ")
    t = t.replace("–", "-").replace("—", "-")
    t = t.strip()
    t = re.sub(r"\s+", " ", t)
    return t


def sokjefragment_kandidatar(tek: str) -> list[str]:
    """
    Dersom Brreg svarer 400 på navn= (visse bruk får feil for strengar med «… og»),
    prøver me alternative utan «og»-ledd, men fortsatt som delstreng i org­namn.
    """
    f = normaliser_sokjefragment(tek)
    if not f:
        return []
    ut: list[str] = [f]
    h = re.sub(r"\s+og\s+", " ", f)
    h = re.sub(r"\s+", " ", h).strip()
    if h and h not in ut:
        ut.append(h)
    h2 = re.sub(r"\s+og\s*$", "", f).strip()
    h2 = re.sub(r"\s+", " ", h2)
    if h2 and h2 not in ut:
        ut.append(h2)
    h3 = re.sub(r" og", "", f)
    h3 = re.sub(r"\s+", " ", h3).strip()
    if h3 and h3 not in ut:
        ut.append(h3)
    return ut


def sider_for_sokjefragment(
    fragment: str,
    antall_pr_side: int,
    paus_mellom_sider: float,
) -> list[dict[str, Any]]:
    siste: HTTPError | None = None
    for f in sokjefragment_kandidatar(fragment):
        try:
            return _hugsider_for_ett_sokjefragment(
                f, antall_pr_side, paus_mellom_sider
            )
        except HTTPError as e:
            if e.code == 400:
                siste = e
                continue
            raise
    if siste is not None:
        raise siste
    return []


def _hugsider_for_ett_sokjefragment(
    fragment: str,
    antall_pr_side: int,
    paus_mellom_sider: float,
) -> list[dict[str, Any]]:
    enheter: list[dict[str, Any]] = []
    kodet = quote(fragment, safe="")
    fyrste = f"{BRREG_ENHETAR_URL}?navn={kodet}&size={antall_pr_side}&page=0"
    svar = hent_som(fyrste)
    side = svar.get("page") or {}
    sider_til_saman = int(side.get("totalPages") or 0)
    fyrstegang = svar.get("_embedded", {}).get("enheter", [])
    enheter.extend(fyrstegang)
    for side_nr in range(1, sider_til_saman):
        time.sleep(paus_mellom_sider)
        url = f"{BRREG_ENHETAR_URL}?navn={kodet}&size={antall_pr_side}&page={side_nr}"
        neste = hent_som(url)
        enheter.extend((neste.get("_embedded") or {}).get("enheter", []))
    return enheter


def last_fylkeskart(rot: Path) -> dict[str, str] | None:
    """Returnerer kommunenummer → fylkesnamn, eller None viss fila ikkje finst."""
    f = rot / "data" / "kommune_til_fylke.json"
    if not f.is_file():
        return None
    d = json.loads(f.read_text(encoding="utf-8"))
    ut = d.get("kommune_til_fylkesnamn")
    if isinstance(ut, dict):
        return {str(k).zfill(4): str(v) for k, v in ut.items()}
    return None


def fylkesnamn_for_kommunenummer(
    kommunenummer: str,
    kart: dict[str, str] | None,
) -> str:
    if not kart or not kommunenummer:
        return ""
    return kart.get(kommunenummer.zfill(4), "")


def registeroppføring_frå_enhet(
    enhet: dict[str, Any],
    dato: str,
    fylkeskart: dict[str, str] | None,
) -> dict[str, str]:
    orgnr = str(enhet.get("organisasjonsnummer") or "")
    navn = (enhet.get("navn") or "").strip()
    a = adresselinjer_frå_enhet(enhet)
    heime = enhet.get("hjemmeside")
    fylke = fylkesnamn_for_kommunenummer(a["kommunenummer"], fylkeskart)
    return {
        "lagsnavn": navn,
        "orgnr": orgnr,
        "kommune": a["kommune"],
        "fylke": fylke,
        "adresse": a["adresse"],
        "postnummer": a["postnummer"],
        "poststed": a["poststed"],
        "nettstad": normaliser_nettadresse(heime) if heime else "",
        "kjelde_type": "brreg",
        "kjelde_url": BRREG_OPPSLAG_MAL.format(orgnr=orgnr) if orgnr else "",
        "henta_dato": dato,
    }


def tolk_valet() -> argparse.Namespace:
    t = argparse.ArgumentParser(
        description="Innhent brreg-oppføringar til lagsregisteret (CSV, nynorske felta).",
    )
    t.add_argument(
        "-O",
        "--oppsettmappe",
        type=Path,
        default=None,
        help=(
            "Mappa med sokjefragment.txt og valfritt sokjefragment_bygd.txt/"
            "sokjefragment_grende.txt (normalt <repo>/oppsett)"
        ),
    )
    t.add_argument(
        "-u",
        "--utdatafil",
        type=Path,
        default=None,
        dest="utdatafil",
        help="UTF-8-CSV (normalt <repo>/utdata/innhenta_lag_frå_brreg.csv)",
    )
    t.add_argument(
        "--antall_pr_side",
        type=int,
        default=200,
        help="Tal treff per side mot API (høgare = færre kall)",
    )
    t.add_argument(
        "--paus",
        type=float,
        default=0.12,
        metavar="S",
        help="Sekund mellom sider (minskar belastning for API)",
    )
    t.add_argument(
        "--maks_sokjefragment",
        type=int,
        default=None,
        help="Berre fyrste N søkje-fragmenta (prøvkjøyring, færre kall)",
    )
    t.add_argument(
        "--utan_fylke",
        action="store_true",
        help="Ikkje bruk data/kommune_til_fylke.json (fylke-kolonnen vert tom)",
    )
    t.add_argument(
        "--hald-fram-ved-sokjefeil",
        action="store_true",
        dest="hald_fram_ved_sokjefeil",
        help="Hopp over søkje-fragment som feilar (loggar åtvaring) i staden for stopp",
    )
    t.add_argument(
        "--utan-forkorting-mellomrom",
        action="store_true",
        dest="utan_forkorting_mellomrom",
        help="Ikkje bruk forkorting_krev_mellomrom.txt (i tilfelle samanlikning/eld data)",
    )
    t.add_argument(
        "--krev-frivillighetsregister",
        action="store_true",
        dest="krev_frivillighetsregister",
        help=(
            "Berre lag (rader) med orgnr registrert i "
            "Brreg sitt frivillighetsregister (éi nedlasting av totalbestand-CSV)"
        ),
    )
    t.add_argument(
        "--krev-norsk-tilhald",
        action="store_true",
        dest="krev_norsk_tilhald",
        help=(
            "Berre når Brreg-vis adresse tyder på norsk tilhald: "
            "norsk folkeregisterpostnr (fire tal) eller kommunenummer/kommune (sjå dokumentasjon i skriptet)"
        ),
    )
    return t.parse_args()


def hovud() -> int:
    val = tolk_valet()
    rot = prosjektrot()
    oppsettmappe = val.oppsettmappe or (rot / "oppsett")
    utdatafilsti = val.utdatafil or (rot / "utdata" / "innhenta_lag_frå_brreg.csv")
    sokjefil = oppsettmappe / "sokjefragment.txt"
    if not sokjefil.is_file():
        print(f"Finn ikkje {sokjefil}", file=sys.stderr)
        return 1
    fragment_med_liste = sokjefragment_med_liste(oppsettmappe)
    if val.maks_sokjefragment is not None:
        fragment_med_liste = fragment_med_liste[: val.maks_sokjefragment]
    utelatingar = last_utelatingsfrasar(oppsettmappe)
    forkort_mellom: list[str] = []
    if not val.utan_forkorting_mellomrom:
        forkort_mellom = last_forkorting_krev_mellomrom(oppsettmappe)
    friv_org: set[str] | None = None
    if val.krev_frivillighetsregister:
        try:
            print("Hentar frivillighetsregister totalbestand frå Brreg …", file=sys.stderr)
            friv_org = mengd_orgnr_frivillighetsregister()
        except (HTTPError, URLError, OSError, ValueError) as e:
            print(f"Kunne ikkje lesa frivillighetsregister: {e}", file=sys.stderr)
            return 1
        print(f"  → {len(friv_org)} organisasjonar i mengda", file=sys.stderr)
    dagsdato = date.today().isoformat()
    fylkeskart: dict[str, str] | None = None
    if not val.utan_fylke:
        fylkeskart = last_fylkeskart(rot)
        if fylkeskart is None:
            print(
                "Åtvaring: finn ikkje data/kommune_til_fylke.json — fylke vert tomme. "
                "Køyr: python3 skript/bygg_kommune_til_fylke.py",
                file=sys.stderr,
            )
    per_org: dict[str, dict[str, str]] = {}
    lister_per_org: defaultdict[str, set[str]] = defaultdict(set)

    for fragment, liste_id in fragment_med_liste:
        try:
            treff = sider_for_sokjefragment(
                fragment,
                antall_pr_side=max(1, min(200, val.antall_pr_side)),
                paus_mellom_sider=val.paus,
            )
        except (HTTPError, URLError, OSError, json.JSONDecodeError) as feil:
            if val.hald_fram_ved_sokjefeil:
                print(f"Åtvaring: søk «{fragment}» hoppa over: {feil}", file=sys.stderr)
                continue
            print(f"Søk «{fragment}» feila: {feil}", file=sys.stderr)
            return 1
        for e in treff:
            navn = (e.get("navn") or "").strip()
            if not navn or i_utelatingslista(navn, utelatingar):
                continue
            if not navn_oppfyller_krev_forkorting_mellomrom(navn, forkort_mellom):
                continue
            org = str(e.get("organisasjonsnummer") or "").strip()
            if not org or not org.isdigit():
                continue
            org9 = org.zfill(9)
            if friv_org is not None and org9 not in friv_org:
                continue
            if val.krev_norsk_tilhald and not brreg_enhet_har_norsk_tilhald(e):
                continue
            if org9 not in per_org:
                rad = registeroppføring_frå_enhet(e, dagsdato, fylkeskart)
                rad["orgnr"] = org9
                rad["kjelde_url"] = BRREG_OPPSLAG_MAL.format(orgnr=org9)
                per_org[org9] = rad
            lister_per_org[org9].add(liste_id)

    for org9, rad in per_org.items():
        taggar = lister_per_org.get(org9)
        rad["liste"] = slaa_saman_liste_tags(taggar) if taggar else LISTE_UNGDOMSLAG
        rad.setdefault("nu_mr_status", "")
        rad.setdefault("nu_mr_overordna", "")
        rad.setdefault("nu_mr_orgtype", "")
    utdatafilsti.parent.mkdir(parents=True, exist_ok=True)
    kolonnenamn = [
        "lagsnavn",
        "orgnr",
        "kommune",
        "fylke",
        "adresse",
        "postnummer",
        "poststed",
        "nettstad",
        "kjelde_type",
        "kjelde_url",
        "liste",
        "nu_mr_status",
        "nu_mr_overordna",
        "nu_mr_orgtype",
        "henta_dato",
    ]
    sortert = sorted(
        per_org.values(),
        key=lambda r: (r.get("fylke", ""), r.get("kommune", ""), r.get("lagsnavn", "")),
    )
    with utdatafilsti.open("w", encoding="utf-8", newline="") as f:
        skrivar = csv.DictWriter(f, fieldnames=kolonnenamn, extrasaction="ignore")
        skrivar.writeheader()
        skrivar.writerows(sortert)
    print(f"Skreiv {len(sortert)} rader til {utdatafilsti}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(hovud())
