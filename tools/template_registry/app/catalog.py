"""The policy catalog of the seeded folders, as tools/policy_catalog/build_catalog.py builds it.

The builder is not copied into this app: run.sh puts its folder on the path, and build.sh
puts it beside the app in the image, at the same place relative to run.sh.
"""

import os
from pathlib import Path

from build_catalog import build, check_graph


def folders():
    return (
        Path(os.environ["CREDENTIALS_DIR"]),
        Path(os.environ["POLICY_COMPONENTS_DIR"]),
        Path(os.environ["POLICY_CARDS_DIR"]),
    )


def catalog():
    """The catalog, or ValueError naming every problem in the folders."""
    built, problems = build(*folders())
    if problems:
        raise ValueError("; ".join(problems))
    return built


def graph_problems(name, graph):
    """What is wrong with a graph a template would carry, against the seeded components."""
    built = catalog()
    return check_graph(name, graph, built["components"], built["credentials"])
