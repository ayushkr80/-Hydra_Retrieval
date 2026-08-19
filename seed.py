import sys
import os
from graph import HydraGraph, load_env

# Force stdout to use UTF-8 on Windows to support Unicode characters
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

DATE_START = "2026-08-01T00:00:00Z"
DATE_SALES_FINANCE_START = "2026-08-12T00:00:00Z"
DATE_SALES_FINANCE_END = "2026-08-14T23:59:59Z"

def seed():
    load_env()
    if not os.environ.get("NEO4J_PASSWORD"):
        print("Error: NEO4J_PASSWORD environment variable not set. Cannot run seed script.")
        sys.exit(1)

    graph = HydraGraph()
    try:
        print("\nClearing old data...")
        graph.clear_database()

        # =====================================================
        # CREATE ACTORS
        # =====================================================
        print("Creating Actors...")
        graph.create_actor("actor:agent_support", "Support Agent")
        graph.create_actor("actor:agent_sales", "Sales Agent")
        graph.create_actor("actor:agent_finance", "Finance Agent")

        # =====================================================
        # CREATE SCOPES
        # =====================================================
        print("Creating Scopes...")
        graph.create_scope("scope:company_wide", "Company-Wide")
        graph.create_scope("scope:team_support", "Team-Support")
        graph.create_scope("scope:team_sales", "Team-Sales")
        graph.create_scope("scope:team_finance", "Team-Finance")

        # =====================================================
        # MAP ACTORS TO SCOPES (TEMPORAL)
        # =====================================================
        print("Setting up Scope Memberships...")
        # Company-Wide is open to all agents
        graph.add_actor_to_scope("actor:agent_support", "scope:company_wide", DATE_START)
        graph.add_actor_to_scope("actor:agent_sales", "scope:company_wide", DATE_START)
        graph.add_actor_to_scope("actor:agent_finance", "scope:company_wide", DATE_START)

        # Standard team scopes
        graph.add_actor_to_scope("actor:agent_support", "scope:team_support", DATE_START)
        graph.add_actor_to_scope("actor:agent_sales", "scope:team_sales", DATE_START)
        graph.add_actor_to_scope("actor:agent_finance", "scope:team_finance", DATE_START)

        # Temporal/Cross-functional membership: Sales gets temporary access to Finance
        graph.add_actor_to_scope(
            "actor:agent_sales",
            "scope:team_finance",
            DATE_SALES_FINANCE_START,
            DATE_SALES_FINANCE_END
        )

        # =====================================================
        # CREATE FACTS AND ASSIGN SCOPES
        # =====================================================
        print("Creating Facts and Visibility...")
        facts = [
            # Acme Corp Facts
            ("fact:acme_plan", "Acme Corp is on Enterprise plan", "scope:company_wide"),
            ("fact:acme_contact", "Acme primary contact is Jane Doe", "scope:company_wide"),
            ("fact:acme_support", "Acme raised 3 support tickets this week", "scope:team_support"),
            ("fact:acme_arr", "Acme ARR is $240k", "scope:team_finance"),
            ("fact:acme_deal", "Acme upsell deal is in Q3 pipeline", "scope:team_sales"),
            ("fact:acme_churn", "Acme is flagged as high churn risk", "scope:team_finance"),

            # BetaCo Facts
            ("fact:beta_plan", "BetaCo is on Starter plan", "scope:company_wide"),
            ("fact:beta_overdue", "BetaCo payment is overdue by 45 days", "scope:team_finance"),
            ("fact:beta_support", "BetaCo satisfaction score dropped to 3 out of 10", "scope:team_support"),
            ("fact:beta_deal", "BetaCo renewal discussion is active", "scope:team_sales"),

            # Gamma Ltd Facts
            ("fact:gamma_plan", "Gamma Ltd is on Professional plan", "scope:company_wide"),
            ("fact:gamma_revenue", "Gamma Ltd ARR is $120k", "scope:team_finance")
        ]

        for fact_id, content, scope_id in facts:
            graph.create_fact(fact_id, content, DATE_START)
            graph.make_fact_visible_to(fact_id, scope_id, DATE_START)

        # =====================================================
        # DERIVED FACT AND PROVENANCE
        # =====================================================
        print("Creating Derived Fact and Provenance edges...")
        inference_id = "fact:acme_inference"
        inference_content = "Acme is an Enterprise customer at churn risk with an active upsell"
        
        graph.create_fact(inference_id, inference_content, DATE_START)

        # Provenance links (derived from one Finance fact and one Sales fact)
        graph.add_provenance(inference_id, "fact:acme_churn")  # Derived from Finance fact
        graph.add_provenance(inference_id, "fact:acme_deal")   # Derived from Sales fact

        # To prevent the "public because no ACL exists" security issue,
        # we assign fact:acme_inference to the company_wide scope.
        # Its provenance sources will still restrict it to Sales + Finance agents.
        graph.make_fact_visible_to(inference_id, "scope:company_wide", DATE_START)

        print("\n✓ Seed completed successfully")

    finally:
        graph.close()

if __name__ == "__main__":
    seed()
