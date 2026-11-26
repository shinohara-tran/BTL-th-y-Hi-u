# Báo cáo Phần 1: Làm sạch dữ liệu, Chia đoạn và Gắn nhãn năm

**Người làm:** Nguyễn Tiến Bình  
**Nhánh:** `part-1`  
**Commit kết quả:** `aea5731` (trên nền code `7cbbe5c`, `96296c2`)

---

## 1. Điểm yếu đã xử lý

| # | Điểm yếu | Bằng chứng (file, dòng) |
|---|---|---|
| 1 | **Lỗi 1.1 — Đếm token xấp xỉ (`0.75 * words`) gây cắt cụt vượt quá giới hạn 512 token của BGE** | Đã thay bằng tokenizer thật của `BAAI/bge-small-en-v1.5` và đặt trần cứng `MAX_MODEL_TOKENS = 480` tại `src/hybrid_search/chunking/chunker.py` (dòng 14–42, 60–73). |
| 2 | **Lỗi 1.2 — Làm phẳng bảng HTML bằng dấu `|` làm mất tiêu đề cột và đơn vị tính** | Đã chuyển sang định dạng `Row-to-Text` tự chứa ngữ cảnh (`Table context: ...`, `Unit: ...`) và tự động nhận diện đơn vị (`millions of USD`, `billions of USD`, `thousands of USD`, `USD per share`) tại `src/hybrid_search/ingestion/html_parser.py` (dòng 19–82, 140–318). |
| 3 | **Lỗi 1.3 — `fiscal_period` chỉ lưu năm nộp báo cáo, làm sót số liệu các năm so sánh (2022/2023 trong báo cáo 2024)** | Đã bổ sung trường `fact_years: List[int]` trong `src/hybrid_search/models/document.py` (dòng 57) và hàm `extract_fact_years()` tại `src/hybrid_search/chunking/chunker.py` (dòng 44–54). |

---

## 2. Đã sửa gì

| File | Thay đổi | Có đụng tới phần của người khác không |
|---|---|---|
| `src/hybrid_search/chunking/chunker.py` | Dùng BGE tokenizer thật, cap 480 token, trích xuất `fact_years`. | Không (phạm vi Part 1). |
| `src/hybrid_search/ingestion/html_parser.py` | Chuyển bảng sang `Row-to-Text` với `Table context:` và nhận diện đơn vị (`millions`/`billions`/`thousands of USD`, `USD per share`). | Không (phạm vi Part 1). |
| `src/hybrid_search/models/document.py` | Thêm trường `fact_years: List[int]` vào `Chunk`. | Có thể dùng chung ở Part 3 (lọc metadata). |
| `src/hybrid_search/retrieval/extractor.py` | Phạt dòng tiền tố `Table context:` và mở rộng từ khóa tài chính (`earnings`, `eps`, `share`, `income`, `sales`) để không bốc nhầm tiêu đề bảng. | Có chạm nhẹ phần trích xuất câu trả lời để tương thích định dạng bảng mới. |
| `config/default.yaml` | Đổi `localhost` → `127.0.0.1` (tránh trễ IPv6 trên Windows) và trỏ `collection_name` sang `team_docs_final`. | Có (`config/default.yaml` dùng chung). |
| `scripts/team/common.py` | Tự tìm `git.exe` của GitHub Desktop khi `git` không có trong `PATH` để ghi đúng `git_commit`. | Không ảnh hưởng logic tìm kiếm. |
| `tests/unit/test_api.py`, `tests/unit/test_config.py` | Cho phép tên collection `team_docs_final` trong unit test. | Không. |

---

## 3. Cách chạy lại

```powershell
git checkout part-1
pip install -e ".[dev]"
# Lưu ý: giữ nguyên collection team_docs_final (14.022 chunk) đã chốt của nhóm, không chạy lại index --recreate
python scripts/team/check_dense.py team_docs_final
python scripts/team/evaluate.py --tag part1 --collection team_docs_final --force
python scripts/team/compare.py baseline part1
pytest -q tests/unit
```

---

## 4. Kết quả

- **Máy chạy:** Windows AMD64, Python 3.11.9 (CPU, không GPU)
- **Số chunk sau khi index (`team_docs_final`):** 14.022 chunk (tăng so với 13.137 chunk của bản gốc do chia lại theo trần 480 token thật)
- **Bảng đối chiếu từ `python scripts/team/compare.py baseline part1` (`evaluation/team/results/compare.md`):**

| Tag | Method | mrr | ndcg@10 | recall@10 | p@10 | company@5 | dup@5 | unjudged@10 | p50 ms | commit | dense |
|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | bm25 | - | - | - | - | 0.826 | 0.083 | - | 2094.1 | unknown | BAAI/bge-small-en-v1.5 |
| baseline | dense | - | - | - | - | 0.783 | 0.083 | - | 2102.1 | unknown | BAAI/bge-small-en-v1.5 |
| baseline | bm25_dense | - | - | - | - | 0.817 | 0.067 | - | 2133.8 | unknown | BAAI/bge-small-en-v1.5 |
| baseline | sparse | - | - | - | - | 0.861 | 0.058 | - | 2156.9 | unknown | BAAI/bge-small-en-v1.5 |
| baseline | sparse_dense | - | - | - | - | 0.852 | 0.050 | - | 2255.7 | unknown | BAAI/bge-small-en-v1.5 |
| baseline | rerank | - | - | - | - | 0.843 | 0.067 | - | 32524.6 | unknown | BAAI/bge-small-en-v1.5 |
| part1 | bm25 | - | - | - | - | 0.817 | 0.075 | - | 39.8 | 7cbbe5c | BAAI/bge-small-en-v1.5 |
| part1 | dense | - | - | - | - | 0.800 | 0.050 | - | 67.3 | 7cbbe5c | BAAI/bge-small-en-v1.5 |
| part1 | bm25_dense | - | - | - | - | 0.835 | 0.033 | - | 70.8 | 7cbbe5c | BAAI/bge-small-en-v1.5 |
| part1 | sparse | - | - | - | - | 0.861 | 0.033 | - | 118.2 | 7cbbe5c | BAAI/bge-small-en-v1.5 |
| part1 | sparse_dense | - | - | - | - | 0.861 | 0.017 | - | 371.3 | 7cbbe5c | BAAI/bge-small-en-v1.5 |
| part1 | rerank | - | - | - | - | 0.878 | 0.025 | - | 43951.0 | 7cbbe5c | BAAI/bge-small-en-v1.5 |

**Nhận xét:**
- Các chỉ số `mrr`, `ndcg@10`, `recall@10`, `p@10` hiện đang là `-` do bộ nhãn chuẩn từ người chấm (`q001–q024`) đang trong quá trình hoàn thiện.
- Tỉ lệ trùng lặp `dup@5` giảm đồng loạt trên cả 6 phương pháp (nổi bật: `sparse_dense` giảm từ `0.050` xuống `0.017`; `bm25_dense` giảm từ `0.067` xuống `0.033`; `rerank` giảm từ `0.067` xuống `0.025`).
- Độ chính xác đúng công ty `company@5` tăng ở `dense` (`0.783 → 0.800`), `bm25_dense` (`0.817 → 0.835`), `sparse_dense` (`0.852 → 0.861`), và `rerank` (`0.843 → 0.878`).
- Độ trễ `p50` của BM25 giảm từ `2094.1 ms` xuống `39.8 ms` sau khi sửa lỗi phân giải `localhost` sang `127.0.0.1` trên Windows.
- Kiểm thử đơn vị (`pytest tests/unit -q`): **51/51 passed**.

---

## 5. Demo (Trước và Sau khi sửa lỗi 1.2 & 1.3)

| Ví dụ | Trước khi sửa | Sau khi sửa |
|---|---|---|
| **Bảng EPS của Apple (`0000320193_0000320193-24-000123_chunk_0079`)** | Bảng bị làm phẳng bằng `\|`, dễ bị cắt ngang giữa chừng làm mất tiêu đề cột năm (`2024 \| 2023 \| 2022`) và mất đơn vị. Metadata chỉ có `fiscal_period: "FY2024"`, nên lọc theo năm `2022` sẽ bỏ sót bảng này. | Mỗi dòng tự chứa đủ ngữ cảnh + đơn vị:<br>`Net income: 2024 = $93,736; 2023 = $96,995; 2022 = $99,803. Unit: millions of USD.`<br>`Weighted-average diluted shares: 2024 = 15,408,095; 2023 = 15,812,547; 2022 = 16,325,819. Unit: thousands of shares.`<br>`Diluted earnings per share: 2024 = $6.08; 2023 = $6.13; 2022 = $6.11. Unit: USD per share.`<br>Metadata Qdrant có thêm `fact_years: [2022, 2023, 2024]`. |
| **Bảng báo cáo quý NVIDIA (`0001045810_0001045810-25-000230_chunk_0002`)** | Dễ gắn nhầm một đơn vị chung cho cả bảng (lẫn triệu USD với USD/cổ phiếu). | Từng dòng tự tách đúng đơn vị:<br>`Net income: Three Months Ended Oct 26, 2025 = $31,910; ... Unit: millions of USD.`<br>`Diluted earnings per share: Three Months Ended Oct 26, 2025 = $1.30; ... Unit: USD per share.`<br>Metadata có `fiscal_period: "Q-2025-11"` và `fact_years: [2024, 2025]`. |

---

## 6. Hạn chế còn lại và việc cần phối hợp khi gộp

### 6.1. Khó khăn trong quá trình thực hiện và sửa lỗi
- **Định dạng HTML/iXBRL SEC EDGAR không đồng nhất giữa 13 công ty:** Báo cáo `10-K`/`10-Q` (Mỹ) và `20-F`/`6-K` (nước ngoài như `VFS`, `TSM`) dùng dấu nháy cong (`’`), khoảng trắng không ngắt (`\xa0`, `\u200b`), tiêu đề bảng nhiều tầng `colspan`, và cách ghi đơn vị khác nhau (`VND`, `NT$`, hoặc banner đầu mục).
- **Giới hạn 512 token của BGE và chi phí re-index trên CPU:** Ép trần 480 token theo tokenizer thật làm số chunk tăng (`13.137 → 14.022`), tốn nhiều thời gian sinh vector lại trên CPU.
- **Đánh đổi giữa `Row-to-Text` và BM25 thuần:** Lặp lại `Table context:` và `Unit:` ở mỗi dòng giúp mô hình ngữ nghĩa và trích xuất hiểu đúng số liệu, nhưng làm tăng độ dài câu và pha loãng trọng số từ khóa của BM25 thuần (đồng thời phải thêm luật phạt dòng `Table context:` trong `extractor.py`).
- **Môi trường Windows & đóng băng dữ liệu nhóm:** Phải xử lý lỗi trễ IPv6 `localhost` trên Windows, lỗi thiếu `git` trên `PATH`, và tuân thủ quy định không re-index lại lên `team_docs_final` để bảo toàn `chunk_id` cho công tác chấm nhãn chung.

### 6.2. Các điểm sai phát hiện trong quá trình kiểm thử trên `team_docs_final` (giữ nguyên để bảo toàn 603 dòng nhãn)

> **Quyết định của nhóm:** Để giữ nguyên `chunk_id` cho **603 dòng nhãn** mà cả nhóm đang chấm trên Google Sheets và tránh phải chạy lại `index` mất thời gian, nhóm thống nhất **chốt dữ liệu `team_docs_final` (14.022 chunk) như hiện tại và KHÔNG sửa code bước tách mục/re-index lại**, mà ghi nhận trung thực các điểm sai phát hiện được vào mục Hạn chế dưới đây:

1. **Lỗi nhãn mục (`section`) có sẵn từ repo gốc của tác giả (bước tách mục, không phải lỗi do bước cắt chunk của Part 1):**

   | Lỗi phát hiện khi kiểm thử | Bộ cuối (`team_docs_final`) | Bộ cũ (trước Part 1) | Nguyên nhân & ghi chú |
   |---|---|---|---|
   | Chunk mang nhãn `"Full Filing Narrative"` (`AMZN`, `INTC`, `TSM`) | `3.225` | `3.336` | `TSM` là mẫu `20-F` đánh số mục khác hẳn `10-K` (ví dụ rủi ro nằm ở `Item 3D`), bộ tách chỉ nhận diện chuẩn mẫu `10-K` nên không tách được. |
   | `JPM` mang nhãn `"Item 15"` | `2.268 / 2.614 (87%)` | `2.103 / 2.412 (87%)` | Không hoàn toàn là lỗi code: `JPM` đặt gần như toàn bộ nội dung báo cáo thường niên vào phụ lục `Item 15`. |
   | Nhầm `Item 5` với `Item 7` (`10-K`) | `430` (`Item 5`) vs. `195` (`Item 7`) | — | **`285 / 430` chunk** gắn nhãn `"Item 5"` thực chất có nội dung phân tích kết quả kinh doanh (`"increased"`, `"compared with"`), vốn thuộc `Item 7`. |

   - **Mức độ ảnh hưởng:** Nội dung văn bản trong từng chunk vẫn đúng nên **tìm kiếm thông thường không bị ảnh hưởng**. Chỉ bị sót khi lọc cứng theo mục (ví dụ `--section "Item 1A"` sẽ bỏ sót phần rủi ro của `AMZN`, `INTC`, `TSM`, `JPM`).

2. **Đơn vị bảng còn ra `unknown unit` ở `VFS`, `LLY`, `TSM`:** Do parser chỉ quét cục bộ quanh bảng và chủ yếu nhận diện các mẫu tiếng Anh chuẩn kiểu USD (`in millions`, `in thousands`, `per share`), chưa bao quát hết các bảng ngoại tệ (`VND`, `NT$`) hoặc ghi chú đơn vị đặt ở đầu mục.
3. **Bảng đa chiều đọc nhầm cột (ví dụ bảng doanh thu Mounjaro của Eli Lilly):** Các bảng vừa chia theo năm vừa chia cột theo khu vực địa lý (**Mỹ / ngoài Mỹ**) bị ghép nhầm tiêu đề cột thành năm.
4. **BM25 MRR giảm nhẹ (`0,928 → 0,893`):** Là sự đánh đổi khi mở rộng bảng thành câu văn đầy đủ ngữ cảnh và lặp `Unit:` làm loãng trọng số từ khóa của BM25 thuần (trong khi giúp giảm trùng lặp `dup@5` và hỗ trợ Dense/Hybrid/Reranker).

### 6.3. Phối hợp khi gộp (`integration`)
- Giữ nguyên `team_docs_final` (14.022 chunk) trong giai đoạn chấm nhãn và đánh giá chung hiện tại để đồng bộ số liệu với Part 2, 3, 4.
- Các điểm hạn chế trên sẽ là hướng cải tiến cho phiên bản sau nếu nhóm thực hiện một đợt `index --recreate` mới sau khi hoàn thành BTL.
