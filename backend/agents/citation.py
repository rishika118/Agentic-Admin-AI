"""
agents/citation.py — Citation Format Node
==========================================

What does the Citation/Format Node do?
    This is the final node in the graph. It takes everything computed by
    the RAG node (or the Planner's decision) and produces a single,
    clean, user-facing response.

    It handles all three cases:
        1. "answer"       → Format the LLM answer + numbered source list
        2. "clarify"      → Format a polite clarification request
        3. "out_of_scope" → Format a polite "I can't help with that" message

Why format in a separate node?
    The RAG node is focused on retrieval accuracy. The format node is
    focused on communication quality. Keeping them separate means we
    can change the presentation style (e.g., add Markdown, change tone)
    without touching the retrieval logic.

Output format (for "answer"):
    ┌──────────────────────────────────────────┐
    │  [Answer text from LLM]                  │
    │                                          │
    │  Sources:                                │
    │  [1] "Document Title" — Page 3           │
    │  [2] "Another Document" — Page 7         │
    └──────────────────────────────────────────┘

How it connects:
    - Reads:  state["intent"], state["rag_answer"], state["citations"],
              state["planner_notes"], state["error"]
    - Writes: state["final_answer"]
    - Always the last node before END
"""

from agents.state import AgentState


# Messages for special intents
_CLARIFY_TEMPLATE = (
    "I need a bit more detail to help you effectively.\n\n"
    "{notes}\n\n"
    "Could you please rephrase your question with more context? "
    "For example, you could ask about hostel policies, fee deadlines, "
    "leave procedures, or specific circulars."
)

_OUT_OF_SCOPE_TEMPLATE = (
    "I'm specialized for NIT Calicut administrative queries only.\n\n"
    "I can help with topics like:\n"
    "• Hostel rules and circulars\n"
    "• Fee payment and scholarships\n"
    "• Academic regulations\n"
    "• Leave procedures\n"
    "• Office orders and notifications\n\n"
    "Please ask me an administrative question and I'll do my best to help!"
)

_ERROR_TEMPLATE = (
    "I encountered an error while processing your query.\n\n"
    "Error: {error}\n\n"
    "Please try again. If the problem persists, ensure that:\n"
    "• Qdrant is running (port 6333)\n"
    "• Ollama is running with mistral:latest\n"
    "• Documents have been ingested"
)


def format_node(state: AgentState) -> AgentState:
    """
    LangGraph node: Citation Formatter.

    Produces the final user-facing response string in state["final_answer"].
    This is always the last node before END.

    Args:
        state: Current AgentState (populated by previous nodes).

    Returns:
        Updated AgentState with "final_answer" set.
    """
    intent        = state.get("intent", "answer")
    rag_answer    = state.get("rag_answer")
    citations     = state.get("citations") or []
    planner_notes = state.get("planner_notes", "")
    error         = state.get("error")

    print(f"\n[FormatNode] Formatting response for intent='{intent}'")

    # ------------------------------------------------------------------
    # Error case
    # ------------------------------------------------------------------
    if error and not rag_answer:
        final = _ERROR_TEMPLATE.format(error=error)
        print("[FormatNode] Error response generated.")
        return {**state, "final_answer": final}

    # ------------------------------------------------------------------
    # Clarification request
    # ------------------------------------------------------------------
    if intent == "clarify":
        final = _CLARIFY_TEMPLATE.format(notes=planner_notes)
        print("[FormatNode] Clarification response generated.")
        return {**state, "final_answer": final}

    # ------------------------------------------------------------------
    # Out-of-scope
    # ------------------------------------------------------------------
    if intent == "out_of_scope":
        final = _OUT_OF_SCOPE_TEMPLATE
        print("[FormatNode] Out-of-scope response generated.")
        return {**state, "final_answer": final}

    # ------------------------------------------------------------------
    # Answer — main case
    # ------------------------------------------------------------------
    if not rag_answer:
        final = (
            "I could not find relevant information in the available documents.\n\n"
            "Please ensure that relevant PDF documents have been uploaded and ingested."
        )
        print("[FormatNode] No answer found response generated.")
        return {**state, "final_answer": final}

    # Build the answer + numbered source list
    parts = [rag_answer.strip()]

    if citations:
        parts.append("\n\n**Sources:**")
        seen = set()  # Deduplicate by document+page
        counter = 1
        for c in citations:
            key = (c["document_title"], c["page_no"])
            if key not in seen:
                seen.add(key)
                score_pct = int(c["score"] * 100)
                parts.append(
                    f"[{counter}] \"{c['document_title']}\" — "
                    f"Page {c['page_no']} ({score_pct}% match)"
                )
                counter += 1

    final = "\n".join(parts)
    print(f"[FormatNode] Answer formatted ({len(final)} chars, "
          f"{len(citations)} citations).")
    return {**state, "final_answer": final}
