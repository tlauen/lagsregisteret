#!/usr/bin/env python3
"""
Innhent oppføringar frå Brønnøysund sitt enhets-API, filtrer med utelatingsfrasar,
og skriv éi CSV (kjelde_url = lenkje til oppslag i nettlesar).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen

import trygg_nett

BRREG_ENHETAR_URL = "https://data.brreg.no/enhetsregisteret/api/enheter"
BRREG_OPPSLAG_MAL = "https://data.brreg.no/enhetsregisteret/oppslag/enheter/{orgnr}"


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


def last_utelatingsfrasar(oppsettmappe: Path) -> list[str]:
    f = oppsettmappe / "utelatingsfrasar_i_navn.txt"
    if not f.exists():
        return []
    return [x.lower() for x in les_linjer(f)]


def i_utelatingslista(navn: str, frasar: list[str]) -> bool:
    n = navn.lower()
    return any(f in n for f in frasar)


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


def sider_for_sokjefragment(
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
        help="Mappa med sokjefragment.txt m.m. (normalt <repo>/oppsett)",
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
    sokjefragment = les_linjer(sokjefil)
    if val.maks_sokjefragment is not None:
        sokjefragment = sokjefragment[: val.maks_sokjefragment]
    utelatingar = last_utelatingsfrasar(oppsettmappe)
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

    for fragment in sokjefragment:
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
            org = str(e.get("organisasjonsnummer") or "")
            if not org:
                continue
            per_org[org] = registeroppføring_frå_enhet(e, dagsdato, fylkeskart)

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
