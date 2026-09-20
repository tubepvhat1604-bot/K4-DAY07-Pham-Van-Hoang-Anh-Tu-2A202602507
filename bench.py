"""
bench.py — Công cụ đo benchmark riêng (KHÔNG phải bài test chấm bằng pytest).

Việc nó làm, đúng 4 bước theo day7-lab-data-foundations.md mục "bench.py":
    1. Đọc từng file .md trong data/ecommerce/, tách frontmatter (metadata) và phần thân
    2. Chunk phần thân bằng CHUNKER bên dưới, mỗi chunk -> một Document
    3. Nạp vào EmbeddingStore, chạy 5 benchmark query qua search_with_filter()
    4. In top-3 kèm score và doc_id để đối chiếu với gold answer

Chạy:
    python bench.py
    python bench.py > ket_qua_benchmark.txt      # lưu lại để nộp bài

MỖI THÀNH VIÊN CHỈ ĐỔI ĐÚNG MỘT DÒNG: dòng gán biến CHUNKER ở dưới, sang chiến
lược của mình (FixedSizeChunker / SentenceChunker / RecursiveChunker / HeadingChunker).
Mọi thứ khác giữ nguyên để so sánh mới công bằng.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from src import (
    Document,
    EmbeddingStore,
    FixedSizeChunker,  # noqa: F401  (giữ import sẵn cho các bạn đổi chiến lược)
    RecursiveChunker,
    SentenceChunker,  # noqa: F401
)

DATA_DIR = Path("data/ecommerce")


class HeadingChunker:
    """Chunking theo tiêu đề/mục (## 1. ..., ## 2. ...) của văn bản chính sách.

    Lý do thiết kế: mỗi tài liệu trong data/ecommerce/ được soạn theo mục đánh
    số (## 1. Phạm vi áp dụng, ## 2. Các trường hợp..., ...) — mỗi mục đã là
    một đơn vị ngữ nghĩa trọn vẹn do người soạn chia sẵn, nên tách trước mỗi
    dòng heading giữ được ngữ cảnh tốt hơn so với cắt theo kích thước cố định
    hoặc theo câu, vốn có thể cắt ngang giữa một điều khoản.
    """

    HEADING_PATTERN = re.compile(r"(?=^#{1,3}\s+.+$)", re.MULTILINE)

    def __init__(self, chunk_size: int = 500) -> None:
        self.chunk_size = chunk_size
        self._fallback = RecursiveChunker(chunk_size=chunk_size)

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        sections = [s.strip() for s in self.HEADING_PATTERN.split(text) if s.strip()]
        if not sections:
            sections = [text.strip()]

        chunks: list[str] = []
        for section in sections:
            if len(section) <= self.chunk_size:
                chunks.append(section)
                continue

            # Mục quá dài: hạ xuống recursive chunker, nhưng GẮN LẠI TIÊU ĐỀ
            # vào từng mảnh con — thiếu bước này, mảnh thứ hai trở đi sẽ mất
            # ngữ cảnh "đây là mục nói về cái gì".
            lines = section.split("\n", 1)
            heading = lines[0].strip()
            body = lines[1] if len(lines) > 1 else ""
            for sub_chunk in self._fallback.chunk(body):
                chunks.append(f"{heading}\n{sub_chunk}".strip())

        return chunks


# ============================================================================
# ĐỔI DUY NHẤT DÒNG NÀY SANG CHIẾN LƯỢC CỦA BẠN:
#   FixedSizeChunker(chunk_size=500, overlap=50)
#   SentenceChunker(max_sentences_per_chunk=3)
#   RecursiveChunker(chunk_size=500)
#   HeadingChunker(chunk_size=500)          <- mặc định: chunker theo heading
# ============================================================================
CHUNKER = HeadingChunker(chunk_size=500)


def parse_markdown_file(path: Path) -> tuple[dict, str]:
    """Tách một file .md thành (metadata_dict, noi_dung_than_bai)."""
    raw = path.read_text(encoding="utf-8")
    _, frontmatter_block, body = raw.split("---", 2)

    metadata: dict[str, str] = {}
    for line in frontmatter_block.strip().splitlines():
        if not line.strip() or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        # Bỏ comment mẫu kiểu "buyer               # buyer | seller | both"
        if " #" in value:
            value = value.split(" #", 1)[0].strip()
        metadata[key] = value

    return metadata, body.strip()


def load_documents() -> list[Document]:
    """Đọc mọi file .md, chunk phần thân, trả về list[Document] để nạp store."""
    documents: list[Document] = []
    for path in sorted(DATA_DIR.glob("*.md")):
        metadata, body = parse_markdown_file(path)
        chunks = CHUNKER.chunk(body)
        for i, chunk_text in enumerate(chunks):
            chunk_metadata = dict(metadata)
            # doc_id LUÔN trỏ về file gốc, không phải id của từng chunk —
            # search_with_filter() và delete_document() đều dựa vào đây.
            chunk_metadata["doc_id"] = path.stem
            documents.append(
                Document(id=f"{path.stem}#{i}", content=chunk_text, metadata=chunk_metadata)
            )
    return documents


# ============================================================================
# 5 câu hỏi benchmark của nhóm — CẢ NHÓM DÙNG CHUNG đúng 5 câu này.
# Câu 3 bắt buộc cần metadata_filter={"audience": "seller"} mới trả lời đúng,
# vì corpus có 2 tài liệu cùng chủ đề "bảo hành" nhưng khác audience:
#   - seller-warranty-policy.md         (audience: seller)
#   - shopee-warranty-electronics-general-rules.md (audience: both)
# ============================================================================
BENCHMARK_QUERIES = [
    {
        "question": "Người mua cần gửi yêu cầu trả hàng trong bao lâu nếu sản phẩm là thực phẩm tươi sống hoặc đông lạnh?",
        "gold_answer": "Trong vòng 24 giờ kể từ khi đơn hàng được cập nhật trạng thái giao thành công.",
        "gold_doc_id": "return-refund-policy",
        "metadata_filter": None,
    },
    {
        "question": "Trên Tiki, thời hạn đổi trả chung là bao nhiêu ngày kể từ khi giao hàng thành công?",
        "gold_answer": "30 ngày, áp dụng cho phần lớn mặt hàng trừ nhóm điện tử/điện gia dụng/phụ kiện điện tử.",
        "gold_doc_id": "tiki-return-policy-buyer",
        "metadata_filter": None,
    },
    {
        "question": "Điều kiện để một yêu cầu bảo hành sản phẩm được chấp nhận là gì?",
        "gold_answer": "Cần hóa đơn điện tử hoặc mã đơn hàng, và với hàng điện gia dụng cần phiếu/tem bảo hành cùng tem niêm phong của nhà sản xuất còn nguyên vẹn.",
        "gold_doc_id": "seller-warranty-policy",
        # Không lọc thì có thể lẫn với shopee-warranty-electronics-general-rules.md
        # (cũng nói về bảo hành/khiếu nại nhưng audience: both, không nêu điều
        # kiện chấp nhận yêu cầu bảo hành cụ thể như tài liệu audience: seller).
        "metadata_filter": {"audience": "seller"},
    },
    {
        "question": "Người bán có quyền gì khi sàn quyết định hoàn tiền cho người mua mà không yêu cầu gửi trả sản phẩm?",
        "gold_answer": "Người bán có quyền khiếu nại trong vòng 2 ngày kể từ khi nhận được thông báo hoàn tiền nếu không đồng ý với quyết định đó.",
        "gold_doc_id": "shopee-warranty-electronics-general-rules",
        "metadata_filter": None,
    },
    {
        "question": "Người bán phải cung cấp những thông tin định danh nào khi đăng ký sử dụng dịch vụ sàn giao dịch thương mại điện tử?",
        "gold_answer": "Tên và địa chỉ trụ sở/thường trú, cùng số/ngày cấp/nơi cấp giấy chứng nhận đăng ký kinh doanh, quyết định thành lập, hoặc mã số thuế cá nhân tương ứng.",
        "gold_doc_id": "seller-legal-obligations-nd52-2013",
        "metadata_filter": None,
    },
]


def main() -> None:
    documents = load_documents()
    store = EmbeddingStore(collection_name="ecommerce_bench")
    store.add_documents(documents)

    n_files = len(list(DATA_DIR.glob("*.md")))
    print(f"Chiến lược chunking : {CHUNKER.__class__.__name__}")
    print(f"Số tài liệu nguồn   : {n_files}")
    print(f"Số chunk đã nạp     : {store.get_collection_size()}")
    print("=" * 78)

    for i, q in enumerate(BENCHMARK_QUERIES, start=1):
        print(f"\nCâu {i}: {q['question']}")
        print(f"  Gold answer  : {q['gold_answer']}")
        print(f"  Gold doc_id  : {q['gold_doc_id']}")

        if q["metadata_filter"]:
            print(f"  metadata_filter = {q['metadata_filter']}")
            results = store.search_with_filter(
                q["question"], top_k=3, metadata_filter=q["metadata_filter"]
            )
        else:
            results = store.search(q["question"], top_k=3)

        for rank, r in enumerate(results, start=1):
            preview = r["content"].replace("\n", " ")[:100]
            hit = "✓" if r["metadata"].get("doc_id") == q["gold_doc_id"] else " "
            print(
                f"    [{hit}] top-{rank}  score={r['score']:.3f}  "
                f"doc_id={r['metadata'].get('doc_id')}  | {preview}..."
            )

        # A/B bắt buộc cho câu cần filter: chạy lại KHÔNG filter để so sánh.
        if q["metadata_filter"]:
            print("  -- Không dùng filter (để so sánh A/B) --")
            unfiltered = store.search(q["question"], top_k=3)
            for rank, r in enumerate(unfiltered, start=1):
                preview = r["content"].replace("\n", " ")[:100]
                hit = "✓" if r["metadata"].get("doc_id") == q["gold_doc_id"] else " "
                print(
                    f"    [{hit}] top-{rank}  score={r['score']:.3f}  "
                    f"doc_id={r['metadata'].get('doc_id')}  | {preview}..."
                )

    print("\n" + "=" * 78)
    print("Xong. Đối chiếu cột 'doc_id' với 'Gold doc_id' phía trên cho từng câu.")


class _Tee:
    """Ghi đồng thời ra terminal VÀ ra file UTF-8, không phụ thuộc vào bảng mã
    của PowerShell/CMD — tránh hẳn lỗi UnicodeEncodeError / chữ tiếng Việt bị
    lỗi font khi dùng `python bench.py > ket_qua_benchmark.txt` trên Windows.
    """

    def __init__(self, *streams) -> None:
        self._streams = streams

    def write(self, text: str) -> None:
        for stream in self._streams:
            stream.write(text)

    def flush(self) -> None:
        for stream in self._streams:
            stream.flush()


if __name__ == "__main__":
    output_path = Path("ket_qua_benchmark.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        original_stdout = sys.stdout
        sys.stdout = _Tee(original_stdout, f)
        try:
            main()
        finally:
            sys.stdout = original_stdout
    print(f"\n(Đã lưu kết quả vào {output_path.resolve()})")
