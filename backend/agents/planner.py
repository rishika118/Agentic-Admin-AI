"""
agents/planner.py — Planner Node
==================================

What does the Planner do?
    The Planner is the "brain" of the agent — it reads the user's query and
    decides what to do next. This is what makes the system "agentic":
    instead of blindly running RAG on every input, we reason about the input
    first.

    The Planner classifies queries into one of three intents:

        "answer"       → Query is a clear administrative question.
                         Action: proceed to RAGNode.

        "clarify"      → Query is too short, vague, or ambiguous.
                         Action: skip RAG and ask the user for more detail.
                         Example: "hostel" → "Could you clarify what you'd
                                              like to know about hostels?"

        "out_of_scope" → Query has nothing to do with NIT Calicut administration.
                         Action: politely decline and redirect.
                         Example: "Write me a poem" → "I can only help with
                                                       administrative queries."

Implementation approach (two-layer):
    Layer 1 — Fast rule-based checks (no LLM needed):
        - Too short (< 5 words) → clarify
        - Contains explicit off-topic keywords → out_of_scope

    Layer 2 — LLM-based classification (optional, graceful fallback):
        - Sends query to Mistral with a classification prompt
        - If Mistral is unavailable → defaults to "answer" (optimistic)

Why rule-based first?
    Calling an LLM for every query adds latency (1-3 seconds each time).
    Simple rules handle 80% of obvious cases instantly. LLM is only used
    for the ambiguous middle ground.

How it connects:
    - Reads: state["query"]
    - Writes: state["intent"], state["planner_notes"]
    - Called by graph.py as the first node in the graph
"""

from agents.state import AgentState

# ---------------------------------------------------------------------------
# Off-topic keyword lists (fast rule-based pre-check)
# ---------------------------------------------------------------------------

_MIN_WORDS = 3   # Queries shorter than this → ask for clarification

_OFF_TOPIC_KEYWORDS = [
    "poem", "song", "joke", "recipe", "weather", "cricket", "movie",
    "game", "stock", "price", "bitcoin", "hello", "hi there", "who are you",
    "what is your name", "translate", "write code", "write a",
]

_ADMIN_KEYWORDS = [
    "hostel", "circular", "notification", "order", "fee", "admission",
    "regulation", "policy", "rule", "guideline", "leave", "scholarship",
    "exam", "result", "course", "department", "faculty", "student",
    "nit", "nitc", "calicut", "registrar", "dean", "academic",
    "attendance", "certificate", "transcript", "office", "procedure",
    "form", "deadline", "semester", "holiday", "schedule", "timetable",
]


def _rule_based_classify(query: str) -> tuple[str, str]:
    """
    Fast rule-based classification — no LLM needed.

    Returns:
        (intent, notes) tuple
        intent: "answer" | "clarify" | "out_of_scope" | "uncertain"
                "uncertain" means we should try the LLM
    """
    q = query.strip().lower()
    words = q.split()

    # Too short → ask for clarification
    if len(words) < _MIN_WORDS:
        return ("clarify",
                f"Query is too short ({len(words)} word(s)). "
                "Please provide more context.")

    # Explicit off-topic keywords
    for kw in _OFF_TOPIC_KEYWORDS:
        if kw in q:
            return ("out_of_scope",
                    f"Query appears to be off-topic (matched: '{kw}'). "
                    "I only handle NIT Calicut administrative questions.")

    # Contains known admin keywords → confident it's answerable
    for kw in _ADMIN_KEYWORDS:
        if kw in q:
            return ("answer",
                    f"Query contains administrative keyword '{kw}'. "
                    "Proceeding with document retrieval.")

    # Ambiguous — needs LLM judgment
    return ("uncertain", "Query is ambiguous. Checking with LLM.")


def planner_node(state: AgentState) -> AgentState:
    """
    LangGraph node: Planner.

    Reads `state["query"]` and sets `state["intent"]` + `state["planner_notes"]`.

    Logic flow:
        1. Rule-based check (fast, no LLM)
        2. If uncertain → LLM classification (Mistral via Ollama)
        3. If LLM unavailable → optimistic fallback → "answer"

    Args:
        state: Current AgentState (must have "query" set).

    Returns:
        Updated AgentState with "intent" and "planner_notes" set.
    """
    query = state.get("query", "").strip()
    print(f"\n[Planner] Classifying query: '{query[:80]}...' " if len(query) > 80
          else f"\n[Planner] Classifying query: '{query}'")

    if not query:
        print("[Planner] Empty query -> clarify")
        return {
            **state,
            "intent":        "clarify",
            "planner_notes": "No query provided. Please ask a question.",
        }

    # ------------------------------------------------------------------
    # Layer 1: Fast rule-based classification
    # ------------------------------------------------------------------
    intent, notes = _rule_based_classify(query)

    if intent != "uncertain":
        print(f"[Planner] Rule-based -> intent='{intent}' | {notes}")
        return {**state, "intent": intent, "planner_notes": notes}

    # ------------------------------------------------------------------
    # Layer 2: LLM classification for ambiguous queries
    # ------------------------------------------------------------------
    print("[Planner] Ambiguous query. Trying LLM classification...")
    try:
        from langchain_ollama import OllamaLLM
        from config import settings

        llm = OllamaLLM(
            model    = settings.OLLAMA_MODEL,
            base_url = settings.OLLAMA_BASE_URL,
        )

        classification_prompt = f"""You are a query classifier for NIT Calicut's administrative AI assistant.
Classify the following user query into exactly one of these categories:
- "answer"       : A clear question about NIT Calicut administration (hostel, fees, rules, policies, circulars, etc.)
- "clarify"      : The question is too vague or ambiguous to answer well
- "out_of_scope" : Completely unrelated to NIT Calicut administration

Respond with ONLY the category word, nothing else.

Query: {query}
Category:"""

        result = llm.invoke(classification_prompt).strip().lower()

        # Parse the LLM's response
        if "out_of_scope" in result or "out of scope" in result:
            intent = "out_of_scope"
            notes  = f"LLM classified as out_of_scope: '{result}'"
        elif "clarify" in result:
            intent = "clarify"
            notes  = f"LLM classified as clarify: '{result}'"
        else:
            # Default to "answer" for any other response (optimistic)
            intent = "answer"
            notes  = f"LLM classified as answer: '{result}'"

    except Exception as e:
        # LLM unavailable → optimistic fallback
        print(f"[Planner] LLM unavailable ({e}). Defaulting to 'answer'.")
        intent = "answer"
        notes  = f"LLM unavailable (fallback). Proceeding with RAG."

    print(f"[Planner] LLM -> intent='{intent}' | {notes}")
    return {**state, "intent": intent, "planner_notes": notes}
