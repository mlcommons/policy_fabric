import unittest

from app.schemas import errors

APPROVAL = {
    "$id": "EthicsApprovalCredential",
    "type": "object",
    "properties": {
        "project": {"type": "string"},
        "approvedBy": {"type": "string"},
        "reference": {"type": "string"},
    },
    "required": ["project", "approvedBy"],
}


class Schemas(unittest.TestCase):
    def test_errors_name_what_is_wrong(self):
        self.assertEqual(errors({"project": "did:example:p1", "approvedBy": "did:example:irb"}, APPROVAL), [])
        self.assertEqual(errors({"project": "p1"}, APPROVAL), ["'approvedBy' is a required property"])
        self.assertEqual(errors({"project": 7, "approvedBy": "x"}, APPROVAL), ["project: 7 is not of type 'string'"])
