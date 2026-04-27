#!/usr/bin/env python3
"""
Jamfører namn på lokal­lag list på ungdomslag.no/lokallag med lagsregisteret (Brreg-CSV).

Bruk:
  python3 skript/jamfoer_nu_lokallag.py [--skriv] /sti/til/lokallag-ekstrahert.md

--skriv  Skriv/oppdaterer `data/nu_saman_med_nu_no.json` (orgnr for grøn rad + manuell medlem)
         og `data/nu_lokallag_manglar_i_register.json` (NU-tittlar utan treff i registeret),
         deretter: `python3 skript/publiser_data_til_nettside.py` for `docs/data/…`.

Dersom fil manglar: lagre nettsideteksten med éi `## …`-overskrift per lag (t.d. frå
Cursor «Fetch» av https://www.ungdomslag.no/lokallag) og køyr mot den fila.
"""
from __future__ import annotations

import csv
import difflib
import json
import re
import sys
from datetime import date
from pathlib import Path


def rot() -> Path:
    return Path(__file__).resolve().parent.parent


def nøkkel(tek: str) -> str:
    t = tek.lower()
    t = t.replace("fril.", "frilynde")
    t = re.sub(r"[^a-zæøå0-9]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    t = t.replace(" u l ", " ul ")
    t = t.replace("u.l.", "ul")
    t = t.replace(" fr ", " frilynte ")
    return t


def nøklar_fra_brukeleg(n: str) -> set[str]:
    s = nøkkel(n)
    u: set[str] = {s}
    s2 = s.replace(" ungdomslag", "").replace(" ungdoms og idrettslag", " idrettslag")
    s2 = re.sub(
        r"\b(bondeungdomslaget|folkedanslaget|folkedans|ungdomslaget)\b",
        "",
        s2,
    )
    s2 = re.sub(r"\s+", " ", s2).strip()
    u.add(s2)
    return {x for x in u if len(x) >= 4}


def hent_nu_tittlar(fil: Path) -> list[str]:
    rå = fil.read_text(encoding="utf-8", errors="replace")
    ut: list[str] = []
    for line in rå.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if not m:
            continue
        ut.append(m.group(1).strip())
    return ut


HOPP_OVER = {
    "filtrer",
    "kartvisning",
    "kva er eit nu-lag",
    "å drive lokallag",
    "kva gjer eit fylkeslag",
    "ressursar",
    "andre initiativ",
    "medlemsregister (hypersys)",
    "lokallag",
    "noregs ungdomslag",
    "om nu",
    "om noregs ungdomslag",
    "prisar og medlemskap",
    "fordelar ved lagsmedlemskap",
    "medlemsskap",
    "kva gjer eit fylkeslag",
}


def fylltrål_nu(alle: list[str]) -> list[str]:
    s = {t.lower() for t in HOPP_OVER}
    gode: list[str] = []
    for t in alle:
        tl = t.lower().strip()
        if not tl or tl in s:
            continue
        if "logo for" in tl:
            continue
        gode.append(t)
    return gode


def last_register(sti: Path) -> list[tuple[str, str, str, str]]:
    rader: list[tuple[str, str, str, str]] = []
    with sti.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            n = (row.get("lagsnavn") or "").strip()
            o = (row.get("orgnr") or "").strip()
            k = (row.get("kommune") or "").strip()
            fy = (row.get("fylke") or "").strip()
            if n:
                rader.append((n, o, k, fy))
    return rader


def to_beste_treff(
    nu: str, register: list[tuple[str, str, str, str]]
) -> tuple[float, str | None, str | None, float]:
    """Returnerer (beste, navn, orgnr, andre_beste) — andre for å unngå forvekslingar."""
    poeng: list[tuple[float, str, str]] = []
    for navn, orgnr, _, _ in register:
        var = nøklar_fra_brukeleg(nu)
        sammen = 0.0
        reg_set = nøklar_fra_brukeleg(navn)
        for a in var:
            for b in reg_set:
                sammen = max(
                    sammen, difflib.SequenceMatcher(None, a, b).ratio()
                )
        poeng.append((sammen, navn, orgnr))
    poeng.sort(key=lambda x: -x[0])
    if not poeng:
        return 0.0, None, None, 0.0
    best, navn, orgn = poeng[0]
    andre = poeng[1][0] if len(poeng) > 1 else 0.0
    return best, navn, orgn, andre


def inkluder_saman(
    skor: float, andre: float, nu: str, rnav: str, orgnr9: str
) -> bool:
    """Gjev ja for orgnr som skal få grøn markering saman med heuristikk."""
    if not orgnr9 or not rnav:
        return False
    nul = nu.lower()
    rvl = (rnav or "").lower()
    if "askøy" in nul and "kvar" in rvl and "askøy" not in rvl:
        return False
    if skor >= 0.98:
        return True
    if skor < 0.86:
        return False
    if andre > 0.3 and (skor - andre) < 0.02 and skor < 0.93:
        return False
    if len(nøkkel(nu)) < 16 and skor < 0.92:
        return False
    return (skor - andre) >= 0.04 or skor >= 0.91


def beste_treff(
    nu: str, register: list[tuple[str, str, str, str]]
) -> tuple[float, str | None, str | None]:
    a, b, c, _ = to_beste_treff(nu, register)
    return a, b, c


def les_medlem_frå_manuell_status(sti: Path) -> set[str]:
    if not sti.is_file():
        return set()
    rå = sti.read_text(encoding="utf-8").strip()
    if not rå or rå == "{}":
        return set()
    d = json.loads(rå)
    if not isinstance(d, dict):
        return set()
    ut: set[str] = set()
    for k, v in d.items():
        if not re.match(r"^\d{9}$", str(k)) or not isinstance(v, dict):
            continue
        if (v.get("nu") or "").strip().lower() == "medlem":
            ut.add(k)
    return ut


def hovud() -> int:
    args = [a for a in sys.argv[1:] if a not in ("--skriv", "-s")]
    skriv = "--skriv" in sys.argv[1:] or "-s" in sys.argv[1:]
    pro = rot()
    csv_sti = pro / "docs" / "data" / "lag.csv"
    if len(args) < 1:
        print(
            f"Bruk: {sys.argv[0]} [--skriv] <markdown med ## per NU-lag>\n"
            f"  --skriv  oppdaterer data/nu_saman_med_nu_no.json og nu_lokallag_manglar_i_register.json frå samanlikninga\n"
            f"Døme: lim sida (markdown) i .md med ## per lag og gjev sti",
            file=sys.stderr,
        )
        return 1
    md_sti = Path(args[0]).resolve()
    if not md_sti.is_file():
        print(f"Finn ikkje {md_sti}", file=sys.stderr)
        return 1
    if not csv_sti.is_file():
        print(f"Finn ikkje {csv_sti}", file=sys.stderr)
        return 1

    tittar = fylltrål_nu(hent_nu_tittlar(md_sti))
    register = last_register(csv_sti)
    terskel = 0.62
    høg_tilvis = 0.82
    samsvar: list[tuple[str, str, str, str]] = []
    tvilsam: list[tuple[str, str, str, str, str]] = []
    manglar: list[str] = []
    for nu in tittar:
        skor, rnav, orgn = beste_treff(nu, register)
        sstr = f"{skor:.2f}"
        if rnav is None or orgn is None:
            manglar.append(nu)
        elif skor >= høg_tilvis:
            samsvar.append((nu, rnav, orgn, sstr))
        elif skor >= terskel:
            tvilsam.append((nu, rnav, orgn, sstr))
        else:
            manglar.append(nu)

    samsvarte_lagsnavn: set[str] = {a[1] for a in samsvar} | {a[1] for a in tvilsam}

    i_register_utan_nu: list[str] = []
    for n, o, k, f in register:
        best = 0.0
        for tit in tittar:
            sk, _, _ = beste_treff(tit, [(n, o, k, f)])
            best = max(best, sk)
        if best < terskel:
            i_register_utan_nu.append(f"{n}  orgnr {o}  {f or k}")

    print("— Jamføring: nu.no lokallag vs. lagsregisteret (Brreg) —\n")
    print(f"NU-lista: {len(tittar)} lag (etter filter)")
    print(f"Register: {len(register)} rader\n")
    print(
        f"** Tydeleg samsvar (≥ {høg_tilvis*100:.0f} % likskap):** {len(samsvar)}"
    )
    for nu, rnav, orgn, sc in samsvar:
        print(f"  OK  «{nu}»\n     →  {rnav}  ({sc})  orgnr {orgn}")
    print(
        f"\n** Samsvar med manuell sjekk ({terskel*100:.0f}–{høg_tilvis*100:.0f} % likskap):** {len(tvilsam)}"
    )
    for nu, rnav, orgn, sc in tvilsam:
        print(f"  ?   «{nu}»\n     →  {rnav}  ({sc})  orgnr {orgn}")
    print(
        f"\n** På nu.no, ikkje funnen i register (låg likskap / anna skrivemåte):** {len(manglar)}"
    )
    for x in manglar:
        print(f"  —   «{x}»")
    print(
        f"\n** I register, ikkje samsvar med nokon NU-overskrift (≥{terskel*100:.0f}%):** {len(i_register_utan_nu)}"
    )
    for x in i_register_utan_nu[:80]:
        print(f"  —   {x}")
    if len(i_register_utan_nu) > 80:
        print(f"  …  og {len(i_register_utan_nu) - 80} til")

    if skriv:
        man_sti = pro / "data" / "manuell_status.json"
        orgnrs: set[str] = set(les_medlem_frå_manuell_status(man_sti))
        for nu in tittar:
            sk, rnav, orgn, andre = to_beste_treff(nu, register)
            if rnav and orgn and inkluder_saman(sk, andre, nu, rnav, orgn):
                o9 = re.sub(r"\D", "", str(orgn))
                if len(o9) == 9:
                    orgnrs.add(o9)
        ut_sti = pro / "data" / "nu_saman_med_nu_no.json"
        payload = {
            "kjelde_oppføring": "https://www.ungdomslag.no/lokallag",
            "generert": date.today().isoformat(),
            "merknad": "orgnr: heuristisk samanlikning med lag.csv pluss manuell nu=medlem i manuell_status. Utmelding (utmeld) overstykkjer i nettvisaren.",
            "orgnrar": sorted(orgnrs),
        }
        ut_sti.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(
            f"Skreiv {ut_sti.relative_to(pro)} ({len(orgnrs)} orgnr, inkl. manuell medlem).",
            file=sys.stderr,
        )
        mag_sti = pro / "data" / "nu_lokallag_manglar_i_register.json"
        mag_payload = {
            "kjelde_oppføring": "https://www.ungdomslag.no/lokallag",
            "generert": date.today().isoformat(),
            "merknad": "NU-lokallag (##-overskrifter) utan godt nok Brreg-treff i docs/data/lag.csv — vert vist under tabellen i registeret.",
            "tittlar": sorted(manglar),
        }
        mag_sti.write_text(
            json.dumps(mag_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(
            f"Skreiv {mag_sti.relative_to(pro)} ({len(manglar)} tittlar utan treff i registeret).",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(hovud())
