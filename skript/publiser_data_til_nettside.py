#!/usr/bin/env python3
"""
Kopierer utdata-CSV (etter innhenting) til docs/data/lag.csv slik at GitHub Pages
kan vise siste register, pluss kopi av manuell status og (om filene finst) nu-JSON
for grøn rad og liste over NU-lokallag som manglar i registeret.
"""
from __future__ import annotations

import sys
from pathlib import Path


def prosjektrot() -> Path:
    return Path(__file__).resolve().parent.parent


def hovud() -> int:
    rot = prosjektrot()
    kjelde = rot / "utdata" / "innhenta_lag_frå_brreg.csv"
    mål = rot / "docs" / "data" / "lag.csv"
    if not kjelde.is_file():
        print(
            f"Finn ikkje {kjelde} — køyr fyrst: python3 skript/innhent_lag_frå_brreg.py",
            file=sys.stderr,
        )
        return 1
    mål.parent.mkdir(parents=True, exist_ok=True)
    mål.write_bytes(kjelde.read_bytes())
    linjer = len(mål.read_text(encoding="utf-8").splitlines())
    print(
        f"Kopierte {kjelde.name} → {mål.relative_to(rot)} ({linjer} liner)",
        file=sys.stderr,
    )
    status_kjelde = rot / "data" / "manuell_status.json"
    status_mål = rot / "docs" / "data" / "manuell_status.json"
    if not status_kjelde.is_file():
        status_mål.write_text("{}\n", encoding="utf-8")
        print("Skreiv tom docs/data/manuell_status.json", file=sys.stderr)
    else:
        status_mål.parent.mkdir(parents=True, exist_ok=True)
        status_mål.write_bytes(status_kjelde.read_bytes())
        print(
            f"Kopierte {status_kjelde.name} → {status_mål.relative_to(rot)}",
            file=sys.stderr,
        )
    nu_kjelde = rot / "data" / "nu_saman_med_nu_no.json"
    nu_mål = rot / "docs" / "data" / "nu_saman_med_nu_no.json"
    if nu_kjelde.is_file():
        nu_mål.parent.mkdir(parents=True, exist_ok=True)
        nu_mål.write_bytes(nu_kjelde.read_bytes())
        print(
            f"Kopierte {nu_kjelde.name} → {nu_mål.relative_to(rot)}",
            file=sys.stderr,
        )
    mag_kjelde = rot / "data" / "nu_lokallag_manglar_i_register.json"
    mag_mål = rot / "docs" / "data" / "nu_lokallag_manglar_i_register.json"
    if mag_kjelde.is_file():
        mag_mål.parent.mkdir(parents=True, exist_ok=True)
        mag_mål.write_bytes(mag_kjelde.read_bytes())
        print(
            f"Kopierte {mag_kjelde.name} → {mag_mål.relative_to(rot)}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(hovud())
