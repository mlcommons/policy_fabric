// Policy graphs, drawn the same way in the webapp's read-only views and in the docs composer.
//
//   PolicyGraph.layout(graph, catalog) -> {items, wires, columns}   pure: what to draw, and where
//   PolicyGraph.render(element, graph, catalog, theme) -> {destroy}  draws it, refits on resize
//   PolicyGraph.shapes                                               the shapes, for the composer
//
// graph is a policy graph (version 4) and catalog the catalog tools/policy_catalog builds. theme is
// "light", "dark", or "auto" to follow prefers-color-scheme. policy_graph.css holds the look, the docs
// composer's too.

(function (root) {
    'use strict';

    var SEAL = '<svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 7.2a2.2 2.2 0 0 1 2.2-2.2h1a2.2 2.2 0 0 0 1.55-.64l.7-.7a2.2 2.2 0 0 1 3.12 0l.7.7c.41.41.97.64 1.55.64h1a2.2 2.2 0 0 1 2.2 2.2v1c0 .58.23 1.14.64 1.55l.7.7a2.2 2.2 0 0 1 0 3.12l-.7.7a2.2 2.2 0 0 0-.64 1.55v1a2.2 2.2 0 0 1-2.2 2.2h-1a2.2 2.2 0 0 0-1.55.64l-.7.7a2.2 2.2 0 0 1-3.12 0l-.7-.7a2.2 2.2 0 0 0-1.55-.64h-1a2.2 2.2 0 0 1-2.2-2.2v-1a2.2 2.2 0 0 0-.64-1.55l-.7-.7a2.2 2.2 0 0 1 0-3.12l.7-.7A2.2 2.2 0 0 0 5 8.2v-1"/><path d="m9 12 2 2 4-4"/></svg>';
    var KEY = '<svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true"><circle cx="5" cy="8" r="3.2" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M8.2 8H15M12.6 8v3M14.6 8v2" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>';
    var SLIDERS = '<svg width="11" height="11" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 6a2 2 0 1 0 4 0 2 2 0 1 0-4 0M4 6h8M16 6h4M6 12a2 2 0 1 0 4 0 2 2 0 1 0-4 0M4 12h2M10 12h10M15 18a2 2 0 1 0 4 0 2 2 0 1 0-4 0M4 18h11M19 18h1"/></svg>';
    var SCALE = '<svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v18M7 21h10M5 7h14M5 7l-3 7a3.5 3.5 0 0 0 6 0zM19 7l-3 7a3.5 3.5 0 0 0 6 0z"/></svg>';
    var LIST = '<svg width="11" height="11" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6h11M9 12h11M9 18h11M5 6v.01M5 12v.01M5 18v.01"/></svg>';

    var DEFAULTS = { '--vw': 176, '--pcw': 200, '--colgap': 36 };
    var MINIMUMS = { '--vw': 100, '--pcw': 108, '--colgap': 8 };

    function esc(s) {
        return String(s).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }

    // break a name only between the words of a CamelCase name and after . or _
    function brk(s) {
        return esc(s)
            .replace(/([a-z0-9])([A-Z])/g, '$1<wbr>$2')
            .replace(/([A-Z])([A-Z][a-z])/g, '$1<wbr>$2')
            .replace(/([._])/g, '$1<wbr>');
    }

    // ------------------------------------------------------------------ shapes
    // the claims a credential carries; none, no section
    function claimsSection(claims, newClaims) {
        var listed = claims.filter(function (c) { return c !== 'subject'; });
        if (!listed.length) return '';
        return '<div class="sec"><div class="lbl">' + LIST + 'claims</div><ul class="cl">' + listed.map(function (c) {
            return '<li>' + brk(c) + (newClaims.indexOf(c) !== -1 ? ' <span class="new">new</span>' : '') + '</li>';
        }).join('') + '</ul></div>';
    }

    // a credential: seal, type, "subject: <word>", claims; acceptedPresented adds the read-only switch row
    function credential(type, about, claims, newClaims, subjects, acceptedPresented, attrs) {
        return '<div class="vw s-' + esc(about) + '"' + attrs + '><span class="seal">' + SEAL + '</span><div class="vc">' +
            '<div class="vc-h"><div class="vc-t">' + brk(type) + '</div></div>' +
            '<div class="sec subj">subject: <b>' + esc(subjects[about].word) + '</b></div>' +
            claimsSection(claims, newClaims) +
            (acceptedPresented
                ? '<div class="ap on"><span class="ap-track"><span class="ap-thumb"></span></span>accept presented</div>'
                : '') +
            '</div></div>';
    }

    // a decision: whom it is about (null while that is not known) and the parameters it admits besides
    // its subject; no seal, since nobody signs it
    function decision(about, parameters, subjects, attrs) {
        var subject = about === null ? '' : '<div class="sec subj">subject: <b>' + esc(subjects[about].word) + '</b></div>';
        var admits = parameters.length
            ? '<div class="sec"><div class="lbl">' + LIST + 'admits</div><ul class="cl">' +
              parameters.map(function (p) { return '<li>' + brk(p) + '</li>'; }).join('') + '</ul></div>'
            : '';
        return '<div class="vd' + (about === null ? '' : ' s-' + esc(about)) + '"' + attrs + '><div class="vc dec">' +
            '<div class="vc-h">' + SCALE + '<div class="vc-t">Decision</div></div>' + subject + admits + '</div></div>';
    }

    // the adapter that makes a decision into the capability
    function adapter(attrs) {
        return '<div class="ad"' + attrs + '><div class="ad-tab">Adapter</div><div class="ad-box">ToCapability</div></div>';
    }

    // a Policy Component: its name, and the keys of its policy data when it takes some
    function component(name, policyData, attrs) {
        var data = policyData.length
            ? '<div class="sec"><div class="lbl">' + SLIDERS + 'policy data</div><ul class="cl">' +
              policyData.map(function (k) { return '<li>' + brk(k) + '</li>'; }).join('') + '</ul></div>'
            : '';
        return '<div class="pcw"' + attrs + '><div class="pc-tab">Policy Component</div><div class="pc">' +
            '<div class="pc-nm">' + brk(name) + '</div>' + data + '</div></div>';
    }

    function capability(operation, parameters, attrs) {
        return '<div class="vc cap"' + attrs + '><div class="vc-h">' + KEY + '<div class="vc-t"><span class="vc-sub">capability</span>' +
            brk(operation) + '</div></div>' +
            (parameters.length ? '<ul class="cl">' + parameters.map(function (p) { return '<li>' + brk(p) + '</li>'; }).join('') + '</ul>' : '') +
            '</div>';
    }

    // the legend names only what is drawn: the subjects used, in the catalog's order, then the rest
    function legend(subjectsUsed, subjects, extra) {
        var items = Object.keys(subjects).filter(function (k) { return subjectsUsed.indexOf(k) !== -1; }).map(function (k) {
            return '<span><i class="lg lg-vc s-' + esc(k) + '"></i>credential about ' + esc(subjects[k].legend) + '</span>';
        });
        items.push('<span><i class="lg lg-dec"></i>decision</span>');
        items.push('<span><i class="lg lg-card"></i>Policy Component</span>');
        items.push('<span><i class="lg lg-cap"></i>capability</span>');
        return '<div class="legend">' + items.concat(extra).join('') + '</div>';
    }

    // ------------------------------------------------------------------ layout
    // Whom a node's decision is about and the parameters it admits besides its subject: its
    // component's, or for a component that combines decisions, those of the decisions it takes
    // (about null when they are not about one kind of subject).
    function decisionOf(graph, catalog, n) {
        var c = catalog.components[graph.nodes[n].component];
        if (c.group !== 'decision') return { about: c.output.about, parameters: c.output.parameters };
        var abouts = [], parameters = [];
        Object.keys(c.inputs).forEach(function (name) {
            graph.nodes[n].inputs[name].nodes.forEach(function (m) {
                var d = decisionOf(graph, catalog, m);
                if (abouts.indexOf(d.about) === -1) abouts.push(d.about);
                d.parameters.forEach(function (p) { if (parameters.indexOf(p) === -1) parameters.push(p); });
            });
        });
        return { about: abouts.length === 1 ? abouts[0] : null, parameters: parameters.sort() };
    }

    // The items a graph expands into, the wires between them, and the columns they sit in, left to
    // right by their longest path to the capability; within a column, by the average position of
    // their neighbours (three sweeps each way).
    function layout(graph, catalog) {
        var items = {};
        var wires = [];
        Object.keys(graph.nodes).forEach(function (n) {
            var node = graph.nodes[n];
            var c = catalog.components[node.component];
            items['c:' + n] = { kind: 'component', node: n, name: c.name, policyData: Object.keys(c.policy_data) };
            Object.keys(node.inputs).forEach(function (name) {
                var spec = c.inputs[name];
                var source = node.inputs[name];
                if (source.from === 'nodes') {
                    source.nodes.forEach(function (m) { wires.push(['o:' + m, 'c:' + n]); });
                } else if (source.from === 'presented') {
                    items['p:' + n + ':' + name] = {
                        kind: 'credential', type: spec.type, about: spec.about, claims: spec.claims,
                        newClaims: 'new_claims' in spec ? spec.new_claims : [], acceptedPresented: false,
                    };
                    wires.push(['p:' + n + ':' + name, 'c:' + n]);
                } else {
                    wires.push(['o:' + source.node, 'c:' + n]);
                }
            });
            if (c.output.type === 'Decision') {
                var d = decisionOf(graph, catalog, n);
                items['o:' + n] = { kind: 'decision', about: d.about, parameters: d.parameters };
            } else {
                items['o:' + n] = {
                    kind: 'credential', type: c.output.type, about: c.output.about, claims: c.output.claims,
                    newClaims: [], acceptedPresented: false,
                };
            }
            wires.push(['c:' + n, 'o:' + n]);
        });
        Object.keys(graph.nodes).forEach(function (n) {
            Object.keys(graph.nodes[n].inputs).forEach(function (name) {
                var source = graph.nodes[n].inputs[name];
                if (source.from === 'node' && source.accept_presented) items['o:' + source.node].acceptedPresented = true;
            });
        });
        // the adapter makes the capability's decision into the capability: the operation, with its parameters
        var capability = graph.capability;
        items.adapter = { kind: 'adapter' };
        items.cap = { kind: 'capability', operation: capability.operation, parameters: capability.parameters };
        wires.push(['o:' + capability.decision, 'adapter']);
        wires.push(['adapter', 'cap']);
        return { items: items, wires: wires, columns: columns(Object.keys(items), wires, 'cap') };
    }

    function columns(ids, wires, sink) {
        var succ = {}, pred = {}, dist = {}, pos = {};
        ids.forEach(function (id) { succ[id] = []; pred[id] = []; });
        wires.forEach(function (w) { succ[w[0]].push(w[1]); pred[w[1]].push(w[0]); });
        function distance(id) {
            if (!(id in dist)) {
                dist[id] = id === sink ? 0 : 1 + Math.max.apply(null, succ[id].map(distance));
            }
            return dist[id];
        }
        ids.forEach(distance);
        var top = Math.max.apply(null, ids.map(function (id) { return dist[id]; }));
        var cols = [];
        for (var i = 0; i <= top; i++) cols.push([]);
        ids.forEach(function (id) { cols[top - dist[id]].push(id); });

        function reindex(col) {
            col.forEach(function (id, k) { pos[id] = (k + 0.5) / col.length; });
        }
        function byNeighbours(neighbours) {
            return function (id) {
                var list = neighbours[id];
                return list.length ? list.reduce(function (s, x) { return s + pos[x]; }, 0) / list.length : pos[id];
            };
        }
        function sortBy(col, key) {
            var keyed = col.map(function (id, k) { return { id: id, key: key(id), k: k }; });
            keyed.sort(function (a, b) { return a.key - b.key || a.k - b.k; });
            return keyed.map(function (x) { return x.id; });
        }
        cols.forEach(reindex);
        for (var round = 0; round < 3; round++) {
            for (var l = 1; l < cols.length; l++) { cols[l] = sortBy(cols[l], byNeighbours(pred)); reindex(cols[l]); }
            for (var r = cols.length - 2; r >= 0; r--) { cols[r] = sortBy(cols[r], byNeighbours(succ)); reindex(cols[r]); }
        }
        return cols;
    }

    // ------------------------------------------------------------------ drawing
    function itemHtml(id, item, catalog) {
        var attrs = ' data-item="' + esc(id) + '"';
        if (item.kind === 'component') return component(item.name, item.policyData, attrs);
        if (item.kind === 'decision') return decision(item.about, item.parameters, catalog.subjects, attrs);
        if (item.kind === 'adapter') return adapter(attrs);
        if (item.kind === 'capability') return capability(item.operation, item.parameters, attrs);
        return credential(item.type, item.about, item.claims, item.newClaims, catalog.subjects, item.acceptedPresented, attrs);
    }

    // shrink cards, components and gaps by one factor until the graph fits its panel, down to the
    // minimums; past them the panel scrolls sideways
    function fit(graphEl, panel) {
        var v = {};
        Object.keys(DEFAULTS).forEach(function (k) { v[k] = DEFAULTS[k]; });
        function apply() { Object.keys(v).forEach(function (k) { graphEl.style.setProperty(k, v[k] + 'px'); }); }
        apply();
        var avail = panel.clientWidth - 24;
        for (var i = 0; i < 10 && graphEl.scrollWidth > avail; i++) {
            var f = Math.min(0.97, avail / graphEl.scrollWidth);
            Object.keys(v).forEach(function (k) { v[k] = Math.max(MINIMUMS[k], Math.floor(v[k] * f)); });
            apply();
        }
    }

    function drawWires(graphEl, wires, markerId) {
        var svg = graphEl.querySelector('svg');
        var box = graphEl.getBoundingClientRect();
        function anchor(id) {
            var n = graphEl.querySelector('[data-item="' + id.replace(/"/g, '\\"') + '"]');
            if (n.classList.contains('pcw')) n = n.querySelector('.pc');
            if (n.classList.contains('ad')) n = n.querySelector('.ad-box');
            var r = n.getBoundingClientRect();
            return { x: r.left - box.left, y: r.top - box.top, w: r.width, h: r.height };
        }
        svg.setAttribute('width', Math.ceil(graphEl.scrollWidth));
        svg.setAttribute('height', Math.ceil(graphEl.scrollHeight));
        var into = {};
        wires.forEach(function (w) { (into[w[1]] = into[w[1]] || []).push(w[0]); });
        function f(x) { return x.toFixed(1); }
        var d = '';
        Object.keys(into).forEach(function (target) {
            var tr = anchor(target);
            var list = into[target].map(anchor).sort(function (p, q) { return (p.y + p.h / 2) - (q.y + q.h / 2); });
            var k = list.length, span = Math.min(tr.h - 16, 18 * (k - 1));
            list.forEach(function (r, i) {
                var sx = r.x + r.w, sy = r.y + r.h / 2;
                var ty = tr.y + tr.h / 2 + (k > 1 ? (i / (k - 1) - 0.5) * span : 0);
                var tx = tr.x - 9;
                var dx = Math.max(16, (tx - sx) / 2);
                var out = target === 'cap';
                d += '<path class="edge' + (out ? ' out' : '') + '" d="M' + f(sx) + ',' + f(sy) + ' C' + f(sx + dx) + ',' + f(sy) +
                    ' ' + f(tx - dx) + ',' + f(ty) + ' ' + f(tx) + ',' + f(ty) + '" marker-end="url(#' + markerId + (out ? '-out' : '') + ')"/>';
            });
        });
        function marker(id, colour) {
            return '<marker id="' + id + '" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="7" markerHeight="7" orient="auto">' +
                '<path d="M0,0 L10,5 L0,10 z" style="fill: var(' + colour + ')"/></marker>';
        }
        svg.innerHTML = '<defs>' + marker(markerId, '--pf-ink-3') + marker(markerId + '-out', '--pf-grant') + '</defs>' + d;
    }

    var drawn = 0;

    function render(element, graph, catalog, theme) {
        var laid = layout(graph, catalog);
        var markerId = 'pf-wire-' + (++drawn);
        var used = [];
        Object.keys(laid.items).forEach(function (id) {
            var item = laid.items[id];
            if ((item.kind === 'credential' || item.kind === 'decision') && item.about !== null && used.indexOf(item.about) === -1) used.push(item.about);
        });
        element.classList.add('pf-graph');
        if (theme === 'auto') element.removeAttribute('data-theme');
        else element.setAttribute('data-theme', theme);
        element.innerHTML = '<div class="pf-panel"><div class="graph"><svg aria-hidden="true"></svg>' +
            laid.columns.map(function (col) {
                return '<div class="layer">' + col.map(function (id) { return itemHtml(id, laid.items[id], catalog); }).join('') + '</div>';
            }).join('') + '</div></div>' + legend(used, catalog.subjects, []);
        var panel = element.querySelector('.pf-panel');
        var graphEl = element.querySelector('.graph');
        var svg = graphEl.querySelector('svg');
        function draw() {
            // the wires still span the graph as last drawn: collapse them so only the cards are measured
            svg.setAttribute('width', 0);
            svg.setAttribute('height', 0);
            fit(graphEl, panel);
            drawWires(graphEl, laid.wires, markerId);
        }
        draw();
        var observer = new ResizeObserver(draw);
        observer.observe(panel);
        return {
            destroy: function () {
                observer.disconnect();
                element.innerHTML = '';
            },
        };
    }

    var api = {
        layout: layout,
        render: render,
        shapes: { credential: credential, decision: decision, adapter: adapter, component: component, capability: capability, legend: legend },
        icons: { SEAL: SEAL, KEY: KEY, SLIDERS: SLIDERS, LIST: LIST },
        esc: esc,
        brk: brk,
    };
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    else root.PolicyGraph = api;
})(this);
