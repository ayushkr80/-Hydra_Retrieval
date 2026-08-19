import unittest
import os
from graph import HydraGraph, load_env
from agents import query_agent

class TestBasicAccess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_env()
        if not os.environ.get("NEO4J_PASSWORD"):
            raise unittest.SkipTest("NEO4J_PASSWORD not configured in environment.")

    def test_support_access(self):
        res = query_agent("Support", "Acme", "2026-08-19T00:00:00Z")
        self.assertIn("fact:acme_plan", res["accessible_ids"])
        self.assertIn("fact:acme_support", res["accessible_ids"])
        self.assertNotIn("fact:acme_arr", res["accessible_ids"])
        self.assertNotIn("fact:acme_deal", res["accessible_ids"])

    def test_finance_access(self):
        res = query_agent("Finance", "Acme", "2026-08-19T00:00:00Z")
        self.assertIn("fact:acme_plan", res["accessible_ids"])
        self.assertIn("fact:acme_arr", res["accessible_ids"])
        self.assertNotIn("fact:acme_support", res["accessible_ids"])
        self.assertNotIn("fact:acme_deal", res["accessible_ids"])

if __name__ == "__main__":
    unittest.main()
