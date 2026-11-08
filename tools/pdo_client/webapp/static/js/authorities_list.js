// Authorities page: the creation form shows the fields of the kind chosen, and
// an authority card can be read before it is chosen.

(function () {
    function init() {
        var form = document.getElementById('create-authority-form');
        if (!form) return;

        function showKind() {
            var kind = form.querySelector('input[name="kind"]:checked').value;
            form.querySelectorAll('[data-kind-fields]').forEach(function (box) {
                box.classList.toggle('hidden', box.dataset.kindFields !== kind);
            });
        }
        form.querySelectorAll('input[name="kind"]').forEach(function (radio) {
            radio.addEventListener('change', showKind);
        });
        showKind();

        var templates = JSON.parse(document.getElementById('authority-templates-data').textContent);
        form.addEventListener('click', function (e) {
            var btn = e.target.closest('[data-view-template]');
            if (!btn) return;
            var t = templates[Number(btn.dataset.viewTemplate)];
            window.render.showCard(t.title, t.readme, t.rego_source);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
