from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Input, Button, Label, RadioSet, RadioButton, ListView, ListItem
from graph import HydraGraph
import os
import traceback

class FactListItem(ListItem):
    def __init__(self, fact_id: str, content: str, is_allowed: bool, scope_name: str):
        super().__init__()
        self.fact_id = fact_id
        self.content = content
        self.is_allowed = is_allowed
        self.scope_name = scope_name

    def compose(self) -> ComposeResult:
        icon = "✓" if self.is_allowed else "🔒"
        style_class = "allowed" if self.is_allowed else "blocked"
        yield Label(f"{icon} {self.content} ({self.scope_name})", classes=style_class)

class HydraRbacTui(App):
    CSS = """
    Screen {
        background: #1e1e1e;
        color: #ffffff;
    }
    
    #app-title {
        text-align: center;
        background: #005f73;
        color: #ffffff;
        padding: 1;
        text-style: bold;
        height: 3;
    }
    
    .pane {
        border: tall #005f73;
        height: 1fr;
        padding: 1;
        margin: 1;
        background: #2a2a2a;
    }
    
    #agents-pane {
        width: 25%;
    }
    
    #query-pane {
        width: 45%;
    }
    
    #trace-pane {
        width: 30%;
    }
    
    .panel-title {
        text-style: bold;
        color: #94d2bd;
        margin-bottom: 1;
    }
    
    .label-field {
        margin-top: 1;
        text-style: bold;
    }
    
    #run-btn {
        margin-top: 2;
        margin-bottom: 2;
        width: 100%;
        background: #0a9396;
        color: white;
    }
    
    #run-btn:hover {
        background: #94d2bd;
        color: black;
    }
    
    #results-list {
        background: #1e1e1e;
        border: solid #005f73;
        height: 1fr;
    }
    
    .allowed {
        color: #52b788;
    }
    
    .blocked {
        color: #e63946;
    }
    
    #trace-content {
        background: #1e1e1e;
        padding: 1;
        border: solid #005f73;
        height: 1fr;
    }
    
    #db-status {
        color: #ffb703;
        text-style: italic;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("HYDRA RBAC MEMORY - GRAPH REACHABILITY TRAVERSAL", id="app-title")
        
        with Horizontal():
            # 1. Agents Pane
            with Vertical(id="agents-pane", classes="pane"):
                yield Label("AGENTS", classes="panel-title")
                yield Label("Select active agent actor:")
                with RadioSet(id="agent-selector"):
                    yield RadioButton("Support Agent", value=True, id="rb-support")
                    yield RadioButton("Sales Agent", id="rb-sales")
                    yield RadioButton("Finance Agent", id="rb-finance")
                yield Label("Database Status:", classes="label-field")
                yield Static("Connecting...", id="db-status")

            # 2. Query & Results Pane
            with Vertical(id="query-pane", classes="pane"):
                yield Label("QUERY & AUTHORIZATION TRAVERSAL", classes="panel-title")
                
                yield Label("Topic / Search Keyword:", classes="label-field")
                yield Input(value="Acme", placeholder="e.g. Acme, BetaCo", id="topic-input")
                
                yield Label("As of Date/Time (UTC ISO 8601):", classes="label-field")
                yield Input(value="2026-08-19T00:00:00Z", placeholder="YYYY-MM-DDTHH:MM:SSZ", id="time-input")
                
                yield Button("Run Graph Traversal Query", id="run-btn")
                
                yield Label("Traversal Results:", classes="label-field")
                yield ListView(id="results-list")

            # 3. Trace Pane
            with Vertical(id="trace-pane", classes="pane"):
                yield Label("GRAPH AUTHORIZATION TRACE", classes="panel-title")
                yield Static("Select a fact from the results to view authorization trace path.", id="trace-content")
                
        yield Footer()

    def on_mount(self) -> None:
        # Verify and initialize Neo4j connection
        try:
            self.graph = HydraGraph()
            self.query_db_status()
        except Exception as e:
            self.query_one("#db-status").update("✗ Disconnected (Neo4j not running)")
            self.graph = None

    def query_db_status(self):
        if self.graph:
            self.query_one("#db-status").update("✓ Connected to Neo4j")
        else:
            self.query_one("#db-status").update("✗ Disconnected (Neo4j not running)")

    def get_selected_actor_id(self) -> str:
        selector = self.query_one("#agent-selector")
        if selector.pressed_button.id == "rb-support":
            return "actor:agent_support"
        elif selector.pressed_button.id == "rb-sales":
            return "actor:agent_sales"
        elif selector.pressed_button.id == "rb-finance":
            return "actor:agent_finance"
        return "actor:agent_support"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "run-btn":
            self.run_traversal()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.run_traversal()

    def run_traversal(self):
        if not self.graph:
            self.query_one("#trace-content").update("[red]Error: Database connection is not available.[/red]")
            return

        actor_id = self.get_selected_actor_id()
        topic = self.query_one("#topic-input").value.strip()
        as_of = self.query_one("#time-input").value.strip()

        try:
            # Query graph for allowed facts
            allowed_facts = self.graph.get_facts_for_actor(actor_id, topic, as_of)
            allowed_ids = {f["id"] for f in allowed_facts}

            # Query all facts matching topic to find blocked ones
            all_facts = self.graph.get_all_topic_facts(topic)

            # Build list items
            list_view = self.query_one("#results-list")
            list_view.clear()

            # Render results
            for fact in all_facts:
                fact_id = fact["id"]
                content = fact["content"]
                
                is_allowed = fact_id in allowed_ids
                
                # Retrieve the scope name if allowed, otherwise find it
                scope_name = "Restricted"
                if is_allowed:
                    # Find matching item in allowed_facts to get its scope name
                    matching = next((f for f in allowed_facts if f["id"] == fact_id), None)
                    if matching:
                        scope_name = matching["scope_name"]
                else:
                    # Try to fetch scope name manually
                    trace = self.graph.get_trace(actor_id, fact_id, as_of)
                    target_trace = next((t for t in trace if t["id"] == fact_id), None)
                    if target_trace and target_trace["scopes"]:
                        scope_name = ", ".join([s["scope_name"] for s in target_trace["scopes"]])

                list_view.append(FactListItem(fact_id, content, is_allowed, scope_name))

            self.query_one("#trace-content").update("Click a result above to inspect graph permission path.")
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
        as_of = self.query_one("#time-input").value.strip()

        try:
            trace_items = self.graph.get_trace(actor_id, fact_id, as_of)
            formatted_text = self.format_trace_tree(trace_items, fact_id)
            self.query_one("#trace-content").update(formatted_text)
        except Exception as e:
            self.query_one("#trace-content").update(f"[red]Error fetching trace:\n{e}[/red]")

    def format_trace_tree(self, trace_items, target_fact_id):
        # Find the target fact first
        target = next((item for item in trace_items if item["id"] == target_fact_id), None)
        if not target:
            return f"No trace details found for fact: {target_fact_id}"

        lines = []
        lines.append(f"[bold]Fact ID:[/bold] [yellow]{target['id']}[/yellow]")
        lines.append(f"[bold]Content:[/bold] {target['content']}")
        
        status_icon = "[bold][green]✓ ALLOWED[/green][/bold]" if target["is_accessible"] else "[bold][red]🔒 BLOCKED[/red][/bold]"
        lines.append(f"[bold]Status Check:[/bold] {status_icon}")
        
        # Scopes of the target fact itself
        if target["scopes"]:
            lines.append("\n[underline]Target Scope Visibility Check:[/underline]")
            for sc in target["scopes"]:
                act_m = "[green]✓ Active[/green]" if sc["is_membership_active"] else "[red]✗ Inactive/None[/red]"
                act_v = "[green]✓ Active[/green]" if sc["is_visibility_active"] else "[red]✗ Inactive/None[/red]"
                lines.append(f"  - [cyan]{sc['scope_name']}[/cyan] Scope:")
                lines.append(f"    * Fact visibility: {act_v} (since: {sc['visible_since']} until: {sc['visible_until'] or 'infinity'})")
                lines.append(f"    * Agent membership: {act_m} (since: {sc['membership_since'] or 'N/A'} until: {sc['membership_until'] or 'infinity'})")
                
        # List sources/provenance
        sources = [item for item in trace_items if item["id"] != target_fact_id]
        if sources:
            lines.append("\n[bold][underline]Derivation Provenance Trace:[/underline][/bold]")
            lines.append("This is a [yellow]derived fact[/yellow]. Access requires authorization for ALL source facts:")
            for i, src in enumerate(sources):
                prefix = "├── " if i < len(sources) - 1 else "└── "
                src_status = "[green]✓ ALLOWED[/green]" if src["is_accessible"] else "[red]🔒 BLOCKED[/red]"
                lines.append(f"{prefix}{src_status} [bold]{src['id']}[/bold]")
                
                # Details of this source
                indent = "│   " if i < len(sources) - 1 else "    "
                lines.append(f"{indent}Content: [italic]\"{src['content']}\"[/italic]")
                
                if src["scopes"]:
                    for sc in src["scopes"]:
                        act_m = "[green]Active[/green]" if sc["is_membership_active"] else "[red]Inactive/None[/red]"
                        lines.append(f"{indent}Required Scope: [cyan]{sc['scope_name']}[/cyan] (Agent Membership: {act_m})")
                else:
                    lines.append(f"{indent}Required Scope: None (Inherited/Public)")
                    
        return "\n".join(lines)

if __name__ == "__main__":
    app = HydraRbacTui()
    app.run()
