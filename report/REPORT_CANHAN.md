# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Phạm Văn Hoàng Anh Tú
**MSSV:** 2A202602507
**Nhóm:** [ThienAn/G70] — Chính sách đổi trả & bảo hành TMĐT
**Ngày:** [20/09]

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Hai vector embedding gần như cùng hướng trong không gian nhiều chiều — góc giữa chúng nhỏ, cosine tiến gần 1. Với text embedding, điều này nghĩa là hai đoạn văn bản mang ý nghĩa/chủ đề tương đồng, dù có thể dùng từ ngữ khác nhau.

**Ví dụ có độ tương tự CAO:**
- Câu A: "Người mua có thể yêu cầu hoàn tiền nếu sản phẩm bị lỗi."
- Câu B: "Khách hàng được phép đề nghị trả lại tiền khi hàng hóa có khiếm khuyết."
- Tại sao tương đồng: Hai câu diễn đạt cùng một ý (người mua có quyền hoàn tiền khi hàng lỗi) bằng từ vựng hoàn toàn khác nhau ("yêu cầu hoàn tiền" ↔ "đề nghị trả lại tiền", "sản phẩm bị lỗi" ↔ "hàng hóa có khiếm khuyết") — một embedder hiểu ngữ nghĩa tốt sẽ cho điểm cao.

**Ví dụ có độ tương tự THẤP:**
- Câu A: "Thời hạn đổi trả trên Tiki là 30 ngày."
- Câu B: "Con mèo đang ngủ trên ghế sofa."
- Tại sao khác: Hai câu không liên quan gì về chủ đề (chính sách thương mại điện tử vs. sinh hoạt của mèo), không chia sẻ từ vựng hay ngữ cảnh nào.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Cosine chỉ đo góc (hướng) giữa hai vector, không bị ảnh hưởng bởi độ dài (magnitude) của vector — trong khi độ dài embedding có thể thay đổi theo độ dài văn bản chứ không phản ánh ý nghĩa. Euclidean distance lại nhạy với magnitude, nên hai văn bản cùng nghĩa nhưng độ dài khác nhau (embedding có norm khác nhau) có thể bị coi là "xa nhau" một cách sai lệch.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> Trình bày phép tính: `ceil((10000 - 50) / (500 - 50)) = ceil(9950 / 450) = ceil(22.11) = 23`
> Đáp án: **23 chunk** — đã kiểm lại bằng `FixedSizeChunker(chunk_size=500, overlap=50).chunk('a'*10000)` trong repo, cho đúng `len == 23`.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Tăng overlap lên 100: `ceil((10000-100)/(500-100)) = ceil(9900/400) = 25` chunk — đã kiểm lại bằng code, đúng 25. Overlap càng lớn thì bước nhảy (`chunk_size - overlap`) càng nhỏ, nên cần nhiều chunk hơn để phủ hết văn bản. Muốn overlap lớn hơn vì: nếu một câu/ý quan trọng nằm đúng ranh giới giữa 2 chunk, overlap giúp câu đó xuất hiện trọn vẹn trong ít nhất 1 chunk thay vì bị cắt đôi và mất ngữ cảnh ở cả hai phía — đánh đổi là tốn thêm chunk (và thêm chi phí embedding).

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Dùng regex `(?<=[.!?])\s+` với lookbehind để tách câu ngay sau dấu `.`/`!`/`?` mà **không nuốt mất dấu câu** (nếu tách bằng `[.!?]\s+` thông thường, dấu câu sẽ bị `re.split` loại bỏ khỏi kết quả, làm câu bị cụt). Sau đó gom từng nhóm `max_sentences_per_chunk` câu lại, dùng `.strip()` xóa khoảng trắng thừa. Edge case đã xử lý: text rỗng hoặc chỉ có khoảng trắng trả về `[]` ngay từ đầu, không cho lọt vào regex. Edge case **chưa xử lý được**: chữ viết tắt có dấu chấm giữa câu (`TS.`, `v.v.`) và số thập phân (`3.14`) sẽ bị nhận nhầm là kết thúc câu, gây tách sai.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Thuật toán có hai chiều như tài liệu mô tả: (1) *đệ quy xuống* — thử tách bằng separator đầu tiên trong danh sách (`\n\n` → `\n` → `. ` → ` ` → `""`), mảnh nào sau khi tách vẫn dài hơn `chunk_size` thì gọi đệ quy `_split` tiếp với danh sách separator còn lại; (2) *gom lên* — sau khi tách, các mảnh nhỏ liền kề được nối lại (kèm separator gốc) cho tới sát ngưỡng `chunk_size`, tránh sinh ra hàng loạt mảnh vụn vài ký tự. Có 2 base case: text đã đủ ngắn (`len <= chunk_size`) thì trả về nguyên văn; hết separator để thử (`remaining_separators` rỗng) thì cắt cứng theo `chunk_size`. Riêng separator rỗng (`""`) được xử lý đặc biệt bằng `list(text)` vì `str.split("")` sẽ ném lỗi trong Python.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> Lưu trữ hoàn toàn trong bộ nhớ (`self._store` là list các dict), **không dùng nhánh ChromaDB** dù thư viện có được cài hay không — vì nhánh đó chưa được lập trình sẵn trong template và sẽ làm cả 14 test của `EmbeddingStore` sập nếu vô tình bật lên. Mỗi `Document` được `_make_record` chuyển thành 1 record gồm `id`, `content`, `metadata` (copy riêng, không dùng chung reference với object gốc) và `embedding` đã tính sẵn. Vì embedding đã được chuẩn hóa (`||v||=1`), `search` chỉ cần tính dot product giữa embedding câu hỏi và từng record (hàm `_dot` có sẵn) — dot product lúc này bằng đúng cosine similarity, không cần chia lại cho norm.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> Lọc **trước rồi mới search**, không làm ngược lại: nếu search top-k trước rồi mới lọc bỏ phần không khớp, có thể mất hết kết quả dù store vẫn còn tài liệu hợp lệ (k slot đã bị các bản ghi sai chiếm hết). Cách làm: xây danh sách `candidates` bằng cách duyệt `self._store` và giữ lại record có `metadata` khớp toàn bộ điều kiện trong `metadata_filter`, sau đó gọi lại đúng hàm `_search_records` dùng chung cho cả `search` lẫn `search_with_filter` — nhờ vậy `test_no_filter_returns_all_candidates` tự động pass vì cả hai đường code không thể lệch kết quả. `delete_document` xóa bằng cách lọc lại `self._store`, chỉ giữ những record có `metadata['doc_id'] != doc_id`, rồi so sánh độ dài trước/sau để trả về `True`/`False`.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> `__init__` chỉ lưu tham chiếu `store` và `llm_fn`. `answer` gồm 3 nhịp: truy xuất top-k từ `store.search`, dựng ngữ cảnh bằng cách đánh số từng chunk `[1] [2] [3]` kèm `doc_id` nguồn, rồi ghép vào prompt yêu cầu model chỉ dùng ngữ cảnh được cung cấp và trích dẫn số thứ tự khi trả lời — đúng tiêu chí *Source Traceability* trong `docs/EVALUATION.md`. Nếu `store.search` trả về rỗng (store trống hoặc không có gì liên quan), agent trả thẳng câu thông báo "không tìm thấy" thay vì gọi `llm_fn` với ngữ cảnh trống, tránh lãng phí lệnh gọi LLM và tránh model bịa đáp án.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
$ pytest tests/ -v
collecting ... collected 42 items

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

============================== 42 passed in 0.04s ==============================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

> Dự đoán được ghi lại **trước khi chạy** `compute_similarity`, dùng `MockEmbedder` (`_mock_embed`) như quy định mặc định của lab.

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Người mua có thể yêu cầu hoàn tiền nếu sản phẩm bị lỗi. | Khách hàng được phép đề nghị trả lại tiền khi hàng hóa có khiếm khuyết. | cao | 0.2336 | Đúng phần nào — điểm cao nhất trong 5 cặp, nhưng tuyệt đối không "cao" (< 0.3) |
| 2 | Người bán phải cung cấp hóa đơn điện tử cho khách hàng. | Hôm nay trời mưa rất to ở Hà Nội. | thấp | -0.0188 | Đúng |
| 3 | Trung tâm bảo hành sẽ thẩm định sản phẩm trước khi ra quyết định. | Sản phẩm cần được kiểm tra bởi bộ phận bảo hành trước khi có kết luận. | cao | 0.0490 | **Sai** — dự đoán cao (paraphrase rõ ràng) nhưng điểm thực tế thấp hơn cả cặp 5 |
| 4 | Thời hạn đổi trả trên Tiki là 30 ngày. | Con mèo đang ngủ trên ghế sofa. | thấp | -0.0458 | Đúng — thấp nhất trong 5 cặp |
| 5 | Người bán phải tuân thủ quy định pháp luật khi bán hàng trên sàn. | Người mua có quyền khiếu nại nếu không hài lòng với sản phẩm. | thấp/trung bình | 0.0617 | Đúng phần nào |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Bất ngờ nhất là cặp 3: hai câu gần như là bản diễn giải lại của nhau (cùng nói về việc trung tâm bảo hành kiểm tra sản phẩm trước khi quyết định), lẽ ra phải có similarity cao nhất, nhưng điểm thực tế (0.049) lại thấp hơn cả cặp 5 — hai câu không hề paraphrase nhau. Điều này cho thấy `MockEmbedder` chỉ băm MD5 chuỗi ký tự thành số giả ngẫu nhiên, **hoàn toàn không mã hóa ý nghĩa** — hai câu đồng nghĩa nhưng khác chuỗi ký tự sẽ cho ra vector gần như độc lập ngẫu nhiên với nhau. Similarity từ MockEmbedder chỉ có ý nghĩa để kiểm tra cấu trúc code (đúng công thức toán), không phản ánh được quan hệ ngữ nghĩa thật — đúng như cảnh báo của tài liệu lab về việc benchmark bằng mock sẽ cho số liệu nhiễu.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chiến lược chunking cá nhân: **HeadingChunker** (custom, chunk theo tiêu đề/mục `## 1. ...`) — 48 chunk nạp từ 7 tài liệu.

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Thời hạn trả hàng thực phẩm tươi sống/đông lạnh | `seller-legal-obligations-nd52-2013` — mục 2 (nghĩa vụ đăng ký) | 0.270 | Không | Sai chủ đề — không nói về thời hạn 24 giờ |
| 2 | Thời hạn đổi trả chung trên Tiki | `shopee-marketplace-operating-rules` — mục 4 (trách nhiệm người bán) | 0.237 | Không | Sai — không nhắc tới Tiki hay 30 ngày |
| 3 | Điều kiện bảo hành được chấp nhận (có `metadata_filter={"audience":"seller"}`) | `seller-warranty-policy` — mục 3 (trường hợp không được bảo hành) | 0.216 | **Có** — đúng tài liệu gold, lệch mục nhưng cùng file | Đúng chủ đề, có thể trích đúng điều kiện ở top-3 |
| 4 | Quyền của người bán khi sàn hoàn tiền không cần trả hàng | `seller-warranty-policy` — mục 6 (khuyến nghị cho người bán) | 0.248 | Không | Sai — không nói về quyền khiếu nại 2 ngày |
| 5 | Thông tin định danh người bán khi đăng ký sàn | `seller-legal-obligations-nd52-2013` — mục 1 (định nghĩa sàn) | 0.241 | **Có** — đúng tài liệu gold | Đúng chủ đề, đáp án nằm trong top-3 |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 2 / 5

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Từ kết quả của Sang (RecursiveChunker), thấy rõ chiến lược của bạn ấy trúng cả câu 1 mà chiến lược Heading của mình lại trượt — cho thấy chunk theo mục cố định (Heading) đôi khi quá "cứng nhắc" khi câu hỏi cần thông tin nằm ở phần đầu một mục dài (RecursiveChunker cắt linh hoạt hơn theo ranh giới câu/đoạn nên bắt trúng đoạn chứa "24 giờ" tốt hơn). Bài học: không nên chọn 1 chiến lược duy nhất cho toàn bộ corpus khi chưa benchmark thử — nên thử nghiệm A/B thực tế trước khi quyết định.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 9 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 6 / 10 |
| **Tổng phần cá nhân** | **55 / 60** |
