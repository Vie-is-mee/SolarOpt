# Trạng thái source sau khi hoàn thiện MVP

## Chạy thật ở backend
- FastAPI API.
- Sun position.
- PVGIS fetch + fallback.
- Geometry/obstacle constraints.
- Candidate panel grid.
- CP-SAT khi OR-Tools được cài; greedy fallback khi thiếu package.
- Annual energy estimate.
- Shadow scoring nhiều thời điểm đại diện.
- Verification.
- 8 stress scenarios.
- Dependency Graph.
- Minimal Repair / preservation bonus.
- SQLite version history.

## AI ngoài
- Gemini 2.5 Flash-Lite cho Vision/OCR khi có key.
- Không có key: trả demo fallback để frontend vẫn sử dụng được.

## Chưa phải sản phẩm thương mại
- Chưa có CAD/BIM đầy đủ.
- Chưa kiểm định kết cấu/PCCC.
- Chưa có auth/multi-tenant.
- Chưa có mô hình 3D photogrammetry.
- Chưa có electrical string sizing đầy đủ cho inverter/string/MPPT.

Các giới hạn này phải được nói trung thực trong proposal và Q&A.
