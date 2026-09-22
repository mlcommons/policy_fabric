// Identity provisioning: enhance <form class="provision-form"> (the navbar
// identity selector and the config page) to stream provisioning progress
// through window.progress instead of a plain POST + redirect. The native POST
// to IdentitySetView / ConfigPageView stays as the no-JS fallback.

(function () {
    function onSubmit(e) {
        var form = e.currentTarget;
        var field = form.querySelector('[name="public_key"]');
        var publicKey = field ? (field.value || '').trim() : '';
        if (!publicKey) return;  // nothing selected/entered — let it be
        e.preventDefault();
        // The stream's terminal {redirect: "/"} lands on the home page.
        window.progress.run('/identity/provision/', { public_key: publicKey }, {
            title: 'Signing in…',
        });
    }

    function init() {
        document.querySelectorAll('form.provision-form').forEach(function (form) {
            form.addEventListener('submit', onSubmit);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
