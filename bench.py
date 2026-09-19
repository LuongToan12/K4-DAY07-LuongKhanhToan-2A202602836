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

# 5 Benchmark queries from gold_queries.json designed for FPTU HCM Student Knowledge Base
BENCHMARK_QUERIES = [
    {
        "id": 1,
        "query": "Sinh viên cần đáp ứng đầy đủ những điều kiện nào để tham gia OJT?",
        "gold_doc_id": "07-ojt-regulations",
        "gold_answer": "Sinh viên phải hoàn thành ít nhất 90% tổng số tín chỉ từ học kỳ 1 đến học kỳ 5, không tính Giáo dục thể chất và Giáo dục quốc phòng; đồng thời phải đọc tài liệu OJT và tham gia đầy đủ Orientation bắt buộc.",
        "must_contain": "90%",
        "filter": None,
    },
    {
        "id": 2,
        "query": "Học phí mỗi học kỳ năm 2026 của ngành Trí tuệ nhân tạo tại TP.HCM là bao nhiêu cho KV1 và các khu vực khác?",
        "gold_doc_id": "03-tuition-hcm",
        "gold_answer": "Với tân sinh viên K22 nhập học năm 2026, ngành Trí tuệ nhân tạo có học phí mỗi học kỳ là 22.120.000 đồng ở KV1 và 31.600.000 đồng ở các khu vực khác.",
        "must_contain": "22.120.000",
        "filter": None,
    },
    {
        "id": 3,
        "query": "Hạn nộp hồ sơ học bổng năm 2026 là khi nào và GPA tối thiểu để duy trì học bổng là bao nhiêu?",
        "gold_doc_id": "04-scholarship-faq",
        "gold_answer": "Hạn nộp hồ sơ học bổng là ngày 15/5/2026. Điều kiện duy trì học bổng khi theo học tại FPTU là GPA từ 7.0/10 trở lên.",
        "must_contain": "15/5/2026",
        "filter": None,
    },
    {
        "id": 4,
        "query": "Trên FAP, sinh viên gửi và theo dõi đơn online như thế nào, đồng thời xem báo cáo điểm danh ở đâu?",
        "gold_doc_id": "02-fap-and-academic-procedures",
        "gold_answer": "Trong Academic Information, sinh viên chọn loại đơn hoặc mục Gửi Đơn, sau đó theo dõi kết quả tại mục Xem Đơn. Muốn xem điểm danh, vào mục Báo cáo rồi chọn Báo cáo điểm danh.",
        "must_contain": "Gửi Đơn",
        "filter": None,
    },
    {
        "id": 5,
        "query": "Sinh viên gặp vấn đề về thủ tục hành chính hoặc đời sống trong quá trình học tại campus TP.HCM thì liên hệ đơn vị nào, hotline và phòng bao nhiêu?",
        "gold_doc_id": "05-student-services-hcm",
        "gold_answer": "Sinh viên liên hệ Phòng Dịch vụ Sinh viên, hotline 028 7300 5585, tại phòng 202 campus FPTU TP.HCM.",
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
