# BẢN KÊ KHAI CÔNG CỤ AI, DỮ LIỆU, API, THƯ VIỆN, MÃ NGUỒN MỞ VÀ PHẦN ĐỘI TỰ XÂY DỰNG

**Dự án:** SolarOpt  
**Đội:** Axiom  
**Bảng:** C

> Tài liệu này kê khai theo source hiện tại. Trước khi nộp, đội chỉ cần rà lại phiên bản package/model thực tế sau lần cài cuối.

## 1. Công cụ AI / API / nguồn ngoài

| Thành phần | Loại | Vai trò | Có quyết định PASS/FAIL kỹ thuật không? | Phần đội kiểm soát |
|---|---|---|---|---|
| Gemini 2.5 Flash-Lite | AI API | Hỗ trợ phân tích ảnh/bản vẽ, trích xuất nội dung và gợi ý vật cản | **Không** | Backend proxy, prompt/schema, hậu xử lý, cho phép kỹ sư hiệu chỉnh |
| Google AI Studio | Dịch vụ | Tạo/quản lý Gemini API key | Không | Key lưu ở backend `.env`, không gửi xuống frontend |
| PVGIS | API/dữ liệu công khai | Bức xạ mặt trời | Không | Mapping dữ liệu vào cấu hình dự án và fallback khi lỗi |
| ChatGPT | AI hỗ trợ phát triển | Nghiên cứu, rà soát kiến trúc, hỗ trợ code/tài liệu/proposal | Không trực tiếp trong runtime sản phẩm | Thành viên đọc, sửa, chạy test và chịu trách nhiệm đầu ra |

## 2. Thư viện/mã nguồn mở

| Thành phần | Mục đích | Cách SolarOpt sử dụng |
|---|---|---|
| React | Giao diện web | SolarOpt Studio 5 bước |
| Vite | Build/dev frontend | Chạy ứng dụng React |
| Tailwind CSS | Giao diện | Styling của frontend gốc |
| FastAPI | Backend | REST API và điều phối engine |
| Shapely | Hình học | Mái, vật cản, vùng khả thi, giao cắt |
| OR-Tools CP-SAT | Tối ưu ràng buộc | Chọn vị trí tấm pin; objective do đội thiết kế |
| pvlib | Mặt trời | Cao độ/phương vị mặt trời |
| SQLite | Lưu trữ nhẹ | Lịch sử phiên bản |
| PyMuPDF (nếu cài) | Tệp PDF | Chuyển/đọc PDF phục vụ Vision |

## 3. Dữ liệu

### Dữ liệu do người dùng/đội cung cấp
- Bản vẽ kỹ thuật.
- Ảnh mái từ trên xuống.
- Ảnh hiện trường.
- Thông số tấm pin/inverter.
- Các thông số kỹ thuật do kỹ sư hiệu chỉnh.

### Dữ liệu bên ngoài
- PVGIS cho dữ liệu bức xạ khi endpoint được gọi.

### Dữ liệu demo repository
- `sample_data/` và `frontend/public/demo/` chỉ phục vụ trình diễn.
- Không đưa bản vẽ mật của doanh nghiệp lên repository công khai.

## 4. Phần cốt lõi đội tự xây dựng

1. Luồng trải nghiệm SolarOpt Studio 5 bước.
2. Data contract của Digital Roof.
3. Pipeline từ ảnh/bản vẽ → dữ liệu mái/vật cản có thể chỉnh.
4. Candidate panel generation.
5. Formulation ràng buộc và objective cho rooftop optimization.
6. Shadow-aware scoring của prototype.
7. Verification Engine orchestration.
8. Stress Test Engine.
9. Dependency Graph và selective invalidation.
10. Impact-aware uncertainty.
11. Minimal Repair / layout preservation.
12. Version history, Before/After và Trace Impact.
13. Tích hợp backend bảo mật API key.

## 5. Phân định trách nhiệm của AI

Gemini chỉ hỗ trợ **hiểu dữ liệu đầu vào**. SolarOpt không giao cho mô hình ngôn ngữ quyền tự tuyên bố thiết kế hợp lệ. Hình học, tối ưu, kiểm chứng và logic tự phục hồi nằm trong code có thể truy vết.

## 6. Kê khai AI trong quá trình phát triển

Đội có sử dụng ChatGPT và/hoặc công cụ AI khác để hỗ trợ nghiên cứu, phân tích, viết tài liệu và hỗ trợ lập trình. Thành viên đội có trách nhiệm:
- kiểm tra đầu ra;
- sửa mã;
- chạy thử;
- đối chiếu tài liệu;
- chịu trách nhiệm cuối cùng với sản phẩm nộp.

## 7. Bảo mật

- `GEMINI_API_KEY` chỉ nằm trong `backend/.env` trên máy chạy.
- `.env` bị loại khỏi Git.
- Không lưu key trong `localStorage`.
- Không quay API key trong video.
- Nếu key từng bị lộ, phải thu hồi và tạo key mới.
