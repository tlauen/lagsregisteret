(function () {
  "use strict";

  var LAGRING_API = "lagreg_api_grunnurl";

  function fåApigrunn() {
    var k = document.getElementById("api_grunnurl");
    if (k && k.value && k.value.trim()) {
      return k.value.trim().replace(/\/$/, "");
    }
    if (window.LAGREG_API_GRUNNURL && String(window.LAGREG_API_GRUNNURL).trim()) {
      return String(window.LAGREG_API_GRUNNURL).trim().replace(/\/$/, "");
    }
    try {
      var l = localStorage.getItem(LAGRING_API);
      if (l && l.trim()) return l.trim().replace(/\/$/, "");
    } catch (e) {
      /* gjev opp */
    }
    return "";
  }

  var data = {};
  var feilEl = null;
  var tabellKropp = null;

  function setFeil(tek) {
    if (!feilEl) return;
    if (tek) {
      feilEl.textContent = tek;
      feilEl.removeAttribute("hidden");
      feilEl.style.display = "block";
    } else {
      feilEl.textContent = "";
      feilEl.setAttribute("hidden", "");
      feilEl.style.display = "none";
    }
  }

  function sorterNøklar(inn) {
    var o = {};
    Object.keys(inn)
      .sort()
      .forEach(function (k) {
        o[k] = inn[k];
      });
    return o;
  }

  function sørgFelt(orgnr) {
    if (!data[orgnr] || typeof data[orgnr] !== "object") {
      data[orgnr] = {};
    }
    return data[orgnr];
  }

  function frysRad(orgnr) {
    var b = data[orgnr] || {};
    var tr = document.createElement("tr");
    tr.dataset.orgnr = orgnr;

    var td0 = document.createElement("td");
    td0.textContent = orgnr;
    tr.appendChild(td0);

    var td1 = document.createElement("td");
    var sel = document.createElement("select");
    sel.setAttribute("aria-label", "NU for " + orgnr);
    [
      ["", "— (ikkje sett) —"],
      ["medlem", "medlem i NU"],
      ["utmeld", "utmeld"],
    ].forEach(
      function (par) {
        var o = document.createElement("option");
        o.value = par[0];
        o.textContent = par[1];
        if (b.nu == null) {
          if (par[0] === "") o.selected = true;
        } else if (b.nu === par[0]) o.selected = true;
        sel.appendChild(o);
      }
    );
    sel.addEventListener("change", function () {
      var f = sørgFelt(orgnr);
      if (sel.value === "") delete f.nu;
      else f.nu = sel.value;
    });
    td1.appendChild(sel);
    tr.appendChild(td1);

    var td2 = document.createElement("td");
    var ch = document.createElement("input");
    ch.type = "checkbox";
    ch.title = "Ikkje vis i hovudlista (luka ut)";
    ch.checked = !!b.skjul;
    ch.addEventListener("change", function () {
      var f = sørgFelt(orgnr);
      if (ch.checked) f.skjul = true;
      else delete f.skjul;
    });
    td2.appendChild(ch);
    tr.appendChild(td2);

    var td2b = document.createElement("td");
    var chN = document.createElement("input");
    chN.type = "checkbox";
    chN.title = "Nedlagt (raud markering i registeret)";
    chN.checked = !!b.nedlagt;
    chN.addEventListener("change", function () {
      var f = sørgFelt(orgnr);
      if (chN.checked) f.nedlagt = true;
      else delete f.nedlagt;
    });
    td2b.appendChild(chN);
    tr.appendChild(td2b);

    var td3 = document.createElement("td");
    var inp = document.createElement("input");
    inp.type = "text";
    inp.className = "merknad-felt";
    inp.value = b.merknad != null ? b.merknad : "";
    inp.placeholder = "Merknad";
    inp.setAttribute("aria-label", "Merknad for " + orgnr);
    inp.addEventListener("input", function () {
      var f = sørgFelt(orgnr);
      if (inp.value.trim() === "") delete f.merknad;
      else f.merknad = inp.value;
    });
    td3.appendChild(inp);
    tr.appendChild(td3);

    var td4 = document.createElement("td");
    var slette = document.createElement("button");
    slette.type = "button";
    slette.textContent = "Slett";
    slette.addEventListener("click", function () {
      delete data[orgnr];
      tr.remove();
    });
    td4.appendChild(slette);
    tr.appendChild(td4);
    return tr;
  }

  function teiknOpp() {
    if (!tabellKropp) return;
    tabellKropp.textContent = "";
    var s = sorterNøklar(data);
    Object.keys(s).forEach(function (k) {
      tabellKropp.appendChild(frysRad(k));
    });
  }

  function normaliser(inn) {
    if (inn == null || typeof inn !== "object" || Array.isArray(inn)) {
      throw new Error("Fila skal vere eit objekt (orgnr som nøklar).");
    }
    var out = {};
    Object.keys(inn).forEach(function (k) {
      var t = (k + "").replace(/\D/g, "");
      if (t.length !== 9) throw new Error("Ugyldig nøkkel: " + k);
      out[t] = inn[k];
    });
    return out;
  }

  function byggReneEiningar(inn) {
    var o = {};
    Object.keys(inn).forEach(function (org) {
      var u = {};
      if (inn[org].nu) u.nu = inn[org].nu;
      if (inn[org].skjul === true) u.skjul = true;
      if (inn[org].nedlagt === true) u.nedlagt = true;
      if (inn[org].merknad) u.merknad = String(inn[org].merknad);
      if (Object.keys(u).length) o[org] = u;
    });
    return sorterNøklar(o);
  }

  function synkBoks() {
    var ta = document.getElementById("rå_json");
    if (ta) ta.value = JSON.stringify(sorterNøklar(data), null, 2);
  }

  function oppdaterFraBoks() {
    var ta = document.getElementById("rå_json");
    if (!ta) return;
    try {
      var rå = JSON.parse(ta.value);
      data = byggReneEiningar(normaliser(rå));
      teiknOpp();
      synkBoks();
      setFeil("");
    } catch (e) {
      setFeil(e.message);
    }
  }

  function basicAuthBase64(b, p) {
    var s = b + ":" + p;
    return btoa(unescape(encodeURIComponent(s)));
  }

  function utgreiKnetthendelse(e) {
    var m = e && e.message != null ? String(e.message) : "";
    if (!m) m = "Ukjent feil";
    if (/load failed|failed to fetch|networkerror|aborted|fetch/i.test(m)) {
      return (
        m +
        " — Vanleg: CORS. I Vercel, anten tøm LAGREG_TILLATTE_URSPRUNG, eller sett ho til sida di nøyaktig, t.d. https://dittnavn.github.io,http://127.0.0.1:8765 (koma, utan sti). Sjekk Vercel-URL (https://lagsregisteret.vercel.app, utan / slutt)."
      );
    }
    return m;
  }

  function lagreTilApi() {
    setFeil("");
    var grunn = fåApigrunn();
    if (!grunn) {
      setFeil(
        "Set fyrst grunn-URL for API (Vercel) under, eller fyll i docs/js/lagreg_nettoppsett.js (LAGREG_API_GRUNNURL)."
      );
      return;
    }
    var br = (document.getElementById("admin_brukar") || {}).value;
    var pa = (document.getElementById("admin_pass") || {}).value;
    if (br == null || pa == null) {
      setFeil("Fyll brukar og passord.");
      return;
    }
    var kropp = sorterNøklar(data);
    var url = grunn + "/api/lagre-manuell-status";
    var auth = basicAuthBase64(String(br), String(pa));

    var merkn = document.getElementById("lagre_status");
    if (merkn) merkn.textContent = "Lagrar…";

    fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        Authorization: "Basic " + auth
      },
      body: JSON.stringify({ manuell_status: kropp })
    })
      .then(function (r) {
        return r.text().then(function (t) {
          return { s: r.status, t: t };
        });
      })
      .then(function (e) {
        if (e.s === 200) {
          setFeil("");
          if (merkn) merkn.textContent = "Lagra (Git). Vent eitt augeblikk, så oppdaterer GitHub Pages.";
          return;
        }
        var o = {};
        try {
          o = JSON.parse(e.t);
        } catch (x) {
          o = { feil: e.t || "Ukjent feil" };
        }
        if (merkn) merkn.textContent = "";
        setFeil(o.feil || "HTTP " + e.s);
      })
      .catch(function (e) {
        if (merkn) merkn.textContent = "";
        setFeil(utgreiKnetthendelse(e));
      });
  }

  function hentFila() {
    setFeil("");
    if (document.getElementById("hent_status")) {
      document.getElementById("hent_status").textContent = "Hentar…";
    }
    return fetch("data/manuell_status.json", { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("Kunne ikkje henta: " + r.status);
        return r.text();
      })
      .then(function (t) {
        var ta = document.getElementById("rå_json");
        if (ta) ta.value = t;
        data = byggReneEiningar(normaliser(JSON.parse(t)));
        teiknOpp();
        if (document.getElementById("hent_status")) {
          document.getElementById("hent_status").textContent = "Lasta.";
        }
      })
      .catch(function (e) {
        if (document.getElementById("hent_status")) {
          document.getElementById("hent_status").textContent = "";
        }
        setFeil(e.message);
      });
  }

  function lagtTilEitt() {
    var oin = (document.getElementById("nytt_orgnr") || {}).value;
    if (!oin) {
      setFeil("Skriv 9 siffer (orgnr).");
      return;
    }
    var t = (oin + "").replace(/\D/g, "");
    if (t.length !== 9) {
      setFeil("Org.nr skal vere 9 siffer.");
      return;
    }
    setFeil("");
    if (!data[t]) data[t] = {};
    teiknOpp();
    synkBoks();
  }

  function init() {
    feilEl = document.getElementById("feil");
    tabellKropp = document.getElementById("tabell_oppf");
    var apiInp = document.getElementById("api_grunnurl");
    if (apiInp) {
      try {
        var s = localStorage.getItem(LAGRING_API);
        if (s && !apiInp.value) apiInp.value = s;
      } catch (e) {
        /* gjev opp */
      }
      apiInp.addEventListener("change", function () {
        try {
          if (apiInp.value.trim()) localStorage.setItem(LAGRING_API, apiInp.value.trim());
        } catch (e) {
          /* gjev opp */
        }
      });
    }
    var knHent = document.getElementById("kn_hent");
    if (knHent) knHent.addEventListener("click", hentFila);
    var knSave = document.getElementById("kn_lagre");
    if (knSave) knSave.addEventListener("click", lagreTilApi);
    var knOppd = document.getElementById("kn_oppd_frå_boks");
    if (knOppd) knOppd.addEventListener("click", oppdaterFraBoks);
    var knLegg = document.getElementById("kn_legg_til");
    if (knLegg) knLegg.addEventListener("click", lagtTilEitt);
    hentFila();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
