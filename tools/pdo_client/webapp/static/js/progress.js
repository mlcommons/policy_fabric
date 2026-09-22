// Reusable multi-step progress UI.
//
//   window.progress.run(url, payload, opts) -> Promise<terminalEvent|null>
//
// POSTs `payload` as JSON to `url`, expects an NDJSON stream of step events
// (see app/views/_streaming.py), and renders each step live in the shared
// #progress-modal. Options:
//   title      -- modal heading while it runs
//   method     -- HTTP method (default POST)
//   onComplete(term) -- called on success instead of the default redirect; use
//                       it to consume term.result (e.g. show downloaded data)
//   onError(term)    -- called when the flow reports an error
// Without onComplete, a terminal {redirect: url} navigates there.
//
// Any <form data-progress-url="..." data-progress-title="..."> is auto-wired:
// its fields become the payload (repeated names -> arrays) and submit runs the
// flow instead of a plain POST.

(function () {
    function csrfToken() {
        var m = document.querySelector('meta[name="csrf-token"]');
        return m ? m.getAttribute('content') : '';
    }
    function el(id) { return document.getElementById(id); }

    var ICONS = { running: '', done: '✓', skip: '✓', error: '✕', pending: '•' };

    function resetModal(title) {
        // Close any other open modal (e.g. the form the user just submitted) so
        // the progress modal isn't rendered behind it.
        document.querySelectorAll('.modal-backdrop').forEach(function (m) {
            if (m.id !== 'progress-modal') m.classList.add('hidden');
        });
        el('progress-title').textContent = title || 'Working…';
        el('progress-steps').innerHTML = '';
        el('progress-close').style.display = 'none';
        el('progress-modal').classList.remove('hidden');
    }

    function setRow(row, status, label, detail) {
        row.dataset.status = status;
        row.querySelector('.progress-step-label').textContent = label || '';
        var icon = row.querySelector('.progress-step-icon');
        if (status === 'running') {
            icon.innerHTML = '<span class="progress-spin"></span>';
        } else {
            icon.textContent = ICONS[status] || ICONS.pending;
        }
        row.querySelector('.progress-step-detail').textContent = detail || '';
    }

    function upsertStep(ev) {
        var steps = el('progress-steps');
        var row = steps.querySelector('[data-step="' + ev.step + '"]');
        if (!row) {
            row = document.createElement('li');
            row.className = 'progress-step';
            row.dataset.step = ev.step;
            row.innerHTML =
                '<span class="progress-step-icon"></span>' +
                '<span class="progress-step-label"></span>' +
                '<span class="progress-step-detail"></span>';
            steps.appendChild(row);
        }
        // "start" reads as a running spinner; the rest map straight through.
        setRow(row, ev.status === 'start' ? 'running' : ev.status, ev.label, ev.detail);
    }

    function fail(title) {
        el('progress-title').textContent = title;
        el('progress-close').style.display = '';
    }

    var active = false;

    async function run(url, payload, opts) {
        opts = opts || {};
        if (active) return null;  // one flow at a time
        active = true;
        try {
            resetModal(opts.title);

            var resp;
            try {
                resp = await fetch(url, {
                    method: opts.method || 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken(),
                        'X-Requested-With': 'fetch',
                    },
                    body: JSON.stringify(payload || {}),
                });
            } catch (e) {
                fail('Could not reach the server');
                return null;
            }

            if (!resp.ok || !resp.body) {
                var msg = 'HTTP ' + resp.status;
                try { msg = (await resp.json()).error || msg; } catch (e) { /* ignore */ }
                fail('Error: ' + msg);
                return null;
            }

            var term = null;
            function handle(ev) {
                if (ev.step === 'complete') { term = ev; } else { upsertStep(ev); }
            }

            var reader = resp.body.getReader();
            var decoder = new TextDecoder();
            var buf = '';
            while (true) {
                var chunk = await reader.read();
                if (chunk.done) break;
                buf += decoder.decode(chunk.value, { stream: true });
                var idx;
                while ((idx = buf.indexOf('\n')) >= 0) {
                    var line = buf.slice(0, idx).trim();
                    buf = buf.slice(idx + 1);
                    if (line) { try { handle(JSON.parse(line)); } catch (e) { /* skip */ } }
                }
            }
            if (buf.trim()) { try { handle(JSON.parse(buf.trim())); } catch (e) { /* skip */ } }

            el('progress-close').style.display = '';
            if (term && term.status === 'error') {
                el('progress-title').textContent = 'Something went wrong';
                if (opts.onError) opts.onError(term);
                return term;
            }
            if (opts.onComplete) {
                opts.onComplete(term || {});
            } else if (term && term.redirect) {
                setTimeout(function () { window.location = term.redirect; }, 600);
            }
            return term;
        } finally {
            active = false;
        }
    }

    // --- declarative <form data-progress-url> binding --------------------
    function formPayload(form) {
        var out = {};
        new FormData(form).forEach(function (v, k) {
            if (k === 'csrfmiddlewaretoken') return;
            if (k in out) {
                if (!Array.isArray(out[k])) out[k] = [out[k]];
                out[k].push(v);
            } else {
                out[k] = v;
            }
        });
        return out;
    }

    function init() {
        document.querySelectorAll('form[data-progress-url]').forEach(function (form) {
            form.addEventListener('submit', function (e) {
                e.preventDefault();
                run(form.dataset.progressUrl, formPayload(form), {
                    title: form.dataset.progressTitle,
                });
            });
        });
    }

    window.progress = { run: run };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
