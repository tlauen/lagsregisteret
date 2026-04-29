#!/usr/bin/env python3
"""
Oppdater éin oppføring i data/manuell_status.json (orgnr, NU-status, skjul, nedlagt, merknad).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def prosjektrot() -> Path:
    return Path(__file__).resolve().parent.parent


def reint_orgnr(verd: str) -> str:
    t = re.sub(r"\D", "", verd.strip())
    if len(t) != 9:
        raise SystemExit("Org.nr må vere 9 siffer (utan mellomrom).")
    return t


def hovud() -> int:
    t = argparse.ArgumentParser(
        description="Set manuell NU-status / skjuling for eitt lag (orgnr).",
    )
    t.add_argument("--orgnr", required=True, help="9-sifra organisasjonsnummer")
    t.add_argument(
        "--nu",
        choices=(
            "medlem",
            "utmeld",
            "potensiell_medlem",
            "ikkje_aktuell",
            "inaktiv_medlem",
            "tom",
        ),
        default=None,
        help="NU-status (vel «tom» for å tømme feltet)",
    )
    t.add_argument(
        "--luk-ut",
        action="store_true",
        help="Ikkje vis dette laga i hovudlista (ikkje rett låg / ikkje frilynde o.l.)",
    )
    t.add_argument(
        "--i-lista",
        action="store_true",
        help="Vis att i hovudlista (fjern skjuling)",
    )
    t.add_argument(
        "--nedlagt",
        action="store_true",
        help="Merk at laget er nedlagt (får raud markering; lag med orgnr får skrive nedlagt i json)",
    )
    t.add_argument(
        "--ikkje-nedlagt",
        action="store_true",
        help="Fjern nedlagt-merke",
    )
    t.add_argument("--merknad", default=None, help="Fritekst (bruk --merknad '' for å tømme)")
    val = t.parse_args()
    ro = reint_orgnr(val.orgnr)
    sti = prosjektrot() / "data" / "manuell_status.json"
    sti.parent.mkdir(parents=True, exist_ok=True)
    if sti.is_file() and sti.read_text().strip():
        d = json.loads(sti.read_text(encoding="utf-8"))
    else:
        d = {}
    if not isinstance(d, dict):
        print("Forventa at rota i manuell_status.json er eit objekt ({}).", file=sys.stderr)
        return 1
    nå = d.get(ro, {})
    if not isinstance(nå, dict):
        nå = {}
    if val.luk_ut and val.i_lista:
        print("Vel anten --luk-ut eller --i-lista, ikkje begge.", file=sys.stderr)
        return 1
    if val.nedlagt and val.ikkje_nedlagt:
        print("Vel anten --nedlagt eller --ikkje-nedlagt, ikkje begge.", file=sys.stderr)
        return 1
    if val.luk_ut:
        nå["skjul"] = True
    if val.i_lista:
        nå["skjul"] = False
    if val.nedlagt:
        nå["nedlagt"] = True
    if val.ikkje_nedlagt:
        nå.pop("nedlagt", None)
    if val.nu is not None:
        if val.nu == "tom":
            nå.pop("nu", None)
        else:
            nå["nu"] = val.nu
    if val.merknad is not None:
        m = val.merknad
        nå["merknad"] = m
        if m == "":
            nå.pop("merknad", None)
    if not nå:
        d.pop(ro, None)
    else:
        d[ro] = nå
    sti.write_text(json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Oppdatert {ro} i {sti.relative_to(prosjektrot())}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(hovud())
