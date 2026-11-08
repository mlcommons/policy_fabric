// Accept or withdraw authorities fact by fact, in the table templates/_trust_table.html
// renders: for an asset's policy, and for a rule-based authority's inputs.
//
//   window.trustTable.wire(panel, baseUrl)
//
// posts {did, credential_types} to baseUrl + 'accept-authority/' and
// {contract_id, credential_types} to baseUrl + 'withdraw-authority/', then reloads.

(function () {
    function wire(panel, baseUrl) {
        if (!panel) return;

        panel.addEventListener('change', function (e) {
            var select = e.target.closest('[data-accept-select]');
            if (!select) return;
            select.parentNode.querySelector('[data-accept-did]')
                .classList.toggle('hidden', select.value !== 'paste');
        });

        panel.addEventListener('click', async function (e) {
            var btn = e.target.closest('[data-action]');
            if (!btn) return;
            var url, payload;
            if (btn.dataset.action === 'withdraw') {
                url = baseUrl + 'withdraw-authority/';
                payload = { contract_id: btn.dataset.contractId, credential_types: [btn.dataset.fact] };
            } else if (btn.dataset.action === 'accept') {
                var box = btn.parentNode;
                var select = box.querySelector('[data-accept-select]');
                var did = select.value === 'paste'
                    ? box.querySelector('[data-accept-did]').value.trim()
                    : select.value;
                if (!did) {
                    window.flash('Choose an authority first.', 'error');
                    return;
                }
                url = baseUrl + 'accept-authority/';
                payload = { did: did, credential_types: [btn.dataset.fact] };
            } else {
                return;
            }
            btn.disabled = true;
            try {
                var res = await window.api.post(url, payload);
                window.flash(res.message, 'success');
                window.location.reload();
            } catch (err) {
                btn.disabled = false;
                window.flash(err.message, 'error');
            }
        });
    }

    window.trustTable = { wire: wire };
})();
