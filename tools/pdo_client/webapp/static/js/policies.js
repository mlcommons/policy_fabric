// The Policies page: every card of the catalog, drawn as its graph.
(function () {
    function init() {
        var node = document.getElementById('policy-catalog');
        if (!node) return;
        var catalog = JSON.parse(node.textContent);
        document.querySelectorAll('[data-graph-of]').forEach(function (el) {
            window.PolicyGraph.render(el, catalog.cards[el.dataset.graphOf].graph, catalog, 'light');
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
