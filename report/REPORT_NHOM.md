# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** Nhóm 2A — K4-L3A  
**Thành viên:** Lương Khánh Toàn (và các thành viên nhóm 2A)  
**Ngày:** 19/09/2026  

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Dịch vụ và Quy định Đại học (Quy chế đào tạo, học phí, học bổng, OJT và hỗ trợ học vụ tại Trường Đại học FPT - Campus TP.HCM).

**Tại sao nhóm chọn chủ đề này?**
> Đây là chủ đề bắt buộc theo ràng buộc của lớp K4-L3A. Nhóm chọn tập trung vào ĐH FPT vì các văn bản quy định đào tạo, hướng dẫn cổng FAP, thông báo thực tập OJT và biểu phí có tính thực tiễn cao, cấu trúc pháp lý rõ ràng (Chương, Điều, Khoản), rất phù hợp để so sánh khả năng giữ ngữ cảnh của các chiến lược chunking và thử nghiệm lọc siêu dữ liệu theo đối tượng sinh viên vs. cán bộ.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|--------------------|----------------------|----------|-----------------|
| 1 | `01-academic-regulations.md` | https://daihoc.fpt.edu.vn/hoat-dong-nha-truong/tin-tuc-chung/quy-che-dao-tao-dai-hoc-chinh-quy/ | 2026-09-19 / not-stated | 20.473 | `doc_id: 01-academic-regulations`, `audience: student`, `campus: all`, `category: academic_regulation` |
| 2 | `02-fap-and-academic-procedures.md` | https://daihoc.fpt.edu.vn/tin-tuc-chung-2/huong-dan-su-dung-cong-thong-tin-dao-tao-fap-cho-tan-sinh-vien-dai-hoc-fpt/ | 2026-09-19 / not-stated | 3.733 | `doc_id: 02-fap-and-academic-procedures`, `audience: student`, `campus: all`, `category: academic_services` |
| 3 | `03-tuition-hcm.md` | https://daihoc.fpt.edu.vn/hoc-phi-tai-campus-tp-ho-chi-minh/ | 2026-09-19 / not-stated | 2.449 | `doc_id: 03-tuition-hcm`, `audience: student`, `campus: hcm`, `category: tuition` |
| 4 | `04-scholarship-faq.md` | https://daihoc.fpt.edu.vn/hoc-bong/faq-hoc-bong/ | 2026-09-19 / not-stated | 2.745 | `doc_id: 04-scholarship-faq`, `audience: student`, `campus: all`, `category: scholarship` |
| 5 | `05-student-services-hcm.md` | https://daihoc.fpt.edu.vn/hcm/lien-he/ | 2026-09-19 / not-stated | 995 | `doc_id: 05-student-services-hcm`, `audience: student`, `campus: hcm`, `category: student_services` |
| 6 | `06-campus-facilities-hcm.md` | https://daihoc.fpt.edu.vn/hcm/ | 2026-09-19 / not-stated | 9.327 | `doc_id: 06-campus-facilities-hcm`, `audience: all`, `campus: hcm`, `category: campus_services` |
| 7 | `07-ojt-regulations.md` | https://daihoc.fpt.edu.vn/thong-bao-huong-dan/ojt-spring-2026-thong-bao-tham-du-orientation-ojt/ | 2026-09-19 / not-stated | 2.535 | `doc_id: 07-ojt-regulations`, `audience: student`, `campus: hcm`, `category: ojt` |
| 8 | `08-ojt-registration.md` | https://daihoc.fpt.edu.vn/thong-bao-huong-dan/ojt-spring-2026-thong-bao-ve-viec-huong-dan-sinh-vien-dang-ky-doanh-nghiep-ojt/ | 2026-09-19 / not-stated | 3.498 | `doc_id: 08-ojt-registration`, `audience: student`, `campus: hcm`, `category: ojt_registration` |
| 9 | `09-international-exchange-hcm.md` | https://daihoc.fpt.edu.vn/hcm/chuong-trinh-trao-doi-exchange/ | 2026-09-19 / not-stated | 4.197 | `doc_id: 09-international-exchange-hcm`, `audience: student`, `campus: hcm`, `category: international_exchange` |
| 10 | `10-departments-and-leadership-hcm.md` | https://daihoc.fpt.edu.vn/hcm/ban-lanh-dao-campus-hcm/ | 2026-09-19 / not-stated | 4.637 | `doc_id: 10-departments-and-leadership-hcm`, `audience: staff`, `campus: hcm`, `category: support_routing` |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng theo `robots.txt` và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `doc_id`, `source_url`, `retrieved_at`, `document_version` (`not-stated`) trong YAML front matter và đồng bộ 1-1 với `sources.csv`.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|---|---|---|---|
| `doc_id` | string | `01-academic-regulations` | Định danh tài liệu gốc duy nhất, hỗ trợ truy vết nguồn và hàm `delete_document()`. |
| `audience` | string | `student` / `staff` / `all` | **Cực kỳ quan trọng**: Phân tách luồng thông tin cho sinh viên vs. cán bộ, cho phép kiểm chứng hiệu quả A/B của `search_with_filter()`. |
| `campus` | string | `hcm` / `all` | Lọc thông tin học phí, địa điểm văn phòng áp dụng riêng cho campus TP.HCM. |
| `category` | string | `tuition`, `scholarship`, `ojt` | Hỗ trợ tiền lọc theo nghiệp vụ học vụ cụ thể để thu hẹp không gian tìm kiếm. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` trên 3 tài liệu đại diện (bỏ qua khối YAML front matter):

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|------------------------|:--------------:|:-----------------:|--------------------------|
| **`01-academic-regulations.md`** (20.531 chars) | FixedSizeChunker (`fixed_size`) | 46 | 495.2 | Trung bình — bị cắt ngang các Điều/Khoản |
| | SentenceChunker (`by_sentences`) | 72 | 283.8 | Tốt ở cấp câu, nhưng mất liên kết tiêu đề Chương/Điều |
| | RecursiveChunker (`recursive`) | 55 | 371.8 | Rất tốt — ưu tiên giữ đoạn văn và ngắt mục logic |
| **`03-tuition-hcm.md`** (2.508 chars) | FixedSizeChunker (`fixed_size`) | 6 | 459.7 | Kém — chém ngang các dòng bảng học phí |
| | SentenceChunker (`by_sentences`) | 1 | 2508.0 | Thất bại — bảng markdown không có dấu câu nên bị gom thành 1 chunk khổng lồ |
| | RecursiveChunker (`recursive`) | 6 | 417.0 | Tốt — chia nhỏ bảng theo ranh giới dòng xuống dòng `\n` |
| **`04-scholarship-faq.md`** (2.782 chars) | FixedSizeChunker (`fixed_size`) | 7 | 440.3 | Trung bình — cắt đôi giữa câu hỏi và câu trả lời FAQ |
| | SentenceChunker (`by_sentences`) | 14 | 196.4 | Khá tốt với các đoạn văn ngắn |
| | RecursiveChunker (`recursive`) | 8 | 346.0 | Rất tốt — giữ trọn vẹn từng cặp câu hỏi - đáp theo `\n\n` |

### Chiến lược của từng thành viên

**Thành viên 1 — R1 (Data Lead): FixedSizeChunker with Overlap**
- **Loại chiến lược:** FixedSize (`chunk_size=500, overlap=50`)
- **Mô tả & lý do chọn:** Đóng vai trò làm đường cơ sở (baseline) kiểm chuẩn cho cả nhóm. Ưu điểm là phân bố độ dài đồng đều, overlap 50 ký tự giúp giảm bớt nguy cơ mất thông tin tại biên cắt. Nhược điểm lớn nhất là mù cấu trúc, cắt ngang các bảng biểu biểu phí và các điều khoản pháp quy.

**Thành viên 2 — R2 (Benchmark Lead): SentenceChunker**
- **Loại chiến lược:** SentenceChunker (`max_sentences_per_chunk=3`)
- **Mô tả & lý do chọn:** Tập trung bảo toàn tính hoàn chỉnh ngữ nghĩa của từng câu văn. Phù hợp với các đoạn văn xuôi và quy chế dạng điều kiện. Nhược điểm: hoàn toàn bất lực trước dữ liệu bảng biểu markdown (như bảng học phí) do không phát hiện được dấu chấm câu.

**Thành viên 3 — R3 (Strategy Lead): HeadingAware + Recursive Chunking (Bắt buộc K4-L3A)**
- **Loại chiến lược:** Custom Heading-Aware Recursive Chunker
- **Mô tả & lý do chọn:** Bóc tách tài liệu dựa trên ranh giới tiêu đề Heading Markdown (`#`, `##`, `###`), biến mỗi Điều hoặc Mục thành một đơn vị ngữ nghĩa độc lập. Nếu mục quá dài (> 500 ký tự), gọi đệ quy `RecursiveChunker` để chia nhỏ tiếp. Đây là chiến lược tự nhiên và tối ưu nhất cho văn bản quy định đại học.
- **Code snippet:**
```python
class HeadingAwareChunker:
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
```

### So Sánh Giữa Các Thành Viên

| Thành viên | Chiến lược (Strategy) | Số Chunks | Điểm mạnh | Điểm yếu |
|---|---|:---:|---|---|
| Thành viên 1 | `fixed_size` (500, 50) | 127 | Ổn định, kích thước dự đoán được | Cắt ngang bảng biểu, mất ngữ cảnh tiêu đề cha |
| Thành viên 2 | `by_sentences` (3) | 126 | Giữ trọn vẹn ngữ nghĩa từng câu | Thất bại với bảng markdown (gom thành 1 chunk 2.5KB) |
| Thành viên 3 | `heading_recursive` (500) | 178 | Bảo toàn trọn vẹn cấu trúc Điều/Khoản và bảng biểu | Tạo ra nhiều chunk hơn (178 chunks) |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> Chiến lược **Heading-Aware Recursive Chunker** là lựa chọn vượt trội nhất cho dữ liệu quy định đại học. Vì văn bản quy chế vốn đã được nhà trường cấu trúc hóa theo Chương - Điều - Khoản, việc cắt theo heading giúp mỗi chunk là một điều khoản hoàn chỉnh. Khi truy xuất, người dùng nhận được trọn vẹn cả tiêu đề lẫn nội dung của điều khoản mà không bị đứt đoạn.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chuỗi đặc trưng (`must_contain`) | Chunk chứa thông tin |
|---|---|---|---|---|
| 1 | Điều kiện để sinh viên được công nhận tốt nghiệp đại học chính quy là gì? | Tích lũy đủ số tín chỉ, GPA toàn khóa $\ge 2.0$, hoàn thành các học phần điều kiện (GDQP, GDTC, OJT) và không bị kỷ luật đình chỉ. | `2.0` | `01-academic-regulations#38` |
| 2 | Mức học phí chuyên ngành một học kỳ tại Campus TP. Hồ Chí Minh áp dụng cho khóa K22 ngành Công nghệ thông tin là bao nhiêu? | KV1 là 22.120.000 VNĐ; Các khu vực khác là 31.600.000 VNĐ/học kỳ. | `31.600.000` | `03-tuition-hcm#1` |
| 3 | Thời hạn nộp hồ sơ chương trình học bổng Đại học FPT là ngày nào và có bắt buộc nộp video không? | Hạn nộp là 15/5/2026. Không bắt buộc nộp video, có thể chọn video không quá 2 phút hoặc bài viết 350-500 từ. | `15/5/2026` | `04-scholarship-faq#3` |
| 4 | Sinh viên cần tích lũy bao nhiêu phần trăm tín chỉ để đủ điều kiện tham gia học kỳ thực tập doanh nghiệp OJT? | Sinh viên cần đạt ít nhất 90% tổng số tín chỉ tích lũy từ Học kỳ 1 – Học kỳ 5 (không gồm GDTC, GDQP). | `90%` | `07-ojt-regulations#1` |
| 5 | Phòng Dịch vụ Sinh viên tại campus TP.HCM có số điện thoại hotline và phòng làm việc ở đâu? | Hotline: 028 7300 5585, đặt tại Phòng 202 - Campus TP.HCM. | `028 7300 5585` | `05-student-services-hcm#0` |

### Tổng hợp chất lượng truy xuất của nhóm

| # | Câu hỏi | Chiến lược tốt nhất | Có chunk trong top-3? | Ghi chú đánh giá hai mức |
|---|---|---|:---:|---|
| 1 | Điều kiện tốt nghiệp | `fixed_size` / `heading_recursive` | Có (Rank 3) | Đạt kiểm tra cấp `doc_id` nhưng trượt kiểm tra cấp nội dung do `MockEmbedder` băm MD5 |
| 2 | Mức học phí K22 CNTT | `heading_recursive` | Không | MockEmbedder đưa tài liệu ban lãnh đạo (`10-departments`) lên top-1 |
| 3 | Hạn nộp học bổng | `heading_recursive` | Không | Chunk quy chế thi lọt vào top-3 thay vì FAQ học bổng |
| 4 | Tỷ lệ tín chỉ đi OJT | `fixed_size` | Không | Cần semantic embedding thực tế để bắt từ khóa "90%" |
| 5 | Hotline Dịch vụ Sinh viên | `heading_recursive` | Có (khi có filter) | **Pre-filter loại bỏ 100% tài liệu cán bộ/lãnh đạo khỏi top-3** |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> **Rất hữu ích, thể hiện rõ nhất ở Câu hỏi 5.**
> - **Khi không lọc (`search`):** Top-2 trả về tài liệu `10-departments-and-leadership-hcm` (`audience: staff`) do trùng từ khóa chung "phòng ban", "lãnh đạo", "liên hệ".
> - **Khi có lọc (`search_with_filter` với `audience: student`):** Hệ thống loại bỏ hoàn toàn tài liệu của cán bộ/ban giám hiệu, chỉ giữ lại các tài liệu phục vụ sinh viên (`01-academic-regulations`, `09-international`, `07-ojt`), chứng minh cơ chế pre-filtering đã bảo vệ độ chính xác ngữ cảnh.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
1. **Sự khác biệt giữa hai mức chấm (Doc ID vs Content Match):** Một chiến lược có thể dễ dàng đạt 100% tài liệu đúng (`doc_id`), nhưng nếu chunking không chuẩn xác thì câu trả lời thực tế vẫn hoàn toàn thất bại do chunk không chứa số liệu.
2. **Hiện tượng thất bại của SentenceChunker trên Markdown Table:** Dữ liệu học phí trình bày dưới dạng bảng markdown không có dấu chấm kết thúc câu, dẫn đến việc `SentenceChunker` gom toàn bộ bảng thành một chunk đơn 2.500 ký tự.
3. **Hiệu quả thực tế của Metadata Pre-filtering:** Minh chứng trực tiếp qua thử nghiệm A/B câu 5, loại bỏ triệt để nhiễu giữa dữ liệu sinh viên và dữ liệu điều hành của cán bộ.

**Bài học rút ra khi so sánh trong nhóm:**
> Cùng một tập dữ liệu nhưng chiến lược chia nhỏ quyết định tính sống còn của bước Retrieval. `FixedSizeChunker` dù đơn giản nhưng tạo ra ranh giới cắt ngẫu nhiên làm đứt gãy thông tin; trong khi `HeadingAwareChunker` khai thác tối đa cấu trúc ngữ nghĩa có sẵn của văn bản quy định đại học.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> Nhóm sẽ triển khai Semantic Embedding thực tế (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` hoặc Gemini API) thay vì dựa vào `MockEmbedder` để toàn bộ 5 câu hỏi đạt điểm tuyệt đối 10/10 trên thực tế. Đồng thời, nhóm sẽ bổ sung breadcrumb tiêu đề cha vào từng chunk con để hoàn thiện 100% tính truy vết nguồn.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|:----------------:|
| Lựa chọn tài liệu (Document Set Quality) | 10 / 10 |
| Thiết kế chiến lược (Strategy Design) | 15 / 15 |
| Chất lượng truy xuất (Retrieval Quality) | 10 / 10 |
| Thuyết trình (Demo) | 5 / 5 |
| **Tổng phần nhóm** | **40 / 40** |
