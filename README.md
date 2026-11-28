# Hybrid Search for Financial Intelligence (Qdrant), nhóm Topic 3

Bài tập nhóm môn Phân tích dữ liệu tài chính, Topic 3. Nhóm lấy repo mã nguồn mở [satyam671/financial-hybrid-search-qdrant](https://github.com/satyam671/financial-hybrid-search-qdrant) (README gốc: [docs/UPSTREAM_README.md](docs/UPSTREAM_README.md)), kiểm tra lại, sửa lỗi, mở rộng dữ liệu và tự xây bộ đánh giá có gán nhãn tay.

Bài toán: chuyên viên phân tích cần tìm nhanh đúng đoạn trong báo cáo SEC (10-K, 10-Q, 20-F). Câu hỏi có khi là mã số hay tên riêng (tìm theo từ khóa làm tốt), có khi là ý diễn đạt khác chữ (tìm theo nghĩa làm tốt). Hybrid search kết hợp cả hai trong một collection Qdrant. Mọi mô hình chạy trên CPU, không dùng API trả phí.

## Thành viên và phần việc

| Phần | Người làm | Nội dung | Tài liệu |
|---|---|---|---|
| 1. Dữ liệu và chia đoạn | Bình | Đếm token thật, trần 480 token, đổi bảng thành câu (row-to-text), gắn năm cho số liệu | [docs/team/Hanchepart1.md](docs/team/Hanchepart1.md) |
| 2. Vector BM25 / Dense / SPLADE | Huy Hoàng | Bỏ IDF thừa của SPLADE, kiểm tra BM25, thử bge-base, phát hiện lỗi vector Dense bằng 0 | [docs/team/part2/00_MUC_LUC.md](docs/team/part2/00_MUC_LUC.md) |
| 3. Hiểu câu hỏi, RRF có trọng số, lọc trùng | Trần Hoàng (nhóm trưởng) | Nhận diện công ty và đối thủ trong câu hỏi, RRF có trọng số theo loại câu hỏi, lọc đoạn trùng nội dung | [docs/team/PART3.md](docs/team/PART3.md) |
| 4. Xếp hạng lại và đọc bảng | Tùng | Cross-encoder rerank (top 10, cắt 256 token), trích con số từ bảng, đóng gói bộ dữ liệu cuối | [docs/team/REPORT_PART4.md](docs/team/REPORT_PART4.md) |

## Dữ liệu

- 13 công ty: 10 công ty của repo gốc (NVDA, AAPL, MSFT, GOOGL, AMZN, META, TSLA, AMD, INTC, TSM) cộng 3 ngành mới là VinFast (VFS), Eli Lilly (LLY), JPMorgan (JPM). Danh sách trong `config/companies.yaml`.
- 56 báo cáo, 14.022 chunk, collection Qdrant `team_docs_final`.
- Ba vector trên mỗi chunk: `bm25` (Qdrant/bm25), `dense` (BAAI/bge-small-en-v1.5, 384 chiều), `sparse` (SPLADE prithivida/Splade_PP_en_v1).

## Cài đặt và chạy

Cần Python 3.10 trở lên và Docker. Đặt repo ở đường dẫn không dấu, ví dụ `F:\topic3-team`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### Nạp bộ dữ liệu cuối

Tính lại vector cho 14.022 chunk trên CPU mất nhiều giờ, nên nhóm dùng chung một bản đã index sẵn: `team13-final.zip` (gồm `qdrant_storage/` và `data/processed/`). Giải nén vào thư mục repo rồi chép `qdrant_storage` vào một Docker volume:

```powershell
docker volume create qdrant_vol
docker run --rm -v qdrant_vol:/dst -v "${PWD}\qdrant_storage:/src" alpine sh -c "cp -a /src/. /dst/"
docker compose up -d
```

Phải dùng Docker volume. Nếu gắn thẳng thư mục Windows vào container, nhóm đã gặp trường hợp vector Dense bị ghi thành toàn số 0 (xem phần Kết quả).

Kiểm tra dữ liệu trước khi đo:

```powershell
python scripts/team/check_dense.py
```

Lệnh phải in OK, đủ 14022 point, không có vector Dense nào bằng 0.

### Đánh giá

```powershell
python scripts/team/evaluate.py --tag <ten-lan-chay>
```

Lệnh chạy 24 câu hỏi qua 9 cấu hình và ghi `evaluation/team/results/<tag>.md` và `.json`. Kết quả chính thức của nhóm là [evaluation/team/results/team.md](evaluation/team/results/team.md).

### Demo

```powershell
python -m hybrid_search.cli serve --port 8000
```

Mở `http://127.0.0.1:8000`, chọn cấu hình (BM25, Dense, SPLADE, các bản hybrid, Rerank, Smart Hybrid) rồi gõ câu hỏi. Tab Benchmark hiển thị kết quả chính thức đọc từ `evaluation/team/results/team.json`. Tìm bằng dòng lệnh:

```powershell
python -m hybrid_search.cli search "Mounjaro revenue in 2024" --method hybrid_plus -k 5
```

### Unit test

```powershell
pytest -q tests/unit
```

## Bộ đánh giá của nhóm

Benchmark gốc chấm bằng khớp từ khóa nên thiên vị BM25. Nhóm tự làm bộ đánh giá riêng:

- 24 câu hỏi về 3 công ty mới, chia 7 nhóm: company, exact_code, hybrid, long, numeric_year, rare_term, semantic.
- Gộp top 10 của các cấu hình thành 603 cặp câu hỏi và đoạn, mỗi cặp do 2 người chấm độc lập theo thang 0/1/2 ([docs/team/LABELING.md](docs/team/LABELING.md)).
- Độ đồng thuận Cohen's kappa 0,681 (hai cặp chấm: 0,703 và 0,654). 477 cặp hai người chấm giống nhau. 126 cặp lệch nhau được nhóm ủy quyền cho AI (Claude) phân xử, luôn chọn một trong hai nhãn đã chấm, theo LABELING.md; cột `note` đánh dấu các cặp này. Nhãn A của nhóm trưởng cũng do AI gợi ý trước rồi người duyệt.
- Chỉ số: MRR, NDCG@10, Recall@10, P@10, company@5 (tỉ lệ kết quả đúng công ty), dup@5 (tỉ lệ đoạn trùng nội dung trong top 5), unjudged@10 (tỉ lệ đoạn chưa được chấm).

## Kết quả

Trên `team_docs_final`, 24 câu, `unjudged@10 = 0` ở mọi cấu hình:

| Cấu hình | MRR | NDCG@10 | company@5 | dup@5 |
|---|---|---|---|---|
| bm25 | 0,823 | 0,617 | 0,817 | 0,075 |
| dense | 0,824 | 0,607 | 0,800 | 0,050 |
| bm25_dense (RRF) | 0,853 | 0,659 | 0,835 | 0,033 |
| sparse (SPLADE) | 0,944 | 0,742 | 0,861 | 0,033 |
| sparse_dense (RRF) | 0,921 | 0,739 | 0,852 | 0,017 |
| rerank | 0,939 | 0,726 | 0,870 | 0,033 |
| hybrid_qp | 0,832 | 0,667 | 0,826 | 0,042 |
| hybrid_qp_w | 0,917 | 0,699 | 0,843 | 0,033 |
| hybrid_plus | 0,920 | 0,631 | 0,843 | 0,000 |

Nhận xét chính:

- SPLADE có MRR và NDCG cao nhất, mạnh nhất ở câu hỏi số liệu theo năm (NDCG 0,761, trong khi Dense chỉ đạt 0,156).
- Rerank có company@5 cao nhất (0,870). Thời gian trung vị 2,5 đến 9 giây mỗi câu tùy máy.
- Phần 3: RRF có trọng số (hybrid_qp_w) tốt hơn bm25_dense ở NDCG trên 14/24 câu. Với 24 câu, khoảng tin cậy bootstrap 95% của mức tăng MRR (+0,063, khoảng [−0,040; +0,184], chạy bằng `scripts/team/bootstrap.py`) vẫn chứa 0, nên đây là xu hướng chứ chưa khẳng định được. Lọc trùng (hybrid_plus) đưa dup@5 về 0 nhưng làm giảm NDCG, vì đoạn lặp lại ở báo cáo các năm khác vẫn được tính là đúng.
- Lỗi đáng kể nhất nhóm phát hiện: trong một bộ dữ liệu trung gian, toàn bộ vector Dense bằng 0, nghi do gắn thẳng thư mục Windows vào Docker. Sau khi tính lại vector, Dense MRR trên benchmark gốc tăng từ 0,211 lên 0,827. `scripts/team/check_dense.py` được viết để bắt lỗi này.

**Chạy lại trên 4 máy.** Bốn thành viên chạy `evaluate.py` độc lập (3 máy Windows, 1 máy Linux). bm25, dense, sparse và hai cấu hình Phần 3 cho số khớp hoàn toàn. Các cấu hình có trộn kết quả lệch dưới 0,02 MRR và khoảng 0,01 NDCG, do tìm kiếm Dense gần đúng (HNSW) xếp các đoạn bằng điểm khác nhau giữa các máy.

## Hạn chế

- Chỉ có 24 câu hỏi, mỗi câu chiếm khoảng 0,04 MRR, nên chênh lệch nhỏ khó phân biệt với nhiễu.
- Bộ câu hỏi chỉ hỏi 3 công ty mới. 10 công ty gốc chỉ được đo bằng benchmark của tác giả.
- Chỉ những đoạn mà các cấu hình hiện có tìm ra mới được chấm. Phương pháp mới có thể tìm ra đoạn chưa ai chấm.
- Hạn chế của chia đoạn (nhãn mục sai, đơn vị "unknown unit", đọc nhầm cột bảng): xem [docs/team/Hanchepart1.md](docs/team/Hanchepart1.md).

## Thư mục của nhóm

- `scripts/team/`: `evaluate.py` (đo), `bootstrap.py` (khoảng tin cậy khi so hai cấu hình), `pool.py` (tạo danh sách cần chấm), `agreement.py` (kappa và gộp nhãn), `check_dense.py` (kiểm tra vector Dense)
- `evaluation/team/`: câu hỏi, `labels.csv` (603 nhãn), `results/` (kết quả từng lần chạy, xem `results/README.md`; kết quả cũ trên dữ liệu lỗi nằm ở `results/archive/`)
- `src/hybrid_search/retrieval/smart_hybrid.py`: Phần 3
- `docs/team/`: quy trình làm việc, quy tắc gán nhãn, báo cáo từng phần
