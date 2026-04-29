/**
 * Vercel serverless: sjekk Basic-bruk, skriv manuell_status.json i GitHub-repositoriet.
 * Miljø: LAGREG_BRUKER, LAGREG_PASS, LAGREG_GITHUB_TOKEN, LAGREG_GITHUB_EIGER, LAGREG_GITHUB_NAMN,
 *        LAGREG_TILLATTE_URSPRUNG (komma, valfri — tom = lett CORS for kva opphav som helst; i prod: lås til GitHub Pages + lokal host),
 *        LAGREG_GIT_GREIN (valfri, main), LAGREG_FILAR (valfri, to stiar).
 */
const crypto = require("node:crypto");

const STANDARD_FILAR = ["data/manuell_status.json", "docs/data/manuell_status.json"];

function fårHash(tekst) {
  return crypto.createHash("sha256").update(tekst, "utf8").digest();
}

function sikreLik(a, b) {
  if (typeof a !== "string" || typeof b !== "string") return false;
  const hA = fårHash(a);
  const hB = fårHash(b);
  return crypto.timingSafeEqual(hA, hB);
}

function parseBasic(req) {
  const h = req.headers.authorization;
  if (!h || !String(h).startsWith("Basic ")) return null;
  const rå = Buffer.from(h.slice(6), "base64").toString("utf8");
  const i = rå.indexOf(":");
  if (i < 0) return null;
  return { brukar: rå.slice(0, i), pass: rå.slice(i + 1) };
}

function sjekkBrukarpass(token) {
  const b = process.env.LAGREG_BRUKER;
  const p = process.env.LAGREG_PASS;
  if (b == null || b === "" || p == null) {
    return { ok: false, feil: "Mangla LAGREG_BRUKER eller LAGREG_PASS" };
  }
  if (!token) return { ok: false, feil: "Bruk HTTP Basic (brukar:passord)" };
  if (!sikreLik(token.brukar, b) || !sikreLik(token.pass, p)) {
    return { ok: false, feil: "Feil brukar eller passord" };
  }
  return { ok: true };
}

function validerInnhald(inn) {
  if (inn === null || typeof inn !== "object" || Array.isArray(inn)) {
    return "Må vere eit objekt (orgnr → felt)";
  }
  for (const [k, v] of Object.entries(inn)) {
    if (!/^\d{9}$/.test(k)) {
      return `Ugyldig orgnr: ${k} (9 siffer)`;
    }
    if (v === null || typeof v !== "object" || Array.isArray(v)) {
      return `Ugyldig blokk for ${k}`;
    }
    if (Object.prototype.hasOwnProperty.call(v, "nu") && v.nu != null) {
      if (
        !["medlem", "utmeld", "potensiell_medlem", "ikkje_aktuell", "inaktiv_medlem"].includes(
          v.nu
        )
      ) {
        return `Ugyldig nu for ${k} (medlem, utmeld, potensiell_medlem, ikkje_aktuell, inaktiv_medlem)`;
      }
    }
    if (Object.prototype.hasOwnProperty.call(v, "skjul") && v.skjul != null) {
      if (typeof v.skjul !== "boolean") {
        return `Ugyldig skjul for ${k}`;
      }
    }
    if (Object.prototype.hasOwnProperty.call(v, "nedlagt") && v.nedlagt != null) {
      if (typeof v.nedlagt !== "boolean") {
        return `Ugyldig nedlagt for ${k}`;
      }
    }
    if (Object.prototype.hasOwnProperty.call(v, "merknad") && v.merknad != null) {
      if (typeof v.merknad !== "string") {
        return `Ugyldig merknad for ${k}`;
      }
    }
  }
  return null;
}

function tilJson(inn) {
  const sortert = Object.keys(inn)
    .sort()
    .reduce((o, n) => {
      o[n] = inn[n];
      return o;
    }, {});
  return JSON.stringify(sortert, null, 2) + "\n";
}

function filarFraMilo() {
  const r = process.env.LAGREG_FILAR;
  if (r && r.trim()) {
    return r
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
  }
  return STANDARD_FILAR;
}

function githubHeaders(kennimerke) {
  return {
    Accept: "application/vnd.github+json",
    Authorization: `Bearer ${kennimerke}`,
    "X-GitHub-Api-Version": "2022-11-28",
  };
}

function corsFor(opphav) {
  const list = (process.env.LAGREG_TILLATTE_URSPRUNG || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  if (!opphav) {
    return null;
  }
  if (list.length > 0 && !list.includes(opphav)) {
    return null;
  }
  const løyve = list.length > 0 ? opphav : opphav;
  return løyve;
}

function byggCorsHovud(lovOpphav) {
  if (!lovOpphav) return {};
  return {
    "Access-Control-Allow-Origin": lovOpphav,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Max-Age": "86400",
  };
}

function contentsUrl(eiger, namn, sti) {
  const stiKoda = sti.split("/").map(encodeURIComponent).join("/");
  return `https://api.github.com/repos/${eiger}/${namn}/contents/${stiKoda}`;
}

async function hentInnhald(kennimerke, eiger, namn, sti) {
  const u = contentsUrl(eiger, namn, sti);
  const svar = await fetch(u, { headers: githubHeaders(kennimerke) });
  if (svar.status === 404) {
    return { finst: false, sha: null };
  }
  if (!svar.ok) {
    return { feil: `GitHub les ${sti}: ${svar.status} ${await svar.text()}` };
  }
  const j = await svar.json();
  return { finst: true, sha: j.sha };
}

async function skrivFiler(kennimerke, eiger, namn, sti, innhald, sha, grein) {
  const u = contentsUrl(eiger, namn, sti);
  const b64 = Buffer.from(innhald, "utf8").toString("base64");
  const kropp = {
    message: process.env.LAGREG_GIT_MELDING || "Nett: oppdater manuell status",
    content: b64,
    branch: grein,
  };
  if (sha) {
    kropp.sha = sha;
  }
  const svar = await fetch(u, {
    method: "PUT",
    headers: { ...githubHeaders(kennimerke), "Content-Type": "application/json" },
    body: JSON.stringify(kropp),
  });
  if (!svar.ok) {
    return { feil: `GitHub skriv ${sti}: ${svar.status} ${await svar.text()}` };
  }
  return {};
}

function lesKropp(req) {
  return new Promise((resolve, reject) => {
    const biter = [];
    req.on("data", (b) => biter.push(b));
    req.on("end", () => {
      try {
        const s = Buffer.concat(biter).toString("utf8");
        resolve(s ? JSON.parse(s) : {});
      } catch (e) {
        reject(new Error("Ugyldig JSON i kropp"));
      }
    });
    req.on("error", reject);
  });
}

module.exports = async (req, res) => {
  const opphav = req.headers.origin;
  const lov = opphav ? corsFor(opphav) : null;
  if (opphav && !lov) {
    res.statusCode = 403;
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.end(
      JSON.stringify({
        feil: "CORS: opphav ikkje tillate. Set LAGREG_TILLATTE_URSPRUNG (komma) i Vercel med full https://-URL for GitHub Pages + ev. lokal førehandsvising.",
      })
    );
    return;
  }
  const c = byggCorsHovud(lov);
  Object.assign(c, { "Content-Type": "application/json; charset=utf-8" });
  for (const [k, v] of Object.entries(c)) {
    res.setHeader(k, v);
  }

  if (req.method === "OPTIONS") {
    res.statusCode = 204;
    res.end();
    return;
  }

  if (req.method !== "POST") {
    res.statusCode = 405;
    res.end(JSON.stringify({ feil: "Bruk POST" }));
    return;
  }

  const auth = sjekkBrukarpass(parseBasic(req));
  if (!auth.ok) {
    res.setHeader("WWW-Authenticate", 'Basic realm="lagsregisteret"');
    res.statusCode = 401;
    res.end(JSON.stringify({ feil: auth.feil }));
    return;
  }

  let kropp;
  try {
    kropp = await lesKropp(req);
  } catch (e) {
    res.statusCode = 400;
    res.end(JSON.stringify({ feil: e.message || "Kunne ikkje lesa kropp" }));
    return;
  }

  if (kropp == null || typeof kropp.manuell_status === "undefined") {
    res.statusCode = 400;
    res.end(
      JSON.stringify({ feil: "Kropp skal innehalde nøkkelen manuell_status" })
    );
    return;
  }

  const fe = validerInnhald(kropp.manuell_status);
  if (fe) {
    res.statusCode = 400;
    res.end(JSON.stringify({ feil: fe }));
    return;
  }

  const kenn = process.env.LAGREG_GITHUB_TOKEN;
  const eiger = process.env.LAGREG_GITHUB_EIGER;
  const namn = process.env.LAGREG_GITHUB_NAMN;
  if (!kenn || !eiger || !namn) {
    res.statusCode = 500;
    res.end(
      JSON.stringify({
        feil: "Mangla LAGREG_GITHUB_TOKEN, LAGREG_GITHUB_EIGER eller LAGREG_GITHUB_NAMN",
      })
    );
    return;
  }

  const tekst = tilJson(kropp.manuell_status);
  if (Buffer.byteLength(tekst, "utf8") > 1.5 * 1024 * 1024) {
    res.statusCode = 400;
    res.end(JSON.stringify({ feil: "Register for stort" }));
    return;
  }

  const grein = process.env.LAGREG_GIT_GREIN || "main";
  const stier = filarFraMilo();
  for (const sti of stier) {
    const meta = await hentInnhald(kenn, eiger, namn, sti);
    if (meta.feil) {
      res.statusCode = 500;
      res.end(JSON.stringify({ feil: meta.feil }));
      return;
    }
    const ut = await skrivFiler(kenn, eiger, namn, sti, tekst, meta.sha, grein);
    if (ut.feil) {
      res.statusCode = 500;
      res.end(JSON.stringify({ feil: ut.feil }));
      return;
    }
  }
  res.statusCode = 200;
  res.end(JSON.stringify({ ok: true, stier, grein }));
};
