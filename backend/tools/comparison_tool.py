"""
tools/comparison_tool.py — Policy Comparison Tool (Stub)
=========================================================
Phase: Implemented in Phase 5

What it will do:
- Accept two policy names or topics.
- Retrieve the relevant chunks for each using the Retrieval Agent.
- Ask Mistral to compare both policies side-by-side.
- Return a structured comparison with citations for both sources.

Why it exists:
- Administrative queries often ask "how does policy A differ from policy B?".
  This tool answers that systematically using retrieved evidence.

How it connects:
- Called by agents/task.py.
- Uses agents/retrieval.py twice (once per policy).
- Uses agents/citation.py to attach sources.
"""

# TODO: Implement in Phase 5
