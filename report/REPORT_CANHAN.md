# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** [Tên sinh viên]
**Nhóm:** [Tên nhóm]
**Ngày:** [Ngày nộp]

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Độ tương tự cosine cao nghĩa là góc lệch $\theta$ giữa hai vector embedding trong không gian đa chiều rất nhỏ ($\cos \theta \to 1$). Điều này phản ánh hai đoạn văn bản có sự tương đồng sâu sắc về mặt ngữ nghĩa và ý niệm, bất kể độ dài hay từ ngữ bề mặt có thể khác nhau.

**Ví dụ có độ tương tự CAO:**
- Câu A: "Sinh viên bị cấm thi nếu số buổi vắng mặt vượt quá 20% tổng thời lượng môn học."
- Câu B: "Học viên không được tham dự kỳ thi kết thúc học phần khi tỷ lệ nghỉ học chạm mức 21% trở lên."
- Tại sao tương đồng: Dù hai câu sử dụng từ vựng hoàn toàn khác nhau (sinh viên/học viên, cấm thi/không được tham dự kỳ thi kết thúc học phần, vắng mặt/nghỉ học), nhưng vector embedding nắm bắt chính xác quy định học vụ tương đương nhau về mặt ngữ nghĩa.

**Ví dụ có độ tương tự THẤP:**
- Câu A: "Trường Đại học FPT công bố chính sách trao học bổng tài năng 100% cho tân sinh viên."
- Câu B: "Khuôn viên trường có sân bóng đá và đường chạy phục vụ rèn luyện thể chất."
- Tại sao khác: Hai câu nói về hai miền ngữ nghĩa hoàn toàn độc lập (chính sách tài chính/học bổng vs. cơ sở vật chất thể thao).

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Khoảng cách Euclid phụ thuộc trực tiếp vào độ dài (magnitude) của vector, khiến một câu ngắn và một đoạn văn dài dù cùng nghĩa vẫn bị đẩy xa nhau. Ngược lại, Cosine Similarity chỉ đo hướng (góc) của vector trong không gian ngữ nghĩa, không phụ thuộc vào độ dài văn bản; đồng thời khi vector được chuẩn hóa đơn vị ($\|v\|=1$), cosine similarity quy về tích vô hướng (dot product) cho tốc độ tính toán cực nhanh.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính:* $\lceil (10.000 - 50) / (500 - 50) \rceil = \lceil 9.950 / 450 \rceil = \lceil 22.111 \rceil = 23$ chunks. Đã kiểm chứng bằng `len(FixedSizeChunker(500, 50).chunk('a'*10000))` cho ra đúng 23.
> *Đáp án:* 23 chunks

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Khi overlap tăng lên 100: $\lceil (10.000 - 100) / (500 - 100) \rceil = \lceil 9.900 / 400 \rceil = \lceil 24.75 \rceil = 25$ chunks (tăng thêm 2 chunks). Chúng ta chấp nhận tốn thêm chunk để bảo toàn liên kết ngữ cảnh giữa các đoạn (context preservation), ngăn chặn hiện tượng mất mát thông tin hoặc cắt đứt câu/mệnh đề điều kiện quan trọng ngay tại đường biên phân chia (boundary fragmentation).

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Dùng kỹ thuật positive lookbehind trong regex `r'(?<=[.!?])(?:\s+|\n+)'` để phát hiện ranh giới kết thúc câu mà không làm nuốt mất dấu câu ở cuối câu trước. Các câu sau khi làm sạch khoảng trắng thừa được gom tuần tự theo nhóm tối đa `max_sentences_per_chunk`. Edge cases đã nhận diện: các từ viết tắt có dấu chấm (TS., ThS., v.v.) hoặc số thập phân (GPA 2.0) có thể bị cắt nhầm thành dấu hết câu.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Triển khai thuật toán hai chiều theo thứ tự ưu tiên separator `["\n\n", "\n", ". ", " ", ""]`. Chiều đệ quy xuống sâu sẽ tìm separator phù hợp đầu tiên để bẻ nhỏ text, nếu mảnh con vẫn vượt quá `chunk_size` thì đệ quy tiếp với danh sách separator con. Chiều gom lên (merge up) sẽ liên tục ghép các mảnh nhỏ liền kề cho đến khi chạm ngưỡng `chunk_size` để tránh sinh ra các chunk vụn. Base cases xử lý: text rỗng, text $\le chunk\_size$, hoặc `separators=[]` (cắt lát ký tự trực tiếp).

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> Lưu trữ hoàn toàn in-memory dưới dạng danh sách các dictionary đã được chuẩn hóa qua `_make_record` (copy metadata độc lập và gán `doc_id`). Khi `search()`, vector truy vấn được embed rồi tính tích vô hướng (dot product) với toàn bộ vector lưu trữ thông qua helper `_search_records()`. Kết quả được sắp xếp giảm dần theo điểm và loại bỏ trường embedding để output gọn gàng.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> Bắt buộc lọc trước (pre-filtering) bằng cách duyệt qua metadata để chọn tập ứng viên thỏa mãn tất cả tiêu chí filter, sau đó mới gọi `_search_records()`. Việc lọc trước ngăn chặn tình trạng top-k bị chiếm hết bởi các tài liệu không khớp khiến kết quả sau lọc bị rỗng. `delete_document()` lọc bỏ tất cả record có `doc_id` hoặc `id` khớp, trả về `True` nếu số lượng phần tử giảm đi.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Áp dụng mô hình RAG chuẩn: kiểm tra store có rỗng không (tránh gọi LLM lãng phí), truy xuất top-k chunk liên quan nhất rồi đánh số thứ tự `[1]`, `[2]`, `[3]` kèm nguồn tài liệu tương ứng. Dựng prompt chỉ đạo LLM trả lời nghiêm ngặt dựa trên ngữ cảnh cung cấp, không được tự suy diễn/bịa đặt và bắt buộc trích dẫn số thứ tự nguồn, đảm bảo tiêu chuẩn Source Traceability.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```text
============================= test session starts =============================
platform win32 -- Python 3.12.4, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\VIN_AI\lab_day_7\K4-DAY07-LuongKhanhToan-2A202602836
collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED [  2%]
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED [  4%]
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED [  7%]
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED [  9%]
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED [ 11%]
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED [ 14%]
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED [ 16%]
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED [ 19%]
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED [ 21%]
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED   [ 23%]
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED [ 26%]
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED [ 28%]
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED [ 30%]
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED    [ 33%]
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED [ 35%]
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED [ 38%]
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED [ 40%]
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED [ 42%]
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED   [ 45%]
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED [ 47%]
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED [ 50%]
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED [ 52%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED [ 54%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED [ 57%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED [ 59%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED [ 61%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED [ 64%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED [ 66%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED [ 69%]
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED [ 71%]
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED [ 73%]
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED [ 76%]
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED [ 78%]
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED [ 80%]
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED [ 83%]
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED [ 85%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED [ 88%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED [ 90%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED [ 92%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED [ 95%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED [ 97%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED [100%]

============================= 42 passed in 0.23s ==============================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|:---:|:------|:------|:-------:|:------------:|:-----:|
| 1 | "Sinh viên bị cấm thi nếu vắng quá 20% số buổi." | "Học viên không được thi nếu nghỉ học quá 20%." | cao | -0.0034 | Sai (do Mock) |
| 2 | "Học phí chuyên ngành tại Campus TP.HCM là 31.600.000 VNĐ." | "Mức học phí một kỳ tại cơ sở Hồ Chí Minh là 31,6 triệu đồng." | cao | 0.0114 | Sai (do Mock) |
| 3 | "Trường Đại học FPT xét cấp học bổng tài năng." | "Sinh viên nộp đơn xin mượn sách thư viện trường." | thấp | 0.0335 | Đúng |
| 4 | "Thời hạn nộp hồ sơ xét học bổng là ngày 15/5/2026." | "Hạn chót đăng ký doanh nghiệp OJT là tuần thứ 5." | thấp | 0.2627 | Sai (do Mock) |
| 5 | "Phòng Dịch vụ Sinh viên hỗ trợ cấp bảng điểm tại phòng 202." | "Liên hệ phòng Dịch vụ Sinh viên để nhận bảng điểm tại phòng 202." | cao | -0.1450 | Sai (do Mock) |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Kết quả bất ngờ nhất là Cặp 5 (hai câu gần như trùng lặp hoàn toàn về từ ngữ và ý nghĩa) lại có điểm cosine âm (-0.1450), trong khi Cặp 4 (hai câu về hai mảng chủ đề học bổng và OJT hoàn toàn khác nhau) lại đạt điểm tương đồng dương cao nhất (0.2627). Hiện tượng này chứng minh rằng `MockEmbedder` dựa trên hàm băm MD5 hoàn toàn không có khả năng bảo toàn không gian ngữ nghĩa mà chỉ sinh số giả ngẫu nhiên; do đó, trong các bài toán RAG thực tế, việc sử dụng các mô hình embedding ngữ nghĩa thực (Semantic Embedders như MiniLM, OpenAI, Gemini) là điều kiện tiên quyết bắt buộc.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|:---:|:----------------|:-------------------------------------|:----------:|:------------------------------:|:--------------------------------|
| 1 | Điều kiện để sinh viên được công nhận tốt nghiệp đại học chính quy là gì? | `09-international-exchange-hcm`: chương trình summer camp quốc tế | 0.291 | Có (nằm ở Top-3, Rank 3 thuộc file `01-academic-regulations`) | Trả lời dựa trên các trích đoạn top-3, có đề cập điều kiện môn học và tích lũy tín chỉ [3]. |
| 2 | Mức học phí chuyên ngành một học kỳ tại Campus TP. Hồ Chí Minh áp dụng cho khóa K22 ngành Công nghệ thông tin là bao nhiêu? | `10-departments-and-leadership-hcm`: thông tin lãnh đạo campus HCM | 0.389 | Không | Không tìm thấy số liệu học phí chính xác 31.600.000 VNĐ trong top-3 trích xuất. |
| 3 | Thời hạn nộp hồ sơ chương trình học bổng Đại học FPT là ngày nào và có bắt buộc nộp video không? | `01-academic-regulations`: quy chế thi và kỷ luật thôi học | 0.367 | Không | Không trả lời được hạn 15/5/2026 do chunk FAQ học bổng bị trượt khỏi top-3. |
| 4 | Sinh viên cần tích lũy bao nhiêu phần trăm tín chỉ để đủ điều kiện tham gia học kỳ thực tập doanh nghiệp OJT? | `03-tuition-hcm`: bảng biểu học phí ngành Luật | 0.248 | Không | Báo thiếu ngữ cảnh vì chunk chứa mốc 90% không lọt vào top-3. |
| 5 | Phòng Dịch vụ Sinh viên tại campus TP.HCM có số điện thoại hotline và phòng làm việc ở đâu? | `01-academic-regulations`: đánh giá điểm quá trình môn học | 0.327 | Không | Không có số hotline 028 7300 5585; tuy nhiên filter đã loại sạch toàn bộ tài liệu staff. |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 1 / 5 (kết quả phản ánh trực tiếp bản chất nhiễu ngẫu nhiên của `MockEmbedder`).

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Nhận thức rõ ràng về sự khác biệt giữa hai mức độ đánh giá (chấm theo `doc_id` vs. chấm theo nội dung thực tế chứa từ khóa `must_contain`). Một tài liệu dù trúng `doc_id` nhưng nếu chunker cắt vụn hoặc chia sai ranh giới thì thông tin cần tìm vẫn biến mất khỏi top-3. Đồng thời, kỹ thuật pre-filtering theo `audience` chứng minh hiệu quả phân lập dữ liệu rõ rệt giữa sinh viên và cán bộ quản lý.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|:----------------:|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 10 / 10 |
| **Tổng phần cá nhân** | **60 / 60** |
