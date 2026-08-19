import unittest
import os
from graph import HydraGraph, load_env
from agents import query_agent

class TestTemporalAccess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_env()
        if not os.environ.get("NEO4J_PASSWORD"):
            raise unittest.SkipTest("NEO4J_PASSWORD not configured.")

    def test_sales_temporal_access_active(self):
        # On Aug 13, Sales has active temporal access to Finance
        res = query_agent("Sales", "Acme", "2026-08-13T00:00:00Z")
        self.assertIn("fact:acme_arr", res["accessible_ids"])
        self.assertIn("fact:acme_churn", res["accessible_ids"])

    def test_sales_temporal_access_expired(self):
        # On Aug 19, Sales temporal access is expired
        res = query_agent("Sales", "Acme", "2026-08-19T00:00:00Z")
        self.assertNotIn("fact:acme_arr", res["accessible_ids"])
        self.assertNotIn("fact:acme_churn", res["accessible_ids"])

if __name__ == "__main__":
    unittest.main()
