"""Rego evaluation for the card tests, on regorus as the rego_policy_agent embeds it.

The regorus Python bindings are not on PyPI. Build them from the commit the contract pins
(pdo-contracts' rego-contract/src/packages/regorus/build.sh) with the contract's builtins, so
that a component which runs here also runs on-chain:

    cd regorus/bindings/python
    maturin build --release --no-default-features --features "regorus/opa-no-std,regorus/std"
"""

import json

import regorus


class RegoError(Exception):
    pass


def _check_builtins():
    """Refuse bindings built with builtins the contract lacks (time.* is the telling one)."""
    engine = regorus.Engine()
    engine.add_policy("probe.rego", "package probe\nimport rego.v1\nnow := time.now_ns()\n")
    try:
        engine.eval_rule("data.probe.now")
    except Exception:
        return
    raise RegoError(
        "the regorus bindings have time builtins, which the contract does not; "
        "build them with --features regorus/opa-no-std,regorus/std"
    )


_check_builtins()


def _engine(source):
    engine = regorus.Engine()
    try:
        engine.add_policy("policy.rego", source)
    except Exception as e:
        raise RegoError(f"the module does not compile: {e}")
    return engine


def eval_rule(source, rule, input_doc):
    """The value of ``rule`` over ``input_doc``, in a fresh engine, as the contract's eval_rego."""
    engine = _engine(source)
    engine.set_input_json(json.dumps(input_doc))
    try:
        return json.loads(engine.eval_rule_as_json(rule))
    except Exception as e:
        raise RegoError(f"{rule} failed: {e}")


def packages(source):
    """The packages a module defines, as data paths (``data.pf.components.x``)."""
    return _engine(source).get_packages()
