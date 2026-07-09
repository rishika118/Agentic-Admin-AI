"""
agents/__init__.py
Exports the main agent entry point for use by the API layer.

Usage:
    from agents.graph import run_agent
    result = run_agent("What is the hostel fee structure?")
    print(result["final_answer"])
"""
from agents.graph import run_agent
from agents.state import AgentState

__all__ = ["run_agent", "AgentState"]
