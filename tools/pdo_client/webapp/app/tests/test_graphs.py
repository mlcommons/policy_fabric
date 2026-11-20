"""Composing the graphs of the cards on one asset, and what requesters present to it."""

import copy
import unittest

from app import graphs

from .test_views import CATALOG, DOWNLOAD_PARAMETERS, GS_GRAPH, IS_GRAPH


class Compose(unittest.TestCase):
    def test_one_card_is_its_own_graph(self):
        self.assertEqual(graphs.compose([GS_GRAPH])["nodes"], GS_GRAPH["nodes"])

    def test_several_cards_require_one_capability(self):
        graph = graphs.compose([GS_GRAPH, IS_GRAPH])
        self.assertEqual(graph["name"], "Geographical Restriction + Institution Specific Restriction")
        self.assertEqual(graph["capability"]["requires"], ["geographical_restriction", "institution_specific_restriction"])
        self.assertEqual(graph["capability"]["parameters"], DOWNLOAD_PARAMETERS)

    def test_a_shared_node_is_kept_once(self):
        other = copy.deepcopy(IS_GRAPH)
        other["nodes"]["geographical_restriction"] = GS_GRAPH["nodes"]["geographical_restriction"]
        graph = graphs.compose([GS_GRAPH, other])
        self.assertEqual(list(graph["nodes"]).count("geographical_restriction"), 1)

    def test_a_node_two_cards_use_differently_is_refused(self):
        other = copy.deepcopy(GS_GRAPH)
        other["nodes"]["geographical_restriction"]["inputs"]["location"] = {"from": "node", "node": "x", "accept_presented": False}
        with self.assertRaisesRegex(ValueError, "differently"):
            graphs.compose([GS_GRAPH, other])

    def test_cards_issuing_different_operations_are_refused(self):
        other = copy.deepcopy(IS_GRAPH)
        other["capability"]["operation"] = "do_inference"
        with self.assertRaisesRegex(ValueError, "different operations"):
            graphs.compose([GS_GRAPH, other])


class Requirements(unittest.TestCase):
    def test_a_composed_graph_needs_every_card(self):
        graph = graphs.compose([GS_GRAPH, IS_GRAPH])
        self.assertEqual(graphs.requirement_alternatives(graph, CATALOG),
                         [{"User": ["AffiliationCredential", "LocationCredential", "publicKeyCredential"]}])

    def test_an_alternative_is_open_when_every_credential_is_accepted(self):
        bundles = [{"User": ["LocationCredential", "publicKeyCredential"]}, {"User": ["ScriptOwnershipCredential"]}]
        accepted = {"LocationCredential": ["did:pdo:office"], "publicKeyCredential": []}
        self.assertEqual(graphs.satisfiable(bundles, accepted, {"ScriptOwnershipCredential"}), [bundles[1]])
