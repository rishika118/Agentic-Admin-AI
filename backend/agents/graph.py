"""
agents/graph.py — LangGraph Agent Orchestration
==================================================

What is this file?
    This is where LangGraph is used to wire all agents into a single
    coherent workflow. The graph defines:
        - NODES  : Which functions to run (planner, rag, format)
        - EDGES  : How to move between nodes
        - ROUTING: Conditional logic (where to go based on planner's intent)

What is a LangGraph StateGraph?
    A StateGraph is a directed graph where:
    - Each node is a Python function that reads/updates shared state
    - Edges define what runs after what
    - Conditional edges allow branching (the "agentic" behavior)

    Compared to a simple pipeline (A → B → C), LangGraph lets you build
    workflows that branch, loop, or self-correct based on intermediate results.

Our Graph Structure:
    ┌──────────┐
    │  START   │
    └────┬─────┘
         │
    ┌────▼─────────┐
    │  planner     │  ← Classifies intent
    └────┬─────────┘
         │
    ┌────▼──────────────────────────────────┐
    │  route_after_planner()                │ ← Conditional edge
    │  "answer"       → rag_node            │
    │  "clarify"      → format_node         │
    │  "out_of_scope" → format_node         │
    └────────────────────────────────────────┘
         │                    │
    ┌────▼─────────┐     ┌────▼──────────┐
    │  rag_node    │     │  format_node  │
    └────┬─────────┘     └──────┬────────┘
         │                      │
    ┌────▼──────────┐           │
    │  format_node  │           │
    └────┬──────────┘           │
         └──────────────────────┘
                  │
             ┌────▼─────┐
             │   END    │
             └──────────┘

Public API:
    from agents.graph import run_agent

    result = run_agent("What is the hostel visitor policy?")
    print(result["final_answer"])
    print(result["citations"])
"""

from langgraph.graph import StateGraph, END

from agents.state   import AgentState
from agents.planner import planner_node
from agents.task    import rag_node
from agents.citation import format_node


# ---------------------------------------------------------------------------
# Conditional Routing Function
# ---------------------------------------------------------------------------

def route_after_planner(state: AgentState) -> str:
    """
    Determines which node to visit after the Planner.

    This is a LangGraph "conditional edge" function. It reads the intent
    from the state and returns the name of the next node.

    Returns:
        "rag"    → run the RAG task (answerable query)
        "format" → skip RAG and go straight to formatting
                   (clarification or out-of-scope)
    """
    intent = state.get("intent", "answer")
    print(f"[Router] intent='{intent}' -> routing to: "
          f"{'rag' if intent == 'answer' else 'format'}")

    if intent == "answer":
        return "rag"
    else:
        # "clarify" or "out_of_scope" → skip RAG entirely
        return "format"


# ---------------------------------------------------------------------------
# Build the Graph
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    """
    Constructs and compiles the LangGraph StateGraph.

    This function:
    1. Creates a StateGraph with AgentState as its schema
    2. Adds all three nodes
    3. Sets the entry point
    4. Adds edges (including the conditional routing edge)
    5. Compiles and returns the graph

    Returns:
        A compiled LangGraph app (callable like a function).
    """
    # Create the graph with our state schema
    graph = StateGraph(AgentState)

    # Add nodes — each is a Python function that updates state
    graph.add_node("planner", planner_node)
    graph.add_node("rag",     rag_node)
    graph.add_node("format",  format_node)

    # Set entry point — the first node to run
    graph.set_entry_point("planner")

    # Add conditional edge from planner
    # route_after_planner() decides which node to go to based on intent
    graph.add_conditional_edges(
        source  = "planner",
        path    = route_after_planner,
        path_map = {
            "rag":    "rag",
            "format": "format",
        },
    )

    # After RAG → always go to format
    graph.add_edge("rag", "format")

    # After format → END
    graph.add_edge("format", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Compile the graph once at import time (not on every call)
_app = build_graph()


def run_agent(query: str) -> AgentState:
    """
    Run the full agent pipeline for a user query.

    This is the single entry point used by the API layer and tests.
    Internally it runs the LangGraph StateGraph from START to END.

    Args:
        query: The user's question in plain English.

    Returns:
        The final AgentState with all fields populated:
            - final_answer : The user-facing response string
            - citations    : List of source chunks used
            - intent       : What the planner decided
            - planner_notes: Why the planner made that decision

    Example:
        result = run_agent("What are the hostel visitor timings?")
        print(result["final_answer"])
        # → "Visitors are permitted between 10:00 AM and 6:00 PM per..."
        for c in result["citations"]:
            print(c["document_title"], c["page_no"])
    """
    print(f"\n{'='*60}")
    print(f"[Agent] Starting pipeline for query: '{query[:80]}'")
    print(f"{'='*60}")

    # Initialize state with just the query
    initial_state: AgentState = {
        "query":         query,
        "intent":        None,
        "planner_notes": None,
        "rag_answer":    None,
        "citations":     None,
        "final_answer":  None,
        "error":         None,
    }

    # Run the graph synchronously
    result = _app.invoke(initial_state)

    print(f"\n[Agent] Pipeline complete.")
    print(f"  intent       : {result.get('intent')}")
    print(f"  final_answer : {str(result.get('final_answer', ''))[:100]}...")
    print(f"  citations    : {len(result.get('citations') or [])} sources")
    print(f"{'='*60}\n")

    return result
