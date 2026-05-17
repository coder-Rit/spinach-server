vector_context = """
Classify the user message based on whether it requires:
- RAG (knowledge retrieval, semantic search, documentation lookup, explanations, informational queries)
- TOOLS (CRUD operations, workflows, execution, API calls, automation, status checks, external/system actions)

Rules:
- Return ONLY valid JSON.
- No markdown.
- No explanations.
- No extra text.
- Output format:
{
  "needs_rag": true,
  "needs_tools": false
}

Classification rules:
- If the request is informational only → needs_rag=true, needs_tools=false
- If the request performs actions only → needs_rag=false, needs_tools=true
- If both are required → both true
- If unclear, prefer:
  {
    "needs_rag": true,
    "needs_tools": false
  }
---
"""