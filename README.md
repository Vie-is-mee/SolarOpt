<h1 align="center">SolarOpt Studio</h1>

<p align="center"><strong>Hệ thống hỗ trợ thiết kế và đánh giá sơ bộ phương án điện mặt trời áp mái</strong></p>

<p align="center">
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-20232A?style=flat-square&amp;logo=react&amp;logoColor=61DAFB" alt="React" /></a>
  <a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&amp;logo=typescript&amp;logoColor=white" alt="TypeScript" /></a>
  <a href="https://vite.dev/"><img src="https://img.shields.io/badge/Vite-646CFF?style=flat-square&amp;logo=vite&amp;logoColor=white" alt="Vite" /></a>
  <a href="https://tailwindcss.com/"><img src="https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=flat-square&amp;logo=tailwindcss&amp;logoColor=white" alt="Tailwind CSS" /></a>
</p>
<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&amp;logo=python&amp;logoColor=white" alt="Python" /></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&amp;logo=fastapi&amp;logoColor=white" alt="FastAPI" /></a>
  <a href="https://opencv.org/"><img src="https://img.shields.io/badge/OpenCV-5C3EE8?style=flat-square&amp;logo=opencv&amp;logoColor=white" alt="OpenCV" /></a>
  <a href="https://www.sqlite.org/"><img src="https://img.shields.io/badge/SQLite-003B57?style=flat-square&amp;logo=sqlite&amp;logoColor=white" alt="SQLite" /></a>
</p>

SolarOpt Studio hỗ trợ chuyển đổi ảnh hoặc bản vẽ mái nhà thành dữ liệu hình học có thể chỉnh sửa, mô phỏng ảnh hưởng của nắng và bóng che, đề xuất phương án bố trí tấm pin và kiểm tra kết quả trước khi bàn giao.

Dự án hiện ở giai đoạn **MVP kỹ thuật** (phiên bản sản phẩm tối thiểu có thể kiểm thử). Hệ thống phục vụ nghiên cứu, trình diễn và đánh giá giải pháp; các kết quả chưa thay thế hồ sơ thiết kế thi công đã được kiểm chứng.

## Tổng quan

Bố trí điện mặt trời áp mái đòi hỏi xem xét đồng thời diện tích khả dụng, hình dạng mái, vật cản, công trình xung quanh, hướng nắng, yêu cầu khoảng cách và ngân sách. SolarOpt tổ chức những thông tin này thành một quy trình thống nhất, trong đó người dùng có thể kiểm tra và hiệu chỉnh dữ liệu trước khi hệ thống tính toán.

Điểm trọng tâm của dự án là **khả năng cập nhật phương án khi điều kiện thiết kế thay đổi**. Nếu người dùng điều chỉnh vật cản, chiều cao hoặc thông số mái, hệ thống nhận diện dữ liệu đã thay đổi, đánh dấu phương án cũ cần cập nhật và có thể tính lại với ưu tiên giữ các vị trí tấm pin còn phù hợp.

## Chức năng chính

| Nhóm chức năng | Mô tả |
| --- | --- |
| Tiếp nhận dữ liệu | Nhập ảnh chụp mái, bản vẽ hoặc ảnh một phần mái; bổ sung vị trí địa lý và kích thước thực tế. |
| Hiệu chỉnh bản vẽ | Chỉnh biên mái đa giác, vùng mái cao/thấp, khoảng trống, vật cản, hướng Bắc và công trình lân cận. |
| Phân tích ảnh có hỗ trợ AI | Tích hợp tùy chọn dịch vụ nhận diện ảnh để gợi ý biên mái và vật cản; người dùng xác nhận trước khi sử dụng. |
| Mô phỏng nắng và bóng che | Tính vị trí mặt trời theo địa điểm và thời gian; thể hiện bóng che và bức xạ theo mô hình trời quang. |
| Đề xuất bố trí tấm pin | Tạo ba phương án với mức ưu tiên khác nhau, có xét hình học, bóng che, khoảng cách an toàn và ngân sách. |
| Kiểm tra phương án | Kiểm tra các điều kiện hình học, thông số, ngân sách và thử tám tình huống sai số trên phương án hiện tại. |
| Quản lý kết quả | Lưu lịch sử phiên bản, cập nhật thiết kế sau thay đổi và xuất dữ liệu JSON, bản vẽ SVG hoặc báo cáo PDF. |

### Quy trình sử dụng

1. **Nhập dữ liệu:** Cung cấp ảnh mái hoặc bản vẽ, tọa độ và các số đo thực tế.
2. **Xác nhận hình học:** Chỉnh đường biên, vật cản, cao độ và hướng của bản vẽ.
3. **Mô phỏng điều kiện chiếu sáng:** Xem vị trí mặt trời, bóng che và phân bố bức xạ theo thời gian.
4. **Tính toán phương án:** Tạo và so sánh các cách bố trí tấm pin dựa trên dữ liệu đã xác nhận.
5. **Kiểm tra và bàn giao:** Đánh giá ràng buộc, thử tình huống sai số, lưu bản duyệt sơ bộ và xuất kết quả.

Quy trình nhập tay và dự án mẫu vẫn sử dụng được khi chưa cấu hình dịch vụ AI.

## Kiến trúc hệ thống

SolarOpt sử dụng giao diện web kết nối đến máy chủ Python. Việc xử lý hình học, mô phỏng, tối ưu và kiểm tra phương án được thực hiện ở máy chủ, thay vì sử dụng những kết quả cố định trên giao diện.

| Thành phần | Công nghệ | Vai trò |
| --- | --- | --- |
| Giao diện | React 19, TypeScript, Vite 8 | Nhập dữ liệu, biên tập bản vẽ và hiển thị kết quả. |
| Máy chủ | Python, FastAPI | Cung cấp các chức năng xử lý và giao tiếp với giao diện. |
| Xử lý ảnh | OpenCV, Pillow | Hỗ trợ tách biên và xử lý dữ liệu ảnh. |
| Hình học và tối ưu | Shapely, Google OR-Tools | Kiểm tra hình học, tạo và lựa chọn vị trí bố trí tấm pin. |
| Mô phỏng nắng | pvlib | Tính vị trí mặt trời và các đại lượng bức xạ sử dụng trong mô phỏng. |
| Lưu trữ | SQLite | Lưu lịch sử phiên bản tại máy chủ. |
| Dữ liệu bổ sung | PVGIS | Tùy chọn truy xuất dữ liệu nắng năm khi có mạng. |
| Nhận diện ảnh | Groq, Ollama hoặc Gemini | Tích hợp tùy chọn theo cấu hình máy chủ. |

Các phần xử lý được tách thành các mô-đun riêng cho hình học, vị trí mặt trời, bố trí, kiểm tra, thử sai số và xác định ảnh hưởng khi đầu vào thay đổi.

## Cài đặt và chạy trên Windows

### Yêu cầu

- Python **3.11 trở lên**.
- Node.js **22.12 trở lên**, hoặc phiên bản tương thích với Vite 8.
- Git (nếu tải dự án bằng lệnh `git clone`).
- Kết nối Internet khi cài thư viện hoặc sử dụng các dịch vụ trực tuyến.

### 1. Tải mã nguồn

```powershell
git clone https://github.com/Vie-is-mee/SolarOpt.git
cd SolarOpt
```

### 2. Khởi chạy nhanh

Tại thư mục gốc dự án, chạy `run_backend.bat` để cài các thư viện cần thiết và khởi động máy chủ. Sau khi máy chủ sẵn sàng, mở một cửa sổ khác và chạy `run_frontend.bat`.

Truy cập:

| Địa chỉ | Mục đích |
| --- | --- |
| `http://127.0.0.1:5173` | Giao diện SolarOpt Studio |
| `http://127.0.0.1:8000/docs` | Tài liệu các điểm giao tiếp của máy chủ (API) |

Không mở trực tiếp `frontend/index.html` bằng trình duyệt; giao diện cần máy chủ Vite và máy chủ Python.

### 3. Chạy thủ công bằng PowerShell

**Cửa sổ thứ nhất — máy chủ**

Mở PowerShell tại thư mục gốc dự án:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
}

.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Cửa sổ thứ hai — giao diện**

Mở một cửa sổ PowerShell mới tại thư mục gốc dự án:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev -- --host 127.0.0.1
```

Nếu đã tạo và cấu hình `backend/.env`, không ghi đè tệp này khi cài đặt lại.

## Cấu hình AI (tùy chọn)

Hệ thống hỗ trợ nhập dữ liệu thủ công. Nếu cần nhận diện ảnh có hỗ trợ AI, tạo `backend/.env` từ `backend/.env.example` và chọn một nhà cung cấp phù hợp.

Ví dụ cấu hình Groq:

```dotenv
AI_PROVIDER=groq
AI_MODEL=qwen/qwen3.8-27b
GROQ_API_KEY=your_api_key
```

Có thể chọn Ollama để chạy mô hình tại máy hoặc Gemini thông qua cấu hình tương ứng. Sau khi thay đổi cấu hình, khởi động lại máy chủ Python.

**Lưu ý về dữ liệu và kiểm chứng:** Khi sử dụng dịch vụ AI trực tuyến, ảnh đầu vào sẽ được gửi đến nhà cung cấp được chọn. Khả năng gọi Groq đã được thử nghiệm trên ảnh tự tạo; độ chính xác với mái thực tế chưa được đánh giá đầy đủ. Các đề xuất nhận diện cần được người dùng kiểm tra và xác nhận.

Xem hướng dẫn tại [docs/SETUP_AI_FREE.md](docs/SETUP_AI_FREE.md). Không đưa `backend/.env` hoặc khóa truy cập vào kho GitHub.

## Kiểm thử

Trong thư mục `backend`, sau khi cài thư viện:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Trong thư mục `frontend`:

```powershell
npm.cmd run typecheck
npm.cmd run build
```

Bộ kiểm thử bao gồm những tình huống liên quan đến hình học mái, bóng che, vật cản, ngân sách, xác nhận dữ liệu, lưu và cập nhật phương án. Kết quả kiểm thử được ghi trong [docs/MVP_VALIDATION.md](docs/MVP_VALIDATION.md).

Biên bản hiện có ghi nhận các kiểm tra trên môi trường phát triển và ảnh thử nghiệm. Chưa có bằng chứng đối chuẩn đầy đủ trên mái nhà thực tế hoặc kiểm thử lại toàn bộ trong một môi trường cài đặt sạch.

## Cấu trúc thư mục

```text
SolarOpt/
├── backend/
│   ├── app/
│   │   ├── services/       # Xử lý ảnh, hình học, nắng, tối ưu và kiểm tra
│   │   ├── database.py     # Lưu lịch sử phiên bản
│   │   └── main.py         # Các điểm giao tiếp của máy chủ
│   ├── tests/              # Kiểm thử máy chủ
│   └── requirements.txt    # Thư viện Python
├── frontend/
│   ├── src/
│   │   ├── components/     # Các thành phần giao diện
│   │   └── services/       # Kết nối đến máy chủ
│   └── package.json
├── docs/                   # Tài liệu kỹ thuật và kiểm thử
├── sample_data/            # Dữ liệu ví dụ
├── run_backend.bat
├── run_frontend.bat
└── README.md
```

Các mô-đun chính có thể tham khảo:

- `frontend/src/App.tsx`: quy trình sử dụng năm bước.
- `frontend/src/components/RoofCanvas.tsx`: bản vẽ mái tương tác.
- `backend/app/services/roof_extract.py`: xử lý biên mái từ ảnh.
- `backend/app/services/solar.py`: tính toán liên quan đến vị trí mặt trời.
- `backend/app/services/optimizer.py`: tạo phương án bố trí tấm pin.
- `backend/app/services/verifier.py`: kiểm tra phương án.
- `backend/app/services/dependency.py`: xác định ảnh hưởng khi dữ liệu thay đổi.

## Phạm vi và giới hạn hiện tại

SolarOpt là công cụ **hỗ trợ đánh giá sơ bộ**. Khi sử dụng kết quả, cần lưu ý:

- Chưa tự tái dựng chính xác mô hình ba chiều của mái và công trình xung quanh từ ảnh; kích thước và cao độ cần được đo, nhập hoặc xác nhận.
- Chưa hợp nhất tọa độ từ nhiều ảnh chụp thành một mô hình hình học hoàn chỉnh.
- Bức xạ tại thời điểm dựa trên mô hình trời quang, không phải dữ liệu đo hiện trường hoặc dự báo mây.
- Điện năng năm được quy đổi theo hướng/độ dốc riêng từng mặt mái từ 12 ngày trời quang đại diện; bóng dùng chín thời điểm. Chưa mô phỏng thời tiết từng giờ cả năm hoặc đối chuẩn với hệ thống thực. Mặt tham chiếu dữ liệu nắng phải được khai báo đúng.
- Bố trí được tối ưu trong phạm vi lưới vị trí ứng viên và hướng đặt tấm đang hỗ trợ; chưa khảo sát mọi cấu hình khả thi.
- Giá trong các phương án hiện chỉ tính phần tấm pin, chưa phản ánh đầy đủ chi phí đầu tư và thi công.
- Các kiểm tra trong ứng dụng không thay thế đánh giá kết cấu mái, an toàn điện, thiết kế chuỗi điện và yêu cầu phòng cháy chữa cháy.
- Bản hiện tại hướng tới chạy thử trên máy cá nhân; chưa có hệ thống tài khoản và phân quyền nhiều người dùng.

## Tài liệu liên quan

| Tài liệu | Nội dung |
| --- | --- |
| [Hiện trạng kỹ thuật](docs/MVP_TECH_STATUS.md) | Chức năng đã triển khai, giới hạn và ưu tiên phát triển tiếp theo. |
| [Biên bản kiểm thử](docs/MVP_VALIDATION.md) | Các trường hợp kiểm tra và kết quả đã ghi nhận. |
| [Sửa logic bước 1 — 15/10/2026](docs/STEP1_LOGIC_FIXES.md) | Năm vấn đề đã sửa, 100 kiểm thử và kế hoạch đối chiếu mái thật. |
| [Đối chiếu bước 2 — 15/10/2026](docs/STEP2_REFERENCE_VALIDATION.md) | Bộ đánh giá, ba ca tính tay và mẫu chờ dữ liệu mái thật. |
| [Ảnh drone công khai — bước 3](docs/STEP3_PUBLIC_ROOF_BENCHMARK.md) | Đối chiếu 50 mái Nacala, kết quả biên mái và giới hạn kiểm chứng. |
| [Quy trình xử lý ảnh mái](docs/ROOF_IMAGE_PIPELINE.md) | Tiếp nhận ảnh, tách biên và hiệu chỉnh hình học. |
| [Hướng dẫn cấu hình AI](docs/SETUP_AI_FREE.md) | Cấu hình nhà cung cấp và lưu ý khi sử dụng. |
| [Kịch bản trình diễn](docs/DEMO_SCRIPT_5MIN.md) | Trình tự giới thiệu các chức năng chính. |

---

**SolarOpt Studio** — Dự án phát triển công cụ hỗ trợ thiết kế điện mặt trời áp mái dựa trên dữ liệu, mô phỏng và kiểm tra phương án.
