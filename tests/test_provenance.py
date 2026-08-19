import unittest
import os
from graph import HydraGraph, load_env
from agents import query_agent

class TestProvenanceAccess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_env()
        if not os.environ.get("NEO4J_PASSWORD"):
            raise unittest.SkipTest("NEO4J_PASSWORD not configured.")

    def test_derived_fact_blocked_for_finance(self):
        # Finance agent only has Finance, not Sales -> Blocked
        res = query_agent("Finance", "Acme", "2026-08-19T00:00:00Z")
        self.assertNotIn("fact:acme_inference", res["accessible_ids"])
        self.assertIn("fact:acme_inference", res["blocked_ids"])

    def test_derived_fact_blocked_for_sales_after_revocation(self):
        # Sales agent only has Sales on Aug 19 -> Blocked
        res = query_agent("Sales", "Acme", "2026-08-19T00:00:00Z")
        self.assertNotIn("fact:acme_inference", res["accessible_ids"])
        self.assertIn("fact:acme_inference", res["blocked_ids"])

    def test_derived_fact_allowed_when_both_scopes_active(self):
        # Sales agent has both Sales and Finance on Aug 13 -> Allowed
        res = query_agent("Sales", "Acme", "2026-08-13T00:00:00Z")
        self.assertIn("fact:acme_inference", res["accessible_ids"])
        self.assertNotIn("fact:acme_inference", res["blocked_ids"])

    def test_derived_fact_blocked_for_support(self):
        # Support agent has no Finance/Sales access -> Blocked
        res = query_agent("Support", "Acme", "2026-08-19T00:00:00Z")
        self.assertNotIn("fact:acme_inference", res["accessible_ids"])
        self.assertIn("fact:acme_inference", res["blocked_ids"])

if __name__ == "__main__":
    unittest.main()
