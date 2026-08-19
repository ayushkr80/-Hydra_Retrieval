# Hydra RBAC Memory — Scoped Shared Memory Layer

## Problem

Multi-agent systems increasingly share organizational memory. Traditional retrieval systems fetch information first and apply authorization filters afterward, creating a critical risk that restricted information accidentally enters the agent's context window. 

Hydra RBAC Memory solves this security vulnerability by making **authorization a property of graph reachability** rather than a post-retrieval filter.

---

## Our Solution

Authorization is evaluated directly during graph traversal by checking for an active, time-bound path:

```
Actor
  │
  │ MEMBER_OF (since, until)
  ▼
Scope
  ▲
  │ VISIBLE_TO (since, until)
  │
Fact
```

If there is no valid path (due to missing membership, expired access, or scope mismatch), the fact is completely inaccessible during traversal.

---

## Why HydraDB?

- **Native Authorization Traversal**: Authorization is represented directly as graph relationships. Security is not an afterthought; it is baked into graph reachability queries.
- **Temporal Access Properties**: Historical and temporary access (e.g. cross-functional delegation) are represented through time-bound edge properties (`since`, `until`) and validated at checkout timestamps.
- **Transitive Provenance Security**: Provenance relations (`DERIVED_FROM`) create transitive constraints. When AI agents derive new facts from multiple sources (e.g. Finance + Sales), visibility is dynamically computed as the intersection of all source permissions.

---

## Security Decision Example

### Scenario 1: Standard Query
- **Query Time**: `2026-08-19`
- **Agent**: `Sales`
- **Topic**: `Acme`

**Results**:
- `✓ Acme Corp is on Enterprise plan` (Scope: Company-Wide)
- `✓ Acme primary contact is Jane Doe` (Scope: Company-Wide)
- `✓ Acme upsell deal is in Q3 pipeline` (Scope: Team-Sales)
- `🔒 Acme ARR` (Scope: Team-Finance | Reason: NO ACTIVE PATH)
- `🔒 Acme Churn Risk` (Scope: Team-Finance | Reason: NO ACTIVE PATH)

---

### Scenario 2: Derived Fact Transitive Check
- **Query Fact**: `fact:acme_inference`
- **Derivation Path**:
  ```
  fact:acme_inference
  ├── Churn Risk ──► Finance Scope (🔒 BLOCKED)
  └── Upsell Deal ──► Sales Scope (✓ ALLOWED)
  ```
- **Result**: **`🔒 BLOCKED`**
- **Reason**: Agent lacks access to 1 source fact (Finance). The authorization traversal checks access to *all* derivation nodes, blocking the inference node even though the agent has access to the upsell source fact.

---

## Core Schema & Traversal

```
                  ┌──────────────┐
                  │    Actors    │ (Support, Sales, Finance)
                  └──────┬───────┘
                         │
                     MEMBER_OF (since, until)
                         │
                         ▼
                  ┌──────────────┐
                  │    Scopes    │ (Company-Wide, Support, Sales, Finance)
                  └──────▲───────┘
                         │
                     VISIBLE_TO (since, until)
                         │
                  ┌──────┴───────┐
                  │    Facts     │ (Acme ARR, Support tickets, Deals, Churn)
                  └──────▲───────┘
                         │
                    DERIVED_FROM
                         │
                  ┌──────┴───────┐
                  │  Inferences  │ (Derived Facts)
                  └──────────────┘
```

---

## Installation & Setup

### 1. Install Dependencies
Create a virtual environment, activate it, and install:
```bash
pip install -r requirements.txt
```

### 2. Configure Credentials (Strict Environment Variables)
This project enforces safe credentials handling. It does not use hardcoded passwords. Create a `.env` file in the root of the project:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<your-local-password>
```

*(The application will automatically load variables from `.env` or `../.env` at startup).*

---

## Running the Application

### 1. Launch Neo4j (Optional Helper)
If you have Docker running locally, you can start Neo4j instantly using our helper compose file:
```bash
docker compose -f docker-compose.neo4j.yml up -d
```
This maps:
- Bolt connection to port `7687`
- Neo4j Browser Console to `http://localhost:7474` (Credentials: `neo4j` / your configured `NEO4J_PASSWORD`)

### 2. Seed realistic Demo Data
Populates the graph database with Actors, Scopes, Facts, temporal relations, and derived provenance:
```bash
python seed.py
```

### 3. Run Scenario Verification Tests
Execute the explicit verification test suite covering Support isolation, Finance limits, historical Sales delegation, revoked Sales access, and derived fact blocking:
```bash
python agents.py
```

### 4. Run Automated Test Suite
Run the suite of automated unittest scripts:
```bash
python -m unittest discover tests/
```

### 5. Launch the Dashboard (TUI)
Start the Textual console dashboard to visually run traversal queries and audit paths:
```bash
python main.py
```

---

## 2-3 Minute Hackathon Demo Flow

Use this step-by-step walkthrough to present the core security features to the judges in under 3 minutes:

### 1. **Explain the Problem (15 seconds)**
Show the dashboard running. Explain: *"Traditional systems retrieve memories first and filter permissions later. If search fetches a restricted memory, it risks entering the LLM context window. Hydra makes authorization a native property of graph reachability."*

### 2. **Basic RBAC & Isolation (30 seconds)**
- Select **Support Agent** on the left.
- Search for topic `"Acme"`.
- Click on `✓ Acme raised 3 support tickets this week`. Show the path: `Support → Team-Support → Fact` is active.
- Click on `🔒 Acme ARR is $240k`. Show the block: `Scope (Team-Finance) 🔒 X (NO VALID PATH)`. The fact exists in the DB, but the graph search cannot cross the scope.

### 3. **Temporal Access & Delegation (45 seconds)**
- Change topic time to `2026-08-13T00:00:00Z` (Aug 13).
- Select **Sales Agent**.
- Run query. Click on `✓ Acme ARR is $240k`. Point out: *"On Aug 13, the Sales Agent had active temporary delegation to the Finance scope. The graph path is fully green."*
- Now change topic time back to `2026-08-19T00:00:00Z` (Aug 19).
- Run query. Click on `🔒 Acme ARR is $240k`. Point out: *"On Aug 19, the delegation expired. The MEMBER_OF link immediately breaks, returning BLOCKED without any code changes."*

### 4. **Transitive Provenance Isolation (45 seconds)**
- Select **Finance Agent** (on Aug 19) and query `"Acme"`.
- Click on `🔒 Acme is an Enterprise customer at churn risk...` (Derived Fact).
- Show the Provenance tree on the right:
  - `✓ Churn Risk` (Finance source) is accessible.
  - `✗ Upsell Deal` (Sales source) is blocked.
- Explain: *"This is a derived AI memory. Even though the Finance Agent has direct access to the Churn Risk source, they lack access to the Sales upsell deal. Because permissions are transitive across graph derivations, the derived fact remains securely BLOCKED."*
- Select **Sales Agent** (on Aug 13) and query `"Acme"`.
- Click on `✓ Acme is an Enterprise customer at churn risk...`.
- Explain: *"Only when the agent possesses access to both Finance and Sales scopes (as Sales does during their temporal delegation window on Aug 13) does the entire provenance tree resolve to ALLOWED."*
