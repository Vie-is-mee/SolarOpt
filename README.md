# SolarOpt Studio — MVP kỹ thuật

Ứng dụng hỗ trợ kỹ sư nhập ảnh và số đo mái, sửa dữ liệu, mô phỏng mặt trời/bóng che, tạo phương án bố trí tấm pin, kiểm tra và lưu bản duyệt sơ bộ. Giao diện và các bước tính toán đã được nối với máy chủ; kết quả bố trí không còn là số liệu dựng sẵn trong giao diện.

## Mở bản đang chạy

- Website: http://127.0.0.1:5173
- Tài liệu API: http://127.0.0.1:8000/docs

Nếu hai tiến trình đã dừng, chạy lại theo hướng dẫn dưới đây. Không mở trực tiếp `frontend/index.html` bằng đường dẫn tệp: dự án dùng React/Vite và cần máy chủ Python cho các phép tính.

## Chạy trên Windows

Cần Python 3.11+ và Node.js tương thích Vite 8 (Node 22.12+ hoặc bản hỗ trợ mới hơn). Có thể dùng Miniconda nếu máy đã cài sẵn.

Cách nhanh: mở `run_backend.bat`, chờ cài thư viện và máy chủ sẵn sàng; mở `run_frontend.bat` trong cửa sổ thứ hai. Lần đầu cần mạng để cài thư viện. Nếu cài đặt báo lỗi, kiểm tra lỗi trong cửa sổ lệnh trước khi demo.

Hoặc dùng PowerShell, tại thư mục chứa README này:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Chỉ sao chép `.env.example` khi chưa có `.env`, để giữ cấu hình đã nhập. Mở cửa sổ PowerShell thứ hai:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev -- --host 127.0.0.1
```

## AI miễn phí

Mặc định đã tích hợp **Groq + `qwen/qwen3.8-27b`**. Điền `GROQ_API_KEY` trong `backend/.env`, rồi khởi động lại Python. Có lựa chọn **Ollama + `qwen3-vl:4b`** chạy tại máy không cần khóa. Xem [hướng dẫn cấu hình và hạn mức](docs/SETUP_AI_FREE.md).

Khi chưa có khóa, luồng nhập tay và mẫu vẫn hoạt động. Ứng dụng không tạo vật cản giả để báo AI đã đọc ảnh. Việc nhận diện bằng dịch vụ thật chưa được kiểm tra khi đội chưa cung cấp khóa; tích hợp đã có kiểm thử phản hồi, lỗi hạn mức và dữ liệu không hợp lệ.

## Năm bước sử dụng

1. **Dữ liệu đầu vào:** chọn ảnh drone chụp thẳng xuống, bản vẽ hoặc ảnh một phần; thêm tối đa hai ảnh chi tiết. Nhập vị trí và kích thước thật. Có thể bắt đầu bằng dự án mẫu được gắn nhãn.
2. **Xác nhận bản vẽ:** vẽ biên mái, kéo/chỉnh vật cản, nhập hướng Bắc và cao độ mái. Thêm nhà bên cạnh theo hướng, khoảng cách, số tầng rồi kiểm tra chiều cao và mặt bằng. Kỹ sư xác nhận trước khi bố trí.
3. **Nắng và bóng che:** đổi ngày/giờ, xem bóng chuyển động và bản đồ bức xạ trời quang. Các thay đổi không gọi thêm AI. Có nút lấy dữ liệu nắng năm từ PVGIS khi có mạng.
4. **Bố trí tấm pin:** tính ba phương án bằng các ngưỡng bóng khác nhau, xét biên mái, khoảng lùi, vật cản, số đo tấm và ngân sách.
5. **Kiểm tra và bàn giao:** chạy kiểm tra, thử tám tình huống sai số, lưu bản kỹ sư duyệt, tải JSON/SVG hoặc in PDF có bản vẽ. Đổi dữ liệu sẽ đánh dấu kết quả cũ; cập nhật lại có ưu tiên giữ vị trí tấm pin trước đó.

Hướng trục trên bản vẽ là góc của trục +Y so với Bắc thật, đo thuận chiều kim đồng hồ. Với mặc định 0°, phía trên bản vẽ là Bắc. Chiều cao vật trên mái đo từ mặt mái; nhà bên cạnh đo từ mặt đất. Đây là các thông tin khác nhau và đều ảnh hưởng đến bóng.

## Phạm vi của bản demo

- Biên mái đa giác, khoảng trống, các vùng cao/thấp có độ dốc riêng; vật cản chữ nhật, bầu dục hoặc đa giác xoay được. Cao độ do kỹ sư nhập; chưa tự dựng lại 3D từ ảnh.
- Tách biên bằng OpenCV trên CPU, sửa bằng điểm giữ/loại hoặc chấm biên; hiệu chuẩn một đoạn thật. Hiệu chỉnh bốn góc chỉ cho một mặt phẳng chữ nhật với hai cạnh thật; chưa ghép tọa độ nhiều ảnh. Xem [hướng dẫn thao tác](docs/ROOF_IMAGE_PIPELINE.md).
- Bức xạ tại thời điểm là mô hình trời quang, không phải số đo hiện trường/dự báo mây.
- Điện năng năm là ước lượng sơ bộ bằng chín thời điểm bóng đại diện; chưa mô phỏng theo giờ cả năm và đối chuẩn.
- Giá trong phương án chỉ gồm tấm pin; chưa gồm bộ biến đổi điện, khung, dây, thi công hoặc tính lợi nhuận.
- Kiểm tra hình học và dữ liệu không thay thế kiểm tra tải mái, đấu chuỗi điện, thiết bị hoặc yêu cầu phòng cháy.
- Dành cho demo trên máy cá nhân; chưa có tài khoản và phân quyền dùng chung.

Xem [hiện trạng, các việc còn thiếu và kịch bản demo](docs/MVP_TECH_STATUS.md). Tài liệu thương mại đã lưu riêng tại `output/pdf/SolarOpt_Thuong_mai_Tiep_thi_Trien_khai_thuc_te.pdf`.

## Kiểm tra mã

Tại `backend`, sau khi cài thư viện:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tại `frontend`:

```powershell
npm.cmd run typecheck
npm.cmd run build
```

Các kiểm thử gồm bóng nhà bên cạnh, xoay hướng Bắc, mái nghiêng, mái đa giác, ngân sách bằng 0, kiểm tra bố trí gốc, yêu cầu xác nhận, lưu phiên bản đầy đủ và xử lý lỗi AI. Xem [biên bản kiểm tra](docs/MVP_VALIDATION.md) để phân biệt kiểm thử mô phỏng phản hồi AI với thử nghiệm mô hình thật.

## Cấu trúc chính

- `frontend/src/App.tsx`: luồng năm bước.
- `frontend/src/components/RoofCanvas.tsx`: mặt bằng tương tác và bản vẽ xuất.
- `frontend/src/services/studioApi.ts`: kết nối máy chủ.
- `backend/app/services/vision.py`: trích xuất ảnh qua nhà cung cấp đã chọn.
- `backend/app/services/geometry.py`, `solar.py`, `scene.py`: hình học, vị trí mặt trời và mô phỏng.
- `backend/app/services/optimizer.py`, `verifier.py`, `stress.py`: bố trí và kiểm tra.
- `backend/app/services/dependency.py`: truy vết ảnh hưởng thay đổi.
- `backend/app/database.py`: lịch sử phiên bản SQLite tại máy chủ.
- `docs/legacy/App.v1.tsx`: giao diện cũ để tham khảo, không chạy trong ứng dụng hiện tại.

Khóa AI chỉ được đọc ở máy chủ. `.env`, cơ sở dữ liệu, thư viện cài đặt và bản đóng gói được loại khỏi Git qua `.gitignore`.
