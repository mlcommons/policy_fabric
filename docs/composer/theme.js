/* The composer follows the docs site's theme. MkDocs Material marks dark mode with data-md-color-scheme="slate"
   on its <body>; the composer runs in an iframe of the same origin, so it reads that attribute and watches it,
   and sets data-theme on <html> (the .pf-graph element that policy_graph.css and composer.css theme).
   Opened on its own, it sets nothing and both stylesheets follow prefers-color-scheme. So it does when framed
   by another origin, where window.frameElement is null, or by a page whose <body> has no scheme. Runs in <head>,
   before the page is drawn. */
(function () {
  "use strict";
  var host = window.frameElement ? window.frameElement.ownerDocument.body : null;
  if (!host) return;
  function apply() {
    var scheme = host.getAttribute("data-md-color-scheme");
    if (scheme === null) document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", scheme === "slate" ? "dark" : "light");
  }
  apply();
  new MutationObserver(apply).observe(host, { attributes: true, attributeFilter: ["data-md-color-scheme"] });
})();
