/* Fuzzy Scouting — interface web (sans dépendance, sans étape de build).
 *
 * Toute la logique floue reste côté serveur : cette page ne fait qu'appeler l'API
 * (/rankings, /evaluations, /variables, /knowledge…) et présenter les réponses.
 */
"use strict";

// ----------------------------------------------------------------- utilitaires

const $ = (sel, root = document) => root.querySelector(sel);
const esc = (s) =>
  String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const nf = (v, d = 1) =>
  v == null || Number.isNaN(Number(v))
    ? "–"
    : Number(v).toLocaleString("fr-FR", { minimumFractionDigits: d, maximumFractionDigits: d });
const cap = (s) => (s ? s[0].toUpperCase() + s.slice(1) : "");
const debounce = (fn, ms) => {
  let t;
  return (...a) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...a), ms);
  };
};

async function api(path, body) {
  const res = await fetch(
    path,
    body && { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) },
  );
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const d = data && data.detail;
    throw new Error(typeof d === "string" ? d : d ? JSON.stringify(d) : `Erreur ${res.status}`);
  }
  return data;
}

const store = {
  get(key, fallback) {
    try {
      return JSON.parse(localStorage.getItem("fuzzyscout." + key)) ?? fallback;
    } catch {
      return fallback;
    }
  },
  set(key, value) {
    try {
      localStorage.setItem("fuzzyscout." + key, JSON.stringify(value));
    } catch {
      /* stockage indisponible : la page fonctionne sans persistance */
    }
  },
};

function toast(message) {
  const el = $("#toast");
  el.textContent = message;
  el.hidden = false;
  clearTimeout(toast.t);
  toast.t = setTimeout(() => (el.hidden = true), 2600);
}

// ----------------------------------------------------------------- état

const MAX_COMPARE = 3;
const AGE_MAX = 40;
const SCORES = ["technique", "physique", "profil"];

const S = {
  positions: [],
  players: [],
  byId: {},
  vars: {},
  knowledge: {}, // poste -> résumé (entrées requises, étapes)
  kbDetail: {}, // poste -> règles complètes (chargé à la demande)
  levels: [], // termes ordonnés de la variable « aptitude »
  valueMax: 50,
  search: {
    position: "",
    maxAge: AGE_MAX,
    maxValue: null,
    minMinutes: 0,
    nationality: "",
    naturalOnly: false,
    q: "",
    sort: { key: "rang", dir: 1 },
    report: null,
    error: "",
  },
  shortlist: store.get("shortlist", []), // [{id, position}]
  compare: store.get("compare", []), // [id]
  comparePos: "",
  sim: { position: "", base: "", values: {}, result: null, error: "" },
  rulesPos: "",
  sheet: { id: "", position: "" },
};

const posLabel = (code) => (S.positions.find((p) => p.code === code) || {}).libelle || code || "—";
const varLabel = (name) => (S.vars[name] && S.vars[name].description) || name;
const varUnit = (name) => (S.vars[name] && S.vars[name].unite) || "";
const shortVar = (name) =>
  name
    .replace(/_p90$/, " /90")
    .replace(/_pct$/, " %")
    .replace(/_kmh$/, " km/h")
    .replace(/_cm$/, "")
    .replace(/_/g, " ");
const decimals = (name) => {
  const v = S.vars[name];
  if (!v) return 1;
  const w = v.univers[1] - v.univers[0];
  return w <= 5 ? 2 : w <= 30 ? 1 : 0;
};
/** Valeur mesurée : entiers sans décimales, sinon la précision adaptée à l'échelle. */
const fmtVal = (name, v) => nf(v, Number.isInteger(v) || !(name in S.vars) ? (Number.isInteger(v) ? 0 : 1) : decimals(name));
const stepOf = (name) => {
  const v = S.vars[name];
  const w = v.univers[1] - v.univers[0];
  return w <= 5 ? 0.01 : w <= 30 ? 0.1 : w <= 300 ? 1 : 10;
};

/** Classe de couleur d'un niveau (faible → excellente) : rampe ordinale à une teinte. */
function lv(label) {
  const i = S.levels.indexOf(label);
  if (i < 0) return "lv1";
  const n = Math.max(1, S.levels.length - 1);
  return "lv" + Math.round((i / n) * 3);
}
const levelChip = (label) => `<span class="chip"><i class="dot ${lv(label)}"></i>${esc(label)}</span>`;
const meter = (value, label, cls = "") =>
  `<span class="meter ${cls}" role="img" aria-label="${nf(value)} sur 100"><i class="${lv(label)}" style="width:${Math.max(0, Math.min(100, value))}%"></i></span>`;

const isStarred = (id, position) => S.shortlist.some((s) => s.id === id && s.position === position);

function updateCounts() {
  $("#star-count").textContent = S.shortlist.length || "";
  $("#cmp-count").textContent = S.compare.length || "";
}

// ----------------------------------------------------------------- graphiques

/** Courbes d'appartenance d'une variable, avec repère vertical sur la valeur mesurée. */
function mfChart(variable, value, { w = 240, h = 54, axis = false } = {}) {
  const [lo, hi] = variable.univers;
  const pad = { l: 3, r: 3, t: 5, b: axis ? 18 : 3 };
  const X = (x) => pad.l + ((x - lo) / (hi - lo)) * (w - pad.l - pad.r);
  const Y = (m) => pad.t + (1 - m) * (h - pad.t - pad.b);
  const paths = variable.termes
    .map(
      (t, i) =>
        `<path class="s${(i % 4) + 1}" d="M${t.points.map(([x, m]) => `${X(x).toFixed(1)},${Y(m).toFixed(1)}`).join("L")}"/>`,
    )
    .join("");
  let marker = "";
  if (value != null) {
    const x = X(Math.min(hi, Math.max(lo, value))).toFixed(1);
    marker = `<line class="mark" x1="${x}" x2="${x}" y1="${pad.t - 3}" y2="${Y(0)}"/>`;
  }
  let ticks = "";
  if (axis) {
    ticks = [lo, (lo + hi) / 2, hi]
      .map(
        (x, i) =>
          `<text x="${X(x)}" y="${h - 4}" text-anchor="${["start", "middle", "end"][i]}">${x.toLocaleString("fr-FR", { maximumFractionDigits: 2 })}</text>`,
      )
      .join("");
  }
  return `<svg class="mf" viewBox="0 0 ${w} ${h}" ${axis ? "" : 'preserveAspectRatio="none"'} data-var="${esc(variable.nom)}" role="img" aria-label="Fonctions d'appartenance de ${esc(variable.description || variable.nom)}">
    <line class="base" x1="${pad.l}" x2="${w - pad.r}" y1="${Y(0)}" y2="${Y(0)}"/>${paths}${marker}
    <line class="cross" x1="0" x2="0" y1="${pad.t - 3}" y2="${Y(0)}" visibility="hidden"/>${ticks}</svg>`;
}

function interp(points, x) {
  if (x <= points[0][0]) return points[0][1];
  for (let i = 1; i < points.length; i++) {
    const [x1, m1] = points[i];
    if (x <= x1) {
      const [x0, m0] = points[i - 1];
      return x1 === x0 ? m1 : m0 + ((m1 - m0) * (x - x0)) / (x1 - x0);
    }
  }
  return points[points.length - 1][1];
}

/** Degrés d'appartenance sous forme de pastilles (servent aussi de légende aux courbes). */
function degreeChips(variable, degrees) {
  return variable.termes
    .map((t, i) => {
      const d = degrees ? degrees[t.label] : null;
      const off = d != null && d <= 0;
      return `<span class="chip ${off ? "off" : ""}"><i class="swatch s${(i % 4) + 1}"></i>${esc(t.label)}${d != null ? ` <b>${nf(d, 2)}</b>` : ""}</span>`;
    })
    .join("");
}

// Survol des courbes : réticule + infobulle listant le degré de chaque terme.
document.addEventListener("mousemove", (e) => {
  const svg = e.target.closest && e.target.closest("svg.mf");
  const tip = $("#tip");
  if (!svg) {
    if (!tip.hidden && tip.dataset.kind === "mf") tip.hidden = true;
    document.querySelectorAll("svg.mf .cross[visibility=visible]").forEach((c) => c.setAttribute("visibility", "hidden"));
    return;
  }
  const variable = S.vars[svg.dataset.var];
  if (!variable) return;
  const box = svg.getBoundingClientRect();
  const vbW = svg.viewBox.baseVal.width;
  const ratio = Math.min(1, Math.max(0, ((e.clientX - box.left) / box.width - 3 / vbW) / (1 - 6 / vbW)));
  const [lo, hi] = variable.univers;
  const x = lo + ratio * (hi - lo);
  const cross = svg.querySelector(".cross");
  const cx = 3 + ratio * (vbW - 6);
  cross.setAttribute("x1", cx);
  cross.setAttribute("x2", cx);
  cross.setAttribute("visibility", "visible");
  tip.dataset.kind = "mf";
  tip.innerHTML =
    `<strong>${nf(x, decimals(variable.nom))} ${esc(variable.unite)}</strong>` +
    variable.termes
      .map((t, i) => `<span><i class="swatch s${(i % 4) + 1}"></i>${esc(t.label)} <b>${nf(interp(t.points, x), 2)}</b></span>`)
      .join("");
  tip.hidden = false;
  const tw = tip.offsetWidth;
  tip.style.left = Math.min(window.innerWidth - tw - 8, e.clientX + 14) + "px";
  tip.style.top = e.clientY + 14 + "px";
});

/** Règle rendue lisible : mots-clés atténués, variables remplacées par un libellé court. */
function fmtRule(text) {
  return text
    .replace(/N'EST PAS/g, "N'EST_PAS")
    .split(/(\s+|[()])/)
    .map((tok) => {
      if (/^(SI|ALORS|ET|OU|NON)$/.test(tok)) return `<span class="kw">${tok}</span>`;
      if (tok === "EST") return "est";
      if (tok === "N'EST_PAS") return "<em>n'est pas</em>";
      if (S.vars[tok]) return `<span class="var" title="${esc(varLabel(tok))}">${esc(shortVar(tok))}</span>`;
      return esc(tok);
    })
    .join("");
}

// ----------------------------------------------------------------- fragments communs

function positionSelect(id, value, label = "Poste évalué") {
  return `<label class="field"><span>${label}</span><select id="${id}">${S.positions
    .map((p) => `<option value="${esc(p.code)}" ${p.code === value ? "selected" : ""}>${esc(p.libelle)}</option>`)
    .join("")}</select></label>`;
}

function playerMeta(p) {
  return [p.club, p.nationalite, p.poste && posLabel(p.poste)].filter(Boolean).map(esc).join(" · ");
}

function scoreTiles(ev) {
  return `<div class="tiles">${SCORES.filter((k) => k in ev.scores)
    .map(
      (k) => `<div class="tile"><span class="tile-label">${cap(k)}</span>
        <span class="tile-value">${nf(ev.scores[k])}</span>${levelChip(ev.labels[k])}${meter(ev.scores[k], ev.labels[k])}</div>`,
    )
    .join("")}</div>`;
}

function hero(ev) {
  return `<div class="hero">
    <div><span class="hero-label">Aptitude — ${esc(posLabel(ev.poste))}</span>
      <div class="hero-num">${nf(ev.aptitude)}<small>/100</small></div></div>
    <div class="hero-side">${levelChip(ev.aptitude_label)}${meter(ev.aptitude, ev.aptitude_label, "big")}</div>
  </div>`;
}

/** Explication étape par étape : fuzzification des entrées puis règles déclenchées. */
function stagesHtml(etapes, { inputs = true, open = 1, scores = {} } = {}) {
  return etapes
    .map((st, idx) => {
      const out = Object.keys(st.sorties)[0];
      const outVar = S.vars[out];
      const label = outVar
        ? outVar.termes.reduce((a, t) => (st.sorties_floues[out][t.label] > st.sorties_floues[out][a] ? t.label : a), outVar.termes[0].label)
        : "";
      const rows = Object.entries(st.entrees)
        .map(([name, value]) => {
          const v = S.vars[name];
          if (!v) return "";
          return `<div class="in-row">
            <div class="in-head"><span>${esc(varLabel(name))}</span><b>${fmtVal(name, value)} <small>${esc(v.unite)}</small></b></div>
            ${mfChart(v, value)}
            <div class="chips">${degreeChips(v, st.entrees_floues[name])}</div></div>`;
        })
        .join("");
      const rules = st.regles_declenchees.length
        ? st.regles_declenchees
            .map(
              (r) => `<li class="rule">
              <div class="rule-force" title="Force d'activation de la règle"><b>${nf(r.force, 2)}</b>
                <span class="meter"><i class="acc" style="width:${r.force * 100}%"></i></span></div>
              <div><p class="rule-text"><span class="rule-id">${esc(r.id)}</span> ${fmtRule(r.regle)}</p>
                ${r.description ? `<p class="rule-desc">${esc(r.description)}</p>` : ""}</div></li>`,
            )
            .join("")
        : `<li class="muted">Aucune règle déclenchée.</li>`;
      const more = st.nb_regles_declenchees - st.regles_declenchees.length;
      return `<details class="stage" ${idx < open || idx === etapes.length - 1 ? "open" : ""}>
        <summary><span class="stage-name">${cap(out)}</span>
          <span class="stage-out"><b>${nf(scores[out] ?? st.sorties[out])}</b>${label ? levelChip(label) : ""}</span></summary>
        ${inputs ? `<h4>Ce que disent les statistiques</h4><div class="in-grid">${rows}</div>` : ""}
        <h4>Règles déclenchées <small>${st.nb_regles_declenchees} sur ${st.nb_regles}</small></h4>
        <ol class="rules">${rules}</ol>
        ${more > 0 ? `<p class="muted small">+ ${more} règle(s) de moindre force non affichée(s).</p>` : ""}
        ${st.avertissements.map((w) => `<p class="warn">${esc(w)}</p>`).join("")}
      </details>`;
    })
    .join("");
}

// ----------------------------------------------------------------- vue : recherche

function renderSearch() {
  const f = S.search;
  const nats = [...new Set(S.players.map((p) => p.nationalite).filter(Boolean))].sort();
  $("#view").innerHTML = `
    <section class="page-head">
      <h1>Trouver un joueur</h1>
      <p>Choisissez un poste : chaque candidat est noté par les règles floues de ce poste, puis classé. Cliquez sur un joueur pour comprendre son verdict.</p>
      <div class="pos-picker" role="radiogroup" aria-label="Poste recherché">${S.positions
        .map(
          (p) => `<button role="radio" aria-checked="${p.code === f.position}" data-act="pos" data-pos="${esc(p.code)}">
            <strong>${esc(p.libelle)}</strong><span>${esc(p.description)}</span></button>`,
        )
        .join("")}</div>
    </section>
    <div class="split">
      <aside class="panel filters" aria-label="Filtres">
        <div class="panel-head"><h2>Contraintes</h2><button class="link" data-act="reset-filters">Réinitialiser</button></div>
        <label class="field"><span>Budget maximum <output id="o-value"></output></span>
          <input type="range" id="f-value" min="0" max="${S.valueMax}" step="0.5" value="${f.maxValue ?? S.valueMax}"></label>
        <label class="field"><span>Âge maximum <output id="o-age"></output></span>
          <input type="range" id="f-age" min="17" max="${AGE_MAX}" step="1" value="${f.maxAge}"></label>
        <label class="field"><span>Temps de jeu minimum <output id="o-min"></output></span>
          <input type="range" id="f-min" min="0" max="3000" step="100" value="${f.minMinutes}"></label>
        <label class="field"><span>Nationalité</span>
          <select id="f-nat"><option value="">Toutes</option>${nats
            .map((n) => `<option ${n === f.nationality ? "selected" : ""}>${esc(n)}</option>`)
            .join("")}</select></label>
        <label class="check"><input type="checkbox" id="f-natural" ${f.naturalOnly ? "checked" : ""}>
          <span>Poste naturel uniquement</span></label>
        <p class="hint">Les contraintes sont strictes (un joueur est classé ou exclu, avec la raison). Les préférences vagues — « rapide », « jeune et déjà titulaire » — sont portées par les règles floues.</p>
      </aside>
      <section class="panel results" aria-live="polite">
        <div class="panel-head">
          <div id="summary"></div>
          <input type="search" id="f-q" placeholder="Filtrer par nom ou club…" value="${esc(f.q)}" aria-label="Filtrer par nom ou club">
        </div>
        <div id="results"><p class="loading">Calcul du classement…</p></div>
      </section>
    </div>`;
  syncFilterOutputs();
  runSearch();
}

function syncFilterOutputs() {
  const f = S.search;
  $("#o-value").textContent = f.maxValue == null ? "Sans limite" : `${nf(f.maxValue)} M€`;
  $("#o-age").textContent = f.maxAge >= AGE_MAX ? "Sans limite" : `${f.maxAge} ans`;
  $("#o-min").textContent = f.minMinutes ? `${nf(f.minMinutes, 0)} min` : "Aucun";
}

let searchSeq = 0;
async function runSearch() {
  const f = S.search;
  const seq = ++searchSeq;
  const body = { position: f.position, natural_position_only: f.naturalOnly };
  if (f.maxAge < AGE_MAX) body.max_age = f.maxAge;
  if (f.maxValue != null) body.max_market_value = f.maxValue;
  if (f.minMinutes) body.min_minutes = f.minMinutes;
  if (f.nationality) body.nationality = f.nationality;
  try {
    const report = await api("/rankings", body);
    if (seq !== searchSeq) return;
    f.report = report;
    f.error = "";
  } catch (err) {
    if (seq !== searchSeq) return;
    f.report = null;
    f.error = err.message;
  }
  renderResults();
}
const runSearchSoon = debounce(runSearch, 160);

const SORTS = {
  rang: (e) => e.rang,
  nom: (e) => e.joueur.nom.toLocaleLowerCase("fr"),
  age: (e) => e.joueur.attributs.age ?? Infinity,
  valeur: (e) => e.joueur.attributs.valeur_marche_meur ?? Infinity,
  aptitude: (e) => e.aptitude,
  technique: (e) => e.scores.technique ?? -1,
  physique: (e) => e.scores.physique ?? -1,
  profil: (e) => e.scores.profil ?? -1,
};

function renderResults() {
  const f = S.search;
  const box = $("#results");
  if (!box) return;
  if (f.error) {
    $("#summary").innerHTML = "";
    box.innerHTML = `<p class="error">${esc(f.error)}</p>`;
    return;
  }
  const r = f.report;
  if (!r) return;
  $("#summary").innerHTML = `<h2>${esc(r.poste.libelle)}</h2>
    <p class="muted"><b>${r.classes}</b> classé(s) sur ${r.candidats} candidats · ${r.exclus.length} exclu(s)</p>`;
  const q = f.q.trim().toLocaleLowerCase("fr");
  let rows = r.classement.filter(
    (e) => !q || e.joueur.nom.toLocaleLowerCase("fr").includes(q) || e.joueur.club.toLocaleLowerCase("fr").includes(q),
  );
  const key = SORTS[f.sort.key];
  rows = [...rows].sort((a, b) => (key(a) < key(b) ? -1 : key(a) > key(b) ? 1 : 0) * f.sort.dir);
  const th = (k, label, cls = "") =>
    `<th class="${cls}" aria-sort="${f.sort.key === k ? (f.sort.dir > 0 ? "ascending" : "descending") : "none"}">
      <button data-act="sort" data-key="${k}">${label}<span class="arrow">${f.sort.key === k ? (f.sort.dir > 0 ? "▲" : "▼") : ""}</span></button></th>`;
  const table = rows.length
    ? `<div class="table-wrap"><table class="rank">
      <thead><tr>${th("rang", "#")}${th("nom", "Joueur")}${th("age", "Âge", "num")}${th("valeur", "Valeur", "num")}
        ${th("aptitude", "Aptitude")}${th("technique", "Tech.", "sub")}${th("physique", "Phys.", "sub")}${th("profil", "Profil", "sub")}
        <th><span class="sr">Actions</span></th></tr></thead>
      <tbody>${rows
        .map((e) => {
          const p = e.joueur;
          const starred = isStarred(p.id, r.poste.code);
          const compared = S.compare.includes(p.id);
          return `<tr data-act="open" data-id="${esc(p.id)}" data-pos="${esc(r.poste.code)}" tabindex="0">
            <td class="rk">${e.rang}</td>
            <td><strong>${esc(p.nom)}</strong><span class="meta">${playerMeta(p)}</span></td>
            <td class="num">${nf(p.attributs.age, 0)}</td>
            <td class="num">${p.attributs.valeur_marche_meur != null ? nf(p.attributs.valeur_marche_meur) + " M€" : "–"}</td>
            <td class="apt"><b>${nf(e.aptitude)}</b>${levelChip(e.aptitude_label)}${meter(e.aptitude, e.aptitude_label)}</td>
            ${SCORES.map((k) => `<td class="sub"><span>${nf(e.scores[k], 0)}</span>${meter(e.scores[k] ?? 0, e.labels[k])}</td>`).join("")}
            <td class="acts">
              <button class="icon ${starred ? "on" : ""}" data-act="star" data-id="${esc(p.id)}" data-pos="${esc(r.poste.code)}"
                aria-pressed="${starred}" title="${starred ? "Retirer de la sélection" : "Ajouter à la sélection"}">${starred ? "★" : "☆"}</button>
              <button class="icon ${compared ? "on" : ""}" data-act="cmp" data-id="${esc(p.id)}" aria-pressed="${compared}"
                title="${compared ? "Retirer de la comparaison" : "Comparer"}">⇄</button>
            </td></tr>`;
        })
        .join("")}</tbody></table></div>`
    : `<div class="empty"><strong>Aucun joueur ne satisfait ces contraintes.</strong>
        <p>Assouplissez le budget, l'âge ou le temps de jeu — la liste des exclus ci-dessous indique ce qui bloque.</p></div>`;
  const skipped = r.exclus.length
    ? `<details class="skipped"><summary>${r.exclus.length} joueur(s) exclu(s) — voir pourquoi</summary><ul>${r.exclus
        .map((s) => `<li><b>${esc(s.nom)}</b> <span class="muted">${esc(s.raison)}</span></li>`)
        .join("")}</ul></details>`
    : "";
  box.innerHTML = table + skipped;
}

// ----------------------------------------------------------------- fiche joueur

async function openSheet(id, position) {
  const sheet = $("#sheet");
  S.sheet = { id, position };
  const p = S.byId[id];
  if (!p) return;
  const a = p.attributs;
  const fact = (label, value) => `<div><dt>${label}</dt><dd>${value}</dd></div>`;
  sheet.innerHTML = `<div class="sheet-in">
    <header class="sheet-head">
      <div><h2>${esc(p.nom)}</h2><p class="muted">${playerMeta(p)} · ${esc(p.id)}</p></div>
      <button class="icon" data-act="close" aria-label="Fermer la fiche">✕</button>
    </header>
    <dl class="facts">
      ${fact("Âge", a.age != null ? nf(a.age, 0) + " ans" : "–")}
      ${fact("Taille", a.taille_cm != null ? nf(a.taille_cm, 0) + " cm" : "–")}
      ${fact("Valeur", a.valeur_marche_meur != null ? nf(a.valeur_marche_meur) + " M€" : "–")}
      ${fact("Contrat", a.contrat_mois_restants != null ? nf(a.contrat_mois_restants, 0) + " mois" : "–")}
      ${fact("Temps de jeu", a.minutes_jouees != null ? nf(a.minutes_jouees, 0) + " min" : "–")}
      ${fact("Blessures", a.blessures_jours != null ? nf(a.blessures_jours, 0) + " j" : "–")}
    </dl>
    <div class="sheet-bar">${positionSelect("sheet-pos", position)}
      <div class="btns" id="sheet-btns"></div></div>
    <div id="sheet-body"><p class="loading">Évaluation…</p></div></div>`;
  if (!sheet.open) sheet.showModal();
  renderSheetButtons();
  const body = $("#sheet-body");
  try {
    const ev = await api("/evaluations", { position, player_id: id, trace: true });
    if (S.sheet.id !== id || S.sheet.position !== position) return;
    body.innerHTML = `${hero(ev)}${scoreTiles(ev)}
      ${ev.avertissements.map((w) => `<p class="warn">${esc(w)}</p>`).join("")}
      <h3>Pourquoi ce verdict ?</h3>
      <p class="muted small">Chaque étape transforme les statistiques en degrés d'appartenance (0 à 1), applique ses règles, puis résume le résultat en une note. La dernière étape combine les trois notes.</p>
      ${stagesHtml(ev.etapes, { scores: ev.scores })}`;
  } catch (err) {
    if (S.sheet.id !== id || S.sheet.position !== position) return;
    body.innerHTML = `<div class="empty"><strong>Évaluation impossible à ce poste.</strong><p>${esc(err.message)}</p>
      <p>Essayez un autre poste, ou complétez les statistiques dans le simulateur.</p></div>`;
  }
}

function renderSheetButtons() {
  const { id, position } = S.sheet;
  const box = $("#sheet-btns");
  if (!box) return;
  const starred = isStarred(id, position);
  const compared = S.compare.includes(id);
  box.innerHTML = `
    <button class="btn ${starred ? "on" : ""}" data-act="star" data-id="${esc(id)}" data-pos="${esc(position)}" aria-pressed="${starred}">${starred ? "★ Dans la sélection" : "☆ Sélectionner"}</button>
    <button class="btn ${compared ? "on" : ""}" data-act="cmp" data-id="${esc(id)}" aria-pressed="${compared}">⇄ ${compared ? "En comparaison" : "Comparer"}</button>
    <button class="btn" data-act="simulate" data-id="${esc(id)}" data-pos="${esc(position)}">Et si… ?</button>`;
}

// ----------------------------------------------------------------- vue : comparer

async function renderCompare() {
  const view = $("#view");
  const ids = S.compare.filter((id) => S.byId[id]);
  const options = S.players
    .filter((p) => !ids.includes(p.id))
    .map((p) => `<option value="${esc(p.id)}">${esc(p.nom)} — ${esc(posLabel(p.poste))}</option>`)
    .join("");
  view.innerHTML = `
    <section class="page-head"><h1>Comparer des joueurs</h1>
      <p>Jusqu'à ${MAX_COMPARE} joueurs côte à côte, évalués au même poste par les mêmes règles.</p></section>
    <div class="toolbar panel">
      ${positionSelect("cmp-pos", S.comparePos)}
      <label class="field"><span>Ajouter un joueur</span>
        <select id="cmp-add" ${ids.length >= MAX_COMPARE ? "disabled" : ""}><option value="">Choisir…</option>${options}</select></label>
      <div class="chips grow">${ids
        .map(
          (id, i) => `<span class="chip big"><i class="swatch s${i + 1}"></i>${esc(S.byId[id].nom)}
            <button class="x" data-act="cmp" data-id="${esc(id)}" aria-label="Retirer ${esc(S.byId[id].nom)}">✕</button></span>`,
        )
        .join("")}</div>
    </div>
    <div id="cmp-body">${ids.length ? `<p class="loading">Évaluation…</p>` : `<div class="empty panel"><strong>Aucun joueur à comparer.</strong>
      <p>Ajoutez-en ci-dessus, ou utilisez le bouton ⇄ dans le classement.</p></div>`}</div>`;
  if (!ids.length) return;
  const pos = S.comparePos;
  const evals = await Promise.all(
    ids.map((id) => api("/evaluations", { position: pos, player_id: id }).catch((err) => ({ error: err.message }))),
  );
  if (!$("#cmp-body") || pos !== S.comparePos) return;
  const keys = ["aptitude", ...SCORES];
  const bars = keys
    .map(
      (k) => `<div class="cmp-group"><h4>${cap(k)}</h4>${evals
        .map((ev, i) =>
          ev.error
            ? `<div class="cmp-bar"><span class="cmp-name">${esc(S.byId[ids[i]].nom)}</span><span class="muted small">non évaluable</span></div>`
            : `<div class="cmp-bar" title="${esc(S.byId[ids[i]].nom)} — ${cap(k)} : ${nf(ev.scores[k])} (${esc(ev.labels[k])})">
                <span class="cmp-name">${esc(S.byId[ids[i]].nom)}</span>
                <span class="meter"><i class="swatch s${i + 1}" style="width:${ev.scores[k]}%"></i></span>
                <b>${nf(ev.scores[k])}</b><span class="muted small">${esc(ev.labels[k])}</span></div>`,
        )
        .join("")}</div>`,
    )
    .join("");
  const required = (S.knowledge[pos] || { entrees_requises: [] }).entrees_requises;
  const extra = ["valeur_marche_meur", "contrat_mois_restants"];
  const statRow = (name, label, unit) =>
    `<tr><th scope="row">${esc(label)} <small>${esc(unit)}</small></th>${ids
      .map((id) => {
        const v = S.byId[id].attributs[name];
        return `<td class="num ${v == null ? "muted" : ""}">${v == null ? "manquant" : fmtVal(name, v)}</td>`;
      })
      .join("")}</tr>`;
  $("#cmp-body").innerHTML = `
    ${evals.map((ev, i) => (ev.error ? `<p class="warn"><b>${esc(S.byId[ids[i]].nom)}</b> : ${esc(ev.error)}</p>` : "")).join("")}
    <div class="split even">
      <section class="panel"><h2>Notes au poste « ${esc(posLabel(pos))} »</h2><div class="cmp-chart">${bars}</div></section>
      <section class="panel"><h2>Statistiques utilisées par les règles</h2>
        <div class="table-wrap"><table class="stats"><thead><tr><th></th>${ids
          .map((id, i) => `<th class="num"><i class="swatch s${i + 1}"></i> ${esc(S.byId[id].nom)}</th>`)
          .join("")}</tr></thead><tbody>
          ${statRow("valeur_marche_meur", "Valeur marchande", "M€")}${statRow("contrat_mois_restants", "Contrat restant", "mois")}
          ${required.filter((n) => !extra.includes(n)).map((n) => statRow(n, varLabel(n), varUnit(n))).join("")}
        </tbody></table></div></section>
    </div>`;
}

// ----------------------------------------------------------------- vue : simulateur

function simInit(position, base) {
  const sim = S.sim;
  const player = S.byId[base];
  const values = {};
  for (const name of S.knowledge[position].entrees_requises) {
    const v = S.vars[name];
    const fallback = sim.values[name] ?? (v.univers[0] + v.univers[1]) / 2;
    const raw = player && player.attributs[name] != null ? player.attributs[name] : fallback;
    values[name] = Math.min(v.univers[1], Math.max(v.univers[0], raw));
  }
  Object.assign(sim, { position, base: player ? base : "", values, result: null, error: "" });
}

function renderSim() {
  const sim = S.sim;
  const kb = S.knowledge[sim.position];
  const player = S.byId[sim.base];
  const produced = new Set();
  const seen = new Set();
  const groups = kb.etapes
    .map((st) => {
      const names = st.entrees.filter((n) => !produced.has(n) && !seen.has(n));
      names.forEach((n) => seen.add(n));
      st.sorties.forEach((n) => produced.add(n));
      if (!names.length) return "";
      return `<section class="panel sim-group"><h2>${cap(st.sorties[0])}</h2>${names
        .map((name) => {
          const v = S.vars[name];
          const missing = player && player.attributs[name] == null;
          return `<div class="sim-row">
            <label for="sim-${esc(name)}"><span>${esc(varLabel(name))}${missing ? ` <em class="muted small">(valeur par défaut)</em>` : ""}</span>
              <output id="simo-${esc(name)}">${fmtVal(name, sim.values[name])} <small>${esc(v.unite)}</small></output></label>
            <input type="range" id="sim-${esc(name)}" data-sim="${esc(name)}" min="${v.univers[0]}" max="${v.univers[1]}"
              step="${stepOf(name)}" value="${sim.values[name]}">
            <div class="chips" id="simd-${esc(name)}">${degreeChips(v, null)}</div></div>`;
        })
        .join("")}</section>`;
    })
    .join("");
  $("#view").innerHTML = `
    <section class="page-head"><h1>Simulateur « et si… ? »</h1>
      <p>Déplacez les curseurs pour évaluer un candidat hors référentiel, ou voir ce qu'il manque à un joueur pour changer de catégorie. Le verdict se met à jour en direct.</p></section>
    <div class="toolbar panel">
      ${positionSelect("sim-pos", sim.position)}
      <label class="field"><span>Partir d'un joueur</span><select id="sim-base"><option value="">Aucun (milieu des échelles)</option>${S.players
        .map((p) => `<option value="${esc(p.id)}" ${p.id === sim.base ? "selected" : ""}>${esc(p.nom)} — ${esc(posLabel(p.poste))}</option>`)
        .join("")}</select></label>
      <button class="btn" data-act="sim-reset">Réinitialiser</button>
    </div>
    <div class="split sim">
      <div class="sim-inputs">${groups}</div>
      <section class="panel sim-result" aria-live="polite"><div id="sim-out"><p class="loading">Évaluation…</p></div></section>
    </div>`;
  evalSim();
}

let simSeq = 0;
async function evalSim() {
  const sim = S.sim;
  const seq = ++simSeq;
  const player = S.byId[sim.base];
  try {
    const ev = await api("/evaluations/ad-hoc", {
      position: sim.position,
      attributes: sim.values,
      name: player ? `${player.nom} (simulé)` : "Candidat simulé",
      trace: true,
    });
    if (seq !== simSeq) return;
    sim.result = ev;
    sim.error = "";
  } catch (err) {
    if (seq !== simSeq) return;
    sim.result = null;
    sim.error = err.message;
  }
  const out = $("#sim-out");
  if (!out) return;
  if (sim.error) {
    out.innerHTML = `<p class="error">${esc(sim.error)}</p>`;
    return;
  }
  const ev = sim.result;
  for (const st of ev.etapes) {
    for (const [name, degrees] of Object.entries(st.entrees_floues)) {
      const el = document.getElementById("simd-" + name);
      if (el) el.innerHTML = degreeChips(S.vars[name], degrees);
    }
  }
  const openState = [...out.querySelectorAll("details.stage")].map((d) => d.open);
  out.innerHTML = `<p class="muted small">${esc(ev.joueur.nom)}</p>${hero(ev)}${scoreTiles(ev)}
    ${ev.avertissements.map((w) => `<p class="warn">${esc(w)}</p>`).join("")}
    <h3>Règles à l'œuvre</h3>${stagesHtml(ev.etapes, { inputs: false, open: 0, scores: ev.scores })}`;
  if (openState.length) out.querySelectorAll("details.stage").forEach((d, i) => (d.open = openState[i] ?? d.open));
}
const evalSimSoon = debounce(evalSim, 90);

// ----------------------------------------------------------------- vue : règles

async function renderRules() {
  const view = $("#view");
  const pos = S.rulesPos;
  view.innerHTML = `
    <section class="page-head"><h1>Base de règles</h1>
      <p>Le savoir-faire du recruteur, écrit en clair. Chaque poste enchaîne quatre petits systèmes flous : technique, physique, profil, puis leur agrégation en aptitude.</p></section>
    <div class="toolbar panel">${positionSelect("rules-pos", pos, "Poste")}<p class="muted grow" id="rules-desc"></p></div>
    <div id="rules-body"><p class="loading">Chargement…</p></div>`;
  let kb;
  try {
    kb = S.kbDetail[pos] || (S.kbDetail[pos] = await api("/knowledge/" + encodeURIComponent(pos)));
  } catch (err) {
    $("#rules-body").innerHTML = `<p class="error">${esc(err.message)}</p>`;
    return;
  }
  if (!$("#rules-body") || pos !== S.rulesPos) return;
  $("#rules-desc").textContent = kb.poste.description;
  const flow = `<ol class="flow" aria-label="Enchaînement des étapes">${kb.etapes
    .map(
      (st, i) => `<li><a href="#stage-${i}"><strong>${cap(st.sorties[0])}</strong>
        <span>${st.entrees.length} entrée(s) · ${st.regles.length} règles</span></a></li>`,
    )
    .join("")}</ol>`;
  const stages = kb.etapes
    .map(
      (st, i) => `<section class="panel" id="stage-${i}">
        <h2>${cap(st.sorties[0])} <small>${esc(st.description)}</small></h2>
        <p class="chips">${st.entrees.map((n) => `<span class="chip" title="${esc(n)}">${esc(varLabel(n))}</span>`).join("")}
          <span class="muted">→</span> <span class="chip strong">${esc(st.sorties[0])}</span></p>
        <ol class="rules plain">${st.regles
          .map(
            (r) => `<li class="rule"><div><p class="rule-text"><span class="rule-id">${esc(r.id)}</span> ${fmtRule(r.regle)}
              ${r.poids < 1 ? `<span class="chip" title="Poids de la règle : atténue sa conclusion">poids ${nf(r.poids, 1)}</span>` : ""}</p>
              ${r.description ? `<p class="rule-desc">${esc(r.description)}</p>` : ""}</div></li>`,
          )
          .join("")}</ol></section>`,
    )
    .join("");
  const names = [...new Set(kb.etapes.flatMap((st) => [...st.entrees, ...st.sorties]))].filter((n) => S.vars[n]);
  const vars = names
    .map((n) => {
      const v = S.vars[n];
      return `<article class="var-card"><h4>${esc(v.description || v.nom)}</h4>
        <p class="muted small"><code>${esc(v.nom)}</code> · ${esc(v.unite)}</p>
        ${mfChart(v, null, { w: 300, h: 96, axis: true })}
        <div class="chips">${v.termes
          .map((t, i) => `<span class="chip" title="${esc(t.forme)}"><i class="swatch s${(i % 4) + 1}"></i>${esc(t.label)}</span>`)
          .join("")}</div></article>`;
    })
    .join("");
  $("#rules-body").innerHTML = `${flow}${stages}
    <section class="panel"><h2>Vocabulaire <small>ce que signifient « élevé », « rapide », « jeune »…</small></h2>
      <p class="muted small">Chaque courbe donne, pour une valeur mesurée, à quel degré (0 à 1) le mot s'applique. Survolez une courbe pour lire les degrés.</p>
      <div class="var-grid">${vars}</div></section>`;
}

// ----------------------------------------------------------------- vue : sélection

async function renderShortlist() {
  const view = $("#view");
  const items = S.shortlist.filter((s) => S.byId[s.id]);
  view.innerHTML = `
    <section class="page-head"><h1>Ma sélection</h1>
      <p>Les joueurs retenus, chacun au poste pour lequel vous l'avez repéré. La liste est conservée dans ce navigateur.</p></section>
    <section class="panel"><div class="panel-head"><h2>${items.length} joueur(s)</h2>
      <button class="btn" data-act="export" ${items.length ? "" : "disabled"}>Exporter en CSV</button></div>
      <div id="short-body">${items.length ? `<p class="loading">Évaluation…</p>` : `<div class="empty"><strong>Votre sélection est vide.</strong>
        <p>Ajoutez des joueurs avec ☆ depuis le <a href="#/recherche">classement</a> ou une fiche.</p></div>`}</div></section>`;
  if (!items.length) return;
  const evals = await Promise.all(
    items.map((s) => api("/evaluations", { position: s.position, player_id: s.id }).catch((err) => ({ error: err.message }))),
  );
  if (!$("#short-body")) return;
  S.shortEvals = items.map((s, i) => ({ ...s, ev: evals[i] }));
  const sorted = [...S.shortEvals].sort((a, b) => (b.ev.aptitude ?? -1) - (a.ev.aptitude ?? -1));
  $("#short-body").innerHTML = `<div class="table-wrap"><table class="rank"><thead><tr>
      <th>Joueur</th><th>Poste visé</th><th class="num">Âge</th><th class="num">Valeur</th><th>Aptitude</th>
      <th class="sub">Tech.</th><th class="sub">Phys.</th><th class="sub">Profil</th><th><span class="sr">Actions</span></th></tr></thead><tbody>${sorted
        .map(({ id, position, ev }) => {
          const p = S.byId[id];
          return `<tr data-act="open" data-id="${esc(id)}" data-pos="${esc(position)}" tabindex="0">
            <td><strong>${esc(p.nom)}</strong><span class="meta">${playerMeta(p)}</span></td>
            <td>${esc(posLabel(position))}</td>
            <td class="num">${nf(p.attributs.age, 0)}</td>
            <td class="num">${p.attributs.valeur_marche_meur != null ? nf(p.attributs.valeur_marche_meur) + " M€" : "–"}</td>
            ${
              ev.error
                ? `<td colspan="4" class="muted">${esc(ev.error)}</td>`
                : `<td class="apt"><b>${nf(ev.aptitude)}</b>${levelChip(ev.aptitude_label)}${meter(ev.aptitude, ev.aptitude_label)}</td>
                   ${SCORES.map((k) => `<td class="sub"><span>${nf(ev.scores[k], 0)}</span>${meter(ev.scores[k] ?? 0, ev.labels[k])}</td>`).join("")}`
            }
            <td class="acts"><button class="icon on" data-act="star" data-id="${esc(id)}" data-pos="${esc(position)}" title="Retirer de la sélection">★</button></td></tr>`;
        })
        .join("")}</tbody></table></div>`;
}

function exportShortlist() {
  const rows = [["id", "nom", "club", "nationalite", "poste_vise", "age", "valeur_marche_meur", "aptitude", "niveau", "technique", "physique", "profil"]];
  for (const { id, position, ev } of S.shortEvals || []) {
    const p = S.byId[id];
    const sc = ev.scores || {};
    rows.push([id, p.nom, p.club, p.nationalite, position, p.attributs.age ?? "", p.attributs.valeur_marche_meur ?? "",
      ev.aptitude ?? "", ev.aptitude_label ?? "", sc.technique ?? "", sc.physique ?? "", sc.profil ?? ""]);
  }
  const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(";")).join("\r\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" }));
  a.download = "selection-fuzzy-scouting.csv";
  a.click();
  URL.revokeObjectURL(a.href);
}

// ----------------------------------------------------------------- navigation et événements

const ROUTES = {
  recherche: renderSearch,
  comparer: renderCompare,
  simulateur: renderSim,
  regles: renderRules,
  selection: renderShortlist,
};
const currentRoute = () => {
  const name = location.hash.replace(/^#\/?/, "");
  return name in ROUTES ? name : "recherche";
};

function route() {
  const name = currentRoute();
  document.querySelectorAll(".tabs a").forEach((a) => {
    if (a.dataset.tab === name) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
  ROUTES[name]();
  window.scrollTo(0, 0);
}

function toggleStar(id, position) {
  const i = S.shortlist.findIndex((s) => s.id === id && s.position === position);
  if (i >= 0) S.shortlist.splice(i, 1);
  else S.shortlist.push({ id, position });
  store.set("shortlist", S.shortlist);
  toast(i >= 0 ? "Retiré de la sélection" : `${S.byId[id].nom} ajouté à la sélection (${posLabel(position)})`);
}

function toggleCompare(id) {
  const i = S.compare.indexOf(id);
  if (i >= 0) S.compare.splice(i, 1);
  else if (S.compare.length >= MAX_COMPARE) return toast(`Comparaison limitée à ${MAX_COMPARE} joueurs — retirez-en un d'abord.`);
  else S.compare.push(id);
  store.set("compare", S.compare);
  toast(i >= 0 ? "Retiré de la comparaison" : `${S.byId[id].nom} ajouté à la comparaison`);
}

function refreshAfterToggle() {
  updateCounts();
  renderSheetButtons();
  const name = currentRoute();
  if (name === "recherche") renderResults();
  else if (name === "comparer") renderCompare();
  else if (name === "selection") renderShortlist();
}

document.addEventListener("click", (e) => {
  const sheet = $("#sheet");
  if (e.target === sheet) return sheet.close(); // clic sur le fond
  const el = e.target.closest("[data-act]");
  if (!el) return;
  const { act, id, pos, key } = el.dataset;
  if (act === "star" || act === "cmp") {
    e.stopPropagation();
    if (act === "star") toggleStar(id, pos);
    else toggleCompare(id);
    refreshAfterToggle();
  } else if (act === "open") {
    if (e.target.closest("button")) return;
    openSheet(id, pos);
  } else if (act === "close") {
    sheet.close();
  } else if (act === "pos") {
    S.search.position = pos;
    S.search.sort = { key: "rang", dir: 1 };
    renderSearch();
  } else if (act === "sort") {
    const s = S.search.sort;
    const descFirst = ["aptitude", "technique", "physique", "profil"].includes(key);
    S.search.sort = s.key === key ? { key, dir: -s.dir } : { key, dir: descFirst ? -1 : 1 };
    renderResults();
  } else if (act === "reset-filters") {
    Object.assign(S.search, { maxAge: AGE_MAX, maxValue: null, minMinutes: 0, nationality: "", naturalOnly: false, q: "" });
    renderSearch();
  } else if (act === "simulate") {
    sheet.close();
    simInit(pos, id);
    if (currentRoute() === "simulateur") renderSim();
    else location.hash = "#/simulateur";
  } else if (act === "sim-reset") {
    S.sim.values = {};
    simInit(S.sim.position, S.sim.base);
    renderSim();
  } else if (act === "export") {
    exportShortlist();
  }
});

document.addEventListener("keydown", (e) => {
  if (e.key !== "Enter" && e.key !== " ") return;
  const row = e.target.matches && e.target.matches("tr[data-act=open]") ? e.target : null;
  if (!row) return;
  e.preventDefault();
  openSheet(row.dataset.id, row.dataset.pos);
});

document.addEventListener("input", (e) => {
  const t = e.target;
  const f = S.search;
  if (t.dataset.sim) {
    const name = t.dataset.sim;
    S.sim.values[name] = Number(t.value);
    document.getElementById("simo-" + name).innerHTML =
      `${fmtVal(name, S.sim.values[name])} <small>${esc(varUnit(name))}</small>`;
    return evalSimSoon();
  }
  if (t.id === "f-value") f.maxValue = Number(t.value) >= S.valueMax ? null : Number(t.value);
  else if (t.id === "f-age") f.maxAge = Number(t.value);
  else if (t.id === "f-min") f.minMinutes = Number(t.value);
  else if (t.id === "f-q") {
    f.q = t.value;
    return renderResults();
  } else return;
  syncFilterOutputs();
  runSearchSoon();
});

document.addEventListener("change", (e) => {
  const t = e.target;
  if (t.id === "f-nat") {
    S.search.nationality = t.value;
    runSearch();
  } else if (t.id === "f-natural") {
    S.search.naturalOnly = t.checked;
    runSearch();
  } else if (t.id === "sheet-pos") {
    openSheet(S.sheet.id, t.value);
  } else if (t.id === "cmp-pos") {
    S.comparePos = t.value;
    renderCompare();
  } else if (t.id === "cmp-add" && t.value) {
    toggleCompare(t.value);
    refreshAfterToggle();
  } else if (t.id === "sim-pos") {
    simInit(t.value, S.sim.base);
    renderSim();
  } else if (t.id === "sim-base") {
    if (!t.value) S.sim.values = {};
    simInit(S.sim.position, t.value);
    renderSim();
  } else if (t.id === "rules-pos") {
    S.rulesPos = t.value;
    renderRules();
  }
});

window.addEventListener("hashchange", route);

// ----------------------------------------------------------------- démarrage

(async function boot() {
  try {
    const [positions, players, variables, knowledge] = await Promise.all([
      api("/positions"),
      api("/players"),
      api("/variables"),
      api("/knowledge"),
    ]);
    S.positions = positions;
    S.players = [...players].sort((a, b) => a.nom.localeCompare(b.nom, "fr"));
    S.byId = Object.fromEntries(players.map((p) => [p.id, p]));
    S.vars = Object.fromEntries(variables.map((v) => [v.nom, v]));
    S.knowledge = Object.fromEntries(knowledge.map((k) => [k.poste, k]));
    S.levels = (S.vars.aptitude ? S.vars.aptitude.termes : []).map((t) => t.label);
    const values = players.map((p) => p.attributs.valeur_marche_meur).filter((v) => v != null);
    S.valueMax = values.length ? Math.ceil(Math.max(...values) / 5) * 5 : 50;
    const first = (positions.find((p) => p.code === "attaquant") || positions[0]).code;
    S.search.position = S.comparePos = S.rulesPos = first;
    S.shortlist = S.shortlist.filter((s) => S.byId[s.id] && S.knowledge[s.position]);
    S.compare = S.compare.filter((id) => S.byId[id]).slice(0, MAX_COMPARE);
    simInit(first, "");
    updateCounts();
    route();
  } catch (err) {
    $("#view").innerHTML = `<div class="empty panel"><strong>Impossible de joindre l'API.</strong><p>${esc(err.message)}</p>
      <p>Vérifiez que le serveur est démarré avec <code>fuzzyscout serve</code>.</p></div>`;
  }
})();
