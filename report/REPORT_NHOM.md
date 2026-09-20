# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** [ThienAn/G70]
**Thành viên:** [Phạm Văn Hoàng Anh Tú], Vũ Đình Thư, Lê Văn Sang, Ngô Thế Khanh
**Ngày:** [20/09]

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Chính sách đổi trả, bảo hành và quy định người bán/người mua trên nền tảng thương mại điện tử (bắt buộc theo biến thể K4-L3B).

**Tại sao nhóm chọn chủ đề này?**
> Đây là chủ đề bắt buộc của lớp L3B theo `K4_VARIANT.md`. Chủ đề có cấu trúc rõ ràng theo điều khoản/mục, phù hợp để thử nghiệm chunking theo heading. Ngoài ra chủ đề có sẵn ranh giới `audience` tự nhiên (buyer/seller/both) từ nhiều sàn khác nhau (Shopee, Lazada, Tiki) và một văn bản pháp luật, giúp minh chứng rõ giá trị của metadata filtering.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | return-refund-policy.md | help.shopee.vn — Chính sách trả hàng và hoàn tiền | 2026-09-20 / not-stated | 3774 | audience: buyer, category: return-refund-policy |
| 2 | seller-warranty-policy.md | help.shopee.vn — Chính sách bảo hành sản phẩm | 2026-09-20 / not-stated | 3101 | audience: seller, category: warranty-policy |
| 3 | shopee-marketplace-operating-rules.md | help.shopee.vn — Quy chế hoạt động sàn Shopee.vn | 2026-09-20 / not-stated | 2959 | audience: both, category: platform-rules |
| 4 | shopee-warranty-electronics-general-rules.md | help.shopee.vn — Quy định chung trả hàng/hoàn tiền | 2026-09-20 / not-stated | 2983 | audience: both, category: warranty-policy |
| 5 | lazada-return-policy-buyer.md | ghn.vn — Hướng dẫn đổi trả hàng Lazada | 2026-09-20 / not-stated | 3368 | audience: buyer, category: return-refund-policy |
| 6 | tiki-return-policy-buyer.md | hotro.tiki.vn — Chính sách đổi trả sản phẩm | 2026-09-20 / not-stated | 2716 | audience: buyer, category: return-refund-policy |
| 7 | seller-legal-obligations-nd52-2013.md | thuvienphapluat.vn — Nghị định 52/2013/NĐ-CP (sửa đổi 85/2021/NĐ-CP) | 2026-09-20 / Nghị định 52/2013/NĐ-CP sửa đổi bởi 85/2021/NĐ-CP | 3158 | audience: seller, category: legal-regulation |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `audience` | string (enum) | `buyer` / `seller` / `both` | Bắt buộc theo K4_VARIANT.md; cho phép lọc để tránh trả lời sai đối tượng khi 2 tài liệu cùng chủ đề nhưng khác người đọc (ví dụ 2 tài liệu về "bảo hành" nhưng khác audience). |
| `category` | string | `return-refund-policy` / `warranty-policy` / `platform-rules` / `legal-regulation` | Cho phép thu hẹp phạm vi tìm kiếm theo loại chính sách khi câu hỏi đã ngụ ý chủ đề (đổi trả vs bảo hành vs pháp lý). |
| `source_url`, `retrieved_at`, `document_version` | string | xem bảng trên | Bắt buộc theo yêu cầu lab để truy vết nguồn và kiểm tra độ mới của thông tin. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` (chunk_size=200) trên 3 tài liệu đại diện (đã bỏ frontmatter trước khi so sánh):

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| return-refund-policy | FixedSizeChunker (`fixed_size`) | 13 | 188.9 | Không — cắt cứng theo ký tự, nhiều chỗ cắt ngang giữa câu |
| return-refund-policy | SentenceChunker (`by_sentences`) | 7 | 349.1 | Có — theo ranh giới câu, nhưng đôi khi gộp 2-3 ý khác mục vào 1 chunk |
| return-refund-policy | RecursiveChunker (`recursive`) | 16 | 151.9 | Có phần — ưu tiên ranh giới đoạn/câu trước khi hạ xuống ký tự |
| seller-warranty-policy | FixedSizeChunker | 10 | 193.7 | Không |
| seller-warranty-policy | SentenceChunker | 5 | 385.6 | Có |
| seller-warranty-policy | RecursiveChunker | 13 | 147.5 | Có phần |
| tiki-return-policy-buyer | FixedSizeChunker | 9 | 189.2 | Không |
| tiki-return-policy-buyer | SentenceChunker | 5 | 338.8 | Có |
| tiki-return-policy-buyer | RecursiveChunker | 12 | 140.2 | Có phần |

### Chiến lược của từng thành viên

**Thành viên 1 — [Đội trưởng]**
- **Loại chiến lược:** Custom — HeadingChunker (chunk theo tiêu đề/mục)
- **Mô tả & lý do chọn cho chủ đề này:** Mỗi tài liệu chính sách được soạn theo mục đánh số (`## 1. ...`, `## 2. ...`), mỗi mục đã là một đơn vị ngữ nghĩa trọn vẹn do người soạn chia sẵn. Tách trước mỗi dòng heading giữ nguyên ranh giới điều khoản; mục nào quá dài thì hạ xuống RecursiveChunker và gắn lại tiêu đề vào từng mảnh con để không mất ngữ cảnh.
- **Code snippet:** xem class `HeadingChunker` trong `bench.py`.

**Thành viên 2 — Sang**
- **Loại chiến lược:** RecursiveChunker (built-in)
- **Mô tả & lý do chọn:** Thử separator theo thứ tự ưu tiên mặc định (đoạn → dòng → câu → khoảng trắng), giữ ngữ nghĩa tốt hơn cắt cứng vì ưu tiên ranh giới "to" trước.
- **Code snippet:** dùng trực tiếp `RecursiveChunker(chunk_size=500)` từ `src/chunking.py`.

**Thành viên 3 — Khánh**
- **Loại chiến lược:** SentenceChunker (built-in)
- **Mô tả & lý do chọn:** Cắt theo câu (`max_sentences_per_chunk=3`), phù hợp với văn phong chính sách vốn viết thành câu đầy đủ, dễ đọc và dễ kiểm tra thủ công.
- **Code snippet:** dùng trực tiếp `SentenceChunker(max_sentences_per_chunk=3)` từ `src/chunking.py`.

**Thành viên 4 — Thu Vũ**
- **Loại chiến lược:** FixedSizeChunker (built-in, có overlap)
- **Mô tả & lý do chọn:** Chunk theo kích thước cố định — đơn giản, dễ dự đoán số lượng chunk, dùng làm đường cơ sở đối chứng với 3 chiến lược "thông minh" hơn.
- **Code snippet:** dùng trực tiếp `FixedSizeChunker(chunk_size=500, overlap=50)` từ `src/chunking.py`.

### So Sánh Giữa Các Thành Viên

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10)* | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| [Đội trưởng] | HeadingChunker | 4 (2/5 câu trúng ×2đ) | Giữ nguyên ranh giới điều khoản; câu 3 vẫn có đáp án dù không filter | 48 chunk hơi vụn khi 1 câu hỏi cần thông tin trải nhiều mục |
| Sang | RecursiveChunker | 6 (3/5 câu trúng ×2đ) | Cân bằng nhất — thắng ở cả câu 1 và câu 5, 100% top-3 đúng ở câu 3 khi có filter | Mất hoàn toàn gold answer ở câu 3 khi KHÔNG filter |
| Khánh | SentenceChunker | 4 (2/5 câu trúng ×2đ) | Duy nhất trúng câu 4 cùng Thu | Trượt câu 1 và câu 5 |
| Thu Vũ | FixedSizeChunker | 4 (2/5 câu trúng ×2đ) | Trúng câu 4; số chunk ít nhất (33) nên chi phí embed thấp | Trượt câu 1, 2, 5; điểm số câu 3 thấp nhất (0.113) |

*Tính thô theo cách chấm ngây thơ (đúng doc_id trong top-3 = 2đ/câu); xem mục 3 để chấm đúng chuẩn 2 mức theo `docs/SCORING.md`.

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> RecursiveChunker (Sang) thắng tổng thể với 3/5 câu đúng, gồm cả câu 1 mà không chiến lược nào khác trúng. Recursive cân bằng tốt hơn Heading (không quá vụn — 40 so với 48 chunk) và tốt hơn FixedSize/Sentence (không cắt cứng, ưu tiên ranh giới ngữ nghĩa). Tuy nhiên với câu cần metadata_filter (câu 3), Heading là chiến lược duy nhất còn giữ được đáp án ở top-2 ngay cả khi KHÔNG lọc, cho thấy chunk theo heading có lợi thế khi metadata filtering không sẵn có.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | Người mua cần gửi yêu cầu trả hàng trong bao lâu nếu sản phẩm là thực phẩm tươi sống hoặc đông lạnh? | Trong vòng 24 giờ kể từ khi đơn hàng được cập nhật trạng thái giao thành công. | `return-refund-policy.md` — mục 4 |
| 2 | Trên Tiki, thời hạn đổi trả chung là bao nhiêu ngày kể từ khi giao hàng thành công? | 30 ngày, áp dụng cho phần lớn mặt hàng trừ nhóm điện tử/điện gia dụng/phụ kiện điện tử. | `tiki-return-policy-buyer.md` — mục 1 |
| 3 | Điều kiện để một yêu cầu bảo hành sản phẩm được chấp nhận là gì? | Cần hóa đơn điện tử hoặc mã đơn hàng, và với hàng điện gia dụng cần phiếu/tem bảo hành cùng tem niêm phong của nhà sản xuất còn nguyên vẹn. | `seller-warranty-policy.md` — mục 1 (cần `metadata_filter={"audience":"seller"}`) |
| 4 | Người bán có quyền gì khi sàn quyết định hoàn tiền cho người mua mà không yêu cầu gửi trả sản phẩm? | Người bán có quyền khiếu nại trong vòng 2 ngày kể từ khi nhận được thông báo hoàn tiền nếu không đồng ý với quyết định đó. | `shopee-warranty-electronics-general-rules.md` — mục 3 |
| 5 | Người bán phải cung cấp những thông tin định danh nào khi đăng ký sử dụng dịch vụ sàn giao dịch thương mại điện tử? | Tên và địa chỉ trụ sở/thường trú, cùng số/ngày cấp/nơi cấp giấy chứng nhận đăng ký kinh doanh, quyết định thành lập, hoặc mã số thuế cá nhân tương ứng. | `seller-legal-obligations-nd52-2013.md` — mục 2 |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | Thực phẩm tươi sống/đông lạnh | Recursive (duy nhất trúng, top-3) | Chỉ Recursive | 3/4 chiến lược trượt hoàn toàn — nghi do MockEmbedder nhiễu |
| 2 | Thời hạn đổi trả Tiki | Không chiến lược nào | Không | **Failure case** — xem mục 4 |
| 3 | Điều kiện bảo hành (cần filter) | Recursive (100% top-3 đúng khi có filter) | Cả 4, khi có filter | Không filter thì 3/4 chiến lược mất trắng — bằng chứng A/B rõ nhất |
| 4 | Quyền khiếu nại người bán | Sentence & FixedSize (top-2, top-3) | Sentence, FixedSize | Heading và Recursive trượt |
| 5 | Thông tin đăng ký người bán | Heading (top-1) | Heading, Recursive | Sentence, FixedSize trượt |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> Có, rất rõ ở câu 3. Khi dùng `metadata_filter={"audience":"seller"}`, cả 4 chiến lược đều đưa được `seller-warranty-policy` vào top-3 (Recursive đạt 100% — cả 3 slot top-3 đều đúng). Khi bỏ filter, 3/4 chiến lược (Recursive, Sentence, FixedSize) **mất trắng** gold answer khỏi top-3, vì bị các tài liệu cùng nói về "sàn"/"bảo hành" nhưng khác `audience` (như `shopee-marketplace-operating-rules`, `seller-legal-obligations-nd52-2013`) chiếm hết chỗ. Đây là minh chứng trực tiếp cho việc metadata filtering giải quyết đúng vấn đề "cùng từ vựng, khác đối tượng" mà lab yêu cầu.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> - Metadata filtering không phải tính năng phụ: ở câu 3, nó quyết định việc gold answer có xuất hiện trong top-3 hay không (3/4 chiến lược mất trắng nếu thiếu filter).
> - Không có chiến lược chunking nào thắng tuyệt đối — Recursive tốt nhất tổng thể (3/5) nhưng Heading lại là chiến lược duy nhất chống chịu tốt khi thiếu filter.
> - Toàn bộ 4 chiến lược đều thất bại ở câu 2 — cho thấy giới hạn của `MockEmbedder` quan trọng hơn cả lựa chọn chiến lược chunking trong một số trường hợp.

**Bài học rút ra khi so sánh trong nhóm:**
> Cùng một bộ tài liệu và cùng 5 câu hỏi, 4 chiến lược cho ra 4 bộ chunk có kích thước rất khác nhau (33 đến 48 chunk) và điểm số retrieval không đồng nhất giữa các câu — chiến lược thắng ở câu này có thể thua ở câu khác (ví dụ Heading thắng câu 5 nhưng Recursive lại thắng câu 1). Điều này cho thấy việc chỉ đo trên 1-2 câu hỏi sẽ đưa ra kết luận sai lệch về "chiến lược tốt nhất".

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> Sẽ bật embedder thật (local, đa ngữ) thay vì MockEmbedder ngay từ đầu, vì câu 2 cho thấy MockEmbedder có thể che lấp hoàn toàn hiệu quả thực sự của một chiến lược chunking tốt. Ngoài ra sẽ thêm overlap giữa các chunk ở chiến lược Heading để giảm rủi ro câu trả lời bị cô lập trong đúng 1 mục duy nhất.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 9 / 10 |
| Thiết kế chiến lược (Strategy Design) | 13 / 15 |
| Chất lượng truy xuất (Retrieval Quality) | 8 / 10 |
| Thuyết trình (Demo) | [Điền sau khi demo] / 5 |
| **Tổng phần nhóm** | **[Điền tổng]** / 40 |
