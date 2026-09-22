// Tiny shared helpers for JSON POST endpoints.
//
//   window.api.post(url, data)           -> resolves to parsed JSON,
//                                           rejects with Error on !ok responses
//   window.flash(msg, type='success')    -> alert(...) with a small prefix
//   window.confirmJSON(formEl, url)      -> serialize a <form> to a JSON
//                                           payload (useful for forms inside
//                                           modals that we post via fetch)

(function () {
    function csrfToken() {
        var el = document.querySelector('meta[name="csrf-token"]');
        return el ? el.getAttribute('content') : '';
    }

    async function post(url, data) {
        var resp = await fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken(),
                'X-Requested-With': 'fetch',
            },
            body: JSON.stringify(data || {}),
        });
        var body = {};
        try { body = await resp.json(); } catch (e) { /* non-JSON response */ }
        if (!resp.ok) {
            var err = new Error(body.error || ('HTTP ' + resp.status));
            err.status = resp.status;
            err.body = body;
            throw err;
        }
        return body;
    }

    function flash(msg, type) {
        var prefix = type === 'error' ? 'Error: '
                   : (type === 'success' ? 'Success: ' : '');
        window.alert(prefix + msg);
    }

    function formToObject(formEl) {
        var out = {};
        new FormData(formEl).forEach(function (v, k) {
            if (k === 'csrfmiddlewaretoken') return;
            out[k] = v;
        });
        return out;
    }

    window.api = { post: post };
    window.flash = flash;
    window.formToObject = formToObject;
})();
