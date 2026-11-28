# Báo cáo Phần 4 — Reranking và trích xuất đáp án

**Người làm:** Thanh Tùng  
**Nhánh sửa bằng chứng:** `fix/part4-period-evidence`  
**Dữ liệu đánh giá chung:** `team_docs_final`, 13 công ty, 14.022 chunk.  
**Lịch sử:** các kiểm tra ban đầu dùng `team_docs` với 13.137 chunk, mốc sửa nhãn năm `fb63299`; số liệu đánh giá chung tại mục 4 dùng bộ cuối.

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

Để đo riêng trước/sau một bản sửa, đặt `$queries`, `$labels` và `$results` thành đường dẫn tuyệt đối dùng chung. Hai checkout cần kết nối tới cùng Qdrant `team_docs_final` và dùng cùng cấu hình đánh giá. Các lệnh dưới đây là hướng dẫn đo riêng trên split dev, không phải nguồn của bảng `split=all` tại mục 4.

```powershell
# Trong checkout main
python scripts/team/evaluate.py --tag baseline --methods rerank --split dev --queries $queries --labels $labels --out-dir $results

# Trong checkout part4
python scripts/team/evaluate.py --tag part4 --methods rerank --split dev --queries $queries --labels $labels --out-dir $results

# Từ checkout part4
python scripts/team/compare.py baseline part4 --method rerank --results-dir $results
```

## 4. Kết quả

**Benchmark theo nhãn chung:** kết quả trong [team.md](../../evaluation/team/results/team.md), chạy trên toàn bộ 24 câu hỏi (`split=all`) và collection `team_docs_final` gồm 14.022 chunk.

| Cấu hình | MRR | NDCG@10 | Recall@10 | company@5 | p50 (ms) | p95 (ms) |
|---|---:|---:|---:|---:|---:|---:|
| Nguồn ứng viên `sparse_dense` | 0,921 | 0,739 | 0,547 | 0,852 | 811,6 | 1.111,4 |
| `rerank` | 0,939 | 0,726 | 0,547 | 0,870 | 8.981,4 | 10.161,5 |

So với nguồn ứng viên, rerank tăng MRR từ 0,921 lên 0,939 và company@5 từ 0,852 lên 0,870 (cao nhất trong các cấu hình của bảng); Recall@10 giữ nguyên ở độ chính xác ba chữ số thập phân, còn NDCG@10 giảm từ 0,739 xuống 0,726. Vì vậy không kết luận rerank tốt hơn trên mọi chỉ số. Đây là so sánh hai cấu hình trong lần đánh giá chung, không phải phép đo trước/sau riêng cho bản sửa bằng chứng kỳ báo cáo.

Độ trễ p50 của rerank trên máy chạy `team.md` khoảng 9 giây/câu. Theo kết quả chạy lại mà nhóm tổng hợp, máy Huy và Tùng khoảng 2,5–2,8 giây/câu; thời gian phụ thuộc máy và môi trường chạy. Không thay số đo của `team.md` bằng số của máy khác. Các số liệu benchmark này không phải kết quả chạy mới sau các commit sửa câu hỏi ngắn.

**Sửa câu hỏi ngắn:** commit `fa1be10` bổ sung tên ngắn và alias công ty trong `metric_request()` để hỗ trợ các câu như `JPMorgan basic EPS FY2024`, `Apple Services net sales FY2024`, `Eli Lilly total revenue FY2024` và `NVIDIA basic weighted average shares FY2025`. Commit `3718c17` bỏ việc tự xóa từ đầu tên công ty, nhằm giữ phạm vi như `Taiwan` trong câu hỏi `TSMC Taiwan revenue FY2024`. Cần phân biệt kiểm tra hồi quy các trường hợp này với benchmark chung ở trên.

### Phép đo cross-encoder ban đầu (20 đoạn, trước tối ưu top 10 / 256 token)

Mỗi cấu hình được đo 12 lượt sau làm nóng trên bốn câu AAPL, JPM, LLY và VFS, với 20 đoạn cố định mỗi câu. Thời gian trong bảng là thời gian chấm điểm của cross-encoder.

| Batch size | p50 (ms) | p95 (ms) | Thứ tự Top 5 trùng với batch 2 |
|---:|---:|---:|---:|
| 2 | 6.681,73 | 8.456,07 | 12/12 |
| 8 | 6.768,85 | 8.259,69 | 12/12 |
| 16 | 6.801,66 | 8.238,39 | 12/12 |

Trong phép thử ban đầu, batch 2 có độ trễ trung vị thấp nhất; batch 16 có p95 thấp hơn khoảng 218 ms. Số đo gốc nằm ở [rerank_batches.json](../../evaluation/team/results/rerank_batches.json). Đây là thời gian riêng của cross-encoder với 20 đoạn, không phải độ trễ toàn câu của cấu hình demo đã tối ưu rerank top 10 và giới hạn mỗi đoạn khoảng 256 token.

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

Bảng benchmark có nhãn đã được bổ sung tại mục 4. Khi chốt bản nộp, cần đối chiếu ảnh demo và mã commit được nhóm sử dụng; chạy lại đánh giá nếu muốn báo cáo tác động của bản sửa bằng chứng mới lên các chỉ số xếp hạng.
