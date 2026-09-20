# SOLAROPT — TÀI LIỆU / MINH CHỨNG KỸ THUẬT

## 1. Kiến trúc

```text
React / SolarOpt Studio
        |
        | REST /api
        v
FastAPI Backend
  |-- Gemini Vision/OCR (optional)
  |-- Geometry / Shapely
  |-- Sun position / pvlib
  |-- PVGIS irradiance
  |-- Shadow engine
  |-- OR-Tools CP-SAT optimizer
  |-- Verification Engine
  |-- Stress Engine
  |-- Dependency Graph
  |-- Impact-aware uncertainty
  |-- Minimal Repair
  `-- SQLite version history
```

## 2. Mapping chức năng → source

| Chức năng | Source chính |
|---|---|
| API server | `backend/app/main.py` |
| Schema dữ liệu | `backend/app/schemas.py` |
| Gemini Vision/OCR | `backend/app/services/gemini_vision.py` |
| Hình học | `backend/app/services/geometry.py` |
| Vị trí mặt trời/PVGIS | `backend/app/services/solar.py` |
| Tối ưu panel | `backend/app/services/optimizer.py` |
| Verification | `backend/app/services/verifier.py` |
| Stress Test | `backend/app/services/stress.py` |
| Dependency Graph | `backend/app/services/dependency.py` |
| Impact-aware uncertainty | `backend/app/services/uncertainty.py` |
| Version DB | `backend/app/database.py` |
| Frontend đúng giao diện proposal | `frontend/src/App.tsx` |
| API bridge frontend | `frontend/src/services/api.ts` |

## 3. Tính nhất quán với proposal

Frontend cuối được khôi phục theo **đúng thiết kế trong file ZIP frontend gốc của đội**, là nguồn của các screenshot đã đưa vào Proposal V4:
1. Thiết lập dự án.
2. Hợp nhất dữ liệu / Digital Roof.
3. Thiết kế với Bố trí, Bóng che, Bức xạ, Solar Time Machine.
4. Kiểm chứng và Stress Test.
5. Tự phục hồi / Trace Impact / Before-After.

Thay đổi bảo mật quan trọng: frontend không còn yêu cầu Anthropic key hay lưu key trong browser. Phân tích ảnh gọi backend SolarOpt, backend mới giữ Gemini API key.

## 4. Kiểm thử source

Backend có test lõi:
- `backend/tests/test_core.py`
- design generation + verify.
- dependency impact.

Chạy:

```bash
cd backend
PYTHONPATH=. pytest -q
```

Trước khi quay video chính thức, đội cần cài đầy đủ `requirements.txt` để OR-Tools, pvlib và Gemini SDK chạy thay vì fallback.

## 5. Scenario minh chứng trọng tâm

```text
Bồn nước 1,2 m → 1,8 m
        ↓
Dependency Graph
        ↓
Shadow / feasible region / layout / energy / cost affected
        ↓
Minimal Repair
        ↓
Verify lại
        ↓
Version Diff
```

## 6. Giới hạn cần nói trung thực

- Đây là prototype kỹ thuật, chưa phải phần mềm cấp chứng nhận thiết kế.
- Chưa thay thế kiểm tra kết cấu/PCCC/chữ ký kỹ sư.
- Vision là gợi ý và luôn cho phép kỹ sư sửa.
- Không dùng số demo có kiểm soát để khẳng định benchmark toàn thị trường.
- Trước khi nộp benchmark, mọi số phải có log/CSV tương ứng.
