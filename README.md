<div align="center">

# ☀️ SolarOpt Studio

### Thiết kế và đánh giá phương án bố trí điện mặt trời áp mái

**Từ ảnh mái nhà đến phương án bố trí tấm pin có thể kiểm tra, điều chỉnh và lưu lại.**

[![Status](https://img.shields.io/badge/Trạng_thái-MVP_kỹ_thuật-2563eb)](docs/MVP_TECH_STATUS.md)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-Frontend-149ECA?logo=react&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-8-646CFF?logo=vite&logoColor=white)

[Giới thiệu](#-tổng-quan) · [Tính năng](#-tính-năng-nổi-bật) · [Cài đặt](#-cài-đặt-và-chạy-thử) · [Giới hạn](#-phạm-vi-và-giới-hạn)

</div>

---

## 🎯 Tổng quan

**SolarOpt Studio** là ứng dụng hỗ trợ kỹ sư khảo sát sơ bộ mái nhà và xây dựng phương án lắp đặt tấm pin năng lượng mặt trời. Người dùng có thể nhập ảnh mái và kích thước thực tế, hiệu chỉnh hình học, mô phỏng hướng nắng và bóng che, so sánh các phương án bố trí, sau đó kiểm tra và lưu kết quả.

Hệ thống kết nối giao diện với máy chủ tính toán: kết quả bố trí được tạo từ dữ liệu đầu vào, **không phải các con số minh họa cố định trên giao diện**. Đây là **bản MVP kỹ thuật**, phục vụ thử nghiệm và trình diễn, chưa thay thế thiết kế thi công chuyên nghiệp.

## ✨ Tính năng nổi bật

| Nhóm chức năng | Khả năng hiện có |
|---|---|
| **Tiếp nhận dữ liệu mái** | Nhập ảnh chụp từ trên cao, bản vẽ hoặc ảnh một phần mái; nhập vị trí và kích thước thực tế; hỗ trợ dữ liệu mẫu. |
| **Biên tập hình học** | Chỉnh biên mái đa giác, khoảng trống, vật cản, hướng Bắc, cao độ và công trình lân cận. |
| **Hỗ trợ nhận diện ảnh** | Tách biên bằng OpenCV; có tích hợp tùy chọn mô hình AI để hỗ trợ trích xuất thông tin ảnh. Kết quả cần được người dùng xác nhận. |
| **Mô phỏng nắng và bóng** | Thay đổi ngày giờ, xem bóng che và bức xạ trời quang; có tùy chọn lấy dữ liệu nắng năm từ PVGIS khi có mạng. |
| **Đề xuất bố trí** | Tạo ba phương án với các ngưỡng bóng khác nhau, xét diện tích khả dụng, khoảng lùi, vật cản, kích thước tấm pin và ngân sách. |
| **Kiểm tra và xuất kết quả** | Kiểm tra dữ liệu và hình học, thử các tình huống sai số, lưu bản đã duyệt; xuất JSON/SVG hoặc in PDF kèm bản vẽ. |

## 🧭 Quy trình sử dụng

```text
① Nhập ảnh mái và số đo thực tế
                 ↓
② Hiệu chỉnh bản vẽ và xác nhận hình học
                 ↓
③ Mô phỏng nắng, hướng chiếu và bóng che
                 ↓
④ Tạo và so sánh 3 phương án bố trí
                 ↓
⑤ Kiểm tra → Phê duyệt sơ bộ → Xuất kết quả
```

**Lưu ý:** Khi dữ liệu đầu vào thay đổi, hệ thống đánh dấu kết quả trước đó là cần cập nhật. Quá trình tính lại có cơ chế ưu tiên giữ các vị trí tấm pin đã bố trí nếu còn phù hợp.

## 🛠️ Công nghệ sử dụng

| Thành phần | Công nghệ / Vai trò |
|---|---|
| Giao diện | React, TypeScript, Vite |
| Máy chủ | Python, FastAPI |
| Xử lý ảnh | OpenCV; tích hợp mô hình AI tùy chọn |
| Mô phỏng và tối ưu | Các mô-đun Python về hình học, vị trí mặt trời, bóng che, bố trí và kiểm tra |
| Lưu phiên bản | SQLite tại máy chủ |
| Dữ liệu bức xạ bổ sung | PVGIS, khi có kết nối mạng |
| AI tùy chọn | Groq hoặc Ollama; không bắt buộc để dùng quy trình nhập tay |

## 🚀 Cài đặt và chạy thử

### Yêu cầu

- **Python 3.11 trở lên**.
- **Node.js 22.12 trở lên**, hoặc phiên bản mới hơn tương thích với Vite 8.
- Kết nối Internet cho lần cài thư viện đầu tiên và những chức năng gọi dịch vụ bên ngoài.

### Cách 1 — Khởi chạy nhanh trên Windows

Tại thư mục gốc dự án:

1. Chạy `run_backend.bat` và chờ máy chủ khởi động.
2. Mở cửa sổ khác, chạy `run_frontend.bat`.
3. Truy cập **http://127.0.0.1:5173** để sử dụng ứng dụng.

Tài liệu giao tiếp máy chủ: **http://127.0.0.1:8000/docs**.

### Cách 2 — Chạy thủ công bằng PowerShell

**Cửa sổ thứ nhất — máy chủ:**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (!(Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Cửa sổ thứ hai — giao diện** (mở tại thư mục gốc dự án):

```powershell
cd frontend
npm.cmd install
npm.cmd run dev -- --host 127.0.0.1
```

> Không mở trực tiếp `frontend/index.html` bằng trình duyệt. Giao diện cần máy chủ phát triển Vite và máy chủ Python để thực hiện các phép tính.

## 🤖 Cấu hình AI (không bắt buộc)

Ứng dụng hỗ trợ hai lựa chọn đã được tích hợp trong mã nguồn:

- **Groq:** cấu hình `GROQ_API_KEY` trong `backend/.env`; cấu hình hiện tại dùng mô hình `qwen/qwen3.8-27b`.
- **Ollama:** lựa chọn chạy tại máy với mô hình `qwen3-vl:4b`, không yêu cầu khóa dịch vụ bên ngoài.

Xem [hướng dẫn cấu hình AI](docs/SETUP_AI_FREE.md). Việc tích hợp đã được kiểm tra ở mức phản hồi mô phỏng và xử lý lỗi; **chưa có xác nhận kiểm thử thành công khả năng nhận diện ảnh với dịch vụ AI thật**. Khi chưa cấu hình AI, người dùng vẫn có thể nhập dữ liệu thủ công hoặc sử dụng mẫu.

**Bảo mật:** Không đưa `backend/.env` hoặc bất kỳ khóa truy cập nào lên GitHub. Chỉ chia sẻ `.env.example`.

## 🧪 Kiểm thử

**Máy chủ** (sau khi tạo môi trường và cài thư viện, chạy trong `backend`):

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

**Giao diện** (chạy trong `frontend`):

```powershell
npm.cmd run typecheck
npm.cmd run build
```

Các trường hợp kiểm thử bao gồm mái đa giác, mái nghiêng, hướng Bắc, bóng nhà lân cận, ngân sách bằng 0, xác nhận phương án, lưu phiên bản và lỗi dịch vụ AI. Xem [biên bản kiểm thử](docs/MVP_VALIDATION.md) để biết phạm vi đã kiểm tra.

## 📁 Cấu trúc dự án

```text
SolarOpt/
├── backend/
│   ├── app/
│   │   ├── services/       # Xử lý ảnh, hình học, mô phỏng, tối ưu và kiểm tra
│   │   └── database.py     # Lưu lịch sử phiên bản tại máy chủ
│   ├── tests/              # Kiểm thử
│   └── requirements.txt    # Thư viện Python
├── frontend/
│   └── src/
│       ├── components/     # Thành phần giao diện và bản vẽ tương tác
│       └── services/       # Kết nối máy chủ
├── docs/                   # Hướng dẫn và báo cáo kiểm thử
├── sample_data/            # Dữ liệu mẫu
├── run_backend.bat
├── run_frontend.bat
└── README.md
```

Một số mô-đun đáng chú ý: `frontend/src/components/RoofCanvas.tsx` (biên tập mái), `backend/app/services/solar.py` (mặt trời), `optimizer.py` (bố trí), `verifier.py` (kiểm tra) và `dependency.py` (theo dõi tác động khi thay đổi dữ liệu).

## ⚠️ Phạm vi và giới hạn

SolarOpt hiện hướng tới **đánh giá sơ bộ**, không phải bộ công cụ chứng nhận thiết kế hoặc dự báo sản lượng đã được đối chuẩn:

- Chưa tự tái dựng mô hình 3D đầy đủ từ ảnh; độ cao và một số thông số hình học cần người dùng nhập và xác nhận.
- Tách biên và hiệu chuẩn ảnh có giới hạn; chưa hợp nhất tọa độ nhiều ảnh chụp.
- Mô phỏng bức xạ tức thời dựa trên điều kiện **trời quang**, không phản ánh đầy đủ mây và thời tiết thực tế.
- Ước lượng điện năng năm sử dụng **9 thời điểm bóng đại diện**, chưa mô phỏng từng giờ của cả năm hoặc đối chuẩn với dữ liệu vận hành.
- Ước tính chi phí phương án mới bao gồm **tấm pin**, chưa tính đầy đủ biến tần, khung, dây dẫn, nhân công và lợi nhuận.
- Chưa thay thế kiểm tra kết cấu mái, an toàn điện, thiết kế chuỗi điện hoặc yêu cầu phòng cháy chữa cháy.
- Được thiết kế để trình diễn trên máy cá nhân; chưa triển khai hệ thống tài khoản và phân quyền nhiều người dùng.

## 📚 Tài liệu kỹ thuật

- [Thiết lập AI và giới hạn sử dụng](docs/SETUP_AI_FREE.md)
- [Quy trình xử lý ảnh mái](docs/ROOF_IMAGE_PIPELINE.md)
- [Hiện trạng kỹ thuật và các hạng mục còn thiếu](docs/MVP_TECH_STATUS.md)
- [Biên bản kiểm thử](docs/MVP_VALIDATION.md)

---

<div align="center">

**SolarOpt Studio** · Hỗ trợ ra quyết định thiết kế điện mặt trời áp mái dựa trên dữ liệu.

*Bản MVP kỹ thuật — các kết quả cần được kỹ sư kiểm tra trước khi sử dụng trong thực tế.*

</div>
