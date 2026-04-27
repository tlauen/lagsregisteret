#!/usr/bin/env python3
"""
Last ned kommune → fylke frå SSB Klass (klassifikasjon 131 → 104) og skriv
`data/kommune_til_fylke.json` for bruk utan nett i innhentinga.

Køyr dette når kommunelister skal oppdaterast (sjeldan).
Kjelde: https://data.ssb.no/api/klass/v1/api-guide.html (CC BY 4.0).
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from urllib.request import urlopen

import trygg_nett

SSB_KORRESPONDANSE = (
    "https://data.ssb.no/api/klass/v1/classifications/131/"
    "correspondsAt.json?targetClassificationId=104&date={dato}"
)


def prosjektrot() -> Path:
    return Path(__file__).resolve().parent.parent


def hent_korrespondanse(dato: str) -> dict:
    url = SSB_KORRESPONDANSE.format(dato=dato)
    with urlopen(
        url,
        timeout=120,
        context=trygg_nett.ssl_kontekst(),
    ) as svar:  # noqa: S310
        rå = svar.read()
    return json.loads(rå.decode("utf-8"))


def hovud() -> int:
    rot = prosjektrot()
    ut = rot / "data" / "kommune_til_fylke.json"
    i_dag = date.today().isoformat()
    try:
        d = hent_korrespondanse(i_dag)
    except OSError as feil:
        print(f"Feil ved nedlasting: {feil}", file=sys.stderr)
        return 1
    element = d.get("correspondenceItems") or []
    # Enkel tabell: kommunenummer (fire siffer) → fylkesnamn (som SSB gjev)
    kart: dict[str, str] = {}
    for punkt in element:
        knr = str(punkt.get("sourceCode") or "").strip()
        fnamn = str(punkt.get("targetName") or "").strip()
        if knr and fnamn:
            kart[knr] = fnamn
    ut.parent.mkdir(parents=True, exist_ok=True)
    innhald = {
        "henta_dato": i_dag,
        "kjelde": "SSB Klass 131→104 correspondsAt.json",
        "kommune_til_fylkesnamn": kart,
    }
    ut.write_text(
        json.dumps(innhald, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Skreiv {len(kart)} kommunar til {ut}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(hovud())
