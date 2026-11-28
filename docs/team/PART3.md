# Phần 3: Hiểu câu hỏi, RRF có trọng số, lọc đoạn trùng

Người làm: Trần Hoàng (nhóm trưởng). Code: [`src/hybrid_search/retrieval/smart_hybrid.py`](../../src/hybrid_search/retrieval/smart_hybrid.py), [`query_parser.py`](../../src/hybrid_search/retrieval/query_parser.py). Cấu hình: mục `smart_hybrid` trong [`config/default.yaml`](../../config/default.yaml).

## 1. Điểm yếu của repo gốc

| Điểm yếu | Biểu hiện |
|---|---|
| Không hiểu tên công ty trong câu hỏi | Hỏi về JPMorgan nhưng top 5 lẫn đoạn của Intel, vì bộ lọc công ty chỉ có khi người dùng tự bấm trên web |
| RRF trong Qdrant không như tài liệu mô tả | ADR-006 ghi k=60, nhưng điểm Qdrant trả về là 1/(hạng+1) (hạng 1 = 0,5, hạng 2 = 0,333). Với k nhỏ như vậy, một đoạn đứng đầu ở một danh sách thắng đoạn đứng thứ 5 ở cả hai danh sách |
| Hai nhánh luôn nặng như nhau | Câu chứa mã (CET1, 340B) cần nghiêng về từ khóa, câu hỏi theo ý thì không |
| Top 5 lặp nội dung | Cùng một đoạn rủi ro chép lại ở báo cáo 2023 và 2024 chiếm 2 chỗ |

## 2. Ba cấu hình, mỗi cấu hình thêm một bước

| Cấu hình | Thêm gì |
|---|---|
| `hybrid_qp` | QueryParser nhận ra công ty và tên gọi khác, tự lọc theo công ty. Nếu tên đi sau "competition from", "versus", "than" thì coi là đối thủ, không lọc. Tên công ty trong câu được thay bằng "the company". Vẫn trộn bằng RRF của Qdrant |
| `hybrid_qp_w` | Tự trộn bằng RRF có trọng số với k=60. Câu có mã (chữ lẫn số) cho BM25 0,7 và Dense 0,3, các câu khác 0,5 và 0,5 |
| `hybrid_plus` | Bỏ đoạn gần trùng: cosine vector Dense ≥ 0,95, hoặc câu trả lời trích ra giống ≥ 0,85 (difflib) và dài ≥ 40 ký tự. Đoạn liền kề trong cùng báo cáo không bị bỏ |

Bản thử trọng số 0,3/0,7 cho câu hỏi theo ý đã bị bỏ. Khi hai danh sách không có đoạn chung, đoạn hạng 10 của nhánh nặng (0,7/70 = 0,0100) vẫn thắng đoạn hạng 1 của nhánh nhẹ (0,3/61 = 0,0049), nên nhánh nhẹ gần như bị bỏ hẳn.

## 3. Kết quả

Bộ 24 câu của nhóm, 603 nhãn, collection `team_docs_final` (14.022 chunk). Số lấy từ [`evaluation/team/results/team.md`](../../evaluation/team/results/team.md).

| Cấu hình | MRR | NDCG@10 | company@5 | dup@5 | p50 |
|---|---|---|---|---|---|
| bm25_dense (gốc) | 0,853 | 0,659 | 0,835 | 0,033 | 0,17 s |
| hybrid_qp | 0,832 | 0,667 | 0,826 | 0,042 | 0,19 s |
| hybrid_qp_w | 0,917 | 0,699 | 0,843 | 0,033 | 0,67 s |
| hybrid_plus | 0,920 | 0,631 | 0,843 | 0,000 | 1,34 s |
| sparse (tham khảo) | 0,944 | 0,742 | 0,861 | 0,033 | 0,35 s |

NDCG@10 theo nhóm câu, bm25_dense so với hybrid_qp_w: company 0,677 → 0,741; semantic 0,579 → 0,672; exact_code 0,738 → 0,766; numeric_year 0,395 → 0,411.

Ví dụ trong bộ 24 câu:

| Câu | bm25_dense | hybrid_qp_w |
|---|---|---|
| q016 "can the company keep operating without more money from its founder" (VFS) | MRR 0, NDCG 0 | MRR 1, NDCG 0,40 |
| q008 "Standardized CET1 capital ratio" (JPM) | NDCG 0,87 | NDCG 0,92 |
| q010 "how higher deposit costs could reduce the profit the bank makes on loans" (JPM) | NDCG 0,88 | NDCG 0,71 (kém đi) |

Câu q016 là câu hỏi 50/50, nên mức tăng ở đây đến từ cách trộn k=60, không phải từ trọng số.

## 4. Kiểm định

Bootstrap ghép cặp trên 24 câu, 10.000 lần lấy mẫu, seed 42. Chạy lại bằng `python scripts/team/bootstrap.py <A> <B>`.

| So sánh | Chỉ số | Chênh | Khoảng tin cậy 95% | Hơn / kém / hòa |
|---|---|---|---|---|
| hybrid_qp_w − bm25_dense | MRR | +0,063 | [−0,040; +0,184] | 4 / 2 / 18 |
| hybrid_qp_w − bm25_dense | NDCG@10 | +0,040 | [−0,000; +0,086] | 14 / 7 / 3 |
| hybrid_plus − hybrid_qp_w | NDCG@10 | −0,069 | [−0,124; −0,016] | 5 / 13 / 6 |
| hybrid_qp − bm25_dense | NDCG@10 | +0,008 | [−0,014; +0,030] | 7 / 5 / 12 |

Kết luận:

- hybrid_qp_w có xu hướng tốt hơn bản trộn gốc, nhưng khoảng tin cậy vẫn chứa 0 nên chưa khẳng định được. MRR hòa ở 18/24 câu vì cả hai bản đều đã đưa đoạn đúng lên hạng 1.
- Lọc công ty một mình (hybrid_qp) gần như không đổi kết quả. Mức tăng chủ yếu đến từ việc trộn lại với k=60.
- Lọc trùng làm NDCG giảm thật (khoảng tin cậy không chứa 0). Lý do: đoạn lặp lại ở báo cáo năm khác vẫn được chấm là liên quan. hybrid_plus hợp khi người đọc cần top 5 gồm 5 ý khác nhau, không hợp khi đo bằng NDCG.

Chạy lại trên 4 máy: hybrid_qp_w và hybrid_plus cho số khớp hoàn toàn. hybrid_qp lệch dưới 0,02 MRR do Qdrant xếp các đoạn bằng điểm khác nhau.

## 5. Hạn chế

- 24 câu, mỗi câu nặng khoảng 0,04 MRR, nên mức chênh nhỏ khó tách khỏi nhiễu.
- QueryParser chỉ lọc theo công ty, chưa lọc theo năm hay loại báo cáo. Nhóm câu numeric_year vẫn thấp (0,411), trong khi SPLADE đạt 0,761.
- Phần 3 mới được áp lên BM25 cộng Dense. Áp cùng lớp này lên SPLADE là hướng làm tiếp.
- Tự trộn ở ngoài Qdrant làm độ trễ tăng từ 0,17 s lên 0,67 s. Lọc trùng tăng lên 1,34 s vì phải lấy lại vector Dense.

## 6. Cách chạy

```powershell
python -m hybrid_search.cli search --query "JPMorgan CET1 capital ratio" --method hybrid_qp_w -k 5 -v
python scripts/team/evaluate.py --tag <ten> --methods bm25_dense hybrid_qp hybrid_qp_w hybrid_plus
python scripts/team/bootstrap.py hybrid_qp_w bm25_dense
```
