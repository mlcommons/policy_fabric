---
title: Policy Composer
hide:
  - navigation
  - toc
---

# Policy Composer

Draw a policy card from the components in this repository: add components from the library, wire each output to
an input that takes the same credential, choose the operation the card's capability issues, switch **required** on
at the output of each component the capability requires, and check the result. Download the `graph.json` and open
a pull request to add or change a card.

[Open the composer on a page of its own](composer/app/index.html){ .md-button }

<iframe class="pf-composer-frame" src="app/" title="Policy Composer" loading="lazy"></iframe>

<style>
  .md-main__inner.md-grid { max-width: none; }
  .md-content .pf-composer-frame { width: 100%; height: calc(100vh - 3rem); min-height: 640px; border: 0; border-radius: 8px; }
</style>
