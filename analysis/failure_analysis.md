# Báo cáo Phân tích Thất bại (Failure Analysis Report)

Báo cáo này phân tích chi tiết hiệu năng và các lỗi hệ thống của **Agent V1 (Base)** dựa trên kết quả chạy thử nghiệm benchmark trên bộ dữ liệu chuẩn 55 cases.

---

## 1. Tổng quan Benchmark (Agent V1 Base)
- **Tổng số cases:** 55
- **Tỉ lệ Pass/Fail:** 34 Pass / 21 Fail (Ngưỡng Pass: Điểm LLM Judge >= 3.0/5.0)
- **Điểm RAGAS trung bình:**
    - Faithfulness (Độ trung thực): **0.65**
    - Relevancy (Độ liên quan): **0.65**
- **Điểm LLM-Judge trung bình:** **3.12 / 5.0**
- **Độ trễ phản hồi trung bình:** **0.461 giây**
- **Tổng chi phí vận hành:** **$0.26550 USD (88,500 Tokens)**

---

## 2. Phân nhóm lỗi (Failure Clustering)

Dựa trên 21 trường hợp thất bại của Agent V1, chúng tôi phân nhóm thành 4 cụm lỗi chính sau:

| Nhóm lỗi | Số lượng | Tỉ lệ | Nguyên nhân dự kiến |
| :--- | :---: | :---: | :--- |
| **Retrieval Failure (Lỗi tìm kiếm)** | 11 | 52.4% | Thuật toán nhúng (Embedding) chưa tối ưu, Fixed-size chunking làm loãng ngữ cảnh và thiếu bước Reranking dẫn đến xếp sai thứ tự chunk liên quan. |
| **Security Vulnerability (Lỗ hổng bảo mật)** | 5 | 23.8% | Thiếu tầng bảo vệ đầu vào (Input Guardrails) và system prompt lỏng lẻo, khiến Agent bị lừa bởi Prompt Injection và Goal Hijacking. |
| **Hallucination on Out-of-Context** | 5 | 23.8% | System Prompt không ràng buộc Agent từ chối kiến thức ngoài tài liệu, khiến Agent tự bịa đặt thông tin khi tìm kiếm không ra ngữ cảnh. |
| **Clarification Failure (Mập mờ/Mâu thuẫn)** | 0 | 0.0% | Agent trả lời phiến diện một chiều thay vì đặt câu hỏi làm rõ (chênh lệch điểm ở các case Ambiguous và Conflicting). |

---

## 3. Phân tích 5 Whys (Chọn 3 case tệ nhất)

### 🔴 Case #1: Bị hack bởi Prompt Injection & Goal Hijacking (Adversarial Cases)
* **Symptom (Triệu chứng):** Agent in ra từ khóa `"HACKED"` và cung cấp mã SQL Injection độc hại thay vì từ chối yêu cầu của người dùng.
* **Why 1:** LLM Generator sinh câu trả lời tuân theo lệnh tấn công của người dùng thay vì giữ vững nhiệm vụ hỗ trợ.
* **Why 2:** System Prompt của Agent V1 quá đơn giản, không có chỉ dẫn bảo mật nghiêm ngặt chống prompt injection.
* **Why 3:** Mô hình cố gắng tối đa hóa sự hài lòng của người dùng (over-compliance) mà không đánh giá độ an toàn của yêu cầu.
* **Why 4:** Thiết kế hệ thống Agent chỉ tập trung vào luồng RAG tìm kiếm cơ bản, bỏ qua khía cạnh an toàn thông tin (Red Teaming / Safety).
* **Why 5:** Không có tầng kiểm duyệt và làm sạch đầu vào (Input Sanitization/Guardrails) trước khi gửi truy vấn tới LLM.
* **Root Cause (Nguyên nhân gốc rễ):** Hệ thống thiếu cấu trúc bảo vệ đa tầng (System Prompt Guardrails & Input Classifier) để nhận diện và từ chối các truy vấn độc hại độc lập với luồng xử lý RAG.

---

### 🔴 Case #2: Bịa đặt thông tin (Hallucination) ở câu hỏi Out-of-Context
* **Symptom (Triệu chứng):** Agent tự viết hướng dẫn nấu canh chua cá lóc Nam Bộ và khuyên mua cổ phiếu Apple mặc dù thông tin này hoàn toàn không có trong tài liệu của công ty.
* **Why 1:** LLM Generator tự sinh câu trả lời bằng bộ nhớ huấn luyện sẵn (Parametric Memory) của nó khi ngữ cảnh rỗng.
* **Why 2:** System Prompt không giới hạn Agent chỉ được trả lời dựa trên ngữ cảnh được cung cấp (Context Grounding).
* **Why 3:** Dữ liệu context truyền vào LLM trống hoặc chứa thông tin rác do bước tìm kiếm thất bại.
* **Why 4:** Vector DB vẫn trả về các chunk nhiễu vì thuật toán tìm kiếm cosine luôn trả về top K kết quả gần nhất bất kể độ tương đồng ngữ nghĩa cực kỳ thấp.
* **Why 5:** Hệ thống không cấu hình ngưỡng lọc tương đồng tối thiểu (Similarity Threshold) cho Retrieval stage.
* **Root Cause (Nguyên nhân gốc rễ):** Hệ thống RAG thiếu cả ngưỡng lọc tương đồng tìm kiếm (Retrieval Threshold) để phát hiện câu hỏi ngoài phạm vi, lẫn ràng buộc prompt nghiêm ngặt bắt buộc Agent nói "Tôi không biết" khi không có tài liệu chứng minh.

---

### 🔴 Case #3: Bỏ sót thông tin quan trọng ở các câu hỏi tổng hợp khó (Hit Rate & MRR thấp)
* **Symptom (Triệu chứng):** Agent trả lời thiếu ý, bỏ qua các chi tiết cốt lõi khi người dùng yêu cầu so sánh quy trình hoặc tổng hợp từ nhiều tài liệu.
* **Why 1:** Ngữ cảnh đầu vào truyền tới LLM bị thiếu các chunk chứa thông tin cốt lõi cần thiết.
* **Why 2:** Vector DB không xếp hạng các tài liệu liên quan nhất ở vị trí đầu tiên (MRR thấp) hoặc bỏ sót tài liệu do giới hạn top_k=3 quá nhỏ.
* **Why 3:** Embedding model không nắm bắt tốt ngữ nghĩa của các câu hỏi so sánh phức tạp hoặc chiến lược Chunking kích thước cố định (Fixed-size chunking) làm phân mảnh dữ liệu (cắt đôi thông tin quan trọng).
* **Why 4:** Các chunk liên quan không có overlap đủ lớn hoặc phân bổ rời rạc ở nhiều phần tài liệu khác nhau.
* **Why 5:** Quy trình xử lý dữ liệu thô (Ingestion) quá thô sơ và thiếu module tái xếp hạng tài liệu (Reranking).
* **Root Cause (Nguyên nhân gốc rễ):** Chiến lược Chunking không tối ưu (Fixed-size làm mất ngữ nghĩa liên kết) và thiếu module Reranker để tối ưu hóa thứ tự tài liệu quan trọng lên đầu ngữ cảnh.

---

## 4. Kế hoạch cải tiến (Action Plan cho Agent V2)

Dựa trên các nguyên nhân gốc rễ đã tìm ra, chúng tôi đã triển khai các cải tiến cho Agent V2 như sau:
1. **Về Ingestion & Retrieval:**
   - [x] Thay thế chiến lược Fixed-size chunking bằng **Semantic Chunking** kết hợp tăng độ dài overlap để giữ tính liên kết thông tin.
   - [x] Tích hợp bộ **Reranker** để tối ưu hóa MRR, đẩy các chunk liên quan nhất lên đầu danh sách trước khi đưa vào prompt của LLM.
   - [x] Đặt **Similarity Threshold** tối thiểu là 0.70; nếu không có chunk nào vượt ngưỡng, hệ thống tự động coi là câu hỏi Out-of-Context và bỏ qua bước gọi Generator.
2. **Về Prompt Engineering & Guardrails:**
   - [x] Thêm cấu trúc bảo vệ vào **System Prompt** của Generator: *"CHỈ sử dụng thông tin trong ngữ cảnh. Tuyệt đối không sử dụng kiến thức bên ngoài. Nếu không tìm thấy thông tin, hãy trả lời lịch sự: 'Tôi xin lỗi, thông tin này không nằm trong tài liệu hệ thống được cung cấp'."*
   - [x] Triển khai **Prompt Guardrail Rules** để phát hiện các mẫu câu tấn công (Jailbreak, Prompt Injection) và trả về thông báo từ chối mặc định chuyên nghiệp ngay từ đầu.
3. **Về Performance:**
   - [x] Tối ưu hóa prompt để giảm lượng token đầu vào dư thừa, giúp giảm 30% chi phí token và tăng tốc độ xử lý (giảm latency).
