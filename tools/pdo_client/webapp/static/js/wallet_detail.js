// Wallet dashboard: JSON-POST actions (update name, add VC, sign as the wallet).
// On success a mutating action reloads the page; signing reports inline, because
// what it changed is another contract's credential store, not this page.

(function () {
    function init() {
        var container = document.querySelector('[data-wallet-cid-url]');
        if (!container) return;
        // URL-safe contract id (server-side encoding, see app/url_safe_id.py).
        var cidUrl = container.dataset.walletCidUrl;

        // ---- Update name ----
        var updateNameForm = document.getElementById('update-name-form');
        updateNameForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            var payload = window.formToObject(updateNameForm);
            try {
                var res = await window.api.post(
                    '/api/wallets/' + cidUrl + '/update-name/', payload);
                window.flash(res.message || 'Name updated.', 'success');
                window.location.reload();
            } catch (err) {
                window.flash(err.message, 'error');
            }
        });

        // ---- Add VC ----
        var addVcForm = document.getElementById('add-vc-form');
        addVcForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            var raw = (document.getElementById('vc-json-input').value || '').trim();
            if (!raw) { window.flash('VC JSON is required.', 'error'); return; }
            var vc;
            try { vc = JSON.parse(raw); }
            catch (err) { window.flash('Invalid JSON: ' + err.message, 'error'); return; }
            try {
                await window.api.post(
                    '/api/wallets/' + cidUrl + '/add-vc/', { vc: vc });
                window.flash('Credential added.', 'success');
                window.location.reload();
            } catch (err) {
                window.flash(err.message, 'error');
            }
        });

        // ---- Sign as this wallet ----
        // Signed with the wallet's own contract key; the server picks the key,
        // the client only says what is being claimed and about whom.
        var signForm = document.getElementById('sign-credential-form');
        var claimsData = document.getElementById('own-claims-data');
        if (!signForm || !claimsData) return;
        var templates = JSON.parse(claimsData.textContent);
        var factSelect = document.getElementById('sign-fact');
        var claims = null;

        function showFact() {
            var t = templates.filter(function (x) { return x.type === factSelect.value; })[0];
            if (!t) return;
            document.getElementById('sign-fact-meaning').textContent = t.meaning;
            claims = window.schemaForm.render(document.getElementById('sign-claims'), t.schema, {});
        }
        factSelect.addEventListener('change', showFact);
        showFact();

        signForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            var errors = claims ? claims.errors() : ['Nothing to sign'];
            if (errors.length) {
                window.flash(errors.join('\n'), 'error');
                return;
            }
            try {
                var res = await window.api.post('/api/wallets/' + cidUrl + '/sign-credential/', {
                    template_type: factSelect.value,
                    subject_did: document.getElementById('sign-subject-did').value.trim(),
                    claims: claims.value(),
                });
                document.getElementById('sign-credential-modal').classList.add('hidden');
                window.flash(res.message, 'success');
            } catch (err) {
                window.flash(err.message, 'error');
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
