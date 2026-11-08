// Assets page: clicking "Use" opens a modal shaped by the guardian in front of
// the asset. A public guardian needs nothing at all; a policy-gated one needs an
// identity for each role its policy declares — one of the requester's wallets, or
// a script asset. The roles come from the policy, so they are fetched when the
// modal opens rather than rendered with the page.
//
// Once identities are chosen, the readiness checklist says, fact by fact, what
// they hold, what will be obtained on the way, and whom to ask for the rest. Use
// is enabled only when every fact is held or automatic. When a fact the asset
// needs is about a project, the requester names the project this use is for.

(function () {
    var assetDid = '';
    var checking = 0;
    var needsProject = false;

    function el(id) { return document.getElementById(id); }

    function renderRoles(roles) {
        var container = el('use-roles');
        var template = el('use-role-template');
        container.innerHTML = '';

        roles.forEach(function (entry) {
            var node = template.content.cloneNode(true);
            var select = node.querySelector('[data-role-select]');
            var label = node.querySelector('[data-role-label]');
            var hint = node.querySelector('[data-role-hint]');
            var id = 'use-wallet-' + entry.role;

            select.id = id;
            select.dataset.role = entry.role;
            select.required = true;
            select.addEventListener('change', refreshChecklist);
            label.setAttribute('for', id);
            label.textContent = entry.role;
            hint.textContent = 'Presents: ' + entry.facts.join(', ');

            container.appendChild(node);
        });
    }

    function collectWallets() {
        var wallets = {};
        document.querySelectorAll('#use-roles [data-role-select]').forEach(function (select) {
            wallets[select.dataset.role] = select.value;
        });
        return wallets;
    }

    function renderProjects(needed, projects) {
        needsProject = needed;
        var select = el('use-project');
        var current = select.value;
        select.innerHTML = '';
        projects.forEach(function (p) {
            select.appendChild(new Option(p, p, false, p === current));
        });
        el('use-project-none').classList.toggle('hidden', projects.length > 0);
        el('use-project-group').classList.toggle('hidden', !needed);
    }

    function refreshChecklist() {
        var submit = el('use-submit');
        var box = el('use-checklist');
        var wallets = collectWallets();
        var roles = Object.keys(wallets);
        if (!roles.length) {
            box.classList.add('hidden');
            submit.disabled = false;
            return;
        }
        submit.disabled = true;
        if (roles.some(function (r) { return !wallets[r]; })) return;

        var token = ++checking;
        box.classList.remove('hidden');
        box.innerHTML = '<p class="muted">Checking what you hold…</p>';
        window.api.post('/api/assets/checklist/', { asset_did: assetDid, wallets: wallets })
            .then(function (info) {
                if (token !== checking) return;
                window.checklist.render(box, info.rows);
                renderProjects(info.needs_project, info.projects);
                submit.disabled = !info.ready || (info.needs_project && !info.projects.length);
            })
            .catch(function (e) {
                if (token !== checking) return;
                box.innerHTML = '';
                var alert = document.createElement('div');
                alert.className = 'alert alert-error';
                alert.textContent = e.message || String(e);
                box.appendChild(alert);
            });
    }

    function openModal(btn) {
        assetDid = btn.dataset.assetDid || '';
        el('use-asset-did').value = assetDid;
        el('use-asset-name').textContent = btn.dataset.assetName || '';

        var submit = el('use-submit');
        submit.textContent = btn.dataset.actionLabel || 'Use';
        submit.disabled = true;

        // Reset to a blank form before the shape is known, so a previous asset's
        // roles are never shown against this one.
        el('use-roles').innerHTML = '';
        el('use-checklist').classList.add('hidden');
        renderProjects(false, []);
        el('use-modal').classList.remove('hidden');

        window.api.post('/api/assets/use-form/', { asset_did: assetDid })
            .then(function (info) {
                renderRoles(info.roles);
                refreshChecklist();
            })
            .catch(function (e) {
                window.flash(e.message || String(e), 'error');
                el('use-modal').classList.add('hidden');
            });
    }

    function renderResult(term) {
        var result = term.result || {};
        var isMetrics = term.result_kind === 'metrics';

        el('use-result-title').textContent = isMetrics ? 'Reported Metrics' : 'Data';
        el('use-result-output').textContent =
            isMetrics ? JSON.stringify(result.metrics || {}, null, 2) : (result.data || '');
        el('use-result-modal').classList.remove('hidden');
    }

    function init() {
        document.addEventListener('click', function (e) {
            var btn = e.target.closest('[data-action="open-use"]');
            if (!btn) return;
            openModal(btn);
        });

        var form = el('use-form');
        if (!form) return;
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            var payload = { asset_did: assetDid, wallets: collectWallets() };
            if (needsProject) payload.project = el('use-project').value;
            window.progress.run('/api/assets/use/stream/', payload, {
                title: 'Using the asset…',
                onComplete: function (term) {
                    // The progress modal has done its job once the flow
                    // completes; the result gets a modal of its own.
                    el('progress-modal').classList.add('hidden');
                    renderResult(term);
                },
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
