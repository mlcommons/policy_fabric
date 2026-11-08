import json

from django.test import TestCase


def post(client, url, body):
    return client.post(url, json.dumps(body), content_type="application/json")


IRB_OFFICE = {
    "did": "did:pdo:irb-office#poc",
    "name": "Best University IRB office",
    "kind": "hand-signing",
    "operator": "vc_issuer",
    "facts": ["EthicsApprovalCredential", "IRBApprovalCredential"],
    "checks": "Signs after its own review.",
    "inputs": {},
    "sources": [],
    "metadata": {},
}

COMMITTEE_CHECK = {
    "did": "did:pdo:committee-check",
    "name": "Accredited-committee check",
    "kind": "rule-based",
    "operator": "vc_issuer",
    "facts": ["EthicsApprovalCredential"],
    "checks": "Approval by a committee accredited for the PI's institution.",
    "inputs": {"User": ["TeamCredential", "IRBApprovalCredential"]},
    "sources": [{"did": "did:pdo:registrar#poc", "credential_types": ["TeamCredential"]}],
    "metadata": {"card": "ACCREDITED-COMMITTEE-CHECK"},
}

TRUST_LIST = {
    "name": "Accredited IRBs",
    "maintainer": "national registry",
    "description": "IRBs the national registry accredits.",
    "entries": [{"did": IRB_OFFICE["did"], "credential_types": ["EthicsApprovalCredential"]}],
}


class Directory(TestCase):
    def test_authorities_are_listed_and_found_by_did(self):
        post(self.client, "/api/authorities/", IRB_OFFICE)
        post(self.client, "/api/authorities/", COMMITTEE_CHECK)

        listed = self.client.get("/api/authorities/").json()
        self.assertEqual([a["name"] for a in listed], [IRB_OFFICE["name"], COMMITTEE_CHECK["name"]])
        self.assertEqual(listed[1]["inputs"], COMMITTEE_CHECK["inputs"])

        found = self.client.get("/api/authorities/by_did/", {"did": "did:pdo:irb-office#poc"}).json()
        self.assertEqual(found["kind"], "hand-signing")
        self.assertEqual(self.client.get("/api/authorities/by_did/", {"did": "did:pdo:nobody"}).status_code, 404)

    def test_an_authority_needs_every_field_a_known_kind_and_a_unique_did(self):
        partial = {k: v for k, v in IRB_OFFICE.items() if k != "checks"}
        self.assertEqual(post(self.client, "/api/authorities/", partial).status_code, 400)
        self.assertEqual(post(self.client, "/api/authorities/", dict(IRB_OFFICE, kind="manual")).status_code, 400)
        self.assertEqual(post(self.client, "/api/authorities/", IRB_OFFICE).status_code, 201)
        self.assertEqual(post(self.client, "/api/authorities/", IRB_OFFICE).status_code, 409)

    def test_an_authority_record_can_be_updated_and_removed(self):
        created = post(self.client, "/api/authorities/", IRB_OFFICE).json()
        url = f"/api/authorities/{created['id']}/"
        updated = self.client.patch(url, json.dumps({"facts": ["IRBApprovalCredential"]}), content_type="application/json")
        self.assertEqual(updated.json()["facts"], ["IRBApprovalCredential"])
        self.client.delete(url)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_trust_lists_are_created_with_every_field(self):
        self.assertEqual(post(self.client, "/api/trust_lists/", TRUST_LIST).status_code, 201)
        self.assertEqual([t["name"] for t in self.client.get("/api/trust_lists/").json()], ["Accredited IRBs"])
        no_description = {k: v for k, v in TRUST_LIST.items() if k != "description"}
        self.assertEqual(post(self.client, "/api/trust_lists/", dict(no_description, name="other")).status_code, 400)

    def test_trust_list_entries_must_name_an_authority_and_its_types(self):
        bad = post(self.client, "/api/trust_lists/", dict(TRUST_LIST, entries=[{"did": "did:pdo:x"}]))
        self.assertEqual(bad.status_code, 400)
