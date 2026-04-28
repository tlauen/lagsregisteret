# lagsregisteret

Oversikt over frilynde ungdomslag og liknande lag i Noreg, bygd på opne kjelder (først og fremst **Brønnøysund**), med rom for manuell utfylling og seinare Facebook-/søkje-tillegg.

**Språk i prosjektet:** nynorsk i kode, filnamn og dokumentasjon — sjå [`.cursor/rules/nynorsk.mdc`](.cursor/rules/nynorsk.mdc) og samanlikn gjerne med `skript/`-løypinga i Oslobygdas depot for tonen i langfilnamn.

## Kva som ligg her

| Del | Innhald |
|-----|---------|
| `oppsett/sokjefragment.txt` | Eitt søkjeord/fragment per line til `.../enheter?navn=` i [enhets-API-et](https://data.brreg.no/enhetsregisteret/api/dokumentasjon) — her kan du skru på breidda. |
| `oppsett/utelatingsfrasar_i_navn.txt` | Dersom minst **éin** frase (låge bokstavar) ligg inne i organisasjonsnamnet, blir rada utelaten. |
| `oppsett/v2_plan.txt` | Utviding i v2 (grende-, hus-typar m.m.) — ikkje kopla til kode enno. |
| `data/nu_saman_med_nu_no.json` | `orgnr` for **grøn rad** (heuristisk samanlikning med [nu.no/lokallag](https://www.ungdomslag.no/lokallag) + manuell `nu: medlem`) — oppdater med `skript/jamfoer_nu_lokallag.py --skriv` |
| `data/nu_lokallag_manglar_i_register.json` | **NU-tittlar utan Brreg-treff** (liste under tabellen) — `jamfoer_nu_lokallag.py --skriv` |
| `data/kommune_til_fylke.json` | Tabell frå SSB: kommunenummer → fylkesnamn (fyller `fylke` i CSV). |
| `data/manuell_status.json` | Manuell **NU-status** (medlem / utmeld), **skjul** (luka ut) og valfritt **nedlagt** per orgnr — sjå `oppsett/nu_status_forklaring.txt`. |
| `oppsett/nu_status_forklaring.txt` | Forklaring av felt i `manuell_status.json`. |
| `docs/index.html` | Søkbar / filtrerbar tabell for **GitHub Pages**; **Rediger i lista** lagrar i nettlesaren (utvid med nedlasting; valfri Vercel‑push for git). |
| `docs/admin.html` | Redigering av manuell status via nett (krev Vercel-API under). |
| `docs/js/lagreg_nettoppsett.js` | Grunn-URL for Vercel-API (`LAGREG_API_GRUNNURL`), oftast føreutfylt med produksjonsdomen. |
| `api/lagre-manuell-status.js` | Vercel serverless: Basic-auth, skriv `manuell_status` i repo. |
| `vercel.json` | Tidsgrense for Vercel-funksjon. |
| `package.json` | Nødvendig for Vercel (privat, ingen ekstra pakkar). |
| `docs/data/nu_saman_med_nu_no.json` | Kopi av `data/…` for nett (grøn markering) — fylgjer når `publiser_data_til_nettside.py` køyrst. |
| `docs/data/lag.csv` | Kopi av siste Brreg-register (ferdig innhenta). |
| `docs/data/manuell_status.json` | Kopi av manuell status (for nett). |
| `skript/innhent_lag_frå_brreg.py` | Les treff, slår saman på orgnr, skriv CSV med `kjelde_url` til [oppslag](https://data.brreg.no/enhetsregisteret/oppslag/enheter/) hos Brreg. |
| `skript/publiser_data_til_nettside.py` | Kopierer `utdata/…csv` → `docs/data/lag.csv`, manuell status og `data/nu_saman_*.json` / `nu_lokallag_manglar_*.json` → `docs/data/` når filene finst. |
| `skript/sett_lag_status.py` | CLI: oppdater éi orgnr-oppføring i `data/manuell_status.json`. |
| `skript/bygg_kommune_til_fylke.py` | OPPDATER: last ned siste kommune → fylke frå SSB (bruk sjeldan). |
| `skript/jamfoer_nu_lokallag.py` | Jamfører [nu.no/lokallag](https://www.ungdomslag.no/lokallag) (markdown med `##` per lag) med `docs/data/lag.csv` — sjekk samsvar manuelt, ikkje blind stol på likskapsdøme. |
| `skript/trygg_nett.py` | Hjelpemodul for SSL (bruk saman med `certifi`, sjå under). |
| `requirements.txt` | Anbefalt: `certifi` slik at HTTPS mot Brreg/SSB fungerer på t.d. macOS. |

## Køyre

Krev **Python 3.10+**.

Først (ein gong, særleg viktig på mac sitt innebygde Python — elles kan du få SSL-feil mot Brreg og SSB):

```bash
cd lagsregisteret
pip install -r requirements.txt
```

Innhenting:

```bash
python3 skript/innhent_lag_frå_brreg.py
```

Berre organisasjonar som også er **innført i frivillighetsregisteret** (Brreg sitt opne totalbestand):

```bash
python3 skript/innhent_lag_frå_brreg.py --krev-frivillighetsregister
```

Vel du elles **berre** dei som etter Brreg-adresse ser ut til å ha **tilhald i norsk kommune** (kommune/kommunenummer) **eller** norsk postnummer som i folkeregisteret (fire siffer), legg til:

```bash
python3 skript/innhent_lag_frå_brreg.py --krev-norsk-tilhald
```

(Dette flagget vert ofte brukt saman med `--krev-frivillighetsregister` — begge er valfrie.) **Begge saman** (full ny lagnamn‑liste ut frå Brreg med begge ting):

```bash
python3 skript/innhent_lag_frå_brreg.py \
  --krev-frivillighetsregister \
  --krev-norsk-tilhald
python3 skript/publiser_data_til_nettside.py
```

Ferdig fil (ikkje sjekka inn i git med mindre du vel det): `utdata/innhenta_lag_frå_brreg.csv`.

Prøvkjøyring (færre søkje- og API-kall):

```bash
python3 skript/innhent_lag_frå_brreg.py --maks_sokjefragment 2
```

Viss eitt søkje-fragment feilar (nettvett), kan du hald fram med resten:

```bash
python3 skript/innhent_lag_frå_brreg.py --hald-fram-ved-sokjefeil
```

Fyll **ikkje** fylke (berre dersom du vil samanlikne utan `data/kommune_til_fylke.json`):

```bash
python3 skript/innhent_lag_frå_brreg.py --utan_fylke
```

Hjelp: `python3 skript/innhent_lag_frå_brreg.py -h`

Oppdatere fylke-tabellen frå SSB (ikkje nødvendig kvar gong, men etter fylkes-/kommunereform):

```bash
python3 skript/bygg_kommune_til_fylke.py
```

`data/kommune_til_fylke.json` blir sjekka inn, slik at innhenting fungerer utan nett så lenge fylke-tabellen allereie finst.

## Noregs Ungdomslag (NU) og «luk ut»

- Rediger `data/manuell_status.json`: nøkkel = **9 siffer orgnr** (streng), verdiar:
  - `nu`: `medlem` | `utmeld` (eller utelat for ukjent). **Grøn rad** i tabellen = `nu: medlem` eller orgnr i `nu_saman_med_nu_no.json` (ungdomslag.no mot Brreg), med mindre rada er `utmeld` eller `nedlagt`.
  - `skjul`: `true` for laga som ikkje skal visast i hovudlista (ikkje rett låg, ikkje frilynde, osb.)
  - `nedlagt`: `true` for oppløyste/ikkje lenger aktive — **raud** rad, same som `utmeld`
  - `merknad`: valfri fritekst
- Eller bruk CLI, døme:
  ```bash
  python3 skript/sett_lag_status.py --orgnr 971320842 --nu medlem
  python3 skript/sett_lag_status.py --orgnr 123456789 --nu utmeld
  python3 skript/sett_lag_status.py --orgnr 123456789 --nedlagt
  python3 skript/sett_lag_status.py --orgnr 123456789 --luk-ut --merknad "Bondelag, ikkje ungdomslag"
  python3 skript/sett_lag_status.py --orgnr 123456789 --i-lista
  ```
- Nettsida: filter **Status** (medlem / utmeld / nedlagt), og avkryssing **Vis luka ut** for `skjul: true`. Sjå elles `oppsett/nu_status_forklaring.txt`.

## Nettvising (GitHub Pages)

1. I GitHub: **Innstillingar** → **Sider (Pages)** → bygg kjelde: **Deploy from a branch** → **main** (eller standardgren) → mappa **/docs** → Lagre. Nettsida vert tilgjengeleg som `https://<brukar>.github.io/lagsregisteret/` (døme — forkort depotnamnet ditt i URL-en).

2. Etter kvar ferdig **innhenting** (og gjerne etter manuelle endringar i `data/manuell_status.json`), oppdater `docs/data/` og **push**:
   ```bash
   python3 skript/innhent_lag_frå_brreg.py
   python3 skript/publiser_data_til_nettside.py
   git add docs/data/lag.csv docs/data/manuell_status.json docs/data/nu_saman_med_nu_no.json docs/data/nu_lokallag_manglar_i_register.json data/manuell_status.json data/nu_saman_med_nu_no.json data/nu_lokallag_manglar_i_register.json
   git commit -m "Oppdatert register og manuell status for nettvising"
   git push
   ```

3. Sida har **fylke**, **status** (eitt spørsmål: medlem / utmeld / nedlagt), søkjefelt, avkryssing for luka-ut, **vel synlege kolonnar** (førespurt lagring i nettlesaren) og i redigeringsmodus: **Status** og **hovudlista** fyrst, deretter **Lag** med **Merknad** rett attmed (fritekst med textarea). **Redigering** treng ikkje innlogging: endringar vert lagra lokalt, og `manuell_status.json` kan lastast ned; valfri **Vercel** med brukar/passord (sjå seksjon under) pushar rett inn i git. Brukar PapaParse + Grid.js.

4. Lokal førehandsvising: stå i mappa `docs/` og køyr `python3 -m http.server 8765`, opne `http://127.0.0.1:8765/`.

Merk: `docs/.nojekyll` gjer at GitHub ikkje køyrer Jekyll på statiske filer.

### Kolonnar i CSV

`lagsnavn`, `orgnr`, `kommune`, `fylke` (frå SSB sitt fylkesnamn via `kommunenummer` hos Brreg, med mindre du bruker `--utan_fylke`), `adresse`, `postnummer`, `poststed`, `nettstad` (ut frå `hjemmeside`, med `https://` når det manglar), `kjelde_type` (`brreg` — fylgjer med i data, ikkje eigen kolonne i vevtabellen), `kjelde_url` (lenkje til kjelde), `henta_dato`.

## Nettredigering (lokal, eller Vercel + GitHub API)

Sida på **GitHub Pages** er statisk og kan ikkje skriva til git av seg sjølv. I **hovudregisteret** kan du **vel «Rediger i lista»**: endringar vert lagra i `localStorage` for den domenen / nettlesaren, med **Last ned manuell_status.json** når du vil sjekkja fila inn. **Valfri** push frå sida utan lokal sjekk inn: litle **API** `api/lagre-manuell-status.js` med **Vercel** (same depot) og Basic passord, typisk for **admin** og som alternativ i eit samanbrett felt på index.

1. Gå til [vercel.com](https://vercel.com) og importér GitHub-repositoriet (eller køyr `vercel` frå mappa, med nettverkstilgang). Root directory er prosjektrota.
2. Under **Innstillingar** → **Miljøvariablar** (evt. både *Production* og *Preview*), set blant anna:
   - `LAGREG_BRUKER` — brukernamn for Basic-autentisering
   - `LAGREG_PASS` — passord (sterkt; lagra berre hos Vercel)
   - `LAGREG_GITHUB_TOKEN` — [Personal access token (classic)](https://github.com/settings/tokens) med `repo` (eller fine-grained med **innhald: les og skriv** for det repositoriet)
   - `LAGREG_GITHUB_EIGER` — GitHub-brukarnamn eller org (t.d. `tlaun`)
   - `LAGREG_GITHUB_NAMN` — repository-namn (t.d. `lagsregisteret`)
   - `LAGREG_TILLATTE_URSPRUNG` — **valfri avgrensing av kven som får bruka API** frå vevsida (CORS). Når sida (t.d. på GitHub Pages) gjer eit lagringskall til Vercel, følger nettlesaren med eit *opphav* som seier kva for nettadresse sida ligg under — t.d. `https://bukarnamn.github.io` eller `http://127.0.0.1:8765` lokal. **Dersom du ikkje set** denne variabelen, svarer Vercel uansett opphav (enkelt når du testar, men lettare å misbruka utanfra). **Dersom du set** han: skriv koma-separert liste over akkurat dei opphava du stolar på, same som starten på URL-en der brukarane opnar registeret, t.d. `https://bukarnamn.github.io,http://127.0.0.1:8765` for Pages pluss lokal førehandsvising. Sider ikkje på lista får svar med **403** (nekta). Sjekk bokstaveleg: `https` mot `http`, `www` ikkje, og port om du bruker annan enn 80/443.
   - `LAGREG_GIT_GREIN` — valfri, standard `main` (må samsvar med gren GitHub Pages bygg frå)
3. Når bygging er ferdig, får Vercel eit kort hovuddomen for prosjektet, t.d. `https://lagsregisteret.vercel.app` (utan avsluttande `/` i `LAGREG_API_GRUNNURL`). I tillegg finst **førehands-URLar** (lange namn med `…-git-…-vercel.app` / `…-tlauens-projects.vercel.app`) for kvar utrulling — dei endrar seg; bruk **berre hovud-domenet** i felta, med mindre du testar noko direkte frå førehands-URL. `docs/js/lagreg_nettoppsett.js` ligg førehandsutfylt med produksjons-API domen; **annan fork** bør bytte (eller tømme) der. Set URL i admin / hovudregister om du føretrekk; `localStorage` lagrar per nettstad.
4. **Admin-sida:** `docs/admin.html` (t.d. `https://<bruker>.github.io/lagsregisteret/admin.html` — følg depotnamn i URL) — bruk fyll inn, last inn register, endra, "Lagre til Git". Eitt lagring fører i standardoppsett til **to** samanhengande commit i git (både `data/manuell_status.json` og `docs/data/manuell_status.json`), så hovudregister og nettkopi er samsvarte.
5. Sjekk at GitHub bygg Pages etter nye commit (eitt augeblikk / minuttar).

Eitt par **tryggleiksmerknader:** Passord ligg aldri i git — berre hos Vercel. Ikkje bruk same passord andre stadar; roter token om noko lek. Basic-auth over **HTTPS** er for slikt admin-snikverk; større løysingar bør vurdere eigne identitetstenester.

**«Load failed» / ikkje til Vercel** når du klikkar *Lagre til Git*: sida ligg t.d. på `https://dittnavn.github.io/…` og API på `lagsregisteret.vercel.app` — då sjekker nettlesaren CORS. I Vercel: anten la `LAGREG_TILLATTE_URSPRUNG` stå **tom** (enklast), eller fyll nøyaktig `https://dittnavn.github.io,http://127.0.0.1:8765` (koma) og **redeploy**. Feil domen, skrivefeil, eller sti etter `github.io` gjev same symptom. Sjekk òg at URL i feltet er `https://lagsregisteret.vercel.app` (https, ikkje `http`, ikkje `/` på slutten).

## Neste steg (idé)

- Stikkprøve og stramme `sokjefragment.txt` / utelatingsfrasar.
- v2: mønster i `v2_plan.txt` som søkje tillegg (eller annan logikk for hus).

Lisens: sjå `LICENSE`. Data i `kommune_til_fylke.json` kjem frå SSB sitt API (opne data, sjå inne i fila).
