#!/usr/bin/env python3
"""
Etter rapport: kopier NU-medlemsfelt mellom registerrader ved godkjenning.

Oppsett: kopier `oppsett/medlemas_ul_jamfor_valg_mal.json` til t.d.
`data/medlemas_ul_jamfor_valg.json` og fyll `kopier_nu_felt` med jamføringsduer.

Berre tomme NU-felt på mottakar vert fyllt (bruk `--overstyr` for å tvingja).

  python3 skript/bruk_medlemas_ul_jamfor_valg.py --valg data/medlemas_ul_jamfor_valg.json --dry-run
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

_skript_dir = Path(__file__).resolve().parent
if str(_skript_dir) not in sys.path:
    sys.path.insert(0, str(_skript_dir))


def rot() -> Path:
    return Path(__file__).resolve().parent.parent


def les_csv(sti: Path) -> tuple[list[str], list[dict[str, str]]]:
    with sti.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames:
            return [], []
        fn = list(r.fieldnames)
        return fn, [{k: (row.get(k) or "").strip() for k in fn} for row in r]


def skriv_csv(sti: Path, felt: list[str], rader: list[dict[str, str]]) -> None:
    sti.parent.mkdir(parents=True, exist_ok=True)
    with sti.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=felt, extrasaction="ignore")
        w.writeheader()
        for rad in rader:
            w.writerow({k: rad.get(k, "") for k in felt})


def reint_orgnr(verd: str) -> str | None:
    import re as _re

    t = _re.sub(r"\D", "", verd or "")
    if len(t) == 9:
        return t
    return None


NU_FELT = ("nu_mr_status", "nu_mr_overordna", "nu_mr_orgtype")


def hovud() -> int:
    p = argparse.ArgumentParser(description="Bruk vald UL/NU kopierliste")
    p.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="lag.csv",
    )
    p.add_argument(
        "--valg",
        type=Path,
        default=None,
        help="JSON med kopier_nu_felt (standard: data/medlemas_ul_jamfor_valg.json)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Berre meld — ikkje skriv CSV",
    )
    p.add_argument(
        "--overstyr",
        action="store_true",
        help="Skriv over eksisterande NU‑felt på mottakar",
    )
    val = p.parse_args()
    ro = rot()
    csv_sti = (val.csv or ro / "docs" / "data" / "lag.csv").resolve()
    vf = (val.valg or ro / "data" / "medlemas_ul_jamfor_valg.json").resolve()

    if not csv_sti.is_file():
        print(f"Finn ikkje {csv_sti}", file=sys.stderr)
        return 1
    if not vf.is_file():
        print(
            f"Finn ikkje {vf} — kopier oppsett/medlemas_ul_jamfor_valg_mal.json",
            file=sys.stderr,
        )
        return 1

    data = json.loads(vf.read_text(encoding="utf-8"))
    kommandoar = list(data.get("kopier_nu_felt") or [])
    felt, rader = les_csv(csv_sti)

    def fin_rad(o9: str) -> int | None:
        for i, rr in enumerate(rader):
            if reint_orgnr(rr.get("orgnr", "")) == o9:
                return i
        return None

    for kn in kommandoar:
        fraw = (
            kn.get("frå_orgnr")
            or kn.get("fra_orgnr")
            or kn.get("frå_org")
            or kn.get("orgnr_frå")
        )
        tb = kn.get("til_orgnr") or kn.get("orgnr_til") or kn.get("til_org")
        if isinstance(fraw, int):
            fraw = str(fraw)
        if isinstance(tb, int):
            tb = str(tb)
        of = reint_orgnr(str(fraw or "").strip())
        ot = reint_orgnr(str(tb or "").strip())
        if not of or not ot:
            print(f"Hopp — manglar orgnr frå eller til i {kn!r}", file=sys.stderr)
            continue
        if of == ot:
            print(f"Hopp — same orgnr i {kn!r}", file=sys.stderr)
            continue
        ia, ib = fin_rad(of), fin_rad(ot)
        if ia is None:
            print(f"Finn ikkje organisasjon med orgnr {of}", file=sys.stderr)
            continue
        if ib is None:
            print(f"Finn ikkje organisasjon med orgnr {ot}", file=sys.stderr)
            continue
        for fk in NU_FELT:
            vv = rader[ia].get(fk, "").strip()
            mål = (rader[ib].get(fk) or "").strip()
            if not vv:
                continue
            if not mål:
                print(f"[{ot}] ← {fk}: {vv[:72]}{'…' if len(vv) > 72 else ''}")
                if not val.dry_run:
                    rader[ib][fk] = vv
            elif val.overstyr and vv != mål:
                print(f"[{ot}] overstyr {fk}: {mål[:40]}… ← {vv[:40]}…")
                if not val.dry_run:
                    rader[ib][fk] = vv

    if val.dry_run:
        print("Dry‑run — ikkje skreiv CSV.", file=sys.stderr)
        return 0

    bak = csv_sti.with_suffix(".bak_før_medlemas_jamfor_valg.csv")
    try:
        shutil.copy2(csv_sti, bak)
        print(f"Backup: {bak.relative_to(ro)}", file=sys.stderr)
    except OSError:
        pass
    skriv_csv(csv_sti, felt, rader)
    print(f"Oppdaterte {csv_sti.relative_to(ro)}.", file=sys.stderr)
    print(
        "Køyr også: python3 skript/publiser_data_til_nettside.py (om du kopier frå docs/data/).",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(hovud())

