from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        if self.store.get_collection_size() == 0:
            return "Knowledge base is empty. No relevant information found."

        results = self.store.search(question, top_k=top_k)
        if not results:
            return "No relevant documents found in knowledge base."

        context_blocks = []
        for i, r in enumerate(results, start=1):
            source = (
                r.get("metadata", {}).get("source")
                or r.get("metadata", {}).get("doc_id")
                or r.get("id", "unknown")
            )
            context_blocks.append(f"[{i}] (Source: {source})\n{r['content']}")

        context_str = "\n\n".join(context_blocks)
        prompt = (
            "You are a helpful and factual assistant. Answer the question based ONLY on the provided context below.\n"
            "If the answer cannot be deduced from the context, state clearly that you do not know.\n"
            "Cite the source number (e.g., [1], [2]) when using information from a chunk.\n\n"
            f"Context:\n{context_str}\n\n"
            f"Question: {question}\n\n"
            "Answer:"
        )

        return self.llm_fn(prompt)
