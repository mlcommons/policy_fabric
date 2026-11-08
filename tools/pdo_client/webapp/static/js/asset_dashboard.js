// Asset dashboard.
//
// Before the asset is exposed, the Expose panel: the owner picks policy cards
// (those that fit this asset's guardian), fills each one's parameter form, and
// accepts authorities fact by fact; a review line says what requesters will
// need. Afterwards: trust can be withdrawn or added fact by fact, and each
// policy's parameters edited.

(function () {
    function el(id) { return document.getElementById(id); }

    function readJson(id) {
        var node = el(id);
        return node ? JSON.parse(node.textContent) : null;
    }

    function unique(list) {
        return list.filter(function (x, i) { return list.indexOf(x) === i; });
    }

    // ------------------------------------------------------------- expose
    function exposePanel(cidUrl, data) {
        var selected = [];   // [{card, form}] in the order the cards are listed
        var chosen = {};     // fact -> [DID, ...], for every fact the platform knows
        var touched = {};    // facts the owner has already seen, so defaults apply once
        Object.keys(data.facts).forEach(function (t) { chosen[t] = []; });

        function fact(type) { return data.facts[type]; }
        function byDid(did) {
            return data.authorities.filter(function (a) { return a.did === did; })[0];
        }
        function byContract(did) {
            var id = did.replace(/^did:pdo:/, '').split('#')[0];
            return data.authorities.filter(function (a) { return a.contract_id === id; })[0];
        }
        function optionsFor(type) {
            return data.authorities.filter(function (a) { return a.facts.indexOf(type) !== -1; });
        }
        function needs(module) {
            var out = [];
            Object.keys(module.requirements).forEach(function (role) {
                out = out.concat(module.requirements[role]);
            });
            return unique(out);
        }
        function neededFacts() {
            var facts = [];
            selected.forEach(function (s) { facts = facts.concat(needs(s.card)); });
            if (selected.length) facts = facts.concat(needs(data.delivery));
            return unique(facts);
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
                item.querySelector('small').textContent = 'Needs: ' + factNames(needs(card));
                item.querySelector('input').addEventListener('change', function (e) {
                    if (e.target.checked) {
                        selected.push({ card: card, form: null });
                        selected.sort(function (a, b) {
                            return data.cards.indexOf(a.card) - data.cards.indexOf(b.card);
                        });
                    } else {
                        selected = selected.filter(function (s) { return s.card !== card; });
                    }
                    refresh();
                });
                item.querySelector('button').addEventListener('click', function () {
                    window.render.showCard(card.code + ' · ' + card.title, card.readme, card.rego_source);
                });
                box.appendChild(item);
            });
            el('expose-delivery').textContent =
                'Always included: ' + data.delivery.title + ' — ' + data.delivery.rule +
                ' Needs: ' + factNames(needs(data.delivery)) + '.';
        }

        // ---- 2. parameters, one generated form per selected card
        function renderParameters() {
            var box = el('expose-parameters');
            var values = {};
            selected.forEach(function (s) {
                if (s.form) values[s.card.id] = s.form.value();
            });
            box.innerHTML = '';
            selected.forEach(function (s) {
                var set = document.createElement('fieldset');
                set.className = 'schema-fieldset';
                set.dataset.parameters = s.card.name;
                var legend = document.createElement('legend');
                legend.textContent = s.card.code + ' · ' + s.card.title;
                set.appendChild(legend);
                var body = document.createElement('div');
                set.appendChild(body);
                box.appendChild(set);
                s.form = window.schemaForm.render(
                    body, s.card.parameters_schema, s.card.id in values ? values[s.card.id] : s.card.defaults
                );
            });
            if (!selected.length) box.innerHTML = '<p class="muted">Choose a policy first.</p>';
        }

        // ---- 3. accepted authorities, one row per fact
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
            if (authority.sources.length) {
                details.push('accepts ' + authority.sources.map(function (s) {
                    var known = byContract(s.did);
                    return known ? known.name : s.did;
                }).join(', ') + ' for its inputs');
            }
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
                    // A fact only a single system authority establishes, such as
                    // the session key, is accepted by default.
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

        // ---- 4. review
        function describe(type) {
            if (fact(type).self_asserted) return fact(type).name + ' (signed by their own wallet)';
            var accepted = chosen[type].map(function (did) {
                return byDid(did) || { name: did, kind: 'unlisted' };
            });
            if (!accepted.length) return fact(type).name + ' (no authority accepted yet)';
            var automatic = accepted.every(function (a) { return a.kind === 'system'; });
            return fact(type).name + ' (' + (automatic
                ? 'automatic'
                : accepted.map(function (a) { return a.name; }).join(' or ')) + ')';
        }

        function missing() {
            return neededFacts().filter(function (t) {
                return !fact(t).self_asserted && !chosen[t].length;
            });
        }

        function renderReview() {
            var facts = neededFacts();
            el('expose-review').textContent = facts.length
                ? 'Requesters will need: ' + facts.map(describe).join(', ') + '.'
                : 'Choose a policy first.';
            el('expose-submit').disabled = !selected.length || missing().length > 0;
        }

        function refresh() {
            renderParameters();
            renderTrustLists();
            renderAuthorities();
            renderReview();
        }

        function submit() {
            var errors = [];
            var parameters = {};
            selected.forEach(function (s) {
                s.form.errors().forEach(function (e) { errors.push(s.card.code + ': ' + e); });
                parameters[s.card.id] = s.form.value();
            });
            if (errors.length) {
                window.flash(errors.join('\n'), 'error');
                return;
            }
            var authorities = {};
            neededFacts().forEach(function (t) {
                if (!fact(t).self_asserted) authorities[t] = chosen[t];
            });
            window.progress.run('/assets/' + cidUrl + '/expose/stream/', {
                cards: selected.map(function (s) { return s.card.id; }),
                parameters: parameters,
                authorities: authorities,
            }, { title: 'Exposing the asset…' });
        }

        renderCards();
        refresh();
        el('expose-submit').addEventListener('click', submit);
    }

    // ------------------------------------------------------------ exposed
    function parametersEditor(cidUrl, cards) {
        var box = el('policy-data-forms');
        var forms = cards.map(function (card) {
            var set = document.createElement('fieldset');
            set.className = 'schema-fieldset';
            set.dataset.parameters = card.name;
            var legend = document.createElement('legend');
            legend.textContent = card.code + ' · ' + card.title;
            set.appendChild(legend);
            var body = document.createElement('div');
            set.appendChild(body);
            box.appendChild(set);
            return { card: card, form: window.schemaForm.render(body, card.parameters_schema, card.values) };
        });

        el('policy-data-form').addEventListener('submit', async function (e) {
            e.preventDefault();
            var errors = [];
            var policyData = {};
            forms.forEach(function (f) {
                f.form.errors().forEach(function (err) { errors.push(f.card.code + ': ' + err); });
                policyData[f.card.name] = f.form.value();
            });
            if (errors.length) {
                window.flash(errors.join('\n'), 'error');
                return;
            }
            try {
                var res = await window.api.post(
                    '/api/assets/' + cidUrl + '/update-policy-data/', { policy_data: policyData }
                );
                window.flash(res.message, 'success');
            } catch (err) {
                window.flash(err.message, 'error');
            }
        });
    }

    function init() {
        var container = document.querySelector('[data-asset-cid-url]');
        if (!container) return;
        var cidUrl = container.dataset.assetCidUrl;

        var expose = readJson('expose-data');
        if (expose) exposePanel(cidUrl, expose);

        window.trustTable.wire(el('trust-panel'), '/api/assets/' + cidUrl + '/');

        var cards = readJson('attached-cards-data');
        if (cards) parametersEditor(cidUrl, cards);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
