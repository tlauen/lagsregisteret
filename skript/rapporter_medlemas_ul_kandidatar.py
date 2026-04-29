#!/usr/bin/env python3
"""
Finn moglege UL↔ungdomslag-par i lag.csv og skriv rapport som JSON (+ usikre namnear).

  python3 skript/rapporter_medlemas_ul_kandidatar.py
  python3 skript/rapporter_medlemas_ul_kandidatar.py --csv docs/data/lag.csv --utfil data/medlemas_ul_kandidatar.json
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

_skript_dir = Path(__file__).resolve().parent
if str(_skript_dir) not in sys.path:
    sys.path.insert(0, str(_skript_dir))

from flett_nu_medlemsregister import (
    canonical_nu_mr_status,
    lik_namn,
    norm_stad,
    reint_orgnr,
    ul_mot_ungdoms_par_navn,
)


def rot() -> Path:
    return Path(__file__).resolve().parent.parent


def les_csv(sti: Path) -> tuple[list[str], list[dict[str, str]]]:
    with sti.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames:
            return [], []
        fn = list(r.fieldnames)
        return fn, [{k: (row.get(k) or "").strip() for k in fn} for row in r]


def hovud() -> int:
    p = argparse.ArgumentParser(description="Rapport: UL/ungerdoms-par og usikre treff")
    p.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="lag.csv (default: docs/data/lag.csv)",
    )
    p.add_argument(
        "--utfil",
        type=Path,
        default=None,
        help="Utfil JSON (default: data/medlemas_ul_kandidatar.json)",
    )
    p.add_argument("--terskel-usikker-o", type=float, default=0.86, help="Ovre namne‑terskel (under flett sin standard)")
    p.add_argument(
        "--terskel-usikker-n",
        type=float,
        default=0.84,
        help="Nedre grense for «usikre» (smalt band = færre treff)",
    )
    val = p.parse_args()
    ro = rot()
    csv_sti = (val.csv or ro / "docs" / "data" / "lag.csv").resolve()
    utfil = (val.utfil or ro / "data" / "medlemas_ul_kandidatar.json").resolve()
    if not csv_sti.is_file():
        print(f"Finn ikkje {csv_sti}", file=sys.stderr)
        return 1
    _, rader = les_csv(csv_sti)

    org_av_rad: dict[int, str | None] = {}
    idx_med_org: list[int] = []
    for i, rad in enumerate(rader):
        o = reint_orgnr(rad.get("orgnr", ""))
        org_av_rad[i] = o
        if o:
            idx_med_org.append(i)

    bøtter: defaultdict[tuple[str, str], list[int]] = defaultdict(list)
    for i in idx_med_org:
        rad = rader[i]
        kk = (norm_stad(rad.get("kommune", "")), norm_stad(rad.get("fylke", "")))
        bøtter[kk].append(i)

    ul_par: list[dict] = []
    handlagt_ul: set[tuple[int, int]] = set()
    for _, bucket in sorted(bøtter.items(), key=lambda x: (-len(x[1]), x[0])):
        n = len(bucket)
        for xi in range(n):
            for yi in range(xi + 1, n):
                ia, jb = bucket[xi], bucket[yi]
                na = rader[ia].get("lagsnavn", "").strip()
                nb = rader[jb].get("lagsnavn", "").strip()
                if not ul_mot_ungdoms_par_navn(na, nb):
                    continue
                ky = (ia, jb) if ia < jb else (jb, ia)
                handlagt_ul.add(ky)
                oo_a = (rader[ia].get("nu_mr_overordna") or "").strip()
                oo_b = (rader[jb].get("nu_mr_overordna") or "").strip()
                st_a = canonical_nu_mr_status(rader[ia].get("nu_mr_status") or "")
                st_b = canonical_nu_mr_status(rader[jb].get("nu_mr_status") or "")
                merk_a = oo_a != "" or st_a != ""
                merk_b = oo_b != "" or st_b != ""
                fors = None
                if merk_a and not merk_b:
                    fors = (
                        "Kopier NU‑felt frå orgsnr_rad_a til b (b tomare). "
                        f"Lim inn i kopier_nu‑felt: {{ frå_orgnr: «{org_av_rad[ia]}», til_orgnr: «{org_av_rad[jb]}» }}"
                    )
                elif merk_b and not merk_a:
                    fors = (
                        "Kopier NU‑felt frå orgsnr_rad_b til a. "
                        f"{{ frå_orgnr: «{org_av_rad[jb]}», til_orgnr: «{org_av_rad[ia]}» }}"
                    )
                elif len(oo_a) < len(oo_b) and len(oo_b) > 10:
                    fors = (
                        "B har lengre nu_mr_overordna — vurder kopiering ned til a"
                    )
                ul_par.append(
                    {
                        "orgsnr_rad_a": org_av_rad[ia],
                        "orgsnr_rad_b": org_av_rad[jb],
                        "lagsnavn_a": na,
                        "lagsnavn_b": nb,
                        "kommune": rader[ia].get("kommune", ""),
                        "fylke": rader[ia].get("fylke", ""),
                        "likskap_verdi_namn": round(lik_namn(na, nb), 4),
                        "nu_mr_overordna_a": oo_a or None,
                        "nu_mr_overordna_b": oo_b or None,
                        "nu_mr_status_syn_a": st_a or None,
                        "nu_mr_status_syn_b": st_b or None,
                        "forslag_fyll": fors,
                    }
                )

    usikre: list[dict] = []
    for _, bucket in bøtter.items():
        n = len(bucket)
        for xi in range(n):
            for yi in range(xi + 1, n):
                ia, jb = bucket[xi], bucket[yi]
                key = (ia, jb) if ia < jb else (jb, ia)
                if key in handlagt_ul:
                    continue
                xa, xb = rader[ia], rader[jb]
                na = xa.get("lagsnavn", "").strip()
                nb = xb.get("lagsnavn", "").strip()
                sc = lik_namn(na, nb)
                if val.terskel_usikker_n <= sc < val.terskel_usikker_o:
                    usikre.append(
                        {
                            "orgsnr_rad_a": org_av_rad[ia],
                            "orgsnr_rad_b": org_av_rad[jb],
                            "lagsnavn_a": na,
                            "lagsnavn_b": nb,
                            "kommune": xa.get("kommune"),
                            "fylke": xa.get("fylke"),
                            "likskap_verdi_namn": round(sc, 4),
                            "sjølvvekting": (
                                "Sjå visuelt; ved treff bruk data/medlemas_ul_jamfor_valg.json"
                            ),
                        }
                    )

    ut = {
        "kjelde_csv": str(csv_sti.relative_to(ro)),
        "bekrefta_ul_ungdoms_par_antal": len(ul_par),
        "bekrefta_ul_ungdoms_par_rader": ul_par,
        "usikre_likande_naman_antal": len(usikre),
        "usikre_likande_rader": usikre,
        "merknad": "Sjå også skript/bruk_medlemas_ul_jamfor_valg.py for å kopiere NU‑felt",
    }

    utfil.parent.mkdir(parents=True, exist_ok=True)
    utfil.write_text(
        json.dumps(ut, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Skreiv {utfil.relative_to(ro)} "
        f"— UL‑par {len(ul_par)}, namne‑usikre {len(usikre)}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(hovud())
