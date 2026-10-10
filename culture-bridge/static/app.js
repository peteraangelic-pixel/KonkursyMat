/* Smak Domu — logika frontendu.
 *
 * Bez frameworka i bez etapu budowania: konkurs wymaga hostowanego, działającego
 * demo, a im mniej kroków do uruchomienia, tym mniej rzeczy może się zepsuć.
 */

const ANCHOR_KINDS = [
  { id: "free", label: "inaczej" },
  { id: "artist", label: "muzyka" },
  { id: "movie", label: "film" },
  { id: "tv_show", label: "serial" },
  { id: "dish", label: "potrawa" },
];

const state = {
  domains: [],
  selectedDomains: new Set(),
  excludeEntities: [],
  excludeTags: [],
  lastRequest: null,
};

const $ = (id) => document.getElementById(id);

/* ---------------------------------------------------------------- źródło */

async function loadHealth() {
  const badge = $("source-badge");
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    if (data.data_source === "qloo") {
      badge.textContent = "Qloo: połączone";
      badge.className = "badge badge-live";
      $("demo-banner").hidden = true;
    } else {
      badge.textContent = "TRYB DEMO — brak klucza Qloo";
      badge.className = "badge badge-demo";
      $("demo-banner").hidden = false;
    }
  } catch {
    badge.textContent = "brak połączenia z API";
    badge.className = "badge badge-demo";
  }
}

async function loadDomains() {
  try {
    const res = await fetch("/api/domains");
    const data = await res.json();
    state.domains = data.domains || [];
  } catch {
    state.domains = [];
  }
  const defaults = new Set([
    "urn:entity:movie",
    "urn:entity:artist",
    "urn:entity:place",
    "urn:entity:podcast",
  ]);
  const box = $("domains");
  box.innerHTML = "";
  for (const d of state.domains) {
    const chip = document.createElement("span");
    chip.className = "chip" + (defaults.has(d.id) ? " on" : "");
    chip.textContent = d.label;
    chip.dataset.id = d.id;
    if (defaults.has(d.id)) state.selectedDomains.add(d.id);
    chip.addEventListener("click", () => {
      chip.classList.toggle("on");
      if (state.selectedDomains.has(d.id)) state.selectedDomains.delete(d.id);
      else state.selectedDomains.add(d.id);
    });
    box.appendChild(chip);
  }
}

/* --------------------------------------------------------------- kotwice */

function addAnchorRow(value = "", kind = "free") {
  const row = document.createElement("div");
  row.className = "anchor-row";

  const input = document.createElement("input");
  input.type = "text";
  input.value = value;
  input.placeholder = "np. Okean Elzy, Amélie, barszcz";

  const select = document.createElement("select");
  for (const k of ANCHOR_KINDS) {
    const opt = document.createElement("option");
    opt.value = k.id;
    opt.textContent = k.label;
    if (k.id === kind) opt.selected = true;
    select.appendChild(opt);
  }

  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "btn x";
  remove.textContent = "×";
  remove.addEventListener("click", () => {
    row.remove();
    if (!$("anchors").children.length) addAnchorRow();
  });

  row.append(input, select, remove);
  $("anchors").appendChild(row);
  input.focus();
}

function readAnchors() {
  const out = [];
  for (const row of $("anchors").children) {
    const name = row.querySelector("input").value.trim();
    if (!name) continue;
    out.push({ name, kind: row.querySelector("select").value });
  }
  return out;
}

/* ----------------------------------------------------------------- plan */

async function buildPlan(extra = {}) {
  const anchors = readAnchors();
  const status = $("status");

  if (!anchors.length) {
    status.textContent = "Dodaj przynajmniej jedną kotwicę smakową.";
    return;
  }

  const payload = {
    origin: $("origin").value.trim() || "—",
    destination: $("destination").value.trim() || "—",
    anchors,
    age_range: $("age").value || null,
    domains: [...state.selectedDomains],
    exclude_entities: [...state.excludeEntities],
    exclude_tags: [...state.excludeTags],
    ...extra,
  };
  state.lastRequest = payload;

  $("go").disabled = true;
  status.textContent = "Układam plan…";

  try {
    const res = await fetch("/api/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      status.textContent = data.detail || "Nie udało się ułożyć planu.";
      return;
    }
    renderPlan(data);
    status.textContent = `Gotowe — ${data.qloo_calls} zapytań, źródło: ${data.data_source}.`;
  } catch (err) {
    status.textContent = `Błąd sieci: ${err.message}`;
  } finally {
    $("go").disabled = false;
  }
}

function renderPlan(plan) {
  $("empty").hidden = true;
  $("plan").hidden = false;

  $("plan-title").textContent = `${plan.origin} → ${plan.destination}`;
  $("narrative").textContent = plan.narrative;
  $("meta").textContent =
    `Zapytań do źródła: ${plan.qloo_calls} · dane: ${plan.data_source}` +
    (state.excludeEntities.length ? ` · wykluczone: ${state.excludeEntities.length}` : "");

  const warnBox = $("warnings");
  warnBox.innerHTML = "";
  for (const w of plan.warnings || []) {
    const div = document.createElement("div");
    div.className = "warn";
    div.textContent = w;
    warnBox.appendChild(div);
  }

  renderWeeks(plan.weeks || []);
  renderSections(plan.sections || []);
}

function renderWeeks(weeks) {
  const box = $("weeks");
  box.innerHTML = "";
  for (const week of weeks) {
    const card = document.createElement("div");
    card.className = "card week-card";
    const h = document.createElement("h3");
    h.textContent = `TYDZIEŃ ${week.week}`;
    card.appendChild(h);
    for (const step of week.steps) {
      const row = document.createElement("div");
      row.className = "week-step";
      const lab = document.createElement("div");
      lab.className = "lab";
      lab.textContent = step.label;
      const val = document.createElement("div");
      val.className = "val";
      val.textContent = step.name;
      const why = document.createElement("span");
      why.className = "why";
      why.textContent = step.why;
      val.appendChild(why);
      row.append(lab, val);
      card.appendChild(row);
    }
    box.appendChild(card);
  }
}

function renderSections(sections) {
  const box = $("sections");
  box.innerHTML = "";
  for (const section of sections) {
    const card = document.createElement("div");
    card.className = "card";
    const h = document.createElement("h2");
    h.className = "section-title";
    h.textContent = section.label;
    card.appendChild(h);

    if (!section.items.length) {
      const p = document.createElement("p");
      p.className = "note";
      p.textContent = section.note || "Brak wyników w tej kategorii.";
      card.appendChild(p);
      box.appendChild(card);
      continue;
    }

    for (const item of section.items) {
      card.appendChild(renderRec(item));
    }
    box.appendChild(card);
  }
}

function renderRec(item) {
  const wrap = document.createElement("div");
  wrap.className = "rec";

  const score = document.createElement("div");
  score.className = "score";
  score.textContent = item.affinity ? `${Math.round(item.affinity * 100)}%` : "—";

  const body = document.createElement("div");
  body.className = "body";

  const name = document.createElement("div");
  name.className = "name";
  name.textContent = item.name;
  body.appendChild(name);

  if (item.address) {
    const addr = document.createElement("div");
    addr.className = "addr";
    addr.textContent = item.address;
    body.appendChild(addr);
  }
  if (item.description) {
    const desc = document.createElement("div");
    desc.className = "desc";
    desc.textContent = item.description;
    body.appendChild(desc);
  }

  const why = document.createElement("div");
  why.className = "why";
  why.textContent = item.why;
  body.appendChild(why);

  if ((item.drivers || []).length) {
    const drivers = document.createElement("div");
    drivers.className = "drivers";
    for (const d of item.drivers) {
      const chip = document.createElement("span");
      chip.className = "driver";
      const b = document.createElement("b");
      b.textContent = d.entity_name || d.entity_id;
      chip.append(b, document.createTextNode(` ${Math.round(d.score * 100)}%`));
      drivers.appendChild(chip);
    }
    body.appendChild(drivers);
  }

  // Pętla doprecyzowania: „to nie to” wyklucza encję i przelicza plan.
  const tools = document.createElement("div");
  tools.className = "tools";
  if (item.qloo_id) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn tiny";
    btn.textContent = "to nie to";
    btn.addEventListener("click", () => {
      state.excludeEntities.push(item.qloo_id);
      buildPlan();
    });
    tools.appendChild(btn);
  }

  wrap.append(score, body, tools);
  return wrap;
}

/* ------------------------------------------------------------------ init */

$("add-anchor").addEventListener("click", () => addAnchorRow());
$("go").addEventListener("click", () => {
  state.excludeEntities = [];
  state.excludeTags = [];
  buildPlan();
});

addAnchorRow("Okean Elzy", "artist");
addAnchorRow("Amélie", "movie");
addAnchorRow("barszcz", "dish");

loadHealth();
loadDomains();
