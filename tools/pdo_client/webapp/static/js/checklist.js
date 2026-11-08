// The requester's readiness checklist (app/checklist.py), as a table.
//
//   window.checklist.render(container, rows)  -> renders one row per fact
//   window.checklist.ready(rows)              -> every fact held or automatic
//
// Each row carries data-fact and data-status, so what the page says about a
// fact can be read off the page.

(function () {
    var LABELS = {
        held: 'Held',
        automatic: 'Automatic',
        ask: 'Ask',
        held_not_accepted: 'Held, not accepted here',
        unreachable: 'Unreachable',
    };

    function either(names) {
        return names.length ? names.join(' or ') : 'no accepted authority';
    }

    function explain(row) {
        if (row.self_asserted) {
            return row.status === 'held'
                ? 'Signed by your own wallet.'
                : 'Sign it with your own wallet, from the wallet\'s page.';
        }
        switch (row.status) {
            case 'held':
                return 'In your wallet, from an authority this asset accepts.';
            case 'automatic':
                return 'Obtained on the way, from ' + row.via + '.';
            case 'ask':
                return 'Ask ' + either(row.authorities) + '.';
            case 'held_not_accepted':
                return 'Held, but this asset accepts only ' + either(row.authorities) + '.';
            default:
                return row.authorities.length
                    ? 'Accepted: ' + row.authorities.join(', ') + ', but none can issue it from what you hold.'
                    : 'No authority is accepted for it.';
        }
    }

    function render(container, rows) {
        container.innerHTML = '';
        if (!rows.length) {
            container.innerHTML = '<p class="muted">This asset needs no facts.</p>';
            return;
        }
        var table = document.createElement('table');
        table.className = 'data-table checklist';
        table.innerHTML = '<thead><tr><th>Role</th><th>Fact</th><th>Status</th><th></th></tr></thead>';
        var body = document.createElement('tbody');
        rows.forEach(function (row) {
            var tr = document.createElement('tr');
            tr.dataset.fact = row.type;
            tr.dataset.status = row.status;
            var cells = [row.role, row.name, null, explain(row)];
            cells.forEach(function (text, i) {
                var td = document.createElement('td');
                if (i === 2) {
                    var badge = document.createElement('span');
                    badge.className = 'status status-' + row.status;
                    badge.textContent = LABELS[row.status];
                    td.appendChild(badge);
                } else {
                    td.textContent = text;
                }
                tr.appendChild(td);
            });
            body.appendChild(tr);
        });
        table.appendChild(body);
        container.appendChild(table);
    }

    function ready(rows) {
        return rows.every(function (r) { return r.status === 'held' || r.status === 'automatic'; });
    }

    window.checklist = { render: render, ready: ready };
})();
