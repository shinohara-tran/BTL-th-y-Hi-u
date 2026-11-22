# Hướng dẫn chấm nhãn

Mỗi dòng trong `evaluation/team/labels.csv` là một cặp (câu hỏi, đoạn văn). Đọc cột `query` và cột `text`, rồi cho điểm vào cột của mình (`label_A` hoặc `label_B`). Không xem điểm của người kia trước khi chấm xong.

| Điểm | Khi nào | Ví dụ với câu "How does Microsoft describe risks from AI regulation?" |
|---|---|---|
| **2** | Đoạn văn trả lời được câu hỏi. Đọc xong là có câu trả lời | "Our implementation of AI systems could result in legal liability, regulatory action..." của Microsoft |
| **1** | Đúng chủ đề nhưng chỉ trả lời một phần, hoặc phải ghép thêm đoạn khác | Một đoạn của Microsoft nói chung về quy định pháp luật, không nhắc AI |
| **0** | Không liên quan, sai công ty, hoặc chỉ trùng vài chữ | "This AI may be developed by Microsoft or others, including our strategic partner, OpenAI." Có chữ AI và Microsoft nhưng không nói về quy định |

Quy tắc chung:
- Sai công ty so với câu hỏi thì cho 0, kể cả khi nội dung đúng chủ đề.
- Câu hỏi về số liệu một năm: đoạn có đúng con số của đúng năm thì 2; có bảng nhưng không thấy năm đó thì 1.
- Đoạn văn trùng nội dung với đoạn khác (cùng câu lặp ở báo cáo năm khác) vẫn chấm theo nội dung. Trùng lặp được đo riêng bằng chỉ số `dup@5`.
- Không chắc thì ghi lý do vào cột `note`. Các dòng này đem ra thảo luận cùng dòng lệch.
- Cột `label` (nhãn cuối) do `agreement.py` điền hoặc do cả nhóm điền sau khi thống nhất. Không tự điền khi chưa thảo luận.

Trước khi chấm thật, cả hai người chấm thử chung khoảng 20 dòng, so kết quả và thống nhất cách hiểu. Nếu kappa dưới 0,4 thì dừng lại, bàn lại cách chấm rồi mới chấm tiếp.
