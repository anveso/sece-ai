"""
Agent tools. Built as a factory (`build_tools`) rather than module-level
singletons because `search_documents` needs to be scoped to the current
request's DB session and user - each request builds its own tool set.
"""
from uuid import UUID

import httpx
from langchain_core.tools import tool
from sqlalchemy.orm import Session

from ..config import settings
from ..rag.retriever import retrieve_relevant_chunks


def build_tools(db: Session, user_id: UUID):
    @tool
    def search_documents(query: str) -> str:
        """Search institutional documents for passages relevant to the
        query: both the current user's own uploads AND the shared
        institutional knowledge base (official documents added by a
        verified admin - college policies, syllabi, circulars, content from
        sece.ac.in). Each result is labeled "Official/shared source" or
        "User's own upload" so you know how authoritative it is. Returns the
        most relevant excerpts with their source filenames, or a message
        saying nothing was found."""
        chunks = retrieve_relevant_chunks(db, user_id, query, top_k=5)
        if not chunks:
            return "No relevant passages found in the user's uploaded documents."

        def _label(c):
            return "Official/shared source" if c["is_shared"] else "User's own upload"

        formatted = "\n\n".join(
            f"[{_label(c)}: {c['filename']}]\n{c['content']}" for c in chunks
        )
        return formatted

    tools = [search_documents]

    if settings.tavily_api_key:

        @tool
        def web_search(query: str) -> str:
            """Search the public web for current information not likely to
            be in the institution's own documents (news, general facts,
            things outside the college's private knowledge base)."""
            try:
                response = httpx.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": settings.tavily_api_key,
                        "query": query,
                        "max_results": 5,
                    },
                    timeout=15,
                )
                response.raise_for_status()
                data = response.json()
                results = data.get("results", [])
                if not results:
                    return "No web results found."
                return "\n\n".join(
                    f"[{r.get('title')}]({r.get('url')})\n{r.get('content', '')}"
                    for r in results
                )
            except Exception as exc:  # noqa: BLE001
                return f"Web search failed: {exc}"

        tools.append(web_search)

    return tools
