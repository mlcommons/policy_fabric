// Assets page: clicking "Use" opens a modal shaped by the guardian in front of
// the asset. A public guardian needs nothing at all; a policy-gated one needs an
// identity for each role its policy declares — one of the requester's wallets, or
// a script asset. The roles come from the policy, so they are fetched when the
// modal opens rather than rendered with the page.

(function () {
    var form = null;

    function renderRoles(roles) {
        var container = document.getElementById('use-roles');
        var template = document.getElementById('use-role-template');
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
            label.setAttribute('for', id);
            label.textContent = entry.role;
            hint.textContent = 'Presents: ' + (entry.credential_types || []).join(', ');

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

    function openModal(btn) {
        var assetDid = btn.dataset.assetDid || '';
        document.getElementById('use-asset-did').value = assetDid;
        document.getElementById('use-asset-name').textContent = btn.dataset.assetName || '';

        var submit = document.getElementById('use-submit');
        submit.textContent = btn.dataset.actionLabel || 'Use';
        submit.disabled = true;

        // Reset to a blank form before the shape is known, so a previous asset's
        // roles are never shown against this one.
        document.getElementById('use-roles').innerHTML = '';
        document.getElementById('use-modal').classList.remove('hidden');

        window.api.post('/api/assets/use-form/', { asset_did: assetDid })
            .then(function (info) {
                renderRoles(info.roles || []);

                // Every role the flow needs must actually have something chosen.
                var wallets = collectWallets();
                submit.disabled = Object.keys(wallets).some(function (r) {
                    return !wallets[r];
                });
            })
            .catch(function (e) {
                window.flash(e.message || String(e), 'error');
                document.getElementById('use-modal').classList.add('hidden');
            });
    }

    function renderResult(term) {
        var result = term.result || {};
        var isMetrics = term.result_kind === 'metrics';

        document.getElementById('use-result-title').textContent =
            isMetrics ? 'Reported Metrics' : 'Data';
        document.getElementById('use-result-output').textContent =
            isMetrics ? JSON.stringify(result.metrics || {}, null, 2) : (result.data || '');
        document.getElementById('use-result-modal').classList.remove('hidden');
    }

    function init() {
        // Open the modal and stash the clicked asset's DID/name.
        document.addEventListener('click', function (e) {
            var btn = e.target.closest('[data-action="open-use"]');
            if (!btn) return;
            openModal(btn);
        });

        form = document.getElementById('use-form');
        if (!form) return;
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            var payload = {
                asset_did: document.getElementById('use-asset-did').value,
                wallets: collectWallets(),
            };
            window.progress.run('/api/assets/use/stream/', payload, {
                title: 'Using the asset…',
                onComplete: function (term) {
                    // The progress modal has done its job once the flow
                    // completes — dismiss it instead of leaving it sitting
                    // on screen, and show the result in its own modal.
                    document.getElementById('progress-modal').classList.add('hidden');
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
