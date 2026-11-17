"""Each component's Rego against its component.json, on both engines.

The interface a component declares is the same on OPA and on regorus (the engine the
contract embeds), its inputs (type, role, and whether it checks one against a key it
supplies) and output are the ones component.json gives, and its policy data schema is the
one the catalog derives from component.json.
"""

import unittest

import jsonschema

from build_catalog import policy_data_schema
from engine import eval_rule
from library import COMPONENTS, component_ids, component_json, opa_eval


def without_descriptions(schema):
    return {
        "type": schema["type"],
        "required": sorted(schema["required"]),
        "properties": {k: {kk: vv for kk, vv in v.items() if kk != "description"} for k, v in schema["properties"].items()},
    }


def name_of(text):
    return text.replace("/", "_").replace("-", "_")


class Interfaces(unittest.TestCase):
    """One test per component, test_<component id>, so that -k selects one."""


def interface_test(cid):
    def test(self):
        meta = component_json(cid)
        rego = COMPONENTS / cid / "component.rego"
        self.assertTrue(rego.exists(), f"{cid} has no component.rego")
        rule = f"data.pf.components.{cid}.interface"
        interface = opa_eval([rego], rule, {})
        self.assertEqual(eval_rule(rego.read_text(), rule, {}), interface)

        self.assertEqual(
            {name: (spec["type"], spec["role"], "supplied_key" in spec) for name, spec in interface["inputs"].items()},
            {name: (spec["type"], spec["role"], "supplied_key" in spec) for name, spec in meta["inputs"].items()},
        )
        output = meta["output"]["type"] if meta["group"] != "grant" else "Capability"
        self.assertEqual(interface["output"], output)

        # the same schema as the catalog derives from component.json, descriptions aside
        schema = interface["policy_data_schema"]
        derived = policy_data_schema(meta["policy_data"])
        if not derived:
            self.assertEqual(schema, {})
            return
        jsonschema.Draft202012Validator.check_schema(schema)
        self.assertEqual(without_descriptions(schema), without_descriptions(derived))

    return test


for component_id in component_ids():
    setattr(Interfaces, f"test_{name_of(component_id)}", interface_test(component_id))


if __name__ == "__main__":
    unittest.main()
