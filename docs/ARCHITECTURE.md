# SolarOpt — Kiến trúc kỹ thuật

## Mục tiêu

Biến một thay đổi nhỏ ngoài hiện trường thành một lần cập nhật có chọn lọc thay vì thiết kế lại toàn bộ.

## Luồng chính

```text
Ảnh / bản vẽ / thông tin kỹ sư
            |
            v
Gemini Vision/OCR (optional)
            |
            v
Digital Roof ----------------------+
            |                       |
            v                       |
Geometry + solar/shadow engine      |
            |                       |
            v                       |
Candidate panel grid                |
            |                       |
            v                       |
CP-SAT optimizer                    |
            |                       |
            v                       |
Verification -> Stress Test         |
            |                       |
            +------ Version --------+
            |
      dự án thay đổi
            |
            v
Dependency Graph -> Selective invalidation
            |
            v
Minimal Repair -> Verify again -> Version Diff
```

## Ownership

### Bên ngoài / mã nguồn mở
- Gemini 2.5 Flash-Lite: hiểu ảnh / OCR gợi ý.
- PVGIS: dữ liệu bức xạ.
- pvlib: vị trí mặt trời.
- Shapely: phép toán hình học.
- OR-Tools: solver CP-SAT.
- FastAPI / React: khung ứng dụng.

### Đội xây dựng
- Hợp đồng dữ liệu Digital Roof.
- Pipeline hợp nhất dữ liệu và chỉnh tay.
- Cách sinh candidate panel cho bài toán rooftop.
- Formulation ràng buộc và objective cho SolarOpt.
- Shadow-aware energy scoring của prototype.
- Verification orchestration.
- Stress scenarios.
- Dependency Graph + selective invalidation.
- Impact-aware uncertainty (boundary simulation + impact score).
- Minimal Repair objective/preservation logic.
- Version Diff và UX 5 bước.
