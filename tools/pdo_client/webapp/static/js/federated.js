// The Federated page.
//
// Connect to an FL server, see which sites are holding data behind an inference
// guardian, pick some, and run one script across all of them.
//
// The sites come from the FL server rather than from the asset registry: the
// registry knows which assets exist, but only the server knows which of them have
// a client connected right now. The join is on the asset DID each FL client
// announces, and the server does it before this page ever sees the list.
//
// The roles are asked for after the selection, not before, because each site's
// policy declares its own — a round over two sites may need one role for one of
// them and two for the other, and the form has to cover the union.

(function () {
    var sites = [];        // what the server last told us
    var serverUrl = '';    // the server those sites came from
    var roles = [];        // the union the selected sites asked for

    function el(id) { return document.getElementById(id); }

    function selectedDids() {
        return sites
            .filter(function (s) { return s.checked; })
            .map(function (s) { return s.asset_did; });
    }

    function refreshRunButton() {
        el('fl-run').disabled = selectedDids().length === 0;
    }

    // ---------------------------------------------------------------- sites
    function stateText(site) {
        if (!site.online) {
            var seen = site.seconds_since_seen;
            return seen == null ? 'offline' : 'last seen ' + Math.round(seen) + 's ago';
        }
        if (!site.known) { return 'not in this asset registry'; }
        if (!site.exposed) { return 'no policy attached yet'; }
        return 'ready';
    }

    function renderSites() {
        var body = el('fl-sites-body');
        var template = el('fl-site-template');
        body.innerHTML = '';

        sites.forEach(function (site, index) {
            var node = template.content.cloneNode(true);
            var check = node.querySelector('[data-site-check]');
            check.dataset.index = String(index);
            check.disabled = !site.selectable;
            check.checked = !!site.checked;

            node.querySelector('[data-site-name]').textContent = site.name;
            node.querySelector('[data-site-did]').textContent = site.asset_did;
            node.querySelector('[data-site-guardian]').textContent = site.guardian || '—';
            node.querySelector('[data-site-client]').textContent = site.client_id;
            node.querySelector('[data-site-state]').textContent = stateText(site);
            body.appendChild(node);
        });

        el('fl-sites-table').classList.toggle('hidden', sites.length === 0);
        el('fl-sites-empty').classList.toggle('hidden', sites.length > 0);
        if (sites.length === 0) {
            el('fl-sites-empty').textContent =
                'No FL clients are connected to ' + serverUrl + '. A site appears here '
                + 'once its owner registers the asset behind an inference guardian.';
        }
        refreshRunButton();
    }

    function connect(url) {
        var status = el('fl-server-status');
        status.className = 'alert alert-info';
        status.textContent = 'Connecting to ' + url + '…';
        el('fl-server-start').classList.add('hidden');

        return window.api.post('/api/federated/sites/', { server_url: url })
            .then(function (info) {
                serverUrl = info.server_url;
                el('fl-server-url').value = serverUrl;
                sites = (info.sites || []).map(function (s) {
                    // A site that can take part starts selected: a round over
                    // everything available is the common case, and unchecking is
                    // less work than checking.
                    s.checked = !!s.selectable;
                    return s;
                });
                var online = sites.filter(function (s) { return s.online; }).length;
                status.className = 'alert alert-success';
                status.textContent =
                    online + ' site(s) connected to ' + serverUrl
                    + ' · ' + (info.server_info.rounds || 0) + ' round(s) submitted so far';
                renderSites();
            })
            .catch(function (e) {
                status.className = 'alert alert-error';
                status.textContent = e.message || String(e);
                // Nothing is answering. Offering to start one is only useful now:
                // a federation normally has a server before it has members.
                el('fl-server-start').classList.remove('hidden');
                sites = [];
                renderSites();
            });
    }

    // ---------------------------------------------------------------- roles
    function renderRoles(info) {
        roles = info.roles || [];
        var container = el('fl-run-roles');
        var template = el('fl-role-template');
        container.innerHTML = '';

        roles.forEach(function (entry) {
            var node = template.content.cloneNode(true);
            var select = node.querySelector('[data-role-select]');
            var label = node.querySelector('[data-role-label]');
            var hint = node.querySelector('[data-role-hint]');
            var id = 'fl-role-' + entry.role;

            select.id = id;
            select.dataset.role = entry.role;
            select.required = true;
            label.setAttribute('for', id);
            label.textContent = entry.role;
            hint.textContent = 'Presents: ' + (entry.credential_types || []).join(', ');
            container.appendChild(node);
        });

        var problems = el('fl-run-problems');
        if ((info.problems || []).length) {
            problems.textContent = 'Some sites could not be read: ' + info.problems.join('; ');
            problems.classList.remove('hidden');
        } else {
            problems.classList.add('hidden');
        }
    }

    function collectWallets() {
        var wallets = {};
        document.querySelectorAll('#fl-run-roles [data-role-select]').forEach(function (s) {
            wallets[s.dataset.role] = s.value;
        });
        return wallets;
    }

    function openRunModal() {
        var chosen = sites.filter(function (s) { return s.checked; });
        if (!chosen.length) { return; }

        el('fl-run-count').textContent = chosen.length + ' site' + (chosen.length > 1 ? 's' : '');
        el('fl-run-sites').textContent =
            'One script, run in place at: '
            + chosen.map(function (s) { return s.name; }).join(', ')
            + '. Each site is asked separately, by its own policy.';
        el('fl-run-roles').innerHTML = '';
        el('fl-run-submit').disabled = true;
        el('fl-run-modal').classList.remove('hidden');

        window.api.post('/api/federated/roles/', { asset_dids: selectedDids() })
            .then(function (info) {
                renderRoles(info);
                el('fl-run-submit').disabled = false;
            })
            .catch(function (e) {
                window.flash(e.message || String(e), 'error');
                el('fl-run-modal').classList.add('hidden');
            });
    }

    // --------------------------------------------------------------- result
    function escapeHtml(text) {
        var div = document.createElement('div');
        div.textContent = text == null ? '' : String(text);
        return div.innerHTML;
    }

    // The round, as the page shows it. Each row carries the site's name and
    // outcome as data attributes: this table is the only place the result of a
    // round is stated, and it should be readable as data by anything looking at
    // the page, not only by a person.
    function renderResult(term) {
        var round = (term && term.result) || {};
        var parts = [];

        parts.push(
            '<h3 style="margin:0 0 0.5rem">Aggregate</h3>'
            + '<pre class="code-block" id="fl-result-aggregate">'
            + escapeHtml(round.aggregate
                ? JSON.stringify(round.aggregate, null, 2)
                : 'No site ran it, so there is nothing to aggregate.')
            + '</pre>'
        );

        function row(name, status, outcome) {
            return '<tr data-site-row data-site-name="' + escapeHtml(name) + '"'
                + ' data-site-status="' + escapeHtml(status) + '">'
                + '<td><strong>' + escapeHtml(name) + '</strong></td>'
                + '<td>' + escapeHtml(status) + '</td>'
                + '<td>' + outcome + '</td></tr>';
        }

        var rows = (round.sites || []).map(function (site) {
            var outcome = site.status === 'complete'
                ? '<pre class="code-block" style="margin:0">'
                    + escapeHtml(JSON.stringify(site.metrics || {}, null, 2)) + '</pre>'
                : escapeHtml(site.error || site.status || 'no result');
            return row(site.name, site.status, outcome);
        });
        (round.refused || []).forEach(function (site) {
            rows.push(row(site.name, 'refused', escapeHtml(site.error)));
        });

        parts.push(
            '<h3 style="margin:1rem 0 0.5rem">Per site</h3>'
            + '<table class="data-table"><thead><tr><th>Site</th><th>Status</th>'
            + '<th>Reported</th></tr></thead><tbody>' + rows.join('') + '</tbody></table>'
        );
        if (round.round_id) {
            parts.push(
                '<p style="color:#888;font-size:0.8rem;margin-top:0.75rem">round '
                + escapeHtml(round.round_id) + ' on ' + escapeHtml(round.server_url) + '</p>'
            );
        }

        el('fl-result-body').innerHTML = parts.join('');
        el('fl-result-modal').classList.remove('hidden');
    }

    // ----------------------------------------------------------------- init
    function init() {
        var container = document.querySelector('[data-default-server-url]');
        if (!container) { return; }

        el('fl-server-form').addEventListener('submit', function (e) {
            e.preventDefault();
            connect(el('fl-server-url').value);
        });

        el('fl-sites-body').addEventListener('change', function (e) {
            var check = e.target.closest('[data-site-check]');
            if (!check) { return; }
            sites[Number(check.dataset.index)].checked = check.checked;
            refreshRunButton();
        });

        el('fl-start-server').addEventListener('click', function () {
            window.progress.run('/api/federated/start-server/stream/', {}, {
                title: 'Starting an FL server…',
                onComplete: function (term) {
                    el('progress-modal').classList.add('hidden');
                    el('fl-server-url').value =
                        term.server_url || container.dataset.defaultServerUrl;
                    connect(el('fl-server-url').value);
                },
            });
        });

        el('fl-run').addEventListener('click', openRunModal);

        el('fl-run-form').addEventListener('submit', function (e) {
            e.preventDefault();
            window.progress.run('/api/federated/run/stream/', {
                server_url: serverUrl,
                asset_dids: selectedDids(),
                wallets: collectWallets(),
            }, {
                title: 'Running the federated round…',
                onComplete: function (term) {
                    el('progress-modal').classList.add('hidden');
                    renderResult(term);
                },
            });
        });

        // Nothing on this page means anything without a server, so ask the one
        // this deployment was pointed at before the reader has to.
        connect(container.dataset.defaultServerUrl);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
