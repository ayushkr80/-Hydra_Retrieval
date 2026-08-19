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
NEO4J_PASSWORD=YOUR_ACTUAL_NEO4J_PASSWORD
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
- Neo4j Browser Console to `http://localhost:7474` (Credentials: `neo4j` / `password` for demo)

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
