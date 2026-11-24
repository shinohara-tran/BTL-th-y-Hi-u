# Chỉ ra lỗi trong code gốc (Phần 2)

Code gốc chưa sửa, bản của tác giả ở commit `16682dd`, nằm tại:

`D:\PTTC\financial-hybrid-search-qdrant-main\financial-hybrid-search-qdrant-main\src\hybrid_search\`

Mở thư mục này trong VS Code. Với mỗi lỗi, mở đúng file, bấm **Ctrl+F** và dán chuỗi trong cột "Tìm".

---

## Lỗi 1: SPLADE bị tính độ hiếm hai lần

| | File | Tìm (Ctrl+F) | Dòng |
|---|---|---|---|
| Chỗ sai | `indexing\qdrant_index.py` | `modifier=models.Modifier.IDF` | 83 và **87** |

Ctrl+F tìm được **2 kết quả**. Kết quả thứ nhất (dòng 83) thuộc `"bm25"` và đúng. Kết quả thứ hai (dòng 87) thuộc `"sparse"` (SPLADE) và **sai**:

```python
"bm25": models.SparseVectorParams(
    modifier=models.Modifier.IDF,      # dòng 83: đúng
    ...
"sparse": models.SparseVectorParams(
    modifier=models.Modifier.IDF,      # dòng 87: SAI
```

**Bằng chứng 1: SPLADE đã tự tính trọng số.** Mở mã nguồn thư viện:

`<HOME>\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastembed\sparse\splade_pp.py`

Tìm `relu_log`, ở dòng 44:

```python
relu_log = np.log1p(np.maximum(output.model_output, 0))
```

Trọng số của SPLADE do mạng neural tính, rồi lấy `log(1 + relu)`. Lúc huấn luyện, mô hình đã học giảm điểm từ phổ biến và tăng điểm từ hiếm. Vì vậy vector SPLADE **đã chứa sẵn thông tin độ hiếm**.

**Bằng chứng 2: BM25 thì chưa có.** Trong `fastembed\sparse\bm25.py`, tìm `def _term_frequency` (dòng 331–359). Hàm này chỉ đếm số lần từ xuất hiện (`num_occurrences`) và không có IDF. Docstring ở dòng 83 ghi rõ IDF là phần nằm ngoài. Đó là lý do BM25 **cần** `Modifier.IDF`, để Qdrant nhân IDF vào.

**Kết luận:** tác giả chép nguyên cấu hình của BM25 sang SPLADE. SPLADE bị nhân thêm IDF dù đã có sẵn thông tin độ hiếm, nên từ hiếm bị đẩy điểm hai lần.

**Bằng chứng 3: đo được.** MRR của SPLADE là 0,877 khi còn IDF và 0,913 khi bỏ IDF. Xem `1_bao_cao\E0_goc.md` và `1_bao_cao\E2_splade_bo_idf.md`.

---

## Lỗi 2: BM25 xử lý câu hỏi như xử lý văn bản

| | File | Tìm (Ctrl+F) | Dòng |
|---|---|---|---|
| Chỗ sai | `embeddings\bm25.py` | `self.model.embed([query]` | **35** |
| So sánh | cùng file | `self.model.embed(texts` | 30 |

```python
def embed_texts(self, texts):                                   # dòng 26: cho VĂN BẢN
    embeddings = self.model.embed(texts, batch_size=...)        # dòng 30: đúng
def embed_query(self, query):                                   # dòng 33: cho CÂU HỎI
    emb_iter = self.model.embed([query], batch_size=1)          # dòng 35: SAI, dùng lại hàm của văn bản
```

Hàm cho văn bản và hàm cho câu hỏi gọi **cùng một** `embed()`.

**Bằng chứng 1: thư viện có hàm riêng cho câu hỏi.** Mở:

`<HOME>\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastembed\sparse\bm25.py`

- Tìm `def _term_frequency` (dòng 355–357). `embed()` gọi hàm này. Hàm nhân mỗi từ với `(k + 1)` rồi chia cho `num_occurrences + k * (1 - b + b * doc_len / avg_len)`. Đây là công thức **chuẩn hóa độ dài văn bản**.
- Tìm `def query_embed` (dòng 365–381). Docstring ghi: câu hỏi không cần trọng số, chỉ cần gán **1.0** cho mỗi từ. Code ở dòng 380 là `values = np.ones_like(token_ids)`.

Tác giả thư viện đã nói rõ câu hỏi phải dùng `query_embed()`. Code gốc lại dùng `embed()`.

**Bằng chứng 2: tính tay.** Với k = 1,2, b = 0,75, avg_len = 256, câu hỏi 4 từ và mỗi từ xuất hiện 1 lần:

```
2,2 / (1 + 1,2 × (0,25 + 0,75 × 4/256)) = 2,2 / 1,314 = 1,674
```

**Bằng chứng 3: chạy thật** (ngày 23/11/2026):

| Câu hỏi | `embed()` (code gốc) | `query_embed()` (đúng) |
|---|---|---|
| `NVDA export restrictions China` | 1,674 · 1,674 · 1,674 · 1,674 | 1 · 1 · 1 · 1 |
| `revenue revenue growth` | **1,904** · 1,679 | 1 · 1 |

- Số 1,674 khớp đúng phép tính tay.
- Từ lặp lại ("revenue" hai lần) bị cộng điểm lên 1,904. Gõ lặp từ là làm lệch kết quả.
- Khi mọi từ cùng hệ số thì thứ hạng không đổi. Vì vậy E1 gần như không thay đổi số đo (NDCG chỉ tăng 0,0008). Đây là **lỗi đúng/sai về lý thuyết, ảnh hưởng thực tế nhỏ**.

Lệnh để chạy lại bằng chứng 3:

```
python -c "from fastembed import SparseTextEmbedding as S; m=S('Qdrant/bm25'); q='revenue revenue growth'; print(next(m.embed([q])).values, next(m.query_embed(q)).values)"
```

---

## Lỗi 3 (thiếu sót, không phải sai): không đổi được cấu hình khi thử nghiệm

| | File | Tìm (Ctrl+F) | Dòng |
|---|---|---|---|
| Chỗ thiếu | `config.py` | `Environment variable overrides` | 110 |

Phần ghi đè bằng biến môi trường chỉ có `QDRANT_URL`, `QDRANT_API_KEY` và `EDGAR_USER_AGENT`. Không có `QDRANT_COLLECTION`, `DENSE_MODEL` hay `DENSE_VECTOR_SIZE`. Muốn so sánh ngăn cũ với ngăn mới, hoặc model nhỏ với model lớn, thì mỗi lần phải sửa `config\default.yaml`. Cách này dễ nhầm và khó lặp lại thí nghiệm.

---

## Xem bản đã sửa

Bản đã sửa nằm ở `D:\PTTC\financial-hybrid-search-qdrant\src\hybrid_search\`, cùng tên file. Toàn bộ khác biệt có trong `3_code\phan2_sua_doi.diff`: dòng `-` là cũ, dòng `+` là mới.
