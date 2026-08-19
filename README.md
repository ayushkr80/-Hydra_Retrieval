# Hydra RBAC Memory — Scoped Shared Memory Layer

Hydra RBAC Memory secures shared AI memory by treating authorization as a property of graph reachability rather than a post-retrieval filter.

## Key Features

1. **Graph Reachability Authorization**: Access to a memory node (Fact) is determined by the existence of an active path:
   `Actor -[:MEMBER_OF]-> Scope <-[:VISIBLE_TO]- Fact`
2. **Temporal Permissions**: Membership of actors in scopes, as well as the visibility of facts in scopes, are time-bound (`since` and `until` properties). The system evaluates authorization dynamically as of a specific historical or current timestamp.
3. **Transitive Provenance Security**: Derived facts (e.g. AI-inferred memories) inherit visibility restrictions from all their source facts. If Fact C is derived from Fact A (Finance) and Fact B (Sales), an agent must have permission to access both Finance and Sales scopes to view Fact C.

---

## Core Architecture

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

## Folder Structure

```
hydra-rbac-memory/
├── main.py          # Entrypoint to run the Textual TUI dashboard
├── graph.py         # Connection wrapper & secure Cypher queries for Neo4j
├── seed.py          # Database initializer with realistic demo data
├── agents.py        # CLI test scripts to verify permission checks
├── requirements.txt # Python dependency declarations
└── README.md        # Project documentation
```

---

## Getting Started

### 1. Installation

Create a virtual environment, activate it, and install dependencies:

```bash
pip install -r requirements.txt
```

Ensure you have a running Neo4j instance. The default configuration connects to:
- **URI**: `bolt://localhost:7687`
- **Username**: `neo4j`
- **Password**: `password`

You can override these using environment variables:
```bash
$env:NEO4J_URI="bolt://localhost:7687"
$env:NEO4J_USER="neo4j"
$env:NEO4J_PASSWORD="yourpassword"
```

### 2. Seeding the Demo Data

Run the seeding script to populate the graph with actors, scopes, facts, temporal links, and derivation provenance:

```bash
python seed.py
```

### 3. Running Verification Tests

Run the command-line tests to verify access patterns (e.g., checking temporal access active/expired and derived fact blocking):

```bash
python agents.py
```

### 4. Running the Dashboard

Launch the interactive Textual TUI dashboard to query facts and visualize authorization paths:

```bash
python main.py
```
