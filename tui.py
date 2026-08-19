from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Input, Button, Label, RadioSet, RadioButton, ListView, ListItem
from graph import HydraGraph, load_env
import os
import traceback
import sys

# Force stdout to use UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

class HeaderListItem(ListItem):
    def __init__(self, text: str):
        super().__init__()
        self.text = text
        self.disabled = True

    def compose(self) -> ComposeResult:
        yield Label(f"─── {self.text} ───", classes="header-label")

class FactListItem(ListItem):
    def __init__(self, fact_id: str, content: str, is_allowed: bool, scope_name: str, actor_name: str, is_derived: bool):
        super().__init__()
        self.fact_id = fact_id
        self.content = content
        self.is_allowed = is_allowed
        self.scope_name = scope_name
        self.actor_name = actor_name
        self.is_derived = is_derived

    def compose(self) -> ComposeResult:
        icon = "✓" if self.is_allowed else "🔒"
        style_class = "allowed-fact" if self.is_allowed else "blocked-fact"
        
        # Build multi-line rich text explanation (Priority 3)
        title = f"{icon} {self.content}"
        
        if self.is_allowed:
            if self.is_derived:
                subtitle = f"  Type: Derived  |  Path: Fully Authorized Provenance"
            else:
                subtitle = f"  Scope: {self.scope_name}  |  Path: {self.actor_name} → {self.scope_name} → Fact"
        else:
            if self.is_derived:
                subtitle = f"  Required Scopes: {self.scope_name}  |  Reason: Lacks access to at least one provenance source"
            else:
                subtitle = f"  Required Scope: {self.scope_name}  |  Reason: NO ACTIVE PATH"
                
        yield Label(f"{title}\n[dim]{subtitle}[/dim]", classes=style_class)

class HydraRbacTui(App):
    CSS = """
    Screen {
        background: #121212;
        color: #e0e0e0;
    }
    
    #app-title {
        text-align: center;
        background: #005f73;
        color: #ffffff;
        padding: 1;
        text-style: bold;
        height: 3;
    }
    
    #main-layout {
        height: 1fr;
    }
    
    .column {
        height: 1fr;
    }
    
    #left-col {
        width: 25%;
    }
    
    #middle-col {
        width: 45%;
    }
    
    #right-col {
        width: 30%;
    }
    
    .pane {
        border: tall #005f73;
        padding: 1;
        margin: 1;
        background: #1e1e1e;
    }
    
    #agents-pane {
        height: 1fr;
    }
    
    #query-pane {
        height: auto;
    }
    
    #results-pane {
        height: 1fr;
    }
    
    #trace-pane {
        height: 1fr;
    }
    
    .panel-title {
        text-style: bold;
        color: #94d2bd;
        margin-bottom: 1;
    }
    
    .label-field {
        margin-top: 1;
        text-style: bold;
        color: #ca5555;
    }
    
    #run-btn {
        margin-top: 1;
        margin-bottom: 1;
        width: 100%;
        background: #0a9396;
        color: white;
    }
    
    #run-btn:hover {
        background: #94d2bd;
        color: black;
    }
    
    #results-list {
        background: #121212;
        border: solid #005f73;
        height: 1fr;
    }
    
    .header-label {
        color: #ee9b00;
        text-style: bold;
        text-align: center;
        background: #2b2d42;
        width: 100%;
        padding: 1;
    }
    
    .allowed-fact {
        color: #52b788;
        text-style: bold;
        padding: 1;
    }
    
    .blocked-fact {
        color: #e63946;
        text-style: bold;
        padding: 1;
    }
    
    #trace-content {
        background: #121212;
        padding: 1;
        border: solid #005f73;
        height: 1fr;
    }
    
    #provenance-footer {
        height: 3;
        background: #005f73;
        color: #ffffff;
        text-align: center;
        padding: 1;
        text-style: bold;
        margin: 1;
    }
    
    #db-status {
        color: #ffb703;
        text-style: italic;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("HYDRA RBAC MEMORY - DYNAMIC GRAPH RETRIEVAL", id="app-title")
        
        with Horizontal(id="main-layout"):
            # 1. Left Column (Agents)
            with Vertical(id="left-col", classes="column"):
                with Vertical(id="agents-pane", classes="pane"):
                    yield Label("AGENT SELECTOR", classes="panel-title")
                    yield Label("Select agent context:")
                    with RadioSet(id="agent-selector"):
                        yield RadioButton("Support Agent", value=True, id="rb-support")
                        yield RadioButton("Sales Agent", id="rb-sales")
                        yield RadioButton("Finance Agent", id="rb-finance")
                    yield Label("Database Connection Status:", classes="label-field")
                    yield Static("Checking...", id="db-status")

            # 2. Middle Column (Query & Results)
            with Vertical(id="middle-col", classes="column"):
                with Vertical(id="query-pane", classes="pane"):
                    yield Label("QUERY CONFIGURATION", classes="panel-title")
                    yield Label("Topic / Keyword:")
                    yield Input(value="Acme", placeholder="e.g. Acme, BetaCo", id="topic-input")
                    yield Label("Temporal Checkpoint (UTC):")
                    yield Input(value="2026-08-19T00:00:00Z", placeholder="YYYY-MM-DDTHH:MM:SSZ", id="time-input")
                    yield Button("Run Security Traversal", id="run-btn")
                
                with Vertical(id="results-pane", classes="pane"):
                    yield Label("SHARED MEMORY RESULTS", classes="panel-title")
                    yield ListView(id="results-list")

            # 3. Right Column (Graph Trace)
            with Vertical(id="right-col", classes="column"):
                with Vertical(id="trace-pane", classes="pane"):
                    yield Label("PATH REACHABILITY GRAPH TRACE", classes="panel-title")
                    yield Static("Select a fact to inspect path reachability...", id="trace-content")
                    
        yield Static("PROVENANCE: No memory selected", id="provenance-footer")
        yield Footer()

    def on_mount(self) -> None:
        load_env()
        # Verify and initialize Neo4j connection
        try:
            self.graph = HydraGraph()
            self.query_one("#db-status").update("✓ Connected to Neo4j")
            self.run_traversal()
        except Exception as e:
            self.query_one("#db-status").update("✗ Disconnected (Set NEO4J_PASSWORD!)")
            self.graph = None
            self.query_one("#trace-content").update(
                "[red][bold]DATABASE CONNECTION ERROR[/bold][/red]\n\n"
                "Please configure [yellow]NEO4J_PASSWORD[/yellow] in a `.env` file or export it in your shell environment.\n\n"
                f"Error: {e}"
            )

    def get_selected_actor_name(self) -> str:
        selector = self.query_one("#agent-selector")
        if selector.pressed_button.id == "rb-support":
            return "Support"
        elif selector.pressed_button.id == "rb-sales":
            return "Sales"
        elif selector.pressed_button.id == "rb-finance":
            return "Finance"
        return "Support"

    def get_selected_actor_id(self) -> str:
        name = self.get_selected_actor_name()
        if name == "Support":
            return "actor:agent_support"
        elif name == "Sales":
            return "actor:agent_sales"
        elif name == "Finance":
            return "actor:agent_finance"
        return "actor:agent_support"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "run-btn":
            self.run_traversal()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.run_traversal()

    def run_traversal(self):
        if not self.graph:
            return

        actor_id = self.get_selected_actor_id()
        actor_name = self.get_selected_actor_name()
        topic = self.query_one("#topic-input").value.strip()
        as_of = self.query_one("#time-input").value.strip()

        try:
            # Query graph for allowed facts
            allowed_facts = self.graph.get_facts_for_actor(actor_id, topic, as_of)
            allowed_ids = {f["id"] for f in allowed_facts}

            # Query all facts matching topic to find blocked ones
            all_facts = self.graph.get_all_topic_facts(topic)

            list_view = self.query_one("#results-list")
            list_view.clear()

            allowed_items = []
            blocked_items = []

            for fact in all_facts:
                fact_id = fact["id"]
                content = fact["content"]
                is_allowed = fact_id in allowed_ids
                
                # Fetch trace to check derivation and scopes
                trace = self.graph.get_trace(actor_id, fact_id, as_of)
                is_derived = len(trace) > 1
                
                scope_name = "None"
                target_trace = next((t for t in trace if t["id"] == fact_id), None)
                if target_trace and target_trace["scopes"]:
                    scope_name = ", ".join([s["scope_name"] for s in target_trace["scopes"]])

                item = FactListItem(fact_id, content, is_allowed, scope_name, actor_name, is_derived)
                if is_allowed:
                    allowed_items.append(item)
                else:
                    blocked_items.append(item)

            # Build list with grouping headers
            list_view.append(HeaderListItem("AVAILABLE (AUTHORIZED)"))
            if allowed_items:
                for item in allowed_items:
                    list_view.append(item)
            else:
                list_view.append(ListItem(Static("  (No memories authorized for retrieval)")))

            list_view.append(HeaderListItem("BLOCKED (UNAUTHORIZED)"))
            if blocked_items:
                for item in blocked_items:
                    list_view.append(item)
            else:
                list_view.append(ListItem(Static("  (No blocked memories matching topic)")))

            self.query_one("#trace-content").update("Select a fact above to inspect graph permission path.")
            self.query_one("#provenance-footer").update("PROVENANCE: No memory selected")
        except Exception as e:
            tb = traceback.format_exc()
            self.query_one("#trace-content").update(f"[red]Error querying database:\n{e}\n\n{tb}[/red]")

    def on_list_view_selected(self, message: ListView.Selected) -> None:
        item = message.item
        if item and hasattr(item, "fact_id"):
            self.display_trace(item.fact_id)

    def display_trace(self, fact_id: str):
        if not self.graph:
            return

        actor_id = self.get_selected_actor_id()
        actor_name = self.get_selected_actor_name()
        as_of = self.query_one("#time-input").value.strip()

        try:
            trace_items = self.graph.get_trace(actor_id, fact_id, as_of)
            formatted_text = self.format_graph_path(trace_items, actor_name, fact_id)
            self.query_one("#trace-content").update(formatted_text)
            
            # Update the provenance status bar/footer
            sources = [item for item in trace_items if item["id"] != fact_id]
            if sources:
                source_ids = " + ".join([s["id"].split(":")[-1] for s in sources])
                self.query_one("#provenance-footer").update(f"PROVENANCE: {fact_id.split(':')[-1]} ← {source_ids}")
            else:
                self.query_one("#provenance-footer").update(f"PROVENANCE: {fact_id.split(':')[-1]} (Base Fact)")
        except Exception as e:
            self.query_one("#trace-content").update(f"[red]Error fetching trace:\n{e}[/red]")

    def format_graph_path(self, trace_items, actor_name, target_fact_id):
        target = next((item for item in trace_items if item["id"] == target_fact_id), None)
        if not target:
            return f"No trace details found for fact: {target_fact_id}"

        lines = []
        is_allowed = all(src["is_accessible"] for src in trace_items)
        status_icon = "[green][bold]✓ ALLOWED[/bold][/green]" if is_allowed else "[red][bold]🔒 BLOCKED[/bold][/red]"
        
        # Check if derived
        sources = [item for item in trace_items if item["id"] != target_fact_id]
        
        if not sources:
            # Base fact traversal path
            lines.append(f"{status_icon} [bold]{target['content']}[/bold]\n")
            lines.append("[underline][bold]GRAPH PATH[/bold][/underline]")
            if target["scopes"]:
                for sc in target["scopes"]:
                    lines.append(f"Agent ({actor_name})")
                    if sc["is_membership_active"]:
                        lines.append("  │")
                        lines.append("  │ MEMBER_OF")
                        lines.append("  ▼")
                        lines.append(f"Scope ({sc['scope_name']})")
                    else:
                        lines.append("  │")
                        lines.append("  ▼")
                        lines.append(f"Scope ({sc['scope_name']}) [red][bold]🔒 X (NO VALID PATH)[/bold][/red]")
                        
                    if sc["is_visibility_active"]:
                        lines.append("  ▲")
                        lines.append("  │ VISIBLE_TO")
                        lines.append("  │")
                    else:
                        lines.append("  X [red]🔒 (INACTIVE VISIBILITY)[/red]")
                        lines.append("  │")
                    lines.append(f"Fact ({target['id']})")
            else:
                lines.append("  [red]🔒 Fact has no explicit scope visibility (BLOCKED)[/red]")
            
            lines.append(f"\n[bold]FINAL DECISION[/bold]\n{status_icon}")
        else:
            # Derived fact (Priority 4 visual trace)
            lines.append(f"{status_icon} [bold]{target['content']}[/bold]\n")
            lines.append("[underline][bold]PROVENANCE[/bold][/underline]")
            
            blocked_count = 0
            for i, src in enumerate(sources):
                prefix = "├── " if i < len(sources) - 1 else "└── "
                src_icon = "[green]✓[/green]" if src["is_accessible"] else "[red]✗[/red]"
                
                scope_desc = ""
                if src["scopes"]:
                    scope_desc = f" [{src['scopes'][0]['scope_name']}]"
                    
                lines.append(f"{prefix}{src_icon} {src['content']}{scope_desc}")
                if not src["is_accessible"]:
                    blocked_count += 1
                    
            lines.append("\n[underline][bold]FINAL DECISION[/bold][/underline]")
            lines.append(status_icon)
            
            if is_allowed:
                lines.append("\n[bold]Reason:[/bold] Agent has access to all source facts.")
            else:
                lines.append(f"\n[bold]Reason:[/bold]\nAgent lacks access to {blocked_count} source fact{'s' if blocked_count > 1 else ''}.")
                
        return "\n".join(lines)

if __name__ == "__main__":
    app = HydraRbacTui()
    app.run()
