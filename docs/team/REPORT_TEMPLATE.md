# Báo cáo Phần N: <tên phần>

**Người làm:**
**Nhánh:** `partN`
**Commit cuối:**

## 1. Điểm yếu đã xử lý

| # | Điểm yếu | Bằng chứng (file, dòng, ảnh chụp) |
|---|---|---|
| 1 | | |
| 2 | | |
| 3 | | |

## 2. Đã sửa gì

| File | Thay đổi | Có đụng tới phần của người khác không |
|---|---|---|
| | | |

Tên cách tìm mới (nếu có), ví dụ `rerank_ce`:

## 3. Cách chạy lại

```powershell
git checkout partN
pip install -e ".[dev]"
python -m hybrid_search.cli index --recreate    # chỉ khi phần này đổi cách index
python scripts/team/evaluate.py --tag partN --split dev
```

## 4. Kết quả

Máy chạy (CPU, RAM):
Số chunk sau khi index:
Thời gian index (nếu có index lại):

Dán bảng từ `python scripts/team/compare.py baseline partN`:

| Tag | Method | mrr | ndcg@10 | recall@10 | p@10 | company@5 | dup@5 | unjudged@10 | p50 ms |
|---|---|---|---|---|---|---|---|---|---|
| baseline | | | | | | | | | |
| partN | | | | | | | | | |

Nhận xét: cải tiến tốt lên ở nhóm câu hỏi nào, xấu đi ở nhóm nào, vì sao.

## 5. Demo

2 đến 3 câu hỏi, mỗi câu có ảnh chụp kết quả trước và sau.

| Câu hỏi | Trước | Sau |
|---|---|---|
| | | |

## 6. Hạn chế còn lại và việc cần phối hợp khi gộp
