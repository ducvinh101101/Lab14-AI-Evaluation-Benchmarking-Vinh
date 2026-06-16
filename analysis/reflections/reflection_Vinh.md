# Báo cáo Phản ánh Cá nhân (Individual Reflection Report)

- **Học viên:** Đức Vinh
- **Mã số sinh viên / Repository:** ducvinh101101/Lab14-AI-Evaluation-Benchmarking-Vinh
- **Vai trò trong nhóm:** AI & Backend Engineer

---

## 1. Đóng góp Kỹ thuật Cá nhân (Individual Contributions)

Trong bài lab Day 14, tôi đã đảm nhiệm việc nghiên cứu thiết kế và phát triển các thành phần lõi của hệ thống đánh giá tự động:
1. **Thiết kế Golden Dataset:** Xây dựng bộ seed dataset gồm 55 test cases đầy đủ các kịch bản thực tế khó (Adversarial, Out-of-Context, Ambiguous, Conflicting) kèm theo việc lập bản đồ `expected_retrieval_ids` để đo đạc chất lượng của Vector DB.
2. **Phát triển Eval Engine & Multi-Judge Engine:** Hiện thực hóa các class `RetrievalEvaluator` và `LLMJudge` trong thư mục `engine/`. Viết logic tính toán Hit Rate, MRR, và gọi song song hai mô hình Judge LLM độc lập để đo độ đồng thuận.
3. **Hiện thực hóa Cơ chế Trọng tài (Arbitration):** Phát triển bộ phân xử tự động khi hai mô hình Judge cho kết quả lệch nhau quá 1.0 điểm, gọi một mô hình thứ ba làm trọng tài tối cao giải quyết xung đột điểm số.
4. **Tối ưu hóa Runner & Cost Tracker:** Xây dựng Async Runner sử dụng `asyncio.gather` theo batch để tăng tốc độ đánh giá, đồng thời đo đạc chính xác thời gian phản hồi (latency), số lượng token tiêu thụ và quy đổi ra giá trị USD thực tế.
5. **Khắc phục lỗi Hệ thống:** Giải quyết triệt để lỗi mã hóa ký tự `UnicodeEncodeError` khi chạy python script in kết quả tiếng Việt ra terminal của Windows.

---

## 2. Chiều sâu Kỹ thuật (Technical Depth)

### 2.1. Mean Reciprocal Rank (MRR)
**MRR** là một chỉ số thống kê đo lường chất lượng xếp hạng (ranking quality) của hệ thống tìm kiếm thông tin (Retrieval). Thay vì chỉ kiểm tra tài liệu liên quan có xuất hiện trong kết quả hay không (như Hit Rate), MRR đánh giá xem tài liệu chính xác nằm ở vị trí thứ mấy.

**Công thức toán học:**
$$MRR = \frac{1}{N} \sum_{i=1}^{N} \frac{1}{\text{rank}_i}$$
Trong đó:
* $N$ là tổng số truy vấn trong bộ kiểm thử.
* $\text{rank}_i$ là thứ hạng (vị trí) của tài liệu liên quan đầu tiên được tìm thấy cho truy vấn thứ $i$ (bắt đầu từ 1). Nếu không có tài liệu liên quan nào được tìm thấy trong kết quả trả về, $\frac{1}{\text{rank}_i} = 0$.

**Ý nghĩa thực tế:**
* MRR rất nhạy cảm với vị trí của kết quả đầu tiên. Ví dụ, nếu tài liệu liên quan nằm ở vị trí số 1, điểm RR là $1.0$. Nếu nằm ở vị trí số 2, điểm RR giảm một nửa còn $0.5$. Nếu nằm ở vị trí số 3, điểm RR chỉ còn $0.33$.
* Trong hệ thống RAG, MRR cao bảo đảm rằng ngữ cảnh chính xác nhất được đẩy lên đầu tiên trong prompt truyền vào LLM, giúp mô hình sinh câu trả lời tập trung hơn và tránh loãng thông tin.

### 2.2. Hệ số Đồng thuận Cohen's Kappa
Trong hệ thống Multi-Judge, việc đo lường mức độ đồng thuận giữa các mô hình đánh giá độc lập là rất quan trọng để đảm bảo tính khách quan. **Cohen's Kappa ($\kappa$)** là chỉ số thống kê đo lường sự đồng thuận giữa hai người đánh giá (hoặc hai Judge LLM) đối với dữ liệu phân loại, sau khi loại bỏ đi xác suất đồng thuận ngẫu nhiên.

**Công thức toán học:**
$$\kappa = \frac{p_o - p_e}{1 - p_e}$$
Trong đó:
* $p_o$ (Observed agreement): Tỉ lệ phần trăm các trường hợp mà cả hai Judge đồng thuận điểm số thực tế.
* $p_e$ (Expected agreement): Tỉ lệ phần trăm các trường hợp mà hai Judge đồng thuận ngẫu nhiên dựa trên phân phối xác suất các nhãn điểm của từng Judge.

**Ý nghĩa thực tế:**
* Điểm $\kappa$ dao động từ -1 đến 1. Điểm gần 1 biểu thị độ đồng thuận tuyệt đối và nhất quán cao. Điểm gần 0 hoặc âm biểu thị sự đồng thuận chỉ mang tính ngẫu nhiên.
* Việc theo dõi Cohen's Kappa giúp phát hiện xem các Judge LLM có đang được căn chỉnh (align) tốt với bộ Rubrics hay không. Nếu Kappa thấp, ta cần điều chỉnh lại hướng dẫn chấm điểm (Prompt Rubric) của các Judge.

### 2.3. Thiên vị Vị trí (Position Bias) trong LLM Judge
**Position Bias** là hiện tượng LLM Judge có xu hướng ưu ái và chấm điểm cao hơn cho câu trả lời nào được đặt ở vị trí đầu tiên (hoặc vị trí thứ hai) trong Prompt so sánh chéo, bất kể chất lượng thực tế của hai câu trả lời đó ra sao.

**Cách khắc phục (Calibration):**
1. **Hoán đổi vị trí (Swapping/Order Inversion):** Khi cho LLM Judge so sánh hai câu trả lời A và B, ta thực hiện hai lượt gọi đánh giá độc lập. Lượt 1 đưa A ở vị trí 1 và B ở vị trí 2. Lượt 2 đảo ngược, đưa B ở vị trí 1 và A ở vị trí 2.
2. **Lấy trung bình kết quả (Score Averaging):** Điểm số cuối cùng sẽ là trung bình cộng điểm số của cả hai lượt chạy. Kỹ thuật này giúp triệt tiêu hoàn toàn sự thiên vị về thứ tự sắp xếp trong prompt của LLM.

---

## 3. Phân tích Trade-off giữa Chi phí & Chất lượng (Cost vs. Quality)

Trong việc xây dựng hệ thống benchmark AI, việc cân đối giữa tính chính xác của kết quả và chi phí tài nguyên (API cost & Latency) là bài toán trade-off cốt lõi:

* **Hướng tiếp cận chất lượng tối đa:** Sử dụng toàn bộ mô hình lớn và đắt tiền (như GPT-4o, Claude 3.5 Sonnet) cho cả Generator lẫn các Judge LLM. 
  - *Ưu điểm:* Kết quả đánh giá có độ chính xác và tin cậy cực kỳ cao.
  - *Nhược điểm:* Chi phí API tăng vọt, thời gian phản hồi (latency) chậm, dễ gặp Rate Limit khi chạy benchmark quy mô lớn.
* **Hướng tiếp cận tiết kiệm chi phí tối đa:** Sử dụng mô hình nhỏ (như GPT-4o-mini) cho mọi tác vụ hoặc dùng các bộ lọc regex thô sơ.
  - *Ưu điểm:* Pipeline chạy cực nhanh, chi phí siêu rẻ.
  - *Nhược điểm:* Đánh giá nông cạn, không phát hiện được lỗi Hallucination phức tạp, độ tin cậy kém.

**Giải pháp Tối ưu hóa 30% Chi phí & Hiệu năng được đề xuất:**
1. **Phân tầng Đánh giá (Hierarchical Evaluation Routing):** 
   - Sử dụng mô hình nhỏ (`gpt-4o-mini`) để giải quyết các trường hợp đánh giá dễ (Easy cases, so khớp thông tin trực tiếp).
   - Chỉ chuyển tiếp các trường hợp khó (Hard cases, so sánh suy luận chéo) hoặc các trường hợp có điểm tương đồng tương đương lên mô hình lớn (`gpt-4o`).
2. **Cơ chế Cache Kết quả:** Cache kết quả chấm điểm của Judge đối với những câu trả lời giống nhau trong quá trình chạy thử nghiệm lặp lại, tránh việc gọi trùng lặp API cho cùng một nội dung.
3. **Cô đọng Prompt (Prompt Compression):** Loại bỏ các từ ngữ dư thừa trong Prompt của Judge giúp giảm số lượng Input Token tiêu thụ mà không làm giảm khả năng suy luận của mô hình.

---

## 4. Giải quyết Vấn đề & Bài học Kinh nghiệm (Problem Solving)

* **Vấn đề gặp phải:** Khi chạy file `synthetic_gen.py` và `check_lab.py` trên hệ điều hành Windows, Python mặc định sử dụng bảng mã `cp1252` của console. Điều này dẫn tới lỗi nghiêm trọng `UnicodeEncodeError: 'charmap' codec can't encode characters...` khi chương trình in các ký tự tiếng Việt có dấu và các emoji trạng thái ra màn hình terminal.
* **Cách giải quyết:** Tôi đã trực tiếp can thiệp vào mã nguồn và chèn đoạn cấu hình đầu file:
  ```python
  import sys
  if hasattr(sys.stdout, 'reconfigure'):
      sys.stdout.reconfigure(encoding='utf-8')
  if hasattr(sys.stderr, 'reconfigure'):
      sys.stderr.reconfigure(encoding='utf-8')
  ```
  Cách tiếp cận này buộc Python runtime giao tiếp với console thông qua mã hóa UTF-8, giúp giải quyết triệt để lỗi hiển thị trên môi trường Windows mà không cần thay đổi cấu hình hệ thống của người dùng.
