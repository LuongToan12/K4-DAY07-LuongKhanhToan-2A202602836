"""
Script danh gia toan dien Retrieval & Agent tren tap gold_queries.json:
- Recall@1
- Recall@5
- MRR (Mean Reciprocal Rank)
- nDCG@5 (Normalized Discounted Cumulative Gain)
- Full Evidence@5 (Kha nang bao trum 100% bang chung trong top-5)
- Faithfulness / Agent Accuracy (Kiem tra tu khoa chuan theo answer_criteria)
- Audience Match Rate (Ti le chunk thuoc doi tuong hop le - student)
"""
import json
import math
import sys
from pathlib import Path

# Đảm bảo import được src từ repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from src.agent import KnowledgeBaseAgent
from src.chunking import FixedSizeChunker, RecursiveChunker, SentenceChunker
from src.embeddings import MockEmbedder
from src.models import Document
from src.store import EmbeddingStore

CORPUS_DIR = Path("data/university")
GOLD_QUERIES_FILE = Path("gold_queries.json")


def load_raw_documents():
    docs = []
    for p in sorted(CORPUS_DIR.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        meta = {}
        content = text
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                content = parts[2].strip()
                for line in frontmatter.strip().split("\n"):
                    if ":" in line:
                        k, v = line.split(":", 1)
                        meta[k.strip()] = v.strip().strip('"').strip("'")
        meta["doc_id"] = p.stem
        docs.append((p.stem, content, meta))
    return docs


def _mock_embed(text: str) -> list[float]:
    embedder = MockEmbedder(dim=64)
    return embedder(text)


class SemanticLexicalEmbedder:
    """Feature-hashed Lexical/Semantic Embedder mô phỏng word-level semantic matching."""
    def __init__(self, dim: int = 512):
        self.dim = dim

    def __call__(self, text: str) -> list[float]:
        import re
        tokens = re.findall(r"\w+", text.lower())
        vec = [0.0] * self.dim
        for t in tokens:
            idx = abs(hash(t)) % self.dim
            vec[idx] += 1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


def build_store(strategy_name: str, embedder_type: str = "mock"):
    if embedder_type == "mock":
        fn = _mock_embed
    else:
        fn = SemanticLexicalEmbedder(dim=512)

    store = EmbeddingStore(collection_name=f"eval_{strategy_name}_{embedder_type}", embedding_fn=fn)
    raw_docs = load_raw_documents()

    for doc_id, text, meta in raw_docs:
        if strategy_name == "fixed_size":
            chunker = FixedSizeChunker(chunk_size=400, overlap=50)
            chunks = chunker.chunk(text)
        elif strategy_name == "by_sentences":
            chunker = SentenceChunker(max_sentences_per_chunk=3)
            chunks = chunker.chunk(text)
        elif strategy_name == "recursive":
            chunker = RecursiveChunker(chunk_size=400)
            chunks = chunker.chunk(text)
        elif strategy_name == "heading_recursive":
            sections = text.split("\n## ")
            chunks = []
            rec = RecursiveChunker(chunk_size=400)
            for i, sec in enumerate(sections):
                sec_text = sec if i == 0 else "## " + sec
                chunks.extend(rec.chunk(sec_text))
        else:
            raise ValueError(f"Unknown strategy: {strategy_name}")

        for idx, c in enumerate(chunks):
            chunk_doc = Document(
                id=f"{doc_id}#{idx}",
                content=c,
                metadata={
                    **meta,
                    "chunk_index": idx,
                    "doc_id": doc_id,
                },
            )
            store.add_documents([chunk_doc])
    return store


def calculate_metrics(store: EmbeddingStore, gold_queries: list, top_k: int = 5, use_filter: bool = False):
    recalls_at_1 = []
    recalls_at_5 = []
    reciprocal_ranks = []
    ndcgs_at_5 = []
    full_evidence_at_5 = []
    faithfulness_scores = []
    audience_match_rates = []

    def extractive_rag_llm(prompt: str) -> str:
        # Mô phỏng LLM tổng hợp câu trả lời dựa trên context được retrieve
        if "Context information:\n" in prompt:
            context = prompt.split("Context information:\n", 1)[1].split("\n\nPlease answer")[0]
            return f"Dựa trên tài liệu nhà trường:\n{context}"
        return prompt

    agent = KnowledgeBaseAgent(store, llm_fn=extractive_rag_llm)

    query_details = []

    for q in gold_queries:
        query_text = q["query"]
        expected_docs = set(q["source_doc_ids"])
        expected_aud = q.get("expected_audience", "student")
        evidences = q.get("evidence", [])
        answer_criteria = q.get("answer_criteria", [])

        # 1. Retrieval
        if use_filter:
            results = store.search_with_filter(
                query=query_text,
                metadata_filter={"audience": expected_aud},
                top_k=top_k,
            )
        else:
            results = store.search(query=query_text, top_k=top_k)

        # Truncate to top_k
        results = results[:top_k]

        retrieved_docs = [r["metadata"].get("doc_id") for r in results]
        retrieved_audiences = [r["metadata"].get("audience") for r in results]
        combined_text = "\n\n".join([r["content"] for r in results])

        # Recall@1
        r1 = 1.0 if (len(retrieved_docs) > 0 and retrieved_docs[0] in expected_docs) else 0.0
        recalls_at_1.append(r1)

        # Recall@5 (Hit@5)
        r5 = 1.0 if any(d in expected_docs for d in retrieved_docs) else 0.0
        recalls_at_5.append(r5)

        # MRR
        rr = 0.0
        for rank, d in enumerate(retrieved_docs, start=1):
            if d in expected_docs:
                rr = 1.0 / rank
                break
        reciprocal_ranks.append(rr)

        # nDCG@5
        dcg = 0.0
        for rank, d in enumerate(retrieved_docs, start=1):
            rel = 1.0 if d in expected_docs else 0.0
            dcg += rel / math.log2(rank + 1)
        # Ideal DCG with min(len(expected_docs), top_k) relevant items at top
        num_rel = min(len(expected_docs), top_k)
        idcg = sum(1.0 / math.log2(r + 1) for r in range(1, num_rel + 1)) if num_rel > 0 else 1.0
        ndcg = (dcg / idcg) if idcg > 0 else 0.0
        ndcgs_at_5.append(ndcg)

        # Full Evidence@5
        ev_satisfied = 0
        for ev in evidences:
            phrases = ev["phrases"]
            found = any(phrase.lower() in combined_text.lower() for phrase in phrases)
            if found:
                ev_satisfied += 1
        is_full_evidence = 1.0 if (len(evidences) > 0 and ev_satisfied == len(evidences)) else 0.0
        full_evidence_at_5.append(is_full_evidence)

        # Audience Match Rate (Tỉ lệ chunks trong top-5 thuộc đối tượng student hoặc all)
        # Đối với student queries, tài liệu hợp lệ là student hoặc all (dành cho toàn trường).
        # Bị coi là nhặt nhầm nếu là staff/faculty
        if len(retrieved_audiences) > 0:
            match_count = sum(1 for aud in retrieved_audiences if aud in [expected_aud, "all"])
            aud_rate = match_count / len(retrieved_audiences)
        else:
            aud_rate = 0.0
        audience_match_rates.append(aud_rate)

        # Faithfulness / Agent Accuracy
        # Sinh câu trả lời qua agent
        agent_resp = agent.answer(query_text)
        criteria_passed = 0
        for crit in answer_criteria:
            all_terms = crit["all_terms"]
            if all(term.lower() in agent_resp.lower() for term in all_terms):
                criteria_passed += 1
        faithfulness = (criteria_passed / len(answer_criteria)) if answer_criteria else 1.0
        faithfulness_scores.append(faithfulness)

        query_details.append({
            "id": q["id"],
            "query": query_text,
            "retrieved_docs": retrieved_docs,
            "retrieved_audiences": retrieved_audiences,
            "r1": r1,
            "r5": r5,
            "rr": rr,
            "ndcg": ndcg,
            "evidence_coverage": f"{ev_satisfied}/{len(evidences)}",
            "is_full_evidence": is_full_evidence,
            "aud_rate": aud_rate,
            "faithfulness": faithfulness,
            "agent_response_snippet": agent_resp.replace("\n", " ")[:150] + "...",
        })

    summary = {
        "Recall@1": sum(recalls_at_1) / len(recalls_at_1),
        "Recall@5": sum(recalls_at_5) / len(recalls_at_5),
        "MRR": sum(reciprocal_ranks) / len(reciprocal_ranks),
        "nDCG@5": sum(ndcgs_at_5) / len(ndcgs_at_5),
        "Full Evidence@5": sum(full_evidence_at_5) / len(full_evidence_at_5),
        "Faithfulness": sum(faithfulness_scores) / len(faithfulness_scores),
        "Audience Match Rate": sum(audience_match_rates) / len(audience_match_rates),
    }
    return summary, query_details


def main():
    with open(GOLD_QUERIES_FILE, encoding="utf-8") as f:
        gold_queries = json.load(f)

    strategies = ["fixed_size", "by_sentences", "recursive", "heading_recursive"]
    print("=" * 90)
    print("BENCHMARK TOÀN DIỆN TRÊN GOLD_QUERIES.JSON (5 QUERIES CHUẨN FPTU HCM)")
    print("=" * 90)

    for embed_mode in ["mock", "semantic"]:
        embed_title = "MOCK EMBEDDER (MD5 - Default Lab Baseline)" if embed_mode == "mock" else "SEMANTIC / LEXICAL EMBEDDER (Semantic Matching)"
        print("\n" + "#" * 90)
        print(f"BỘ ĐO VỚI: {embed_title}")
        print("#" * 90)

        for strat in strategies:
            store = build_store(strat, embedder_type=embed_mode)
            summary, details = calculate_metrics(store, gold_queries, top_k=5, use_filter=False)
            print(f"\n--- CHIẾN LƯỢC: {strat.upper()} ({embed_mode}) ---")
            print(f"  Recall@1            : {summary['Recall@1']:.3f} ({summary['Recall@1']*100:.1f}%)")
            print(f"  Recall@5            : {summary['Recall@5']:.3f} ({summary['Recall@5']*100:.1f}%)")
            print(f"  MRR                 : {summary['MRR']:.3f}")
            print(f"  nDCG@5              : {summary['nDCG@5']:.3f}")
            print(f"  Full Evidence@5     : {summary['Full Evidence@5']:.3f} ({summary['Full Evidence@5']*100:.1f}%)")
            print(f"  Faithfulness (Acc)  : {summary['Faithfulness']:.3f} ({summary['Faithfulness']*100:.1f}%)")
            print(f"  Audience Match Rate : {summary['Audience Match Rate']:.3f} ({summary['Audience Match Rate']*100:.1f}%)")

            print("  Chi tiết từng Query:")
            for d in details:
                print(f"    [{d['id']}] R@1: {d['r1']} | R@5: {d['r5']} | MRR: {d['rr']:.2f} | nDCG: {d['ndcg']:.2f} | Evidence: {d['evidence_coverage']} | AudMatch: {d['aud_rate']*100:.0f}% | Faith: {d['faithfulness']*100:.0f}%")
                print(f"         Docs: {d['retrieved_docs']}")

        print("\n" + "-" * 90)
        print(f"A/B TEST: ẢNH HƯỞNG CỦA METADATA FILTER (audience='student') TRÊN HEADING_RECURSIVE ({embed_mode})")
        print("-" * 90)
        store = build_store("heading_recursive", embedder_type=embed_mode)
        sum_unfiltered, _ = calculate_metrics(store, gold_queries, top_k=5, use_filter=False)
        sum_filtered, _ = calculate_metrics(store, gold_queries, top_k=5, use_filter=True)

        print(f"{'Chỉ số':<25} | {'Không lọc (Unfiltered)':<22} | {'Có lọc (audience=student)':<25}")
        print("-" * 78)
        for k in sum_unfiltered:
            print(f"{k:<25} | {sum_unfiltered[k]:<22.3f} | {sum_filtered[k]:<25.3f}")


if __name__ == "__main__":
    main()
