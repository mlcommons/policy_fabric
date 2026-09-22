// Asset dashboard: drives four interactions depending on whether the
// asset has been exposed yet.
//   * No policy → Expose modal (HTML form, server redirects back here).
//   * Has policy → Use modal (JSON), Register Trusted Issuer modal (JSON
//     with multi-select credential types), and an inline Policy Data
//     editor that PUTs through set_policy_data.

(function () {
    function init() {
        var container = document.querySelector('[data-asset-cid-url]');
        if (!container) return;
        // URL-safe contract id (server-side encoding, see app/url_safe_id.py).
        var cidUrl = container.dataset.assetCidUrl;

        // ---- Expose: merge policy_data schema from the selected policies ----
        // Multiple policies can be chosen; each becomes a Rego subpolicy. The
        // policy_data textarea is prefilled with the union of the checked
        // policies' data schemas (e.g. allowedCountries + allowedInstitutions).
        var policyChecks = document.querySelectorAll('input[name="policy_templates"]');
        var policyDataTextarea = document.getElementById('id_policy_data');
        if (policyChecks.length && policyDataTextarea) {
            function mergeSchemas() {
                var merged = {};
                policyChecks.forEach(function (cb) {
                    if (!cb.checked) return;
                    try {
                        Object.assign(merged, JSON.parse(cb.dataset.schema || '{}'));
                    } catch (e) { /* skip malformed schema */ }
                });
                policyDataTextarea.value = JSON.stringify(merged, null, 2);
            }
            policyChecks.forEach(function (cb) {
                cb.addEventListener('change', mergeSchemas);
            });
            mergeSchemas();
        }

        // ---- Expose: "View" a policy's rego source + README in a popup ----
        // The README (Markdown) is rendered to formatted HTML and the Rego source
        // is syntax-highlighted, each on its own tab. Both come from the trusted
        // template registry, but everything is HTML-escaped before insertion.
        var detailsEl = document.getElementById('policy-details-data');
        var policyDetails = detailsEl ? JSON.parse(detailsEl.textContent) : {};
        var policyModal = document.getElementById('policy-detail-modal');
        var policyTabs = document.getElementById('policy-detail-tabs');

        function selectPolicyTab(name) {
            if (!policyModal) return;
            policyModal.querySelectorAll('[data-policy-tab]').forEach(function (b) {
                b.classList.toggle('active', b.dataset.policyTab === name);
            });
            policyModal.querySelectorAll('[data-policy-panel]').forEach(function (p) {
                p.classList.toggle('active', p.dataset.policyPanel === name);
            });
        }
        if (policyTabs) {
            policyTabs.addEventListener('click', function (e) {
                var b = e.target.closest('[data-policy-tab]');
                if (b) selectPolicyTab(b.dataset.policyTab);
            });
        }

        document.addEventListener('click', function (e) {
            var btn = e.target.closest('[data-action="view-policy"]');
            if (!btn) return;
            var d = policyDetails[btn.dataset.policyId];
            if (!d) return;
            document.getElementById('policy-detail-title').textContent =
                (d.name || 'Policy') + ' policy';
            document.getElementById('policy-detail-readme').innerHTML = d.readme
                ? renderMarkdown(d.readme)
                : '<p class="md-empty">No description provided for this policy.</p>';
            document.getElementById('policy-detail-rego').innerHTML = d.rego_source
                ? highlightRego(d.rego_source)
                : '';
            selectPolicyTab('readme');
            policyModal.classList.remove('hidden');
            policyModal.querySelector('.modal').scrollTop = 0;
        });

        // ---- Expose: dynamic "trusted issuers" boxes ----
        // Each box collects an issuer DID + chosen credential types. On submit
        // they're serialized into a hidden field the expose view reads.
        var addIssuerBtn = document.getElementById('expose-add-issuer');
        var issuersContainer = document.getElementById('expose-trusted-issuers');
        var issuersHidden = document.getElementById('expose-trusted-issuers-json');
        var exposeForm = document.getElementById('expose-form');
        if (addIssuerBtn && issuersContainer && issuersHidden && exposeForm) {
            var ctEl = document.getElementById('expose-credential-types-data');
            var credentialTypes = ctEl ? JSON.parse(ctEl.textContent) : [];

            function addIssuerBox() {
                var box = document.createElement('div');
                box.className = 'trusted-issuer-box';
                box.style.cssText =
                    'border:1px solid #ddd;border-radius:4px;padding:0.5rem;margin-bottom:0.5rem';

                var row = document.createElement('div');
                row.style.cssText = 'display:flex;align-items:center;gap:0.5rem';
                var did = document.createElement('input');
                did.type = 'text';
                did.className = 'ti-did';
                did.placeholder = 'did:pdo:<contract_id>';
                did.style.flex = '1';
                var del = document.createElement('button');
                del.type = 'button';
                del.className = 'btn btn-sm';
                del.title = 'Remove';
                del.textContent = '🗑';
                del.addEventListener('click', function () { box.remove(); });
                row.appendChild(did);
                row.appendChild(del);
                box.appendChild(row);

                var types = document.createElement('div');
                types.className = 'ti-types checkbox-list';
                types.style.marginTop = '0.5rem';
                if (!credentialTypes.length) {
                    types.innerHTML =
                        '<p style="color:#999;margin:0">No credential templates available.</p>';
                } else {
                    credentialTypes.forEach(function (t) {
                        var label = document.createElement('label');
                        label.className = 'checkbox-item';
                        var cb = document.createElement('input');
                        cb.type = 'checkbox';
                        cb.value = t;
                        var span = document.createElement('span');
                        span.textContent = t;
                        label.appendChild(cb);
                        label.appendChild(span);
                        types.appendChild(label);
                    });
                }
                box.appendChild(types);
                issuersContainer.appendChild(box);
            }

            addIssuerBtn.addEventListener('click', addIssuerBox);

            // Stream the expose flow instead of a plain POST: gather the chosen
            // policies, policy data, and inline trusted issuers, then show live
            // per-step progress. The terminal {redirect} reloads the dashboard.
            exposeForm.addEventListener('submit', function (e) {
                e.preventDefault();
                var issuers = [];
                issuersContainer
                    .querySelectorAll('.trusted-issuer-box')
                    .forEach(function (box) {
                        var d = (box.querySelector('.ti-did').value || '').trim();
                        var chosen = Array.from(
                            box.querySelectorAll('.ti-types input:checked')
                        ).map(function (cb) { return cb.value; });
                        if (d && chosen.length) {
                            issuers.push({ did: d, credential_types: chosen });
                        }
                    });
                var policies = Array.from(
                    exposeForm.querySelectorAll('input[name="policy_templates"]:checked')
                ).map(function (cb) { return cb.value; });
                if (!policies.length) {
                    window.flash('Select at least one policy.', 'error');
                    return;
                }
                var dataEl = document.getElementById('id_policy_data');
                window.progress.run('/assets/' + cidUrl + '/expose/stream/', {
                    policy_templates: policies,
                    policy_data: dataEl ? dataEl.value : '',
                    trusted_issuers: issuers,
                }, { title: 'Exposing the asset…' });
            });
        }

        // ---- Use: stream the download flow, show the result in its own popup ----
        var useForm = document.getElementById('use-form');
        if (useForm) {
            useForm.addEventListener('submit', function (e) {
                e.preventDefault();
                var payload = window.formToObject(useForm);
                window.progress.run('/api/assets/use/stream/', payload, {
                    title: 'Using the asset…',
                    onComplete: function (term) {
                        // The progress modal has done its job once the flow
                        // completes — dismiss it instead of leaving it sitting
                        // on screen, and show the decrypted data in its own modal.
                        document.getElementById('progress-modal').classList.add('hidden');
                        document.getElementById('use-result-output').textContent =
                            (term.result || {}).data || '';
                        document.getElementById('use-result-modal').classList.remove('hidden');
                    },
                });
            });
        }

        // ---- Register policy trusted issuer (checkbox credential types) ----
        var registerForm = document.getElementById('register-policy-issuer-form');
        if (registerForm) {
            registerForm.addEventListener('submit', async function (e) {
                e.preventDefault();
                var credentialTypes = Array.from(
                    registerForm.querySelectorAll(
                        'input[name="credential_types"]:checked'
                    )
                ).map(function (cb) { return cb.value; });
                if (credentialTypes.length === 0) {
                    window.flash('Select at least one credential type.', 'error');
                    return;
                }
                var payload = {
                    issuer_did: document.getElementById('rpi-issuer-did').value.trim(),
                    credential_types: credentialTypes,
                };
                try {
                    var res = await window.api.post(
                        '/api/assets/' + cidUrl + '/register-policy-issuer/',
                        payload
                    );
                    window.flash(res.message || 'Issuer registered.', 'success');
                    window.location.reload();
                } catch (err) {
                    window.flash(err.message, 'error');
                }
            });
        }

        // ---- Update policy data ----
        var policyDataForm = document.getElementById('update-policy-data-form');
        if (policyDataForm) {
            policyDataForm.addEventListener('submit', async function (e) {
                e.preventDefault();
                var raw = (document.getElementById('policy-data-textarea').value || '').trim();
                var policyData;
                try {
                    policyData = raw ? JSON.parse(raw) : {};
                } catch (err) {
                    window.flash('Invalid JSON: ' + err.message, 'error');
                    return;
                }
                if (typeof policyData !== 'object' || Array.isArray(policyData)) {
                    window.flash('Policy data must be a JSON object.', 'error');
                    return;
                }
                try {
                    var res = await window.api.post(
                        '/api/assets/' + cidUrl + '/update-policy-data/',
                        { policy_data: policyData }
                    );
                    window.flash(res.message || 'Policy data updated.', 'success');
                } catch (err) {
                    window.flash(err.message, 'error');
                }
            });
        }
    }

    // ---- Minimal Markdown renderer ------------------------------------------
    // Supports the subset the policy READMEs use: ATX headings, bold/italic,
    // inline code, fenced code, links, blockquotes, ordered/unordered lists and
    // horizontal rules. All text is HTML-escaped before any markup is added.
    function escapeHtml(s) {
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

    function renderInline(text) {
        // Protect inline code spans so their contents aren't touched by the
        // emphasis/link passes, then restore them at the end.
        var codes = [];
        text = text.replace(/`([^`]+)`/g, function (_, c) {
            codes.push(c);
            return '\u0000' + (codes.length - 1) + '\u0000';
        });
        text = text.replace(
            /\[([^\]]+)\]\(([^)\s]+)\)/g,
            '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
        );
        text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        text = text.replace(/(^|[^*])\*(?!\s)([^*]+?)\*/g, '$1<em>$2</em>');
        text = text.replace(/\u0000(\d+)\u0000/g, function (_, n) {
            return '<code>' + codes[n] + '</code>';
        });
        return text;
    }

    function renderMarkdown(src) {
        var lines = String(src).replace(/\r\n?/g, '\n').split('\n');
        var html = '';
        var i = 0;
        var isBlockStart = function (l) {
            return /^\s*$/.test(l) || /^#{1,6}\s+/.test(l) || /^```/.test(l) ||
                /^>\s?/.test(l) || /^\s*[-*+]\s+/.test(l) ||
                /^\s*\d+\.\s+/.test(l) || /^(-{3,}|\*{3,}|_{3,})\s*$/.test(l);
        };
        while (i < lines.length) {
            var line = lines[i];
            if (/^```/.test(line)) {
                var buf = [];
                i++;
                while (i < lines.length && !/^```/.test(lines[i])) { buf.push(lines[i]); i++; }
                i++; // closing fence
                html += '<pre class="md-code"><code>' + escapeHtml(buf.join('\n')) + '</code></pre>';
                continue;
            }
            var heading = /^(#{1,6})\s+(.*)$/.exec(line);
            if (heading) {
                var level = heading[1].length;
                html += '<h' + level + '>' + renderInline(escapeHtml(heading[2])) + '</h' + level + '>';
                i++;
                continue;
            }
            if (/^(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) { html += '<hr>'; i++; continue; }
            if (/^>\s?/.test(line)) {
                var quote = [];
                while (i < lines.length && /^>\s?/.test(lines[i])) {
                    quote.push(lines[i].replace(/^>\s?/, ''));
                    i++;
                }
                html += '<blockquote>' + renderMarkdown(quote.join('\n')) + '</blockquote>';
                continue;
            }
            if (/^\s*[-*+]\s+/.test(line)) {
                var items = [];
                while (i < lines.length && /^\s*[-*+]\s+/.test(lines[i])) {
                    items.push(lines[i].replace(/^\s*[-*+]\s+/, ''));
                    i++;
                }
                html += '<ul>' + items.map(function (it) {
                    return '<li>' + renderInline(escapeHtml(it)) + '</li>';
                }).join('') + '</ul>';
                continue;
            }
            if (/^\s*\d+\.\s+/.test(line)) {
                var ordered = [];
                while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
                    ordered.push(lines[i].replace(/^\s*\d+\.\s+/, ''));
                    i++;
                }
                html += '<ol>' + ordered.map(function (it) {
                    return '<li>' + renderInline(escapeHtml(it)) + '</li>';
                }).join('') + '</ol>';
                continue;
            }
            if (/^\s*$/.test(line)) { i++; continue; }
            var para = [];
            while (i < lines.length && !isBlockStart(lines[i])) { para.push(lines[i]); i++; }
            html += '<p>' + renderInline(escapeHtml(para.join('\n'))) + '</p>';
        }
        return html;
    }

    // ---- Rego syntax highlighter --------------------------------------------
    // Tokenizes comments, strings, numbers, keywords, built-in namespaces and
    // operators. Each token is HTML-escaped; anything unmatched passes through
    // escaped, so the output is always safe to inject.
    var REGO_KEYWORDS = {
        package: 1, import: 1, default: 1, some: 1, every: 1, in: 1, if: 1,
        else: 1, not: 1, with: 1, as: 1, contains: 1, null: 1, true: 1, false: 1
    };
    var REGO_BUILTINS = {
        count: 1, array: 1, concat: 1, object: 1, sprintf: 1, json: 1, split: 1,
        sort: 1, sum: 1, max: 1, min: 1, upper: 1, lower: 1, trim: 1, walk: 1,
        startswith: 1, endswith: 1, to_number: 1, is_string: 1, is_number: 1
    };

    function highlightRego(src) {
        var re = /(#[^\n]*)|("(?:\\.|[^"\\])*")|(\b\d+(?:\.\d+)?\b)|([A-Za-z_][A-Za-z0-9_]*)|(:=|==|!=|<=|>=|[=<>+\-*/])|([\s\S])/g;
        var out = '';
        var m;
        while ((m = re.exec(src)) !== null) {
            if (m[1]) {
                out += '<span class="tok-comment">' + escapeHtml(m[1]) + '</span>';
            } else if (m[2]) {
                out += '<span class="tok-string">' + escapeHtml(m[2]) + '</span>';
            } else if (m[3]) {
                out += '<span class="tok-number">' + escapeHtml(m[3]) + '</span>';
            } else if (m[4]) {
                if (REGO_KEYWORDS[m[4]]) {
                    out += '<span class="tok-keyword">' + m[4] + '</span>';
                } else if (REGO_BUILTINS[m[4]]) {
                    out += '<span class="tok-fn">' + m[4] + '</span>';
                } else {
                    out += escapeHtml(m[4]);
                }
            } else if (m[5]) {
                out += '<span class="tok-op">' + escapeHtml(m[5]) + '</span>';
            } else {
                out += escapeHtml(m[6]);
            }
        }
        return out;
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
