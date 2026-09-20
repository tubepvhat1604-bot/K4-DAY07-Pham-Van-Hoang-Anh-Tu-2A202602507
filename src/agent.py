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
        results = self.store.search(question, top_k=top_k)

        if not results:
            # Empty store / no matches: never call the LLM with no
            # context — just say so, instead of crashing or letting the
            # model hallucinate an answer with nothing to ground it in.
            return "Không tìm thấy thông tin liên quan trong cơ sở tri thức để trả lời câu hỏi này."

        # Number each chunk and keep its source doc_id so the model's
        # citation ([1], [2], ...) can be traced back to an exact chunk
        # and file — this is the Source Traceability criterion in
        # docs/EVALUATION.md, not an optional nicety for this corpus.
        context_lines = []
        for i, result in enumerate(results, start=1):
            source = result["metadata"].get("doc_id", result.get("id", "unknown"))
            context_lines.append(f"[{i}] (nguồn: {source}) {result['content']}")
        context = "\n".join(context_lines)

        prompt = (
            "Bạn là trợ lý trả lời câu hỏi CHỈ dựa trên ngữ cảnh được cung cấp dưới đây. "
            "Nếu ngữ cảnh không chứa đủ thông tin để trả lời, hãy nói rõ là không tìm thấy "
            "thông tin thay vì suy đoán. Khi trả lời, trích dẫn số thứ tự đoạn ngữ cảnh bạn "
            "đã dùng, ví dụ [1], [2].\n\n"
            f"Ngữ cảnh:\n{context}\n\n"
            f"Câu hỏi: {question}\n"
            "Trả lời:"
        )
        return self.llm_fn(prompt)
