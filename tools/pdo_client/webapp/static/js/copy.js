// Generic "copy to clipboard" for any element with a data-copy attribute.
// Copies the attribute's value verbatim (already formatted server-side, e.g. a
// DID or a JSON-escaped credential claim).
//
// navigator.clipboard only exists in a "secure context" (HTTPS, or exactly
// "localhost") — a plain-HTTP forwarded port (e.g. a Codespaces preview
// opened over http://, or any non-localhost host) doesn't have it at all, so
// we fall back to the older execCommand('copy') path (via a hidden textarea)
// whenever the modern API is missing or fails.

(function () {
    function fallbackCopy(text) {
        var textarea = document.createElement('textarea');
        textarea.value = text;
        // Keep it out of view and out of the document flow, but still
        // selectable — execCommand('copy') requires a real selection.
        textarea.style.position = 'fixed';
        textarea.style.top = '0';
        textarea.style.left = '-9999px';
        textarea.setAttribute('readonly', '');
        document.body.appendChild(textarea);
        textarea.select();
        textarea.setSelectionRange(0, text.length);
        var ok = false;
        try {
            ok = document.execCommand('copy');
        } catch (e) {
            ok = false;
        }
        document.body.removeChild(textarea);
        return ok;
    }

    function reportResult(ok) {
        window.flash(
            ok ? 'Copied to clipboard.' : 'Copy failed. Select and copy the text manually.',
            ok ? 'success' : 'error'
        );
    }

    document.addEventListener('click', function (e) {
        var btn = e.target.closest('[data-copy]');
        if (!btn) return;
        var text = btn.getAttribute('data-copy') || '';

        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(text).then(
                function () { reportResult(true); },
                // Some browsers expose the API but still reject the call
                // (e.g. missing permission) — fall back before giving up.
                function () { reportResult(fallbackCopy(text)); }
            );
            return;
        }

        reportResult(fallbackCopy(text));
    });
})();
