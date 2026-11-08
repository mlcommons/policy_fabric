"""Card folders, and the Rego engines that evaluate them.

A card is a folder with a card.json. Its rule is the policy.rego beside it, or
the one of the template it names. Modules are evaluated the way the policy agent
does: each in its own engine, with only the policy data meant for it.
"""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

FABRIC = Path(__file__).resolve().parents[2]
POLICY_CARDS = FABRIC / "policy_cards"
AUTHORITY_CARDS = FABRIC / "authority_cards"
CREDENTIALS = FABRIC / "credentials"
TEMPLATES = POLICY_CARDS / "templates"
GUARDIANS = FABRIC / "tools" / "guardians"
COMBINATORS = Path(__file__).resolve().parent / "combinators"

# The kind of subject a role's holder is: the requester's wallet, or the script.
HOLDER_KINDS = {"User": "wallet", "Script": "script"}


class Card:
    def __init__(self, folder, root):
        self.folder = folder
        self.manifest = json.loads((folder / "card.json").read_text())
        relative = folder.relative_to(root)
        # the template registry's name for it, which is also its module id
        self.name = "-".join(relative.parts).upper()
        self.relative = str(relative)

    @property
    def rule_path(self):
        if "template" in self.manifest:
            return TEMPLATES / self.manifest["template"] / "policy.rego"
        return self.folder / "policy.rego"

    @property
    def source(self):
        return self.rule_path.read_text()

    def __repr__(self):
        return f"Card({self.relative})"


def cards(root):
    return [Card(path.parent, root) for path in sorted(root.rglob("card.json"))]


def credential_schemas():
    return {
        path.name[: -len(".schema.json")]: json.loads(path.read_text())
        for path in CREDENTIALS.glob("*.schema.json")
    }


def guardian_types():
    """The guardian types a policy can be attached to: every one except public."""
    types = set()
    for manifest in GUARDIANS.glob("*/guardian.json"):
        kind = json.loads(manifest.read_text())["type"]
        if kind != "public":
            types.add(kind)
    return types


class Engine:
    """A Rego engine on the command line: opa, or the regorus example binary."""

    def __init__(self, name, binary):
        self.name = name
        self.binary = binary

    @classmethod
    def find(cls, name, variable):
        """The engine named by $variable if it is set, else the one on the PATH."""
        binary = os.environ[variable] if variable in os.environ else shutil.which(name)
        if binary is None:
            raise RuntimeError(f"{name} is not installed; put it on the PATH or set ${variable}")
        return cls(name, binary)

    def eval(self, source, query, input_value=None):
        results = self.results(source, query, input_value)
        if not results:
            raise RuntimeError(f"{self.name}: {query} is undefined")
        return results[0]["expressions"][0]["value"]

    def issues(self, source):
        """The type the module declares it issues, read with a query as the policy
        agent reads it: [type], or [] when the module leaves the rule out."""
        return [r["expressions"][0]["value"] for r in self.results(source, "data.subpolicy.issues")]

    def results(self, source, query, input_value=None):
        with tempfile.TemporaryDirectory() as work:
            policy = Path(work) / "policy.rego"
            policy.write_text(source)
            command = [self.binary, "eval", "-d", str(policy)]
            if self.name == "opa":
                command[2:2] = ["-f", "json"]
            if input_value is not None:
                path = Path(work) / "input.json"
                path.write_text(json.dumps(input_value))
                command += ["-i", str(path)]
            command.append(query)
            done = subprocess.run(command, capture_output=True, text=True)
            if done.returncode != 0:
                raise RuntimeError(f"{self.name} failed on {query}: {done.stderr}{done.stdout}")
            # both engines leave "result" out when the query is undefined
            output = json.loads(done.stdout)
            return output["result"] if "result" in output else []


def combinator(name):
    return (COMBINATORS / f"{name}.rego").read_text()


class PolicyAgent:
    """What rego_policy_agent does with its modules, minus the signatures."""

    def __init__(self, engine, modules, policy_data):
        self.engine = engine
        self.modules = modules  # [(module_id, source)]
        self.policy_data = policy_data

    def requirements(self):
        each = [self.engine.eval(source, "data.subpolicy.requirements") for _, source in self.modules]
        return self.engine.eval(
            combinator("requirements"), "data.combine.result", {"subpolicy_requirements": each}
        )

    def judge(self, presentations, holders, request):
        base = {
            "presentations": presentations,
            "holders": holders,
            "request": request,
            "trusted_issuers": {},
        }
        outputs = []
        for module_id, source in self.modules:
            if module_id not in self.policy_data:
                raise ValueError(f"no policy data for module {module_id}")
            outputs.append(
                self.engine.eval(source, "data.subpolicy.result", dict(base, policy_data=self.policy_data[module_id]))
            )
        return self.engine.eval(combinator("results"), "data.combine.result", {"subpolicy_outputs": outputs})
