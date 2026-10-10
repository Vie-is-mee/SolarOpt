# SolarOpt Studio — AI 2026 Prototype

SolarOpt là nguyên mẫu hỗ trợ kỹ sư thiết kế điện mặt trời mái nhà theo cơ chế:

```text
hiểu dữ liệu → Digital Roof → mô phỏng → tối ưu → kiểm chứng
→ Stress Test → truy vết thay đổi → Minimal Repair → kỹ sư duyệt
```

## Điểm quan trọng của bản source này

- Frontend đã được **khôi phục theo đúng giao diện trong file ZIP frontend gốc của đội**, tức cùng thiết kế dùng để chụp các ảnh trong Proposal V4.
- Backend FastAPI chứa các engine hình học, mặt trời, tối ưu, kiểm chứng, stress test, dependency graph, uncertainty và versioning.
- Phân tích ảnh dùng **Gemini 2.5 Flash-Lite qua backend** khi có key.
- **Không lưu API key ở frontend/localStorage**.
- Nếu chưa có Gemini key, backend có chế độ demo fallback cho bước Vision để luồng vẫn có thể kiểm tra.

## 1. Giao diện 5 bước

1. **Thiết lập** — ảnh/bản vẽ, vị trí, kích thước, panel/inverter, ngân sách, mục tiêu.
2. **Hợp nhất dữ liệu** — Digital Roof, vật cản, confidence, công cụ kéo/chỉnh.
3. **Thiết kế** — Bố trí / Bóng che / Bức xạ / So sánh panel / Solar Time Machine.
4. **Kiểm chứng** — so sánh phương án, Verification, Stress Test.
5. **Bàn giao/Tự phục hồi** — Trace Impact, Before/After, version history, export report.

## 2. Backend

```text
backend/app/
├── main.py
├── schemas.py
├── database.py
└── services/
    ├── gemini_vision.py
    ├── geometry.py
    ├── solar.py
    ├── optimizer.py
    ├── verifier.py
    ├── stress.py
    ├── dependency.py
    └── uncertainty.py
```

### Nguyên tắc thiết kế
Gemini chỉ hỗ trợ **hiểu ảnh/bản vẽ**. Mô hình AI không có quyền tự kết luận thiết kế PASS/FAIL. Các bước hình học, tối ưu và kiểm chứng được thực hiện bằng code có thể truy vết.

## 3. Chạy bằng Miniconda trên Windows

### Tạo môi trường

```bat
conda create -n solaropt python=3.11 -y
conda activate solaropt
conda install -c conda-forge nodejs=22 -y
```

### Backend

```bat
cd backend
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
set PYTHONPATH=.
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

### Frontend

Mở Miniconda Prompt thứ hai:

```bat
conda activate solaropt
cd frontend
npm install
npm run dev
```

Mở:

```text
http://127.0.0.1:5173
```

## 4. Gemini API key

Tạo file `backend/.env` từ `.env.example`:

```env
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash-lite
CORS_ORIGINS=http://localhost:5173,http://localhost:4173
```

Điền key sau khi đã test hệ thống không-key. Không commit `.env`.

## 5. Thay đổi bảo mật so với frontend gốc

Frontend gốc từng có luồng nhập Anthropic API key trực tiếp trong browser. Bản này đã bỏ luồng đó:

```text
Browser → /api/vision/analyze → FastAPI → Gemini
```

Key chỉ nằm ở backend.

## 6. Frontend và proposal

`frontend/src/App.tsx` giữ nguyên ngôn ngữ thiết kế, bố cục và 5 màn hình của frontend gốc để source, proposal và video demo không xuất hiện hai hệ giao diện khác nhau.

## 7. Test backend

```bat
cd backend
set PYTHONPATH=.
pytest -q
```

## 8. Trước video/nộp source

- Cài đầy đủ `requirements.txt`.
- Test Gemini bằng ảnh được phép sử dụng.
- Test toàn bộ 5 bước.
- Không quay/commit API key.
- Không để tên GenD/DREAM/Arena trong repo cuối.
- Nếu dùng số benchmark, lưu CSV/log tương ứng.
- Đối chiếu proposal ↔ source ↔ video demo trước khi freeze.

## 9. Tài liệu

- `docs/ARCHITECTURE.md`
- `docs/AI_RESOURCE_DECLARATION.md`
- `docs/BENCHMARK_PLAN.md`
- `docs/DEMO_SCRIPT_5MIN.md`
- `docs/SETUP_GEMINI_FREE.md`
- `docs/SOURCE_STATUS.md`
