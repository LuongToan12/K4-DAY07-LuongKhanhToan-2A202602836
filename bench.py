from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from src.agent import KnowledgeBaseAgent
from src.chunking import FixedSizeChunker, RecursiveChunker, SentenceChunker
from src.embeddings import _mock_embed
from src.models import Document
from src.store import EmbeddingStore

CORPUS_DIR = Path("data/university")

# 5 Benchmark queries designed for FPTU HCM Student Knowledge Base
BENCHMARK_QUERIES = [
    {
        "id": 1,
        "query": "Điều kiện để sinh viên được công nhận tốt nghiệp đại học chính quy là gì?",
        "gold_doc_id": "01-academic-regulations",
        "gold_answer": "Sinh viên tích lũy đủ số tín chỉ, điểm GPA toàn khóa đạt từ 2.0 trở lên, hoàn thành các học phần điều kiện (GDTC, GDQP, OJT) và không bị kỷ luật đình chỉ học tập.",
        "must_contain": "2.0",
        "filter": None,
    },
    {
        "id": 2,
        "query": "Mức học phí chuyên ngành một học kỳ tại Campus TP. Hồ Chí Minh áp dụng cho khóa K22 ngành Công nghệ thông tin là bao nhiêu?",
        "gold_doc_id": "03-tuition-hcm",
        "gold_answer": "Mức học phí mỗi học kỳ ngành Công nghệ thông tin khóa K22 tại campus TP.HCM là 22.120.000 VNĐ đối với KV1 và 31.600.000 VNĐ đối với các khu vực khác.",
        "must_contain": "31.600.000",
        "filter": None,
    },
    {
        "id": 3,
        "query": "Thời hạn nộp hồ sơ chương trình học bổng Đại học FPT là ngày nào và có bắt buộc nộp video không?",
        "gold_doc_id": "04-scholarship-faq",
        "gold_answer": "Hạn nộp hồ sơ học bổng là 15/5/2026. Không bắt buộc nộp video, thí sinh có thể chọn nộp video không quá 2 phút hoặc bài viết 350-500 từ.",
        "must_contain": "15/5/2026",
        "filter": None,
    },
    {
        "id": 4,
        "query": "Sinh viên cần tích lũy bao nhiêu phần trăm tín chỉ để đủ điều kiện tham gia học kỳ thực tập doanh nghiệp OJT?",
        "gold_doc_id": "07-ojt-regulations",
        "gold_answer": "Sinh viên cần đạt ít nhất 90% tổng số tín chỉ tích lũy từ Học kỳ 1 đến Học kỳ 5 (không gồm GDTC và GDQP) để đủ điều kiện tham gia OJT.",
        "must_contain": "90%",
        "filter": None,
    },
    {
        "id": 5,
        "query": "Phòng Dịch vụ Sinh viên tại campus TP.HCM có số điện thoại hotline và phòng làm việc ở đâu?",
        "gold_doc_id": "05-student-services-hcm",
        "gold_answer": "Phòng Dịch vụ Sinh viên tại Campus TP.HCM có Hotline: 028 7300 5585, đặt tại Phòng 202.",
        "must_contain": "028 7300 5585",
        "filter": {"audience": "student"},
    },
]


class HeadingAwareChunker:
    """Splits markdown by headings (##, ###) while preserving section titles."""

    def __init__(self, chunk_size: int = 500) -> None:
        self.chunk_size = chunk_size
        self.recursive = RecursiveChunker(chunk_size=chunk_size)

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        sections = re.split(r"(?m)^(?=#{1,4}\s+)", text)
        chunks = []
        for sec in sections:
            sec = sec.strip()
            if not sec:
                continue
            if len(sec) <= self.chunk_size:
                chunks.append(sec)
            else:
                chunks.extend(self.recursive.chunk(sec))
        return chunks


def parse_front_matter(raw_text: str) -> tuple[dict[str, str], str]:
    if raw_text.startswith("---"):
        parts = raw_text.split("---", 2)
        if len(parts) >= 3:
            fm_text, content = parts[1], parts[2]
            meta = dict(re.findall(r"^(\w+):\s*(.+)$", fm_text, re.M))
            cleaned_meta = {k: v.strip('"\'') for k, v in meta.items()}
            return cleaned_meta, content.strip()
    return {}, raw_text.strip()


def build_corpus_documents(chunker, corpus_dir: Path = CORPUS_DIR) -> list[Document]:
    docs: list[Document] = []
    md_files = sorted(corpus_dir.glob("*.md"))

    for file_path in md_files:
        raw_text = file_path.read_text(encoding="utf-8")
        metadata, content = parse_front_matter(raw_text)
        metadata["doc_id"] = file_path.stem
        metadata["source_file"] = file_path.name

        chunks = chunker.chunk(content)
        for i, chunk in enumerate(chunks):
            doc = Document(
                id=f"{file_path.stem}#{i}",
                content=chunk,
                metadata={**metadata, "chunk_index": i},
            )
            docs.append(doc)

    return docs


def evaluate_retrieval(results: list[dict], q: dict) -> tuple[int, bool, bool, int | None]:
    gold_doc_id = q["gold_doc_id"]
    must_contain = q["must_contain"].lower()

    found_doc_rank = None
    content_match = False

    for rank, r in enumerate(results, start=1):
        doc_id = r.get("metadata", {}).get("doc_id", "")
        chunk_content = r.get("content", "").lower()

        if doc_id == gold_doc_id and found_doc_rank is None:
            found_doc_rank = rank

        if must_contain in chunk_content:
            content_match = True

    doc_in_top3 = found_doc_rank is not None and found_doc_rank <= 3

    if found_doc_rank == 1 and content_match:
        score = 2
    elif doc_in_top3 and content_match:
        score = 1
    elif doc_in_top3 and not content_match:
        score = 1  # partial: right doc but specific chunk lacked keyword
    else:
        score = 0

    return score, doc_in_top3, content_match, found_doc_rank


def run_benchmark_for_chunker(strategy_name: str, chunker, queries=BENCHMARK_QUERIES) -> dict:
    docs = build_corpus_documents(chunker)
    store = EmbeddingStore(collection_name=f"bench_{strategy_name}", embedding_fn=_mock_embed)
    store.add_documents(docs)

    total_score = 0
    query_results = []

    for q in queries:
        # Run filtered search (or standard if filter is None)
        if q["filter"]:
            results = store.search_with_filter(q["query"], top_k=3, metadata_filter=q["filter"])
        else:
            results = store.search(q["query"], top_k=3)

        score, doc_in_top3, content_match, rank = evaluate_retrieval(results, q)
        total_score += score

        query_results.append({
            "query": q,
            "results": results,
            "score": score,
            "doc_in_top3": doc_in_top3,
            "content_match": content_match,
            "rank": rank,
        })

    # A/B test for Query 5 (with vs without filter)
    q5 = queries[4]
    q5_unfiltered = store.search(q5["query"], top_k=3)
    q5_filtered = store.search_with_filter(q5["query"], top_k=3, metadata_filter=q5["filter"])

    return {
        "strategy": strategy_name,
        "total_chunks": len(docs),
        "total_score": total_score,
        "query_results": query_results,
        "ab_test": {
            "unfiltered": q5_unfiltered,
            "filtered": q5_filtered,
        },
    }


def format_benchmark_report(data: dict) -> str:
    lines = [
        "=" * 70,
        f"BENCHMARK REPORT — STRATEGY: {data['strategy'].upper()}",
        "=" * 70,
        f"Total chunks loaded: {data['total_chunks']}",
        f"Benchmark Score    : {data['total_score']} / 10 points",
        "",
        "--- RESULTS BY QUERY ---",
    ]

    for item in data["query_results"]:
        q = item["query"]
        lines.append(f"\n[Q{q['id']}] {q['query']}")
        lines.append(f"  Gold Document : {q['gold_doc_id']}")
        lines.append(f"  Must Contain  : \"{q['must_contain']}\"")
        lines.append(f"  Score (/2)    : {item['score']}")
        lines.append(f"  Doc in Top-3  : {'YES' if item['doc_in_top3'] else 'NO'} (Rank: {item['rank']})")
        lines.append(f"  Content Match : {'YES' if item['content_match'] else 'NO'}")
        lines.append("  Top-3 Chunks  :")
        for idx, r in enumerate(item["results"], start=1):
            source = r.get("metadata", {}).get("doc_id", "unknown")
            snippet = r.get("content", "")[:90].replace("\n", " ")
            lines.append(f"    #{idx} [score={r.get('score', 0):.3f}] ({source}) {snippet}...")

    lines.append("\n" + "=" * 70)
    lines.append("A/B TEST ON FILTER (QUERY 5)")
    lines.append("=" * 70)
    lines.append("WITHOUT FILTER (search):")
    for idx, r in enumerate(data["ab_test"]["unfiltered"], start=1):
        src = r.get("metadata", {}).get("doc_id", "")
        aud = r.get("metadata", {}).get("audience", "")
        lines.append(f"  #{idx} ({src} | audience={aud}) {r.get('content', '')[:80]}...")

    lines.append("\nWITH FILTER metadata_filter={'audience': 'student'}:")
    for idx, r in enumerate(data["ab_test"]["filtered"], start=1):
        src = r.get("metadata", {}).get("doc_id", "")
        aud = r.get("metadata", {}).get("audience", "")
        lines.append(f"  #{idx} ({src} | audience={aud}) {r.get('content', '')[:80]}...")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Run RAG retrieval benchmark on FPTU Corpus.")
    parser.add_argument("--strategy", choices=["fixed_size", "by_sentences", "recursive", "heading_recursive", "all"], default="all")
    args = parser.parse_args()

    strategies = {
        "fixed_size": FixedSizeChunker(chunk_size=500, overlap=50),
        "by_sentences": SentenceChunker(max_sentences_per_chunk=3),
        "recursive": RecursiveChunker(chunk_size=500),
        "heading_recursive": HeadingAwareChunker(chunk_size=500),
    }

    if args.strategy == "all":
        all_reports = []
        summary_rows = []

        for name, chunker in strategies.items():
            print(f"\n[BENCH] Running strategy: {name}...")
            res = run_benchmark_for_chunker(name, chunker)
            report_text = format_benchmark_report(res)
            all_reports.append(report_text)
            summary_rows.append((name, res["total_chunks"], res["total_score"]))

        final_output = "\n\n".join(all_reports) + "\n\n"
        final_output += "=" * 70 + "\n"
        final_output += "ALL STRATEGIES COMPARISON SUMMARY\n"
        final_output += "=" * 70 + "\n"
        final_output += f"{'Strategy':<20} | {'Total Chunks':<14} | {'Score (/10)':<12}\n"
        final_output += "-" * 52 + "\n"
        for name, count, sc in summary_rows:
            final_output += f"{name:<20} | {count:<14} | {sc}/10\n"

        out_path = Path("ket_qua_benchmark.txt")
        out_path.write_text(final_output, encoding="utf-8")
        print(f"\n[DONE] Full benchmark written to {out_path}")
        print("\n" + "=" * 52)
        print(f"{'Strategy':<20} | {'Total Chunks':<14} | {'Score (/10)':<12}")
        print("-" * 52)
        for name, count, sc in summary_rows:
            print(f"{name:<20} | {count:<14} | {sc}/10")
        print("=" * 52)
    else:
        chunker = strategies[args.strategy]
        res = run_benchmark_for_chunker(args.strategy, chunker)
        report_text = format_benchmark_report(res)
        out_path = Path("ket_qua_benchmark.txt")
        out_path.write_text(report_text, encoding="utf-8")
        print(f"\n[DONE] Benchmark for {args.strategy} written to {out_path}")
        print(report_text)


if __name__ == "__main__":
    main()
