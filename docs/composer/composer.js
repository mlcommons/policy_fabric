/* Policy Composer: draw a policy card from the components in this repository, check it, preview a request on
   the Simulate tab, and download its graph.json (version 3) to commit.

   What it knows comes from catalog.json beside this page, which tools/policy_catalog/build_catalog.py builds
   from credentials/, policy_components/ and policy_cards/: the library, the Load menu and the checks. It draws
   credentials, Policy Components and the capability with the shared renderer's shapes (policy_ui/), as the
   webapp's read-only views do. The example issuers of the Simulate tab are preview data, in issuers.js.

   Download and Copy write what a card commits: policy_data {} on every node and [] for every type in
   trusted_issuers; the asset owner sets both when exposing an asset. The values and issuers typed on the
   Simulate tab are examples for the preview and never leave the page. */
"use strict";

/* ---------- vocabulary ---------- */
/* the catalog, and its components by id; set once catalog.json has loaded */
let CAT = null;
let COMPONENTS = null;
/* who signed a presented credential, when it is none of the example issuers */
const UNKNOWN = { id: "did:example:unknown", name: "an unknown issuer" };
const issuersFor = t => EXAMPLE_ISSUERS.filter(i => i.types.includes(t));
const issuerName = id => (id === UNKNOWN.id ? UNKNOWN : EXAMPLE_ISSUERS.find(i => i.id === id)).name;

/* the library's groups, in order: the catalog's group and its title */
const GROUPS = [["shared", "Shared"], ["card", "Cards"]];
function orList(items) {
  return items.length < 2 ? items.join("") : items.slice(0, -1).join(", ") + " or " + items[items.length - 1];
}
/* claims the plan adds to an input's type, which the shapes mark "new" */
const newClaims = inp => ("new_claims" in inp ? inp.new_claims : []);

const ICON_INFO = '<svg width="15" height="15" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.4" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M8 7.3v4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><circle cx="8" cy="4.9" r="1" fill="currentColor"/></svg>';
const ICON_X = '<svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><path d="M2.5 2.5l7 7M9.5 2.5l-7 7" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>';

/* ---------- state ---------- */
let S = blankState();
const ui = { sel: null, tab: "checks", view: { x: 40, y: 40, k: 0.8 }, drag: null, connect: null, sim: blankSim(), toastTimer: 0, filter: "", modal: null };
const GEO = {};      /* measured layout of each component on the canvas, relative to its corner */
let CAPGEO = null;   /* the capability's: where placeCap put it, and its sockets, inputs and card */

/* the canvas: the card's name, its components (with their place, and whether the inputs their output is wired
   to also accept it presented), the wires, and the capability: the operation it issues (null until one is
   chosen) and the components it requires, in order */
function blankState() { return { v: 5, name: "Untitled card", nodes: {}, wires: [], operation: null, requires: [], seq: 1 }; }
/* the Simulate tab: policy data values per node, the issuers ticked per credential type (none ticked: every
   example issuer that signs it), and who signed each presented credential. Kept apart from the canvas, so
   nothing here reaches the graph JSON. */
function blankSim() { return { data: {}, trusted: {}, presented: {}, seen: {} }; }
const comp = n => COMPONENTS[n.component];
const operation = () => CAT.operations[S.operation];
function label(id) {
  const n = S.nodes[id];
  const m = /^_(\d+)$/.exec(id.slice(n.component.length));
  return comp(n).name + (id.startsWith(n.component) && m ? " (" + m[1] + ")" : "");
}

function addNode(st, componentId, x, y) {
  let id = componentId, k = 2;
  while (st.nodes[id]) id = componentId + "_" + k++;
  const n = { id, component: componentId, x: Math.round(x), y: Math.round(y), accept: false };
  st.nodes[id] = n;
  return n;
}
function wire(st, from, to, input) { st.wires.push({ id: "w" + (st.seq++), from, to, input }); }

/* ---------- graph.json in ---------- */
const isObj = v => typeof v === "object" && v !== null && !Array.isArray(v);
const sameKeys = (o, keys) => Object.keys(o).sort().join(",") === keys.slice().sort().join(",");
/* JSON with every object's keys sorted, to compare values whatever order their keys come in */
const canonical = v => JSON.stringify(v, (k, x) => (isObj(x) ? Object.fromEntries(Object.keys(x).sort().map(key => [key, x[key]])) : x));
/* A graph.json (version 3) as canvas state: its nodes in the file's order, one wire per node source, the
   accept switches (one per output: every input an output is wired to accepts it presented, or none does), and
   the capability's operation and the nodes it requires; node ids are kept. policy_data and trusted_issuers are
   not read: they are the asset owner's, and what Download writes for them follows from the graph. Throws,
   naming the problem, on anything this composer does not write. */
function readGraph(g) {
  const fail = text => { throw new Error(text); };
  if (!isObj(g)) fail("it is not a JSON object");
  if (g.version !== 3) fail(`it is version ${JSON.stringify(g.version)}; the composer reads version 3`);
  if (!sameKeys(g, ["version", "name", "nodes", "capability", "trusted_issuers"])) fail("a version 3 graph has exactly version, name, nodes, capability and trusted_issuers");
  if (typeof g.name !== "string") fail("its name is not a string");
  if (!isObj(g.nodes)) fail("its nodes are not an object");
  if (!isObj(g.trusted_issuers) || !Object.values(g.trusted_issuers).every(Array.isArray)) fail("its trusted_issuers do not map each credential type to a list");
  const st = blankState();
  st.name = g.name;
  Object.entries(g.nodes).forEach(([id, n]) => {
    if (!/^[A-Za-z][A-Za-z0-9_-]*$/.test(id)) fail(`its node id ${JSON.stringify(id)} is not a name like the component ids`);
    if (!isObj(n) || !sameKeys(n, ["component", "inputs", "policy_data"]) || !isObj(n.policy_data)) fail(`node ${id} has exactly component, inputs and policy_data`);
    if (!Object.hasOwn(COMPONENTS, n.component)) fail(`node ${id} uses ${n.component}, which is not in this repository`);
    const names = Object.keys(COMPONENTS[n.component].inputs);
    if (!isObj(n.inputs) || !sameKeys(n.inputs, names)) fail(`node ${id} binds ${isObj(n.inputs) ? Object.keys(n.inputs).join(", ") : "no inputs"}, but ${n.component} takes ${names.join(", ")}`);
    st.nodes[id] = { id, component: n.component, x: 0, y: 0, accept: false };
  });
  const accepted = {};   /* the accept_presented of the sources reading each node */
  const nodeSource = (id, name, s) => {
    if (!isObj(s) || !sameKeys(s, ["from", "node", "accept_presented"]) || s.from !== "node" || typeof s.accept_presented !== "boolean") fail(`${id}.${name}: a source is {"from": "presented"} or {"from": "node", "node", "accept_presented"}`);
    if (!Object.hasOwn(st.nodes, s.node)) fail(`${id}.${name} reads node ${s.node}, which the graph does not have`);
  };
  Object.entries(g.nodes).forEach(([id, n]) => Object.keys(COMPONENTS[n.component].inputs).forEach(name => {
    const raw = n.inputs[name];
    if (isObj(raw) && sameKeys(raw, ["from"]) && raw.from === "presented") {
      /* an unwired input: a presented credential */
    } else {
      nodeSource(id, name, raw);
      wire(st, raw.node, id, name);
      if (!Object.hasOwn(accepted, raw.node)) accepted[raw.node] = new Set();
      accepted[raw.node].add(raw.accept_presented);
    }
  }));
  Object.entries(accepted).forEach(([id, values]) => {
    if (values.size > 1) fail(`the inputs reading ${id} disagree on accept_presented; the composer sets it once per output`);
    st.nodes[id].accept = values.has(true);
  });
  /* the capability: an operation of the catalog with exactly its parameters, or none (null, with no parameters)
     while the card is a draft; and the nodes it requires, each once, none while the card is a draft */
  const cap = g.capability;
  if (!isObj(cap) || !sameKeys(cap, ["operation", "requires", "parameters"])) fail("its capability has exactly operation, requires and parameters");
  if (cap.operation !== null && !Object.hasOwn(CAT.operations, cap.operation)) fail(`its capability issues ${JSON.stringify(cap.operation)}, which is not an operation here: ${orList(Object.keys(CAT.operations))}`);
  const parameters = cap.operation === null ? {} : CAT.operations[cap.operation].parameters;
  if (canonical(cap.parameters) !== canonical(parameters)) fail(`its capability's parameters are not ${cap.operation === null ? "empty, as it issues no operation" : `those ${cap.operation} reads: ${JSON.stringify(parameters)}`}`);
  if (!Array.isArray(cap.requires)) fail("its capability's requires is not a list of nodes");
  cap.requires.forEach(id => { if (!Object.hasOwn(st.nodes, id)) fail(`its capability requires ${JSON.stringify(id)}, which the graph does not have`); });
  if (new Set(cap.requires).size !== cap.requires.length) fail("its capability requires a node twice");
  st.operation = cap.operation;
  st.requires = cap.requires.slice();
  return st;
}

/* ---------- graph queries ---------- */
const wiresTo = (id, input) => S.wires.filter(w => w.to === id && w.input === input);
const wiresFrom = id => S.wires.filter(w => w.from === id);
/* a wired input also takes a presented credential when the output wired into it is accepted presented */
const accepts = (id, input) => wiresTo(id, input).some(w => S.nodes[w.from].accept);
/* An output wired to an input has the accept presented switch when a wallet may present its type; a switch
   that is on stays, so that a graph loaded with it on a type no wallet presents can switch it off. */
function hasAcceptSwitch(n) {
  return wiresFrom(n.id).length > 0 && (CAT.credentials[comp(n).output.type].presentable || n.accept);
}
/* A component has the required switch when its output is about the subject of the capability's operation, or
   while no operation is chosen; a switch that is on stays, so that a component the operation cannot require
   can be switched off. */
const required = id => S.requires.includes(id);
function hasRequireSwitch(n) {
  return required(n.id) || S.operation === null || comp(n).output.about === operation().about;
}
function reaches(from, target) {
  const seen = new Set(), stack = [from];
  while (stack.length) {
    const n = stack.pop();
    if (n === target) return true;
    if (seen.has(n)) continue;
    seen.add(n);
    S.wires.forEach(w => { if (w.from === n) stack.push(w.to); });
  }
  return false;
}
/* the components that lead to any of these, over the wires, and these */
function upstream(ids) {
  const seen = new Set(), stack = ids.slice();
  while (stack.length) {
    const n = stack.pop();
    if (seen.has(n)) continue;
    seen.add(n);
    S.wires.forEach(w => { if (w.to === n) stack.push(w.from); });
  }
  return seen;
}
/* every component in run order: depth first from the components the capability requires, inputs in order,
   then the rest */
function runOrderAll() {
  const out = [], state = {};
  const visit = id => {
    if (state[id]) return;
    state[id] = 1;
    Object.keys(comp(S.nodes[id]).inputs).forEach(name => wiresTo(id, name).forEach(w => visit(w.from)));
    out.push(id);
  };
  S.requires.forEach(visit);
  Object.keys(S.nodes).forEach(visit);
  return out;
}
/* Credential types a wallet may present: those of unwired inputs (required), of wired inputs that accept
   presented ones, and those the parameters of the capability's operation are read from (required). registry:
   whether the contract checks its issuer, so that it is in trusted_issuers; not when every input taking it is
   one its component checks against a key it supplies. */
function presentedTypes() {
  const map = new Map();
  runOrderAll().forEach(id => {
    const n = S.nodes[id];
    Object.entries(comp(n).inputs).forEach(([name, inp]) => {
      const wired = wiresTo(id, name).length > 0;
      if (wired && !accepts(id, name)) return;
      if (!map.has(inp.type)) map.set(inp.type, { type: inp.type, required: false, registry: false, uses: [] });
      const e = map.get(inp.type);
      if (!wired) e.required = true;
      if (wired || !("supplied_key" in inp)) e.registry = true;
      e.uses.push({ node: id, input: name, wired });
    });
  });
  if (S.operation !== null) Object.entries(operation().parameters).forEach(([name, p]) => {
    if (!map.has(p.type)) map.set(p.type, { type: p.type, required: false, registry: false, uses: [] });
    const e = map.get(p.type);
    e.required = true;
    e.registry = true;
    e.uses.push({ parameter: name });
  });
  return [...map.values()];
}
/* the issuers the preview trusts for a type: those ticked, or every example issuer that signs it while none is
   (on the contract, an empty list leaves it to the registry) */
function trustedFor(t) {
  const ticked = ui.sim.trusted[t];
  return ticked.length ? ticked : issuersFor(t).map(i => i.id);
}
function syncTrust() {
  presentedTypes().forEach(({ type, registry }) => {
    if (registry && !Object.hasOwn(ui.sim.trusted, type)) ui.sim.trusted[type] = [];
  });
}
/* who signs a presented credential to begin with: the first issuer the preview trusts for it */
function firstIssuer(p) {
  const ids = p.registry ? trustedFor(p.type) : issuersFor(p.type).map(i => i.id);
  return ids.length ? ids[0] : UNKNOWN.id;
}
function syncPresented() {
  const types = presentedTypes();
  /* forget types that are no longer presented, so one that comes back starts from its default again */
  Object.keys(ui.sim.seen).forEach(t => { if (!types.some(p => p.type === t)) { delete ui.sim.seen[t]; delete ui.sim.presented[t]; } });
  types.forEach(p => {
    if (ui.sim.seen[p.type]) return;
    ui.sim.seen[p.type] = true;
    ui.sim.presented[p.type] = p.required ? firstIssuer(p) : null;
  });
}

/* ---------- checks ---------- */
function findLoop() {
  const state = {};
  let loop = null;
  const visit = (id, path) => {
    if (loop) return;
    if (state[id] === 1) { loop = path.slice(path.indexOf(id)).concat(id); return; }
    if (state[id] === 2) return;
    state[id] = 1;
    S.wires.filter(w => w.from === id).forEach(w => visit(w.to, path.concat(id)));
    state[id] = 2;
  };
  Object.keys(S.nodes).forEach(id => visit(id, []));
  return loop;
}
/* What the catalog builder would refuse in a committed graph, said for the canvas. A type is presentable
   (a wallet may present it) as the catalog says: no component produces it, or its schema allows it. */
function checks() {
  const out = [];
  const ids = Object.keys(S.nodes);
  const word = about => CAT.subjects[about].word;
  if (!ids.length) return [{ level: "error", text: "The canvas is empty." }];
  if (S.operation === null) out.push({ level: "error", text: "The capability has no operation." });
  if (!S.requires.length) out.push({ level: "error", text: "The capability requires no component." });
  ids.forEach(id => {
    const n = S.nodes[id], c = comp(n);
    if (!required(id) && !wiresFrom(id).length) out.push({ level: "error", node: id, text: `${label(id)}'s output is neither wired nor required.` });
    if (required(id) && S.operation !== null && c.output.about !== operation().about) {
      out.push({ level: "error", node: id, text: `${S.operation} is about the ${word(operation().about)}, but ${label(id)}'s output is about the ${word(c.output.about)}.` });
    }
    if (n.accept && !CAT.credentials[c.output.type].presentable) {
      out.push({ level: "error", node: id, text: `${label(id)}'s output is accepted presented, but no wallet presents a ${c.output.type}.` });
    }
    Object.entries(c.inputs).forEach(([name, inp]) => {
      const ws = wiresTo(id, name);
      ws.forEach(w => {
        const src = comp(S.nodes[w.from]);
        if (src.output.type !== inp.type) out.push({ level: "error", node: id, text: `${label(id)} takes ${inp.type}, not ${src.output.type}.` });
      });
      if (ws.length && "supplied_key" in inp) out.push({ level: "error", node: id, text: `${label(id)} takes only a presented ${inp.type}.` });
      if (!ws.length && !CAT.credentials[inp.type].presentable) out.push({ level: "error", node: id, text: `${label(id)} needs a wired ${inp.type}.` });
    });
  });
  const loop = findLoop();
  if (loop) out.push({ level: "error", node: loop[0], text: `Loop: ${loop.map(label).join(" → ")}.` });
  return out.sort((a, b) => (a.level === b.level ? 0 : a.level === "error" ? -1 : 1));
}

/* ---------- simulation ---------- */
/* A preview, in JavaScript, of how the contract plans a request. A presented credential counts when a trusted
   issuer signed it; one its component checks against a key it supplies counts when it is presented. A wired
   input that accepts presented credentials takes a presented one when there is one, and the components
   upstream of it are skipped. The components that run are those the capability requires and those they reach
   over the other wires, in the order of their dependency closures (producers first, then by node id), and a
   component runs when every input has its credential. The capability is issued when every component it
   requires ran and each parameter of its operation has its presented credential. It runs no Rego, so it does
   not check that the claims join up or match the policy data. */
function simulate() {
  if (S.operation === null || !S.requires.length || findLoop()) return null;
  const counts = (type, keyed) => { const iss = ui.sim.presented[type]; return iss !== null && (keyed || trustedFor(type).includes(iss)); };
  const shortcut = (id, name, inp) => accepts(id, name) && counts(inp.type, false);
  const deps = id => {
    const out = new Set();
    Object.entries(comp(S.nodes[id]).inputs).forEach(([name, inp]) => { if (!shortcut(id, name, inp)) wiresTo(id, name).forEach(w => out.add(w.from)); });
    return out;
  };
  const closure = ids => {
    const seen = new Set(), stack = ids.slice();
    while (stack.length) { const x = stack.pop(); if (seen.has(x)) continue; seen.add(x); deps(x).forEach(d => stack.push(d)); }
    return seen;
  };
  const active = closure(S.requires);
  const order = [...active].map(id => [closure([id]).size, id]).sort((a, b) => a[0] - b[0] || (a[1] < b[1] ? -1 : 1)).map(p => p[1]);
  const ran = new Set(), blocked = new Set(), missing = [], used = [], shortcuts = [];
  order.forEach(id => {
    let ok = true;
    Object.entries(comp(S.nodes[id]).inputs).forEach(([name, inp]) => {
      const ws = wiresTo(id, name);
      if (shortcut(id, name, inp)) {
        shortcuts.push({ node: id, input: name, type: inp.type, from: ws[0].from });
        used.push({ node: id, input: name, type: inp.type });
      } else if (!ws.length) {
        if (counts(inp.type, "supplied_key" in inp)) used.push({ node: id, input: name, type: inp.type });
        else { ok = false; missing.push({ node: id, input: name, type: inp.type, issuer: ui.sim.presented[inp.type] }); }
      } else if (!ws.every(w => ran.has(w.from))) ok = false;
    });
    (ok ? ran : blocked).add(id);
  });
  let read = true;
  Object.entries(operation().parameters).forEach(([name, p]) => {
    if (counts(p.type, false)) used.push({ parameter: name, type: p.type });
    else { read = false; missing.push({ parameter: name, type: p.type, issuer: ui.sim.presented[p.type] }); }
  });
  const skipped = [...upstream(S.requires)].filter(id => !active.has(id));
  return { order, ran, blocked, missing, used, skipped, shortcuts, issued: read && S.requires.every(id => ran.has(id)) };
}

/* ---------- graph JSON (version 3) ---------- */
/* What Download and Copy write: the nodes in canvas order, each node's inputs in its component's order,
   policy_data {} on every node, the capability (its operation, the nodes it requires in the order they were
   switched on, and the operation's parameters as the catalog has them), and an empty trusted_issuers list for
   every type the graph takes presented and checks against the registry, sorted. */
function graphJson() {
  const nodes = {};
  Object.values(S.nodes).forEach(n => {
    const inputs = {};
    Object.keys(comp(n).inputs).forEach(name => {
      const ws = wiresTo(n.id, name);
      if (!ws.length) inputs[name] = { from: "presented" };
      else inputs[name] = { from: "node", node: ws[0].from, accept_presented: S.nodes[ws[0].from].accept };
    });
    nodes[n.id] = { component: n.component, inputs, policy_data: {} };
  });
  const capability = { operation: S.operation, requires: S.requires.slice(), parameters: S.operation === null ? {} : operation().parameters };
  const trusted = {};
  presentedTypes().filter(p => p.registry).map(p => p.type).sort().forEach(t => { trusted[t] = []; });
  return { version: 3, name: S.name, nodes, capability, trusted_issuers: trusted };
}
const graphText = () => JSON.stringify(graphJson(), null, 2) + "\n";

/* ---------- rendering helpers ---------- */
const $ = id => document.getElementById(id);
const esc = PolicyGraph.esc, brk = PolicyGraph.brk;
const sel = s => CSS.escape(s);
const canvas = $("canvas"), world = $("world"), nodesEl = $("nodes"), wiresEl = $("wires");

/* The shared shapes draw a credential and the capability as the read-only views do. The canvas adds, at the end
   of a card, its status on the Simulate tab and its switches. */
function addToCard(html, extra) {
  const t = document.createElement("template");
  t.innerHTML = html;
  if (extra) t.content.querySelector(".vc").insertAdjacentHTML("beforeend", extra);
  return t;
}
function credCard(type, about, claims, fresh, extra) {
  return addToCard(PolicyGraph.shapes.credential(type, about, claims, fresh, CAT.subjects, false, ""), extra).innerHTML;
}
/* the capability: the operation it issues, picked on the card, and the names of the operation's parameters */
function capCard(extra) {
  const params = S.operation === null ? [] : Object.keys(operation().parameters);
  const t = addToCard(PolicyGraph.shapes.capability("", params, ""), extra);
  const options = (S.operation === null ? '<option value="" selected disabled>operation…</option>' : "") +
    Object.keys(CAT.operations).map(op => `<option value="${esc(op)}"${op === S.operation ? " selected" : ""}>${esc(op)}</option>`).join("");
  t.content.querySelector(".vc-t").insertAdjacentHTML("beforeend", `<select class="cap-op" id="cap-operation" data-act="operation" aria-label="Operation">${options}</select>`);
  return t.innerHTML;
}
/* a switch at the end of an output card: accept presented, or required */
function switchRow(id, act, nodeId, on, text) {
  return `<label class="ap" for="${esc(id)}"><input type="checkbox" role="switch" id="${esc(id)}" data-act="${act}" data-node="${esc(nodeId)}"${on ? " checked" : ""}><span class="ap-track" aria-hidden="true"><span class="ap-thumb"></span></span><span class="ap-text">${text}</span></label>`;
}
/* a presented credential's status on the Simulate tab */
function presentedStatus(miss, used) {
  if (miss) return `<span class="st bad">${miss.issuer !== null ? "untrusted" : "missing"}</span>`;
  return used ? `<span class="st good">✓</span>` : "";
}

/* ---------- library ---------- */
function libSub(c) {
  if (c.group === "card") return c.duo;
  return "→ " + c.output.type;
}
function libHay(c) {
  const card = c.group === "card" ? [CAT.cards[c.card].name, c.card, c.duo] : [];
  return [c.id, c.name, ...card, c.output.type].concat(Object.values(c.inputs).map(i => i.type)).join(" ").toLowerCase();
}
function renderLibrary() {
  const q = ui.filter.trim().toLowerCase();
  const html = GROUPS.map(([g, title]) => {
    const all = Object.values(COMPONENTS).filter(c => c.group === g);
    const items = all.filter(c => !q || libHay(c).includes(q));
    if (!items.length) return "";
    return `<section class="lib-group" aria-label="${title}"><h3><span>${title}</span><span>${items.length}</span></h3>${items.map(c => `
      <div class="lib-item" data-component="${esc(c.id)}">
        <button type="button" class="lib-open" data-act="open-component" data-component="${esc(c.id)}" aria-haspopup="dialog" title="${esc(c.group === "card" ? CAT.cards[c.card].name + " (" + c.duo + ")" : c.name)}"><i class="lg lg-card" aria-hidden="true"></i><span class="lib-text"><span class="n">${brk(c.name)}</span><span class="o">${c.group === "card" ? esc(libSub(c)) : brk(libSub(c))}</span></span></button>
        <button type="button" class="lib-add" data-act="add-component" data-component="${esc(c.id)}" aria-label="Add ${esc(c.name)} to the canvas">Add</button>
      </div>`).join("")}</section>`;
  }).join("");
  $("lib-list").innerHTML = html || `<p class="empty" style="padding:10px 4px">No component matches “${esc(ui.filter)}”.</p>`;
}
/* the Load menu: every card in the catalog, by name, then an empty canvas and a local graph.json */
function renderLoadMenu() {
  const cards = Object.entries(CAT.cards).sort((a, b) => a[1].name.localeCompare(b[1].name));
  $("load-select").innerHTML = `<option value="">Choose…</option>
    <optgroup label="Cards">${cards.map(([folder, card]) => `<option value="card:${esc(folder)}" title="policy_cards/${esc(folder)}">${esc(card.name)}</option>`).join("")}</optgroup>
    <optgroup label="Other"><option value="empty">Empty canvas</option><option value="file">graph.json file…</option></optgroup>`;
}

/* ---------- canvas ---------- */
function nodeHtml(n, sim, live) {
  const c = comp(n);
  const selected = ui.sel && ui.sel.kind === "node" && ui.sel.id === n.id;
  const name = label(n.id);
  const nid = esc(n.id);
  let dim = false, loose = false, order = "", state = "";
  if (sim) {
    const at = sim.order.indexOf(n.id);
    if (at >= 0) {
      order = `<span class="order${sim.blocked.has(n.id) ? " blocked" : ""}" aria-label="Runs ${at + 1}">${at + 1}</span>`;
      if (sim.blocked.has(n.id)) state = `<span class="n-state bad">cannot run</span>`;
    } else if (sim.skipped.includes(n.id)) { dim = true; state = `<span class="n-state">skipped</span>`; }
    else dim = true;
  } else if (live && !live.has(n.id)) loose = true;
  /* a wired input is a lane the wire from the output it reads runs through, into the Policy Component; an
     unwired one is the credential presented to it */
  const ins = Object.entries(c.inputs).map(([iname, inp]) => {
    const iid = esc(iname);
    const at = `data-node="${nid}" data-input="${iid}" data-type="${esc(inp.type)}"`;
    if (wiresTo(n.id, iname).length) return `<div class="n-in lane" ${at}></div>`;
    const ran = sim && sim.order.includes(n.id);
    const status = ran ? presentedStatus(sim.missing.find(m => m.node === n.id && m.input === iname), sim.used.some(u => u.node === n.id && u.input === iname)) : "";
    return `<div class="n-in" ${at}>
        <button type="button" class="port in" data-port="in" data-node="${nid}" data-input="${iid}" aria-label="${esc(name)} input ${iid}, takes ${esc(inp.type)}"></button>
        ${credCard(inp.type, inp.about, inp.claims, newClaims(inp), status)}
      </div>`;
  }).join("");
  /* the output's switches: the inputs it is wired to also accept it presented; the capability requires it */
  const switches = (hasAcceptSwitch(n) ? switchRow(`apc-${n.id}`, "accept", n.id, n.accept, "accept presented") : "") +
    (hasRequireSwitch(n) ? switchRow(`rqc-${n.id}`, "require", n.id, required(n.id), "required") : "");
  const outCard = credCard(c.output.type, c.output.about, c.output.claims, [], switches);
  return `<div class="node${selected ? " selected" : ""}${dim ? " dim" : ""}${loose ? " loose" : ""}" data-node="${nid}" style="transform:translate(${n.x}px,${n.y}px)">
    <div class="n-ins">${ins}</div>
    <div class="n-comp">
      <div class="n-tools">
        <button type="button" class="icon-btn" data-act="node-info" data-node="${nid}" aria-label="Details of ${esc(name)}" title="Details">${ICON_INFO}</button>
        <button type="button" class="icon-btn danger" data-act="node-remove" data-node="${nid}" aria-label="Remove ${esc(name)}" title="Remove">${ICON_X}</button>
      </div>
      <div class="n-compbox">
        ${order}
        ${PolicyGraph.shapes.component(name, Object.keys(c.policy_data), ` data-comp="${nid}"`)}
        ${state}
      </div>
    </div>
    <div class="n-out" data-node="${nid}" data-type="${esc(c.output.type)}">
      ${outCard}
      <button type="button" class="port out" data-port="out" data-node="${nid}" aria-label="${esc(name)} output ${esc(c.output.type)}"></button>
    </div>
  </div>`;
}
/* The capability, at the end of the card: a lane for each component it requires, which that component's output
   runs through, and the presented credential each parameter of its operation is read from, all into the
   capability card. placeCap puts it in its place. */
function capHtml(sim) {
  const reqs = S.requires.map(id => `<div class="n-in lane" data-requires="${esc(id)}"></div>`).join("");
  const params = S.operation === null ? "" : Object.entries(operation().parameters).map(([name, p]) => {
    const status = sim ? presentedStatus(sim.missing.find(m => m.parameter === name), true) : "";
    return `<div class="n-in" data-parameter="${esc(name)}" data-type="${esc(p.type)}">${credCard(p.type, operation().about, [p.claim], [], status)}</div>`;
  }).join("");
  const status = sim ? `<span class="st ${sim.issued ? "good" : "bad"}">${sim.issued ? "✓ issued" : "not issued"}</span>` : "";
  return `<div class="node capability" role="group" aria-label="The capability">
    ${reqs || params ? `<div class="n-ins">${reqs}${params}</div>` : ""}
    <div class="n-out${sim && !sim.issued ? " dim" : ""}">${capCard(status)}</div>
  </div>`;
}

function renderNodes(sim) {
  const live = S.requires.length ? upstream(S.requires) : null;
  const ids = Object.keys(S.nodes);
  nodesEl.innerHTML = Object.values(S.nodes).map(n => nodeHtml(n, sim, live)).join("") + (ids.length ? capHtml(sim) : "");
  const hint = $("canvas-hint");
  hint.hidden = ids.length > 0;
  hint.textContent = "Add a component, or load a card.";
}

function rel(el, root) {
  let x = 0, y = 0, e = el;
  while (e && e !== root) { x += e.offsetLeft; y += e.offsetTop; e = e.offsetParent; }
  return { x, y, w: el.offsetWidth, h: el.offsetHeight };
}
function measure() {
  Object.keys(GEO).forEach(k => { if (!S.nodes[k]) delete GEO[k]; });
  nodesEl.querySelectorAll(".node[data-node]").forEach(el => {
    const g = { w: el.offsetWidth, h: el.offsetHeight, ins: {} };
    el.querySelectorAll(".n-in").forEach(i => { g.ins[i.dataset.input] = rel(i, el); });
    g.comp = rel(el.querySelector(".pc"), el);
    g.out = rel(el.querySelector(".n-out"), el);
    GEO[el.dataset.node] = g;
  });
  const cap = nodesEl.querySelector(".node.capability");
  CAPGEO = null;
  if (!cap) return;
  CAPGEO = { x: 0, y: 0, w: cap.offsetWidth, h: cap.offsetHeight, ins: [], card: rel(cap.querySelector(".n-out"), cap) };
  cap.querySelectorAll(".n-in").forEach(i => {
    CAPGEO.ins.push(Object.assign(rel(i, cap), { requires: "requires" in i.dataset ? i.dataset.requires : null }));
  });
}
/* The capability sits at the end of the card: right of the components it requires (of every component while it
   requires none), level with their outputs. */
function placeCap() {
  if (!CAPGEO) return;
  const ids = S.requires.length ? S.requires : Object.keys(S.nodes);
  const right = Math.max(...ids.map(id => S.nodes[id].x + GEO[id].w));
  const mid = ids.reduce((s, id) => s + outPort(S.nodes[id]).y, 0) / ids.length;
  CAPGEO.x = Math.round(right + 64);
  CAPGEO.y = Math.round(mid - CAPGEO.h / 2);
  nodesEl.querySelector(".node.capability").style.transform = `translate(${CAPGEO.x}px,${CAPGEO.y}px)`;
}
const capBox = () => ({ x: CAPGEO.x, y: CAPGEO.y, w: CAPGEO.w, h: CAPGEO.h });
function inPort(n, input) {
  const g = GEO[n.id], b = g && g.ins[input];
  return b ? { x: n.x + b.x, y: n.y + b.y + b.h / 2 } : { x: n.x, y: n.y };
}
function outPort(n) {
  const g = GEO[n.id];
  return g ? { x: n.x + g.out.x + g.out.w, y: n.y + g.out.y + g.out.h / 2 } : { x: n.x, y: n.y };
}
const f1 = v => Math.round(v * 10) / 10;
/* a curve from a to b, leaving and arriving level; seg continues a path already at a */
function seg(a, b, minDx) {
  const dx = Math.max(minDx, Math.abs(b.x - a.x) / 2);
  return ` C${f1(a.x + dx)} ${f1(a.y)} ${f1(b.x - dx)} ${f1(b.y)} ${f1(b.x)} ${f1(b.y)}`;
}
const curve = (a, b, minDx) => `M${f1(a.x)} ${f1(a.y)}` + seg(a, b, minDx);
/* from an output, through a lane (its box, at x0, y0) and on into the card at t */
function throughLane(a, x0, y0, lane, t) {
  const left = { x: x0 + lane.x, y: y0 + lane.y + lane.h / 2 }, right = { x: left.x + lane.w, y: left.y };
  return curve(a, left, 40) + ` L${f1(right.x)} ${f1(right.y)}` + seg(right, t, 4);
}
const marker = (id, colour) => `<marker id="${id}" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" style="fill: var(${colour})"/></marker>`;
function renderWires(sim) {
  const parts = [`<defs>${marker("arr", "--pf-ink-3")}${marker("arr-cap", "--pf-grant")}${marker("arr-wire", "--pf-accent")}</defs>`];
  /* inside each component: presented inputs into the Policy Component, the Policy Component into its output;
     where each input arrives, for the wires */
  const arrive = {};
  Object.values(S.nodes).forEach(n => {
    const g = GEO[n.id];
    if (!g) return;
    const c = comp(n);
    const hx = n.x + g.comp.x, hy = n.y + g.comp.y, hh = g.comp.h, cy = hy + hh / 2;
    const names = Object.keys(c.inputs).filter(name => g.ins[name]);
    const k = names.length, span = Math.min(hh - 22, 16 * (k - 1));
    arrive[n.id] = {};
    names.forEach((name, i) => {
      const b = g.ins[name];
      const t = { x: hx - 7, y: cy + (k > 1 ? (i / (k - 1) - 0.5) * span : 0) };
      arrive[n.id][name] = t;
      if (!wiresTo(n.id, name).length) parts.push(`<path class="link" d="${curve({ x: n.x + b.x + b.w, y: n.y + b.y + b.h / 2 }, t, 4)}" marker-end="url(#arr)"/>`);
    });
    const o = { x: n.x + g.out.x - 7, y: n.y + g.out.y + g.out.h / 2 };
    parts.push(`<path class="link" d="${curve({ x: hx + g.comp.w, y: cy }, o, 4)}" marker-end="url(#arr)"/>`);
  });
  /* the capability: the output of each component it requires, through its lane, and the credential of each
     parameter, into the card */
  if (CAPGEO) {
    const g = CAPGEO, cy = g.y + g.card.y + g.card.h / 2;
    const k = g.ins.length, span = Math.min(g.card.h - 22, 16 * (k - 1));
    g.ins.forEach((b, i) => {
      const t = { x: g.x + g.card.x - 7, y: cy + (k > 1 ? (i / (k - 1) - 0.5) * span : 0) };
      const d = b.requires === null ? curve({ x: g.x + b.x + b.w, y: g.y + b.y + b.h / 2 }, t, 4) : throughLane(outPort(S.nodes[b.requires]), g.x, g.y, b, t);
      parts.push(`<path class="link cap" d="${d}" marker-end="url(#arr-cap)"/>`);
    });
  }
  /* wires: an output, through the lane of the input it is wired to, into that Policy Component */
  let tool = "";
  S.wires.forEach(w => {
    const from = S.nodes[w.from], to = S.nodes[w.to];
    const a = outPort(from), b = inPort(to, w.input);
    const d = throughLane(a, to.x, to.y, GEO[w.to].ins[w.input], arrive[w.to][w.input]);
    let cls = "wire";
    if (ui.sel && ui.sel.kind === "wire" && ui.sel.id === w.id) {
      cls += " selected";
      tool = `<button type="button" class="wire-tool" data-act="wire-disconnect" data-wire="${w.id}" style="left:${f1((a.x + b.x) / 2)}px;top:${f1((a.y + b.y) / 2)}px">Disconnect</button>`;
    }
    if (sim) {
      if (sim.shortcuts.some(s => s.node === w.to && s.input === w.input)) cls += " shortcut";
      else if (!sim.order.includes(w.to) || !sim.order.includes(w.from)) cls += " idle";
    }
    parts.push(`<path class="wire-hit" data-wire="${w.id}" d="${d}"/><path class="${cls}" d="${d}" marker-end="url(#arr-wire)"/>`);
  });
  if (ui.drag && ui.drag.type === "connect" && ui.drag.moved && S.nodes[ui.drag.from]) {
    parts.push(`<path class="wire temp" d="${curve(outPort(S.nodes[ui.drag.from]), ui.drag.at, 40)}"/>`);
  }
  wiresEl.innerHTML = parts.join("");
  $("wire-tools").innerHTML = tool;
}

function applyView() {
  const v = ui.view;
  world.style.transform = `translate(${v.x}px, ${v.y}px) scale(${v.k})`;
  canvas.style.backgroundSize = `${22 * v.k}px ${22 * v.k}px`;
  canvas.style.backgroundPosition = `${v.x}px ${v.y}px`;
}

function renderCanvas() {
  const sim = ui.tab === "sim" ? simulate() : null;
  renderNodes(sim);
  measure();
  placeCap();
  renderWires(sim);
  markPorts();
  renderLegend();
}

/* the legend names only what is on the canvas: the subjects of the credentials drawn; the capability is drawn
   with the first component */
function renderLegend() {
  const box = $("legend");
  box.hidden = !Object.keys(S.nodes).length;
  if (box.hidden) { box.innerHTML = ""; return; }
  const used = new Set();
  Object.values(S.nodes).forEach(n => {
    const c = comp(n);
    Object.entries(c.inputs).forEach(([name, inp]) => { if (!wiresTo(n.id, name).length) used.add(inp.about); });
    used.add(c.output.about);
  });
  if (S.operation !== null) used.add(operation().about);
  const t = document.createElement("template");
  t.innerHTML = PolicyGraph.shapes.legend([...used], CAT.subjects, []);
  box.replaceChildren(t.content);
}

function render() {
  syncTrust();
  syncPresented();
  renderCanvas();
  renderTray();
  renderSide();
  if (document.activeElement !== $("card-name")) $("card-name").value = S.name;
  save();
}

/* ---------- tray ---------- */
function renderTray() {
  const issues = checks();
  const errors = issues.filter(i => i.level === "error").length;
  const warns = issues.length - errors;
  const c = $("count-checks");
  c.textContent = issues.length ? String(issues.length) : "OK";
  c.className = "count " + (errors ? "bad" : warns ? "warn" : "good");
  document.querySelectorAll(".tab").forEach(t => t.setAttribute("aria-selected", String(t.dataset.tab === ui.tab)));
  const body = $("tray-body");
  body.setAttribute("aria-labelledby", "tab-" + ui.tab);
  if (ui.tab === "checks") body.innerHTML = trayChecks(issues);
  else if (ui.tab === "sim") body.innerHTML = traySim();
  else body.innerHTML = trayJson();
}

function trayChecks(issues) {
  if (!issues.length) return `<p class="ok-line">No problems.</p>`;
  return issues.map(i => `<div class="issue"><span class="lvl ${i.level}">${i.level === "error" ? "Error" : "Warning"}</span><span class="txt">${esc(i.text)}</span>${i.node ? `<button type="button" class="link-btn" data-select="${esc(i.node)}">Show</button>` : ""}</div>`).join("");
}

function missingText(m) {
  return m.issuer !== null ? `${m.type} (signed by ${issuerName(m.issuer)}, not trusted)` : `${m.type} (not presented)`;
}
/* The verdict, then what ran, what was skipped and what was presented in place of a component; a row only when
   it has something. A preview: it runs no Rego, so it does not check that the claims join up. */
function traySim() {
  if (S.operation === null) return `<p class="empty">Choose an operation first.</p>`;
  if (!S.requires.length) return `<p class="empty">Require a component first.</p>`;
  const sim = simulate();
  if (!sim) return `<p class="empty">Remove the loop first.</p>`;
  const miss = [];
  sim.missing.forEach(m => { if (!miss.some(x => x.type === m.type)) miss.push(m); });
  const verdict = sim.issued
    ? `<div class="verdict allow"><strong>Capability issued</strong></div>`
    : `<div class="verdict deny"><strong>No capability</strong>${miss.length ? `<span>Missing: ${esc(miss.map(missingText).join("; "))}</span>` : ""}</div>`;
  const chips = sim.order.map((id, i) => `<span class="chip ${sim.blocked.has(id) ? "bad" : "run"}">${i + 1} ${esc(label(id))}${sim.blocked.has(id) ? " · cannot run" : ""}</span>`).join("");
  const row = (title, id, items) => (items.length ? `<dt>${title}</dt><dd class="chips" id="${id}">${items.join("")}</dd>` : "");
  return `${verdict}<dl class="result">
    ${row("Runs", "sim-order", [chips])}
    ${row("Skipped", "sim-skipped", sim.skipped.map(id => `<span class="chip">${esc(label(id))}</span>`))}
    ${row("Presented instead", "sim-instead", sim.shortcuts.map(s => `<span class="chip good">${esc(s.type)} → ${esc(label(s.node))}</span>`))}
  </dl>`;
}

function trayJson() {
  return `<div class="json-bar"><button type="button" class="small-btn" data-act="copy-json">Copy JSON</button><button type="button" class="small-btn" data-act="download-json">Download graph.json</button></div><pre class="code" id="json-out">${esc(JSON.stringify(graphJson(), null, 2))}</pre>`;
}

/* ---------- side panel: the Simulate tab's settings; while building, the canvas holds every setting ---------- */
function renderSide() {
  const sim = ui.tab === "sim";
  $("side").innerHTML = sim ? policyDataCard() + issuersCard() + presentedCard() : "";
  /* the canvas narrows or widens with the panel: show the whole card again */
  if ($("side").hidden === sim) {
    $("side").hidden = !sim;
    document.querySelector(".workbench").classList.toggle("no-side", !sim);
    fit();
  }
}
function sideCard(title, body, id) {
  return `<section class="panel side-card" id="${id}"><header><h2>${title}</h2></header><div class="side-body">${body}</div></section>`;
}

/* a policy data value typed on the Simulate tab; "" until one is */
function pdValue(nodeId, key) {
  return Object.hasOwn(ui.sim.data, nodeId) && Object.hasOwn(ui.sim.data[nodeId], key) ? ui.sim.data[nodeId][key] : "";
}
function policyDataCard() {
  const nodes = runOrderAll().map(id => S.nodes[id]).filter(n => Object.keys(comp(n).policy_data).length);
  const body = nodes.length ? nodes.map(n => {
    const fields = Object.entries(comp(n).policy_data).map(([key, f]) => {
      const id = `pd-${esc(n.id)}-${esc(key)}`;
      return `<label class="field" for="${id}" title="${esc(f.description)}"><span><code>${esc(key)}</code> · ${esc(f.type)}</span><input type="text" id="${id}" data-act="pd" data-node="${esc(n.id)}" data-key="${esc(key)}" value="${esc(pdValue(n.id, key))}" spellcheck="false"></label>`;
    }).join("");
    return `<div class="blk"><div class="blk-head"><span class="blk-name">${esc(label(n.id))}</span></div>${fields}</div>`;
  }).join("") : `<p class="empty">None.</p>`;
  return sideCard("Policy data", body, "side-pd");
}

function issuersCard() {
  const types = presentedTypes().filter(p => p.registry);
  const body = types.length ? types.map(({ type }) => {
    const list = issuersFor(type);
    const ticked = ui.sim.trusted[type];
    const opts = list.map((iss, k) => {
      const id = `tr-${esc(type)}-${k}`;
      return `<label class="check" for="${id}"><input type="checkbox" id="${id}" data-act="trust" data-type="${esc(type)}" data-issuer="${esc(iss.id)}"${ticked.includes(iss.id) ? " checked" : ""}><span>${esc(iss.name)}<small>${esc(iss.id)}</small></span></label>`;
    }).join("");
    return `<div class="blk"><div class="blk-head"><span class="blk-name">${esc(type)}</span>${list.length ? "" : '<span class="blk-sub">No example issuer.</span>'}</div>${opts}</div>`;
  }).join("") : `<p class="empty">None.</p>`;
  /* none ticked trusts every example issuer, as the contract leaves an empty list to its registry */
  return sideCard("Trusted issuers", (types.length ? `<p class="hint" id="trust-rule">None ticked: all trusted.</p>` : "") + body, "side-trust");
}

function presentedCard() {
  const types = presentedTypes();
  const rows = types.map(p => {
    const iss = ui.sim.presented[p.type];
    const id = "pc-" + esc(p.type);
    const box = `<input type="checkbox" id="${id}" data-act="sim-present" data-type="${esc(p.type)}"${iss !== null ? " checked" : ""}>
      <label for="${id}">${esc(p.type)}${p.required ? "" : '<span class="tag">optional</span>'}</label>`;
    /* its component checks it against a key it supplies, so who signed it does not matter */
    if (!p.registry) return `<div class="wallet-row">${box}<p class="hint">checked by key</p></div>`;
    const trusted = trustedFor(p.type);
    const opts = issuersFor(p.type).concat([UNKNOWN]).map(i => `<option value="${esc(i.id)}"${iss === i.id ? " selected" : ""}>Signed by ${esc(i.name)}${trusted.includes(i.id) ? "" : " (not trusted)"}</option>`).join("");
    return `<div class="wallet-row">${box}
      <select id="${id}-issuer" aria-label="Issuer of the presented ${esc(p.type)}" data-act="sim-issuer" data-type="${esc(p.type)}"${iss !== null ? "" : " disabled"}>${opts}</select></div>`;
  }).join("");
  const presets = `<div class="presets"><button type="button" class="small-btn" data-act="sim-preset" data-preset="required">Required</button><button type="button" class="small-btn" data-act="sim-preset" data-preset="none">None</button></div>`;
  return sideCard("Presented credentials", rows ? presets + rows : `<p class="empty">None.</p>`, "side-presented");
}

/* ---------- component details dialog ---------- */
function openComponent(componentId, nodeId) {
  const c = COMPONENTS[componentId];
  const ins = Object.values(c.inputs).map(inp => credCard(inp.type, inp.about, inp.claims, newClaims(inp), "")).join("");
  const out = credCard(c.output.type, c.output.about, c.output.claims, [], "");
  const keys = Object.keys(c.policy_data);
  const data = keys.length
    ? `<dl class="pd-list">${keys.map(k => `<div><dt>${esc(k)}<span>${esc(c.policy_data[k].type)}</span></dt><dd>${esc(c.policy_data[k].description)}</dd></div>`).join("")}</dl>`
    : `<p class="empty" style="margin:0">None.</p>`;
  const regoHtml = c.rego !== null
    ? `<button type="button" class="small-btn" data-act="toggle-rego" aria-expanded="false" aria-controls="modal-rego">Show Rego</button>
       <div class="rego-box" id="modal-rego" hidden><pre class="code" id="modal-rego-code">${esc(c.rego)}</pre>
       <div style="margin-top:8px"><button type="button" class="small-btn" data-act="copy-modal-rego" data-component="${esc(componentId)}">Copy Rego</button></div></div>`
    : `<p class="empty" id="modal-no-rego" style="margin:0">Not written yet.</p>`;
  const where = c.group === "card" ? `<div class="modal-sub">${esc(CAT.cards[c.card].name)} · ${esc(c.duo)}</div>` : "";
  $("modal-box").innerHTML = `
    <header class="modal-head"><div><h2 id="modal-title"><i class="lg lg-card" aria-hidden="true"></i>${brk(c.name)}</h2><div class="modal-sub">${esc(c.package)}</div>${where}</div>
      <button type="button" class="icon-btn" data-act="close-modal" aria-label="Close">${ICON_X}</button></header>
    <div class="modal-body">
      <p class="modal-desc">${esc(c.summary)}</p>
      <h3>Inputs</h3>
      <div class="io-cards" id="modal-inputs">${ins}</div>
      <h3>Output</h3>
      <div class="io-cards" id="modal-output">${out}</div>
      <h3>Policy data</h3>
      ${data}
      <h3>Rego</h3>
      ${regoHtml}
    </div>
    <footer class="modal-foot"><button type="button" class="btn" data-act="close-modal">Close</button>${nodeId ? "" : `<button type="button" class="btn primary" data-act="add-component" data-component="${esc(componentId)}">Add to canvas</button>`}</footer>`;
  ui.modal = { opener: document.activeElement };
  $("modal").hidden = false;
  $("modal-box").querySelector("[data-act='close-modal']").focus();
}
function closeModal() {
  if (!ui.modal) return;
  $("modal").hidden = true;
  const opener = ui.modal.opener;
  ui.modal = null;
  if (opener && document.contains(opener)) opener.focus();
}
$("modal").addEventListener("click", e => {
  if (e.target === $("modal")) { closeModal(); return; }
  const t = e.target.closest("[data-act]");
  if (!t) return;
  const act = t.dataset.act;
  if (act === "close-modal") closeModal();
  else if (act === "toggle-rego") {
    const box = $("modal-rego");
    box.hidden = !box.hidden;
    t.setAttribute("aria-expanded", String(!box.hidden));
    t.textContent = box.hidden ? "Show Rego" : "Hide Rego";
  } else if (act === "copy-modal-rego") copyText(COMPONENTS[t.dataset.component].rego, $("modal-rego-code"));
  else if (act === "add-component") { closeModal(); addComponent(t.dataset.component); }
});

/* ---------- actions ---------- */
function select(s) { ui.sel = s; renderCanvas(); if (ui.tab !== "sim") renderSide(); }

function toast(msg, bad) {
  const t = $("toast");
  t.textContent = msg;
  t.className = "toast" + (bad ? " bad" : "");
  t.hidden = false;
  clearTimeout(ui.toastTimer);
  ui.toastTimer = setTimeout(() => { t.hidden = true; }, 2800);
}

/* An input takes one source, so a wired input takes no second wire. */
function tryConnect(from, to, input) {
  const src = comp(S.nodes[from]);
  const inp = comp(S.nodes[to]).inputs[input];
  if (from === to) return toast("A component cannot take its own output.", true), false;
  if (inp.type !== src.output.type) return toast(`That input takes ${inp.type}, not ${src.output.type}.`, true), false;
  if ("supplied_key" in inp) return toast(`That input takes only a presented ${inp.type}.`, true), false;
  if (reaches(to, from)) return toast("That wire would make a loop.", true), false;
  const ws = wiresTo(to, input);
  if (ws.some(w => w.from === from)) return toast("Already wired."), false;
  if (ws.length) return toast(`That input already takes the output of ${label(ws[0].from)}.`, true), false;
  wire(S, from, to, input);
  render();
  return true;
}

function boxOf(n) {
  const g = GEO[n.id] || { w: 430, h: 180 };
  return { x: n.x, y: n.y - 30, w: g.w, h: g.h + 60 };
}
/* the first free spot in view for a component of this size, scanning rows from the top left; else right of everything */
function freeSpot(newId) {
  const r = canvas.getBoundingClientRect(), v = ui.view;
  const x0 = -v.x / v.k, y0 = -v.y / v.k, vw = r.width / v.k, vh = r.height / v.k;
  const g = GEO[newId] || { w: 430, h: 200 }, W = g.w, H = g.h + 30, M = 24;
  const boxes = Object.values(S.nodes).filter(n => n.id !== newId).map(boxOf);
  /* and the capability's, where it stays: right of the components it requires (while it requires none, it
     moves right of every component, the new one too) */
  if (S.requires.length) boxes.push(capBox());
  const free = (x, y) => boxes.every(b => x + W + M <= b.x || b.x + b.w + M <= x || y + H + M <= b.y || b.y + b.h + M <= y);
  for (let y = y0 + 40; y + H <= y0 + vh - 56 / v.k; y += 30) {   /* clear of the toast and zoom buttons */
    for (let x = x0 + 24; x + W <= x0 + vw - 10; x += 30) if (free(x, y)) return { x, y, inView: true };
  }
  const right = boxes.length ? Math.max(...boxes.map(b => b.x + b.w)) + 60 : x0 + 24;
  const top = boxes.length ? Math.min(...boxes.map(b => b.y)) + 30 : y0 + 40;
  return { x: right, y: top, inView: false };
}
function addComponent(componentId, at) {
  const n = addNode(S, componentId, -100000, -100000);
  ui.sel = { kind: "node", id: n.id };
  render();                                    /* measures the new component */
  const p = at || freeSpot(n.id);
  n.x = Math.round(p.x);
  n.y = Math.round(p.y);
  render();
  if (!at && !p.inView) fit();
}

/* an output wired to nothing is accepted presented nowhere */
function dropLooseAccepts() {
  Object.values(S.nodes).forEach(n => { if (!wiresFrom(n.id).length) n.accept = false; });
}

function removeNode(id) {
  delete S.nodes[id];
  delete ui.sim.data[id];
  S.requires = S.requires.filter(r => r !== id);
  S.wires = S.wires.filter(w => w.from !== id && w.to !== id);
  dropLooseAccepts();
  ui.sel = null;
  render();
}

function disconnect(wid) {
  S.wires = S.wires.filter(x => x.id !== wid);
  dropLooseAccepts();
  if (ui.sel && ui.sel.kind === "wire" && ui.sel.id === wid) ui.sel = null;
  render();
}

/* every input the component's output is wired to also accepts it presented, or none does */
function setAccept(nodeId, on) {
  S.nodes[nodeId].accept = on;
  render();
}

/* the capability requires the component, after those it already requires, or no longer */
function setRequired(nodeId, on) {
  S.requires = S.requires.filter(id => id !== nodeId);
  if (on) S.requires.push(nodeId);
  render();
}

function setOperation(op) {
  S.operation = op;
  render();
}

/* lay the components out in columns, from the inputs on the left to the components the capability requires on
   the right; the capability follows them */
function arrange() {
  const ids = Object.keys(S.nodes);
  if (!ids.length) return;
  const memo = {};
  const depth = (id, seen) => {
    if (memo[id] !== undefined) return memo[id];
    if (seen.has(id)) return 0;
    seen.add(id);
    const outs = S.wires.filter(w => w.from === id);
    const d = outs.length ? 1 + Math.max(...outs.map(w => depth(w.to, seen))) : 0;
    seen.delete(id);
    return (memo[id] = d);
  };
  ids.forEach(id => depth(id, new Set()));
  const maxD = Math.max(...ids.map(id => memo[id]));
  const colW = Math.max(...ids.map(id => (GEO[id] ? GEO[id].w : 430))) + 64;
  const cols = [];
  ids.forEach(id => { const c = maxD - memo[id]; (cols[c] = cols[c] || []).push(id); });
  const placed = new Set();
  for (let c = cols.length - 1; c >= 0; c--) {
    const want = (cols[c] || []).map(id => {
      const g = GEO[id] || { h: 180, out: { y: 0, h: 60 } };
      const outs = S.wires.filter(w => w.from === id && placed.has(w.to));
      const y = outs.length ? outs.reduce((s, w) => s + inPort(S.nodes[w.to], w.input).y, 0) / outs.length - (g.out.y + g.out.h / 2) : 0;
      return { id, y, h: g.h };
    }).sort((a, b) => a.y - b.y);
    let bottom = -Infinity;
    want.forEach(o => { o.y = Math.max(o.y, bottom + 56); bottom = o.y + o.h; });
    want.forEach(o => { S.nodes[o.id].x = c * colW; S.nodes[o.id].y = Math.round(o.y); placed.add(o.id); });
  }
  const minY = Math.min(...ids.map(id => S.nodes[id].y));
  ids.forEach(id => { S.nodes[id].y -= minY; });
}

function load(st) {
  S = st;
  ui.sel = null;
  ui.connect = null;
  clearTimeout(ui.toastTimer);
  $("toast").hidden = true;
  ui.sim = blankSim();
  render();
  arrange();
  render();
  fit();
}
/* open a graph.json onto the canvas, or say why it cannot be */
function loadGraph(g, what) {
  let st;
  try { st = readGraph(g); } catch (err) { toast(`Could not open ${what}: ${err.message}.`, true); return; }
  load(st);
  /* the asset owner sets policy data and trusted issuers when exposing an asset */
  const owners = Object.values(g.nodes).some(n => Object.keys(n.policy_data).length) || Object.values(g.trusted_issuers).some(l => l.length);
  if (owners) toast("Policy data and trusted issuers left out.");
}

/* ---------- graph.json out ---------- */
function download() {
  const url = URL.createObjectURL(new Blob([graphText()], { type: "application/json" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = "graph.json";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 40000);
  const errors = checks().filter(i => i.level === "error").length;
  if (errors) toast(`Downloaded with ${errors} ${errors === 1 ? "error" : "errors"}.`, true);
}

/* ---------- view ---------- */
function canvasPoint(e) {
  const r = canvas.getBoundingClientRect();
  return { x: (e.clientX - r.left - ui.view.x) / ui.view.k, y: (e.clientY - r.top - ui.view.y) / ui.view.k };
}
function fit() {
  const ns = Object.values(S.nodes);
  const r = canvas.getBoundingClientRect();
  if (!ns.length || !r.width) { ui.view = { x: 24, y: 24, k: 0.7 }; applyView(); return; }
  const boxes = ns.map(boxOf).concat([capBox()]);
  const minX = Math.min(...boxes.map(b => b.x)) - 12, minY = Math.min(...boxes.map(b => b.y));
  const maxX = Math.max(...boxes.map(b => b.x + b.w)) + 12, maxY = Math.max(...boxes.map(b => b.y + b.h));
  const k = Math.max(0.12, Math.min(1, (r.width - 32) / (maxX - minX), (r.height - 60) / (maxY - minY)));
  ui.view = { k, x: (r.width - (maxX - minX) * k) / 2 - minX * k, y: Math.max(8, (r.height - 48 - (maxY - minY) * k) / 2) - minY * k };
  applyView();
}
function zoomBy(f, cx, cy) {
  const r = canvas.getBoundingClientRect();
  const px = cx === undefined ? r.width / 2 : cx, py = cy === undefined ? r.height / 2 : cy;
  const v = ui.view, k = Math.max(0.12, Math.min(1.6, v.k * f));
  v.x = px - (px - v.x) * (k / v.k);
  v.y = py - (py - v.y) * (k / v.k);
  v.k = k;
  applyView();
}

function canWire(from, toId, input) {
  const src = comp(S.nodes[from]);
  const inp = comp(S.nodes[toId]).inputs[input];
  return toId !== from && inp.type === src.output.type && !("supplied_key" in inp) && !reaches(toId, from)
    && !wiresTo(toId, input).length;
}
function markPorts(hot) {
  const c = ui.drag && ui.drag.type === "connect" ? ui.drag.from : ui.connect;
  document.querySelectorAll(".n-in[data-node]:not(.lane)").forEach(p => {
    p.classList.remove("ok", "no", "hot");
    if (!c || !S.nodes[c]) return;
    const good = canWire(c, p.dataset.node, p.dataset.input);
    p.classList.add(good ? "ok" : "no");
    if (hot === p && good) p.classList.add("hot");
  });
  document.querySelectorAll(".n-out").forEach(o => o.classList.toggle("from", !!c && o.dataset.node === c));
  canvas.classList.toggle("connecting", !!c);
}

/* ---------- pointer: canvas ---------- */
canvas.addEventListener("pointerdown", e => {
  if (e.button !== 0 || e.target.closest(".zoom, .toast, .n-tools, .wire-tool, .ap, .cap-op")) return;
  const outEl = e.target.closest(".n-out[data-node]");
  if (outEl) {
    e.preventDefault();
    ui.drag = { type: "connect", from: outEl.dataset.node, sx: e.clientX, sy: e.clientY, moved: false, at: canvasPoint(e) };
    canvas.setPointerCapture(e.pointerId);
    markPorts();
    return;
  }
  const inEl = e.target.closest(".n-in[data-node]");
  if (inEl) {
    e.preventDefault();
    if (ui.connect) { const from = ui.connect; ui.connect = null; tryConnect(from, inEl.dataset.node, inEl.dataset.input); markPorts(); }
    else select({ kind: "node", id: inEl.dataset.node });
    return;
  }
  const hit = e.target.closest(".wire-hit");
  if (hit) { select({ kind: "wire", id: hit.dataset.wire }); return; }
  const nodeEl = e.target.closest(".node[data-node]");
  if (nodeEl) {
    const id = nodeEl.dataset.node;
    if (ui.connect) { ui.connect = null; markPorts(); }
    if (!(ui.sel && ui.sel.kind === "node" && ui.sel.id === id)) select({ kind: "node", id });
    if (e.target.closest(".pcw")) {
      const n = S.nodes[id];
      ui.drag = { type: "node", id, sx: e.clientX, sy: e.clientY, ox: n.x, oy: n.y, el: nodesEl.querySelector(`.node[data-node="${sel(id)}"]`) };
      canvas.setPointerCapture(e.pointerId);
    }
    return;
  }
  if (ui.connect) { ui.connect = null; markPorts(); }
  if (ui.sel) select(null);
  ui.drag = { type: "pan", sx: e.clientX, sy: e.clientY, vx: ui.view.x, vy: ui.view.y };
  canvas.classList.add("panning");
  canvas.setPointerCapture(e.pointerId);
});

canvas.addEventListener("pointermove", e => {
  const d = ui.drag;
  if (!d) return;
  if (d.type === "pan") {
    ui.view.x = d.vx + (e.clientX - d.sx);
    ui.view.y = d.vy + (e.clientY - d.sy);
    applyView();
  } else if (d.type === "node") {
    const n = S.nodes[d.id];
    n.x = Math.round(d.ox + (e.clientX - d.sx) / ui.view.k);
    n.y = Math.round(d.oy + (e.clientY - d.sy) / ui.view.k);
    if (d.el) d.el.style.transform = `translate(${n.x}px,${n.y}px)`;
    placeCap();
    renderWires(ui.tab === "sim" ? simulate() : null);
  } else if (d.type === "connect") {
    if (Math.hypot(e.clientX - d.sx, e.clientY - d.sy) > 4) d.moved = true;
    d.at = canvasPoint(e);
    const under = document.elementFromPoint(e.clientX, e.clientY);
    const p = under && under.closest(".n-in[data-node]");
    d.hot = p ? { node: p.dataset.node, input: p.dataset.input } : null;
    renderWires(null);
    markPorts(p);
  }
});

function endDrag() {
  const d = ui.drag;
  if (!d) return;
  ui.drag = null;
  canvas.classList.remove("panning");
  if (d.type === "node") save();
  if (d.type === "connect") {
    if (d.moved && d.hot) tryConnect(d.from, d.hot.node, d.hot.input);
    else if (!d.moved) ui.connect = d.from;
    renderWires(ui.tab === "sim" ? simulate() : null);
    markPorts();
  }
}
canvas.addEventListener("pointerup", endDrag);
canvas.addEventListener("pointercancel", endDrag);

/* buttons on the canvas, the accept switches, and keyboard activation of ports */
canvas.addEventListener("click", e => {
  const t = e.target.closest("[data-act]");
  if (t && t.tagName === "BUTTON") {
    const act = t.dataset.act;
    if (act === "node-info") openComponent(S.nodes[t.dataset.node].component, t.dataset.node);
    else if (act === "node-remove") removeNode(t.dataset.node);
    else if (act === "wire-disconnect") disconnect(t.dataset.wire);
    return;
  }
  const port = e.target.closest(".port");
  if (!port || e.detail !== 0) return;
  if (port.dataset.port === "out") { ui.connect = port.dataset.node; markPorts(); }
  else if (ui.connect) { const from = ui.connect; ui.connect = null; tryConnect(from, port.dataset.node, port.dataset.input); markPorts(); }
});
canvas.addEventListener("change", e => {
  const t = e.target;
  if (t.dataset.act === "accept") setAccept(t.dataset.node, t.checked);
  else if (t.dataset.act === "require") setRequired(t.dataset.node, t.checked);
  else if (t.dataset.act === "operation") setOperation(t.value);
});

canvas.addEventListener("wheel", e => {
  e.preventDefault();
  if (e.ctrlKey || e.metaKey) {
    const r = canvas.getBoundingClientRect();
    zoomBy(Math.exp(-e.deltaY * 0.0025), e.clientX - r.left, e.clientY - r.top);
  } else {
    ui.view.x -= e.deltaX;
    ui.view.y -= e.deltaY;
    applyView();
  }
}, { passive: false });

$("zoom-in").addEventListener("click", () => zoomBy(1.2));
$("zoom-out").addEventListener("click", () => zoomBy(1 / 1.2));
$("zoom-fit").addEventListener("click", fit);
$("arrange").addEventListener("click", () => { arrange(); render(); fit(); });

/* ---------- library: click for details, Add button, or drag onto the canvas ---------- */
let pal = null, suppressClick = false;
$("lib-list").addEventListener("pointerdown", e => {
  const item = e.target.closest(".lib-item");
  if (!item || e.target.closest(".lib-add") || e.button !== 0 || e.pointerType === "touch") return;
  pal = { component: item.dataset.component, sx: e.clientX, sy: e.clientY, ghost: null };
});
window.addEventListener("pointermove", e => {
  if (!pal) return;
  if (!pal.ghost && Math.hypot(e.clientX - pal.sx, e.clientY - pal.sy) > 6) {
    pal.ghost = document.createElement("div");
    pal.ghost.className = "ghost";
    pal.ghost.textContent = COMPONENTS[pal.component].name;
    document.body.appendChild(pal.ghost);
  }
  if (pal.ghost) { pal.ghost.style.left = e.clientX + 12 + "px"; pal.ghost.style.top = e.clientY + 8 + "px"; }
});
window.addEventListener("pointerup", e => {
  if (!pal) return;
  const p = pal;
  pal = null;
  if (!p.ghost) return;
  p.ghost.remove();
  suppressClick = true;
  setTimeout(() => { suppressClick = false; }, 0);
  const r = canvas.getBoundingClientRect();
  if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) return;
  const pt = canvasPoint(e);
  addComponent(p.component, { x: pt.x - 200, y: pt.y - 40 });
});
$("lib-list").addEventListener("click", e => {
  const t = e.target.closest("[data-act]");
  if (!t || suppressClick) return;
  if (t.dataset.act === "open-component") openComponent(t.dataset.component);
  else if (t.dataset.act === "add-component") addComponent(t.dataset.component);
});
$("lib-search").addEventListener("input", e => { ui.filter = e.target.value; renderLibrary(); });

/* ---------- side panel & tray events ---------- */
function handleClick(e) {
  const t = e.target.closest("[data-act], [data-select]");
  if (!t) return;
  if (t.dataset.select) { if (S.nodes[t.dataset.select]) select({ kind: "node", id: t.dataset.select }); return; }
  const act = t.dataset.act;
  if (act === "copy-json") copyText(graphText(), $("json-out"));
  else if (act === "download-json") download();
  else if (act === "sim-preset") simPreset(t.dataset.preset);
}
function handleChange(e) {
  const t = e.target;
  const act = t.dataset.act;
  if (!act) return;
  if (act === "trust") {
    const type = t.dataset.type;
    const now = new Set(ui.sim.trusted[type]);
    if (t.checked) now.add(t.dataset.issuer); else now.delete(t.dataset.issuer);
    ui.sim.trusted[type] = issuersFor(type).map(i => i.id).filter(id => now.has(id));
  } else if (act === "sim-present") {
    const type = t.dataset.type;
    ui.sim.presented[type] = t.checked ? firstIssuer(presentedTypes().find(p => p.type === type)) : null;
  } else if (act === "sim-issuer") ui.sim.presented[t.dataset.type] = t.value;
  else return;
  render();
}
function handleInput(e) {
  const t = e.target;
  if (t.dataset.act !== "pd") return;
  if (!Object.hasOwn(ui.sim.data, t.dataset.node)) ui.sim.data[t.dataset.node] = {};
  ui.sim.data[t.dataset.node][t.dataset.key] = t.value;
}
["side", "tray-body"].forEach(id => {
  $(id).addEventListener("click", handleClick);
  $(id).addEventListener("change", handleChange);
  $(id).addEventListener("input", handleInput);
});

function simPreset(kind) {
  ui.sim.presented = {};
  presentedTypes().forEach(p => { ui.sim.presented[p.type] = kind === "required" && p.required ? firstIssuer(p) : null; });
  render();
}

function copyText(text, el) {
  const done = () => toast("Copied.");
  const fallback = () => {
    const range = document.createRange();
    range.selectNodeContents(el);
    const s = window.getSelection();
    s.removeAllRanges();
    s.addRange(range);
    toast("Selected: press Ctrl+C or ⌘C.");
  };
  try { navigator.clipboard.writeText(text).then(done, fallback); } catch (err) { fallback(); }
}

document.querySelectorAll(".tab").forEach(t => t.addEventListener("click", () => { ui.tab = t.dataset.tab; ui.connect = null; renderCanvas(); renderTray(); renderSide(); }));
$("card-name").addEventListener("input", e => { S.name = e.target.value; if (ui.tab === "json") renderTray(); save(); });
$("load-select").addEventListener("change", e => {
  const v = e.target.value;
  e.target.value = "";
  if (v === "empty") load(blankState());
  else if (v === "file") $("load-file").click();
  else if (v.startsWith("card:")) loadGraph(CAT.cards[v.slice(5)].graph, CAT.cards[v.slice(5)].name);
});
$("load-file").addEventListener("change", e => {
  const file = e.target.files[0];
  e.target.value = "";
  if (!file) return;   /* the picker was cancelled */
  file.text().then(text => {
    let g;
    try { g = JSON.parse(text); } catch (err) { toast(`Could not open ${file.name}: it is not JSON (${err.message}).`, true); return; }
    loadGraph(g, file.name);
  });
});
$("download").addEventListener("click", download);

document.addEventListener("keydown", e => {
  if (ui.modal) { if (e.key === "Escape") closeModal(); return; }
  const active = document.activeElement;
  const tag = (active && active.tagName) || "";
  if (["INPUT", "SELECT", "TEXTAREA"].includes(tag)) return;
  if (e.key === "Escape") {
    if (ui.connect) { ui.connect = null; markPorts(); }
    else if (ui.sel) select(null);
  } else if ((e.key === "Delete" || e.key === "Backspace") && ui.sel && (!active || active === document.body || canvas.contains(active))) {
    e.preventDefault();
    if (ui.sel.kind === "node") removeNode(ui.sel.id);
    else disconnect(ui.sel.id);
  }
});

/* ---------- persistence (this browser only) ---------- */
/* The draft is the graph JSON, which holds no Simulate values, and where each component sits. A draft that no
   longer reads (a component left the repository, say) is not restored, and the page says why. */
const STORE = "pf-policy-composer-v5";
let saveTimer = 0;
function saveNow() {
  clearTimeout(saveTimer);
  saveTimer = 0;
  const positions = {};
  Object.values(S.nodes).forEach(n => { positions[n.id] = [n.x, n.y]; });
  try { localStorage.setItem(STORE, JSON.stringify({ v: 5, graph: graphJson(), positions })); } catch (err) { /* storage unavailable */ }
}
function save() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(saveNow, 250);
}
window.addEventListener("pagehide", () => { if (saveTimer) saveNow(); });
document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden" && saveTimer) saveNow(); });
function restore() {
  let raw;
  try { raw = localStorage.getItem(STORE); } catch (err) { return null; }   /* storage unavailable */
  if (raw === null) return null;
  try {
    const d = JSON.parse(raw);
    if (!isObj(d) || !sameKeys(d, ["v", "graph", "positions"]) || d.v !== 5 || !isObj(d.positions)) throw new Error("it is not a draft of this composer");
    const st = readGraph(d.graph);
    Object.values(st.nodes).forEach(n => {
      const p = d.positions[n.id];
      if (!Array.isArray(p) || p.length !== 2 || !p.every(Number.isFinite)) throw new Error(`it does not place ${n.id}`);
      n.x = p[0];
      n.y = p[1];
    });
    return st;
  } catch (err) {
    toast(`Your saved draft was not restored: ${err.message}.`, true);
    return null;
  }
}

/* ---------- boot ---------- */
async function boot() {
  const res = await fetch("catalog.json");
  if (!res.ok) throw new Error(`catalog.json answered HTTP ${res.status}`);
  CAT = await res.json();
  COMPONENTS = CAT.components;
  renderLibrary();
  renderLoadMenu();
  const draft = restore();
  S = draft === null ? blankState() : draft;
  render();
  requestAnimationFrame(() => { fit(); document.documentElement.dataset.ready = "true"; });
  let lastWidth = canvas.getBoundingClientRect().width;
  window.addEventListener("resize", () => {
    const w = canvas.getBoundingClientRect().width;
    if (!ui.drag && Math.abs(w - lastWidth) > 40) fit();
    lastWidth = w;
  });
}
boot().catch(err => {
  const hint = $("canvas-hint");
  hint.hidden = false;
  hint.classList.add("bad");
  hint.textContent = `Could not load catalog.json: ${err.message}.`;
  throw err;
});
