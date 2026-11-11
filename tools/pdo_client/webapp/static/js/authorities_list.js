// Authorities page: the creation form shows the fields of the kind chosen.

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
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
