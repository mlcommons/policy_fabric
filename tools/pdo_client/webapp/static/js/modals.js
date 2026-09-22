// Generic modal open/close via data attributes.
//
//   <button data-modal-open="my-modal-id">Open</button>
//   <button data-modal-close="my-modal-id">Close</button>
//
// Click anywhere on a backdrop with class "modal-backdrop" to dismiss it.

(function () {
    function setHidden(modal, hidden) {
        if (!modal) return;
        modal.classList.toggle('hidden', hidden);
    }

    document.addEventListener('click', function (e) {
        var openTarget = e.target.closest('[data-modal-open]');
        if (openTarget) {
            setHidden(document.getElementById(openTarget.dataset.modalOpen), false);
            return;
        }
        var closeTarget = e.target.closest('[data-modal-close]');
        if (closeTarget) {
            setHidden(document.getElementById(closeTarget.dataset.modalClose), true);
            return;
        }
        // Click on the backdrop itself (not children) closes the modal.
        if (e.target.classList && e.target.classList.contains('modal-backdrop')) {
            setHidden(e.target, true);
        }
    });

    // Esc closes any open modal.
    document.addEventListener('keydown', function (e) {
        if (e.key !== 'Escape') return;
        document.querySelectorAll('.modal-backdrop:not(.hidden)').forEach(function (m) {
            m.classList.add('hidden');
        });
    });
})();
