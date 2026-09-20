# Frontend ↔ Proposal Alignment

Bản frontend hiện tại được lấy từ chính file ZIP giao diện gốc của đội và giữ cùng bố cục đã dùng để chụp ảnh cho Proposal V4.

## Mapping

| Proposal | Frontend |
|---|---|
| Thiết lập dự án | Bước 1 — `Step1` |
| Digital Roof / lớp AI | Bước 2 — `Step2` |
| Bố trí / Bóng che / Bức xạ / Solar Time Machine | Bước 3 — `Step3` |
| So sánh phương án / Stress Test | Bước 4 — `Step4` |
| Trace Impact / Before-After / Self-healing | Bước 5 — `Step5` |

## Thay đổi duy nhất có chủ đích so với source frontend gốc

- Bỏ nhập Anthropic API key trực tiếp trên trình duyệt.
- Bỏ lưu API key ở `localStorage`.
- Nút phân tích AI gọi `/api/vision/analyze` của FastAPI.
- Backend giữ Gemini API key trong `.env`.
- Sửa nhãn Bước 5 thành “TỰ PHỤC HỒI”.
- Thay một số câu “3D” ở bước thiết lập bằng “Digital Roof” để không claim chức năng 3D chưa hoàn thiện.

Các thay đổi trên không thay đổi ngôn ngữ thiết kế chính của các ảnh trong proposal.
