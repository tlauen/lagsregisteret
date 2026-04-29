<!-- Rediger denne fila (Markdown + innblanda HTML der nødvendig). Sida lastar den dynamisk. -->

<nav class="hjelp-mini-hoppliste" aria-label="Hoppliste i hjelpseksjon">
  <a href="#hjelp-kjelde">Kjelde</a><span aria-hidden="true">·</span>
  <a href="#hjelp-bruk">Søk og avgrens</a><span aria-hidden="true">·</span>
  <a href="#hjelp-filter">Filter</a><span aria-hidden="true">·</span>
  <a href="#hjelp-nedlasting">Excel</a><span aria-hidden="true">·</span>
  <a href="#hjelp-yting">Mange lag</a><span aria-hidden="true">·</span>
  <a href="#hjelp-farger">Fargar</a><span aria-hidden="true">·</span>
  <a href="#hjelp-gjennomsikt">Søkjefragment</a>
</nav>

<h3 id="hjelp-kjelde" class="hjelp-acc-h hjelp-acc-h-framst">Kjelde</h3>

Kvar rad gjeld **éi organisasjon** i [frivillighetsregisteret](https://www.brreg.no/frivillighetsregisteret/) hjå [Brønnøysund](https://www.brreg.no/) (opne data). Sjølve registret legg inn fleire lokale avgrensingar før treff på Brreg‑sida vert med — liste over korleis (fragment og utelatingar) kjem nedst her. Lista er jamført med uttrekk over lag registrert i Hypersys.

Kolonne **Liste** (`Ungdom*`, `Grend*`, `Bygd*`, ev. kombinasjon med komma) seier kva søkestreng som gjorde at laget dukka opp ved innhenting.

<h3 id="hjelp-bruk" class="hjelp-acc-h">Søk og avgrens</h3>

- **Søk øvst i tabellen** gjeld alle kolonnar som er synlege («Vis / skjul kolonnar»).
- Vel **fylke**; når fylke ikkje er «alle», kan du **velje kommune** nedanfor.

<h3 id="hjelp-filter" class="hjelp-acc-h">Filter og redigering</h3>

- **Vis luka ut**: når det blei henta organisasjonar frå Brønnøysund var det mange som me manuelt har luka ut i etterkant då dei ikkje er relevante, ikkje er ungdomslag, eller kom med ved ein feil. Desse blir skjult automatisk. Kryss denne for å også sjå desse.
- **Vis / skjul statustypar:** når alle boksar er avkryssa, blir status *ikkje* nytta som filter. Kryss *bort* i dei kategoriar du vil gjøyme — dei som står igjen («eller»-logikk) avgrens utvalet for status.
- **Vis / skjul listetypar:** same idé — med alle tre kryssa har kolonne Liste *ingen* filterverknad; ta *bort* kryss for dei typane du vil skjule på skjermen (`Ungdom*`, `Grend*`, `Bygd*`). Har ei rad fleire liste-tag (komma), er den framleis med om minst éin tag framleis er synleg.
- **Rediger i lista:** set NU-status eller merknad på rad. Utan innlogging blir endringane berre lagra i denne nettlesaren; last ned `manuell_status.json` eller bruk valfritt [admin‑sida](admin.html) / depot for permanent lagring i git.

<h3 id="hjelp-nedlasting" class="hjelp-acc-h">Last ned til Excel</h3>

Knappen **Last ned filtrerte rader (.csv til Excel)** ligg attmed filtera øvst — ho gjeld aktuelle **fylkes-/kommunesfilter**, status-, liste- og «luka ut»-val — men *ikkje* mellombels tekstsøk i tabellen. Fila er kodet UTF-16 slik at Excel oftast vis norsk rett — å/æ/ø, tankestrek, osv.

<h3 id="hjelp-yting" class="hjelp-acc-h">Mange rader på skjermen</h3>

Av omsyn til yting blir ikkje alle rader teikna med éin gong — bruk under tabellen **Last inn fleire til** eller **Vis alle** på det framleis filtrerte utvalet.

Brei tabell: dra eller scroll **vassrett under tabellen**, eller bruk <kbd>Tab</kbd> og piler / mus nedanfor rutenettet for å sjå alle kolonnane.

<h3 id="hjelp-farger" class="hjelp-acc-h">Kva betyr radfargene?</h3>

<p><strong class="dome-gron-tekst">Grøn tone</strong> — treff i <a href="https://www.ungdomslag.no/lokallag" rel="noopener noreferrer">lokallaglista på ungdomslag.no (NU)</a> som samsvarar med registret (<code>nu: medlem</code>), eller manuelt vald medlem. <strong>Gul tone</strong> — potensiell medlem. <strong>Dempa</strong> — ikkje aktuell. <strong>Lyseblå tone</strong> — inaktiv medlem (NU eller manuell merking). <strong class="dome-raud-tekst">Raud tone</strong> — utmelding eller nedlegging. Der utmelding kjem i tillegg til grøn NU‑ eller manuell «medlem»-status, gjeld utmeldinga.</p>

<hr class="hjelp-skilje" />

<h3 id="hjelp-gjennomsikt" class="hjelp-acc-h">Søkjefragment ved innhenting (frå depotet)</h3>

Nedanfor kjem dei same fragmenta og utelatingsfrasane som ligg under `oppsett/` og som vert kopiert til `docs/data/oppsett/` ved køying av `publiser_data_til_nettside.py`. Ved visning nedanfor hopp me over tomme liner og liner som byrjar med `#`.

**Søk øvst over tabellen** gjeld berre mellom dei rada som alt er innlasta her — ikkje blanda ordlista nedanfor med det søket.

<p class="hjelp-acc-h-alt">Fragment for <strong>Ungdom*</strong> — <code>sokjefragment.txt</code></p>
<ul id="oppsliste_ungdom" class="hjelp-oppsliste"></ul>

<p class="hjelp-acc-h-alt">Fragment for <strong>Bygd*</strong> — <code>sokjefragment_bygd.txt</code></p>
<ul id="oppsliste_bygd" class="hjelp-oppsliste"></ul>

<p class="hjelp-acc-h-alt">Fragment for <strong>Grend*</strong> — <code>sokjefragment_grende.txt</code></p>
<ul id="oppsliste_grende" class="hjelp-oppsliste"></ul>

<p class="hjelp-acc-h-alt">Utelatingsfrasar — delstrengar i lågare-stavde lag‑namn som gjer treff ignorert — <code>utelatingsfrasar_i_navn.txt</code></p>
<ul id="oppsliste_utelating" class="hjelp-oppsliste"></ul>
