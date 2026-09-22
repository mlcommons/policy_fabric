// Issuer dashboard: JSON-POST actions (update name, add VC, sign credential).
// Each modal form submits via window.api.post; on success we either reload
// the page (mutating actions) or show the result inline (sign). "Sign
// Credential" only exists in the DOM for manual issuers (see
// issuers/detail.html) — an external_key_authority's sign_credential op does
// something else entirely (binds a session key to a wallet).

(function () {
    function init() {
        var container = document.querySelector('[data-issuer-cid-url]');
        if (!container) return;
        // URL-safe contract id (server-side encoding, see app/url_safe_id.py).
        var cidUrl = container.dataset.issuerCidUrl;

        // ---- Update name ----
        var updateNameForm = document.getElementById('update-name-form');
        updateNameForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            var payload = window.formToObject(updateNameForm);
            try {
                var res = await window.api.post(
                    '/api/issuers/' + cidUrl + '/update-name/', payload);
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
                    '/api/issuers/' + cidUrl + '/add-vc/', { vc: vc });
                window.flash('Credential added.', 'success');
                window.location.reload();
            } catch (err) {
                window.flash(err.message, 'error');
            }
        });

        // ---- Sign credential (manual issuers only) ----
        // Always signs from the issuer's fixed "poc" signing context (the
        // server picks it — the client never sends one).
        var signForm = document.getElementById('sign-credential-form');
        if (!signForm) return;

        var templateSelect = document.getElementById('sign-template-select');
        var claimsTextarea = document.getElementById('sign-claims-input');
        function prefillClaims() {
            if (!templateSelect || !claimsTextarea) return;
            var opt = templateSelect.options[templateSelect.selectedIndex];
            if (!opt) return;
            try {
                var schema = JSON.parse(opt.dataset.schema || '{}');
                claimsTextarea.value = JSON.stringify(schema, null, 2);
            } catch (e) { /* leave textarea untouched */ }
        }
        if (templateSelect) {
            templateSelect.addEventListener('change', prefillClaims);
            prefillClaims();
        }

        signForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            var raw = (document.getElementById('sign-claims-input').value || '').trim();
            var claims = {};
            if (raw) {
                try { claims = JSON.parse(raw); }
                catch (err) {
                    window.flash('Invalid claims JSON: ' + err.message, 'error');
                    return;
                }
            }
            var payload = {
                template_type: document.getElementById('sign-template-select').value,
                subject_did: document.getElementById('sign-subject-did').value.trim(),
                claims: claims,
            };
            try {
                var res = await window.api.post(
                    '/api/issuers/' + cidUrl + '/sign-credential/', payload);
                document.getElementById('sign-credential-modal').classList.add('hidden');
                window.flash(res.message || 'Credential issued.', 'success');
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
