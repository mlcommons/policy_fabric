// Asset dashboard.
//
// Before the asset is exposed, the Expose panel: the owner picks policy cards
// (those that fit this asset's guardian), whose graphs of policy components
// compose into one; fills each node's parameter form; and accepts authorities
// for each credential type the graph takes presented. A review line lists the
// ways requesters can meet the graph. Afterwards: the graph is drawn, trust can
// be withdrawn or added type by type, and each node's parameters edited.

(function () {
    function el(id) { return document.getElementById(id); }

    function readJson(id) {
        var node = el(id);
        return node ? JSON.parse(node.textContent) : null;
    }

    function unique(list) {
        return list.filter(function (x, i) { return list.indexOf(x) === i; });
    }

    // a fieldset with a legend and a body for one node's parameter form
    function nodeFieldset(n) {
        var set = document.createElement('fieldset');
        set.className = 'schema-fieldset';
        set.dataset.parameters = n.node;
        var legend = document.createElement('legend');
        legend.textContent = n.name;
        set.appendChild(legend);
        var body = document.createElement('div');
        set.appendChild(body);
        return { set: set, body: body };
    }

    // ------------------------------------------------------------- expose
    function exposePanel(cidUrl, data) {
        var selected = [];   // the chosen cards, in the order they are listed
        var chosen = {};     // credential type -> [DID, ...], for every type the platform knows
        var touched = {};    // types the owner has already seen, so defaults apply once
        Object.keys(data.facts).forEach(function (t) { chosen[t] = []; });
        var composed = null; // {graph, alternatives, nodes} of the selection
        var nodeForms = {};  // node -> its parameter form
        var drawn = null;    // the composed graph, drawn
        var composing = 0;   // the latest compose request; one answered after a later one is dropped

        function fact(type) { return data.facts[type]; }
        function byDid(did) {
            return data.authorities.filter(function (a) { return a.did === did; })[0];
        }
        function optionsFor(type) {
            return data.authorities.filter(function (a) { return a.facts.indexOf(type) !== -1; });
        }
        // the types the composed graph takes presented, and the ones the requester signs
        function neededFacts() {
            if (!composed) return [];
            var types = Object.keys(composed.graph.trusted_issuers);
            composed.alternatives.forEach(function (bundle) {
                Object.keys(bundle).forEach(function (role) { types = types.concat(bundle[role]); });
            });
            return unique(types);
        }
        function factNames(types) {
            return types.map(function (t) { return fact(t).name; }).join(', ');
        }

        // ---- 1. policies
        function renderCards() {
            var box = el('expose-cards');
            data.cards.forEach(function (card) {
                var item = document.createElement('div');
                item.className = 'option-item';
                item.dataset.card = card.name;
                var id = 'expose-card-' + card.id;
                item.innerHTML =
                    '<input type="checkbox" id="' + id + '">' +
                    '<label for="' + id + '">' +
                    '<span class="badge badge-code"></span> <strong></strong>' +
                    '<span class="option-rule"></span><small class="muted"></small></label>' +
                    '<button type="button" class="btn btn-sm">View</button>';
                item.querySelector('.badge-code').textContent = card.code;
                item.querySelector('strong').textContent = card.title;
                item.querySelector('.option-rule').textContent = card.rule;
                item.querySelector('small').textContent = 'Takes: ' + factNames(Object.keys(card.graph.trusted_issuers));
                item.querySelector('input').addEventListener('change', function (e) {
                    if (e.target.checked) {
                        selected.push(card);
                        selected.sort(function (a, b) { return data.cards.indexOf(a) - data.cards.indexOf(b); });
                    } else {
                        selected = selected.filter(function (c) { return c !== card; });
                    }
                    refresh();
                });
                item.querySelector('button').addEventListener('click', function () {
                    window.render.showCard(card.code + ' · ' + card.title, card.policy_card, card.rego_source, card.graph);
                });
                box.appendChild(item);
            });
        }

        // ---- 2. parameters, one generated form per node that takes them
        function renderParameters() {
            var box = el('expose-parameters');
            var values = {};
            Object.keys(nodeForms).forEach(function (n) { values[n] = nodeForms[n].value(); });
            box.innerHTML = '';
            nodeForms = {};
            (composed ? composed.nodes : []).forEach(function (n) {
                if (!Object.keys(n.schema).length) return;
                var parts = nodeFieldset(n);
                box.appendChild(parts.set);
                nodeForms[n.node] = window.schemaForm.render(parts.body, n.schema, n.node in values ? values[n.node] : {});
            });
            if (!box.children.length) {
                box.innerHTML = '<p class="muted">' + (composed ? 'No component of these policies takes parameters.' : 'Choose a policy first.') + '</p>';
            }
        }

        // ---- 3. accepted authorities, one row per credential type
        function choose(type, did, on) {
            var list = chosen[type];
            list = list.filter(function (d) { return d !== did; });
            if (on) list.push(did);
            chosen[type] = list;
        }

        function optionNode(type, authority) {
            var label = document.createElement('label');
            label.className = 'option-item authority-option';
            label.dataset.authority = authority.name;
            var cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.value = authority.did;
            cb.checked = chosen[type].indexOf(authority.did) !== -1;
            cb.addEventListener('change', function () {
                choose(type, authority.did, cb.checked);
                renderReview();
            });
            var text = document.createElement('span');
            text.innerHTML = '<strong></strong> <span class="badge badge-kind"></span>' +
                '<small class="muted"></small>';
            text.querySelector('strong').textContent = authority.name;
            var badge = text.querySelector('.badge-kind');
            badge.textContent = authority.kind_label;
            badge.classList.add('badge-kind-' + authority.kind);
            var details = [];
            if (authority.operator) details.push('operated by ' + authority.operator);
            if (authority.checks) details.push(authority.checks);
            text.querySelector('small').textContent = details.join(' · ');
            label.appendChild(cb);
            label.appendChild(text);
            return label;
        }

        function renderAuthorities() {
            var box = el('expose-authorities');
            box.innerHTML = '';
            neededFacts().forEach(function (type) {
                var row = document.createElement('div');
                row.className = 'fact-row';
                row.dataset.fact = type;
                var head = document.createElement('div');
                head.className = 'fact-head';
                head.innerHTML = '<strong></strong> <span class="did-display"></span><small class="muted"></small>';
                head.querySelector('strong').textContent = fact(type).name;
                head.querySelector('.did-display').textContent = type;
                head.querySelector('small').textContent = fact(type).meaning;
                row.appendChild(head);

                if (fact(type).self_asserted) {
                    var note = document.createElement('p');
                    note.className = 'muted';
                    note.textContent = 'Signed by the requester\'s own wallet and checked against its key; ' +
                        'no authority vouches for it.';
                    row.appendChild(note);
                    box.appendChild(row);
                    return;
                }

                var options = optionsFor(type);
                if (!touched[type]) {
                    touched[type] = true;
                    // A type only a single system authority issues, such as the
                    // session key, is accepted by default.
                    if (options.length === 1 && options[0].kind === 'system') choose(type, options[0].did, true);
                }
                var list = document.createElement('div');
                list.className = 'option-list';
                options.forEach(function (a) { list.appendChild(optionNode(type, a)); });
                chosen[type].forEach(function (did) {
                    if (!byDid(did)) {
                        list.appendChild(optionNode(type, {
                            did: did, name: did, kind: 'unlisted', kind_label: 'unlisted',
                        }));
                    }
                });
                if (!list.children.length) {
                    list.innerHTML = '<p class="muted">No authority in the directory issues this yet.</p>';
                }
                row.appendChild(list);

                var paste = document.createElement('details');
                paste.className = 'paste-did';
                paste.innerHTML = '<summary>Paste a DID</summary>' +
                    '<div class="trust-add"><input type="text" placeholder="did:pdo:…">' +
                    '<button type="button" class="btn btn-sm">Accept</button></div>';
                paste.querySelector('button').addEventListener('click', function () {
                    var did = paste.querySelector('input').value.trim();
                    if (!did) return;
                    choose(type, did, true);
                    renderAuthorities();
                    renderReview();
                });
                row.appendChild(paste);
                box.appendChild(row);
            });
            if (!box.children.length) box.innerHTML = '<p class="muted">Choose a policy first.</p>';
        }

        function renderTrustLists() {
            var box = el('expose-trust-lists');
            box.innerHTML = '';
            var facts = neededFacts();
            data.trust_lists.forEach(function (list) {
                var relevant = list.entries.filter(function (e) {
                    return e.credential_types.some(function (t) { return facts.indexOf(t) !== -1; });
                });
                if (!relevant.length) return;
                var btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'btn btn-sm';
                btn.dataset.trustList = list.name;
                btn.textContent = 'Use trust list: ' + list.name;
                btn.title = list.description;
                btn.addEventListener('click', function () {
                    relevant.forEach(function (e) {
                        e.credential_types.forEach(function (t) {
                            if (facts.indexOf(t) !== -1) choose(t, e.did, true);
                        });
                    });
                    renderAuthorities();
                    renderReview();
                });
                box.appendChild(btn);
            });
        }

        // ---- the graph the selection composes into
        function renderGraph() {
            var box = el('expose-graph');
            if (drawn) drawn.destroy();
            drawn = null;
            box.hidden = !composed;
            if (composed) drawn = window.PolicyGraph.render(box, composed.graph, readJson('policy-catalog'), 'light');
        }

        function compose() {
            var request = ++composing;
            if (!selected.length) {
                composed = null;
                return Promise.resolve();
            }
            return window.api.post('/api/assets/' + cidUrl + '/compose/', {
                cards: selected.map(function (c) { return c.id; }),
            }).then(function (res) {
                if (request === composing) composed = res;
            }, function (err) {
                if (request !== composing) return;
                composed = null;
                window.flash(err.message, 'error');
            });
        }

        // a way to meet the graph is open when every credential in it is accepted from
        // some authority, or signed by the requester
        function openAlternatives() {
            return composed.alternatives.filter(function (bundle) {
                return Object.keys(bundle).every(function (role) {
                    return bundle[role].every(function (t) { return fact(t).self_asserted || chosen[t].length; });
                });
            });
        }

        // ---- 4. review
        function renderReview() {
            if (!composed) {
                el('expose-review').textContent = 'Choose a policy first.';
                el('expose-submit').disabled = true;
                return;
            }
            var open = openAlternatives();
            el('expose-review').textContent = 'Requesters will present one of: ' + composed.alternatives.map(function (bundle) {
                var names = [];
                Object.keys(bundle).forEach(function (role) {
                    names = names.concat(bundle[role].map(function (t) { return fact(t).name; }));
                });
                return names.join(' + ') + (open.indexOf(bundle) === -1 ? ' (no authority accepted for all)' : '');
            }).join('; or ') + '.';
            el('expose-submit').disabled = !open.length;
        }

        function refresh() {
            compose().then(function () {
                renderParameters();
                renderTrustLists();
                renderAuthorities();
                renderReview();
                renderGraph();
            });
        }

        function submit() {
            var errors = [];
            var parameters = {};
            composed.nodes.forEach(function (n) {
                if (n.node in nodeForms) {
                    nodeForms[n.node].errors().forEach(function (e) { errors.push(n.name + ': ' + e); });
                    parameters[n.node] = nodeForms[n.node].value();
                } else {
                    parameters[n.node] = {};
                }
            });
            if (errors.length) {
                window.flash(errors.join('\n'), 'error');
                return;
            }
            var authorities = {};
            Object.keys(composed.graph.trusted_issuers).forEach(function (t) {
                if (!fact(t).self_asserted) authorities[t] = chosen[t];
            });
            window.progress.run('/assets/' + cidUrl + '/expose/stream/', {
                cards: selected.map(function (c) { return c.id; }),
                parameters: parameters,
                authorities: authorities,
            }, { title: 'Exposing the asset…' });
        }

        renderCards();
        refresh();
        el('expose-submit').addEventListener('click', submit);
    }

    // ------------------------------------------------------------ exposed
    function policyGraph(cidUrl, policy) {
        window.PolicyGraph.render(el('asset-policy-graph'), policy.graph, policy.catalog, 'light');
        var box = el('node-data-forms');
        if (!box) return;
        policy.nodes.forEach(function (n) {
            var parts = nodeFieldset(n);
            var form = window.schemaForm.render(parts.body, n.schema, n.values);
            var actions = document.createElement('div');
            actions.className = 'form-actions';
            actions.innerHTML = '<button type="button" class="btn btn-primary">Update</button>';
            actions.querySelector('button').addEventListener('click', async function () {
                var errors = form.errors();
                if (errors.length) {
                    window.flash(n.name + ': ' + errors.join('\n'), 'error');
                    return;
                }
                try {
                    var res = await window.api.post(
                        '/api/assets/' + cidUrl + '/update-policy-data/', { node: n.node, policy_data: form.value() }
                    );
                    window.flash(res.message, 'success');
                } catch (err) {
                    window.flash(err.message, 'error');
                }
            });
            parts.set.appendChild(actions);
            box.appendChild(parts.set);
        });
    }

    function init() {
        var container = document.querySelector('[data-asset-cid-url]');
        if (!container) return;
        var cidUrl = container.dataset.assetCidUrl;

        var expose = readJson('expose-data');
        if (expose) exposePanel(cidUrl, expose);

        window.trustTable.wire(el('trust-panel'), '/api/assets/' + cidUrl + '/');

        var policy = readJson('graph-policy-data');
        if (policy) policyGraph(cidUrl, policy);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
