"""Type-only declarations for the globals ``manage.py seed`` injects.

The ``seed`` command runs each seed file with these names already defined as
globals (see ``app/management/commands/seed.py``), so seeds never import them
at runtime. This module exists purely so VS Code / Pylance knows what they are:
import it under a ``TYPE_CHECKING`` guard and the editor will show signatures,
docstrings, and autocomplete for ``runner.*`` (and friends), while the import
is skipped at runtime.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from seed_context import runner, state, bindings, settings

    wallet_id = runner.create_wallet("seed wallet", "user1")  # fully completed
"""

import app.pdo_runner as runner  # noqa: F401  (re-exported as the runner type)
from django.conf import settings  # noqa: F401
from pdo.client.builder.bindings import Bindings
from pdo.client.builder.state import State

# Declared (not assigned) so editors know their types without a runtime value.
state: State
bindings: Bindings
