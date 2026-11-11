// Authority page. A hand-signing authority signs one of the credential types it
// attests, with the claims form generated from the type's schema.

(function () {
    var SUBJECTS = {
        wallet: 'a wallet', script: 'a script asset', project: 'a project',
        committee: 'a committee', organization: 'an organization', document: 'a document',
    };

    function el(id) { return document.getElementById(id); }

    function signing(cidUrl) {
        var form = el('sign-credential-form');
        if (!form) return;
        var templates = JSON.parse(el('sign-templates-data').textContent);
        var claims = null;

        function current() {
            return templates.filter(function (t) { return t.type === el('sign-fact').value; })[0];
        }
        function showFact() {
            var t = current();
            if (!t) return;
            el('sign-fact-meaning').textContent = t.meaning;
            el('sign-subject-hint').textContent = 'The DID of ' +
                t.subject_kinds.map(function (k) { return SUBJECTS[k]; }).join(' or ') + '.';
            claims = window.schemaForm.render(el('sign-claims'), t.schema, {});
        }
        el('sign-fact').addEventListener('change', showFact);
        showFact();

        form.addEventListener('submit', async function (e) {
            e.preventDefault();
            var errors = claims ? claims.errors() : [];
            if (errors.length) {
                window.flash(errors.join('\n'), 'error');
                return;
            }
            try {
                var res = await window.api.post('/api/authorities/' + cidUrl + '/sign-credential/', {
                    template_type: el('sign-fact').value,
                    subject_did: el('sign-subject-did').value.trim(),
                    holder_did: el('sign-holder-did').value.trim(),
                    claims: claims.value(),
                });
                el('sign-credential-modal').classList.add('hidden');
                window.flash(res.message, 'success');
            } catch (err) {
                window.flash(err.message, 'error');
            }
        });
    }

    function init() {
        var container = document.querySelector('[data-authority-cid-url]');
        if (!container) return;
        var cidUrl = container.dataset.authorityCidUrl;

        var form = el('update-name-form');
        form.addEventListener('submit', async function (e) {
            e.preventDefault();
            try {
                var res = await window.api.post(
                    '/api/authorities/' + cidUrl + '/update-name/', window.formToObject(form));
                window.flash(res.message, 'success');
                window.location.reload();
            } catch (err) {
                window.flash(err.message, 'error');
            }
        });

        signing(cidUrl);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
