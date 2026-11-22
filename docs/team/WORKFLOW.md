# Quy trình làm việc của nhóm Topic 3

Repo này là bản sao của `satyam671/financial-hybrid-search-qdrant` (commit 16682dd), cộng thêm một số sửa tối thiểu để chạy được và bộ công cụ chấm điểm chung của nhóm.

## 1. Repo này khác repo gốc ở đâu

| Thay đổi | File | Lý do |
|---|---|---|
| Thêm `fastapi`, `uvicorn` vào dependencies | `pyproject.toml` | Repo gốc thiếu, `serve` và test API bị lỗi |
| Web đọc `config/default.yaml` | `src/hybrid_search/api.py` | Bản gốc dùng `AppConfig()` mặc định. Phần 2 đổi model trong YAML thì web vẫn dùng model cũ |
| Số chunk hiển thị là số thật | `src/hybrid_search/api.py` | Bản gốc ép tối thiểu 8.609 |
| Danh sách công ty trên web lấy từ config | `src/hybrid_search/api.py` | Bản gốc viết cứng 10 mã |
| Mở rộng dữ liệu: 10 công ty gốc + VinFast, Eli Lilly, JPMorgan | `config/companies.yaml` | Giữ 10 công ty để so được với bài báo; thêm 3 ngành mới vì thầy muốn dữ liệu khác AAPL, NVDA |
| Biến môi trường `HYBRID_COMPANIES_FILE`, `QDRANT_COLLECTION` | `src/hybrid_search/config.py` | Thử nhanh trên ít công ty, collection riêng, không phải sửa file chung |
| Collection Qdrant tên `team_docs` | `config/default.yaml` | Không đè lên collection `financial_docs` của bản gốc nếu dùng chung Qdrant |
| Bộ chấm điểm chung | `scripts/team/`, `evaluation/team/`, `src/hybrid_search/evaluation/team_metrics.py` | Benchmark gốc chấm bằng khớp từ khóa nên thiên vị BM25 |

Các lỗi thuộc 4 phần (IDF của SPLADE, reranker giả, v.v.) **chưa sửa** ở nhánh `main`. Đó là việc của từng người.

## 2. Cài đặt (mỗi người làm một lần)

Đặt repo ở đường dẫn không dấu, không dấu cách, ví dụ `F:\topic3-team`.

```powershell
cd F:\topic3-team
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
$env:EDGAR_USER_AGENT = "TenNhom-Topic3 email_that@gmail.com"
```

Qdrant: chỉ chạy **một** container. Nếu đang chạy Qdrant của repo gốc thì dừng nó trước (`docker compose stop` trong folder cũ), rồi:

```powershell
docker compose up -d
python -m hybrid_search.cli ingest
python -m hybrid_search.cli index --recreate
python -m hybrid_search.cli info
pytest -q tests/unit
```

Ghi lại số chunk mà `info` in ra. Cả nhóm phải ra cùng một số; nếu lệch là dữ liệu tải về khác nhau.

### 2.1. Chỉ một người index đủ, cả nhóm dùng chung

Index đủ 13 công ty rất lâu trên CPU. Không ai cần tự làm lại:

1. Người có máy mạnh nhất chạy `ingest` và `index --recreate` (để qua đêm cũng được).
   Nếu máy đã có dữ liệu của repo gốc, chép `data/raw/edgar` từ folder cũ sang trước: file đã tải sẽ không tải lại.
2. Xong thì `docker compose stop`, nén hai thư mục `qdrant_storage` và `data/processed`, gửi lên Drive.
3. Người khác giải nén vào đúng chỗ trong `F:\topic3-team`, chạy `docker compose up -d`, rồi `python -m hybrid_search.cli info` để kiểm tra đúng số chunk.

Cả nhóm dùng cùng image `qdrant/qdrant:v1.14.0` nên chép thư mục là dùng được.

### 2.2. Thử nhanh trên dữ liệu nhỏ (Phần 1, Phần 2)

Phần nào phải index lại thì thử trên 3 công ty mới, collection riêng, để không đè bản chung:

```powershell
$env:HYBRID_COMPANIES_FILE = "config/companies_new3.yaml"
$env:QDRANT_COLLECTION = "team_docs_part2"
python -m hybrid_search.cli ingest
python -m hybrid_search.cli index --recreate
```

Hai biến này chỉ sống trong cửa sổ terminal hiện tại. Mở terminal mới là quay về bản chung `team_docs`. Lưu ý `ingest` ghi đè `data/processed/`, nên trước khi thử nhỏ hãy sao lưu `data/processed` của bản chung. Khi so sánh, baseline và bản sửa phải chạy trên **cùng** bộ dữ liệu (cùng nhỏ hoặc cùng đủ).

## 3. Nhánh và phạm vi sửa

```
main      bản gốc + sửa tối thiểu + bộ chấm điểm. Không ai push thẳng vào main.
part1     Dữ liệu, chia đoạn, gắn nhãn
part2     BM25 / Dense / SPLADE
part3     Hybrid, RRF, lọc metadata, hiểu câu hỏi
part4     Vòng 2: reranker, confidence, đọc bảng
team      nhánh gộp, tạo ở buổi họp gộp
```

```powershell
git checkout main
git pull
git checkout -b part2
```

File nhiều phần cùng đụng tới. Ai cần sửa thì báo nhóm trước và ghi vào báo cáo:

| File | Phần hay sửa |
|---|---|
| `src/hybrid_search/indexing/qdrant_index.py` | 1, 2 |
| `config/default.yaml` | 2, 3 |
| `src/hybrid_search/retrieval/engine.py` | 3, 4 |
| `src/hybrid_search/chunking/chunker.py` | 1 |

Mẹo để gộp dễ: thêm cách tìm mới dưới **tên mới** thay vì sửa cách cũ. Ví dụ Phần 3 thêm method `bm25_dense_weighted` vào `engine.py`, Phần 4 thêm `rerank_ce`. Như vậy một lần chạy có cả bản gốc lẫn bản cải tiến để so.

## 4. Bộ chấm điểm chung

### 4.1. Bộ câu hỏi: `evaluation/team/queries.yaml`

Bản nháp có 24 câu, chưa kiểm tra trong báo cáo thật. Việc đầu tiên của cả nhóm: đọc lướt báo cáo của 3 công ty, sửa hoặc thay những câu không có đáp án, rồi mở rộng lên khoảng 100 câu. Khoảng 30% gắn `split: dev`, còn lại `split: test`.

### 4.2. Gom ứng viên và gán nhãn

```powershell
python scripts/team/pool.py
```

Script chạy mọi cách tìm, lấy top 20 mỗi cách, ghi vào `evaluation/team/labels.csv`. Mở file bằng Excel. Hai người chấm **độc lập** vào cột `label_A` và `label_B` theo hướng dẫn trong `docs/team/LABELING.md`. Sau đó:

```powershell
python scripts/team/agreement.py
```

Script tính Cohen's kappa, điền cột `label` cho các dòng hai người giống nhau và liệt kê các dòng lệch để cả nhóm thống nhất.

Khi một phần thêm cách tìm mới, chạy lại `pool.py`. Nhãn cũ được giữ, chỉ thêm dòng mới cần chấm.

### 4.3. Chấm điểm

```powershell
python scripts/team/evaluate.py --tag baseline
python scripts/team/evaluate.py --tag part2 --split dev
python scripts/team/compare.py baseline part2
```

Kết quả nằm ở `evaluation/team/results/<tag>.json` và `<tag>.md`. Script không cho ghi đè tag đã có, trừ khi thêm `--force`.

| Chỉ số | Ý nghĩa |
|---|---|
| `mrr` | Đoạn đúng đầu tiên ở hạng mấy (1,0 là hạng 1) |
| `ndcg@10` | Thứ tự top 10 có hợp lý không, có tính mức 1 và 2 |
| `recall@10` | Trong mọi đoạn đúng đã chấm, bao nhiêu đoạn lọt top 10 |
| `p@10` | Trong top 10, bao nhiêu đoạn đúng |
| `company@5` | Trong top 5, bao nhiêu kết quả đúng công ty (chỉ tính câu có `expected_tickers`) |
| `dup@5` | Trong top 5, bao nhiêu kết quả gần trùng với kết quả xếp trên nó |
| `unjudged@10` | Trong top 10, bao nhiêu đoạn chưa ai chấm. Trên 0,2 thì nên pool và chấm thêm |

Quy tắc:
- Chỉnh tham số chỉ dựa trên `--split dev`. Chạy `--split test` một lần cho bản cuối.
- So sánh hai cấu hình phải cùng máy, cùng số chunk, cùng bộ câu hỏi. `compare.py` sẽ cảnh báo nếu số câu khác nhau.
- Lệnh benchmark gốc (`cli benchmark`) nếu có chạy thì luôn thêm `-o`, không ghi đè `data/benchmark_report.md`.

## 5. Các giai đoạn

**Giai đoạn 0 (cả nhóm):** cài đặt, index, kiểm tra cùng số chunk, chốt bộ câu hỏi, chấm nhãn, chạy `evaluate.py --tag baseline`.

**Giai đoạn 1 (từng người):** làm trên nhánh của mình. Chạy `evaluate.py --tag partN` trên cùng máy với baseline của mình. Nộp báo cáo theo `docs/team/REPORT_TEMPLATE.md`.

**Giai đoạn 2 (buổi họp gộp):**
1. Tạo nhánh `team` từ `main`.
2. Gộp theo thứ tự **part2, part1, part3, part4**. Phần 1 và 2 cùng đổi cách index, nên gộp xong hai phần này mới `index --recreate` một lần.
3. Sau mỗi lần gộp: `pytest -q tests/unit` rồi `evaluate.py --tag team-upto-partN --split dev`. Điểm giảm ở bước nào là biết phần nào gây ra.
4. Chạy bản đủ 4 phần: `--tag team`.
5. Chạy bỏ từng phần (ablation): `team-no-part1`, `team-no-part2`, ...

**Giai đoạn 3:** chạy `--split test` cho `baseline` và `team`, gộp bảng bằng `compare.py`, đưa vào slide.
