# Báo cáo Phần 4 — Reranking và trích xuất đáp án

**Người làm:** Thanh Tùng  
**Nhánh:** `part4`  
**Dữ liệu dùng để kiểm tra:** `team_docs`, 13 công ty, 56 hồ sơ, 13.137 chunk.  
**Commit của bộ dữ liệu đã sửa nhãn năm:** `fb63299`. Các sửa đổi sau đó được kiểm tra trên bản làm việc local.

## 1. Điểm yếu đã xử lý

| Điểm yếu | Biểu hiện trước khi sửa |
|---|---|
| 4.1 — Xếp hạng theo kỳ báo cáo | Đoạn từ 10-Q có thể đứng trên đúng báo cáo năm. Câu hỏi riêng quý cần phân biệt với cột lũy kế. |
| 4.2 — Chọn bằng chứng và confidence | Đoạn chứa số có thể thiếu tiêu đề cột để xác minh năm. Confidence dựa nhiều vào trùng từ nên có thể chấm thấp cả đoạn phù hợp. |
| 4.3 — Trích dòng, cột và đơn vị | Web có thể trả cả bảng hoặc lẫn basic EPS với diluted EPS, doanh thu hợp nhất với doanh thu khu vực, xe điện với xe máy điện. |

## 2. Thay đổi trong code

| File | Thay đổi |
|---|---|
| `src/hybrid_search/retrieval/reranker.py` | Dùng cross-encoder, xét kỳ báo cáo và ưu tiên ứng viên có giá trị đã xác nhận trước khi lấy Top K. Cấu hình batch qua `HYBRID_RERANK_BATCH_SIZE`, mặc định 2. |
| `src/hybrid_search/retrieval/engine.py` | Tìm thêm bằng BM25 khi ứng viên của dạng câu hỏi đã hỗ trợ thiếu dòng hoặc tiêu đề cột cần thiết. |
| `src/hybrid_search/retrieval/extractor.py` | Chọn dòng và cột tương ứng cho các ca Apple, JPMorgan và Eli Lilly đã kiểm tra. Với VinFast, đối chiếu loại xe, bên nhận và ngày trong cùng câu nguồn. Sửa cách in đơn vị tiền và số cổ phiếu. |
| `src/hybrid_search/api.py` | Hiện đáp án đủ ngưỡng confidence từ các kết quả truy xuất. Ngưỡng hiện tại là 0,30. |
| `tests/unit/test_answer_evidence.py` | Kiểm tra ca trả đúng và các ca thiếu tiêu đề cột, nhầm kỳ hoặc nhầm chỉ tiêu. |

Method được đánh giá là `rerank` trên hai checkout riêng để mỗi nhánh chạy đúng phiên bản code của mình.

## 3. Cách kiểm tra lại

Chạy các test liên quan từ checkout `part4` đã cài dependencies.

```powershell
python -m pytest -q tests/unit/test_answer_evidence.py tests/unit/test_team_eval.py tests/unit/test_edgar_client.py
```

Khi nhóm đã chốt nhãn, đặt `$queries`, `$labels` và `$results` thành đường dẫn tuyệt đối dùng chung. Hai checkout cần kết nối tới cùng Qdrant `team_docs` và dùng cùng cấu hình đánh giá.

```powershell
# Trong checkout main
python scripts/team/evaluate.py --tag baseline --methods rerank --split dev --queries $queries --labels $labels --out-dir $results

# Trong checkout part4
python scripts/team/evaluate.py --tag part4 --methods rerank --split dev --queries $queries --labels $labels --out-dir $results

# Từ checkout part4
python scripts/team/compare.py baseline part4 --method rerank --results-dir $results
```

## 4. Kết quả

**Kiểm tra tự động:** 25 test liên quan đã đạt. **Benchmark xếp hạng trước/sau:** chờ file nhãn chung. Bản câu hỏi hiện có 24 câu, gồm 6 dev và 18 test. MRR, nDCG và Recall được điền sau khi chạy với nhãn đã thống nhất.

### Độ trễ cross-encoder

Mỗi cấu hình được đo 12 lượt sau làm nóng trên bốn câu AAPL, JPM, LLY và VFS, với 20 đoạn cố định mỗi câu. Thời gian trong bảng là thời gian chấm điểm của cross-encoder.

| Batch size | p50 (ms) | p95 (ms) | Thứ tự Top 5 trùng với batch 2 |
|---:|---:|---:|---:|
| 2 | 6.681,73 | 8.456,07 | 12/12 |
| 8 | 6.768,85 | 8.259,69 | 12/12 |
| 16 | 6.801,66 | 8.238,39 | 12/12 |

Giữ batch 2 cho demo vì có độ trễ trung vị thấp nhất trong phép thử. Batch 16 có p95 thấp hơn khoảng 218 ms. Số đo gốc nằm ở [rerank_batches.json](../../evaluation/team/results/rerank_batches.json).

## 5. Demo

Các ca dưới đây đã được xác nhận trên web hoặc API. Cột trước ghi kết quả quan sát trong quá trình sửa từng mục. Bảng benchmark ở mục 4 sẽ dùng checkout `main` làm baseline.

| Câu thử | Trước | Sau |
|---|---|---|
| Apple Services net sales FY2024 | Đoạn chứa giá trị đúng kèm nhiều chỉ tiêu và năm. | **96.169 triệu USD**, Apple 10-K FY2024. |
| Apple Products gross margin FY2025 và Q3 FY2025 | Trả nhiều tỷ lệ trong bảng. | **36,8%** cả năm và **34,5%** riêng quý III, từ đúng 10-K và 10-Q. |
| JPMorgan basic EPS FY2024 | Đoạn trích có cả basic và diluted EPS. | **19,79 USD/cổ phiếu**, JPMorgan 10-K FY2024. |
| Eli Lilly tổng doanh thu FY2024 | Đoạn trích có doanh thu Mỹ nhưng thiếu tổng doanh thu. | **45.042,7 triệu USD**, Eli Lilly 10-K FY2024. |
| VinFast giao EV cho GSM đến 31/12/2024 | Đoạn trích có số EV và số xe máy điện. | **Khoảng 46.500 EV**, VinFast 20-F FY2024. |

## 6. Hạn chế và việc còn lại

Các quy tắc trích số đã được kiểm tra trên các dạng câu và cấu trúc báo cáo nêu trên. Confidence hiển thị là điểm của hệ thống. Bảng chấm theo nhãn đo chất lượng xếp hạng đoạn, còn tính đúng của số được đối chiếu riêng bằng các ca demo.

Cần bổ sung bảng benchmark có nhãn, ảnh demo gốc và mã commit cuối trước khi chốt bản nộp.
