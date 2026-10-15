# Biên bản kiểm tra SolarOpt Studio

**Cập nhật 15/10/2026:** bước sửa logic đã đạt 100/100 kiểm thử Python, kiểm tra kiểu/đóng gói và luồng trình duyệt. Xem [biên bản bước 1](STEP1_LOGIC_FIXES.md). Nội dung bên dưới là bằng chứng lịch sử ngày 10/10, không thay cho trạng thái mới.

Ngày 10/10/2026, kiểm tra tại máy phát triển Windows, bằng trình duyệt Microsoft Edge không mở cửa sổ.

## Các kết quả đã kiểm tra

| Nhóm | Kết quả | Phạm vi |
|---|---|---|
| Máy chủ Python | 37 ca đạt | Bộ cũ 27 ca và 10 ca mới về tách biên, tỷ lệ/phối cảnh, vùng cao/thấp, hình dạng, khoảng trống và tấm không bắc qua hai mặt mái |
| Kiểu dữ liệu giao diện | `npm run typecheck` đạt | TypeScript, không có lỗi biên dịch kiểu |
| Đóng gói | `npm run build` đạt | React 19 / Vite 8.3.4, tạo `frontend/dist` |
| Luồng website | Đạt | Thêm nhà phía Đông, xác nhận dữ liệu, mô phỏng, tính ba phương án, kiểm tra, thử tám tình huống, lưu bản duyệt |
| Thay đổi phương án | Đạt | Đổi bồn nước từ 1,2 m thành 1,8 m, cảnh báo kết quả cũ, xác nhận và cập nhật, thống kê vị trí giữ lại |
| Bàn giao | Đạt | Tải JSON đủ đầu vào, SVG hợp lệ có các đối tượng bản vẽ, in PDF có sơ đồ mái |
| Khôi phục | Đạt | Khôi phục phiên bản máy chủ và nhập tệp JSON đều yêu cầu xác nhận lại |
| Chỉnh bản vẽ | Đạt | Phím mũi tên thay tọa độ vật cản; vị trí mới làm mất trạng thái xác nhận |
| Điện thoại | Đạt | Chiều rộng 390 px, cả năm bước không tràn ngang |
| Lỗi JavaScript | Không ghi nhận | Trong các luồng trình duyệt đã chạy |
| UI nhận diện ảnh | Đạt với phản hồi mô phỏng | Quan sát được hiển thị; độ cao thiếu có nhãn; ảnh một phần phải đặt lại vị trí; kỹ sư sửa và xác nhận được |

Đã kiểm tra trực tiếp trong trình duyệt: chấm mái lõm sáu đỉnh và áp dụng đúng tỷ lệ 12 × 10,006 m (không ép 12 × 9 m); thêm phần mái cao 9 m và khoảng trống; vật cản đa giác đổi sang bầu dục, xoay 30°, kéo đổi kích thước; kéo đỉnh mái, hoàn tác/làm lại; sửa hình học trong mô phỏng; màn hình 390 px không tràn ngang, không ghi nhận lỗi JavaScript. Đây là thao tác trên ảnh tự tạo, không phải bản vẽ đối chiếu mái thật.

Đã gọi `/api/vision/analyze` bằng cấu hình Groq thật: HTTP 200, trả biên đa giác và vật cản trên ảnh tự tạo. Phép thử không đọc hoặc in giá trị khóa.

Phản hồi mô phỏng chỉ được chặn trong trang kiểm thử, không đưa vào máy chủ hay chế độ dùng bình thường.

## Dữ liệu đối chiếu mô phỏng

Dùng mẫu mái 12 × 9 m, tọa độ 10,7769 / 106,7009, mái cao 6 m, ngày 10/10/2026 giờ Việt Nam, bồn nước/tum thang và một nhà phía Đông cao 16,5 m, cách mái 3 m.

| Chỉ số | 09:00 | 16:00 |
|---|---:|---:|
| Độ cao mặt trời | 46,5° | 23,1° |
| Phương vị mặt trời | 111,7° | 257,9° |
| Diện tích mặt bằng mái chịu bóng | 37,5 m² | 26 m² |
| Bức xạ trời quang trên mặt mái, trước bóng cục bộ | 666,9 W/m² | 290 W/m² |

Các giá trị khác nhau khi đổi giờ; không phải dữ liệu hiện trường. Với mẫu này, phương án cân bằng tính được 9 tấm. Đây là kết quả của mẫu đã kiểm tra, không phải số lượng cố định cho mọi mái.

## Môi trường kiểm tra và bằng chứng

- Thư viện kiểm tra được cài trong `J:/vi/tmp/solaropt-runtime`, bổ sung thư viện ảnh/PDF từ các thư mục tạm trong workspace. Lượt kiểm tra này dùng Shapely 2.2, pvlib 0.16.1, OR-Tools 9.15, OpenCV 4.13; các phiên bản này khác một số bản ghim trong `backend/requirements.txt`. Chưa tạo và kiểm thử lại một môi trường sạch từ toàn bộ tệp yêu cầu.
- Kiểm thử máy chủ dùng cơ sở dữ liệu tạm độc lập. Trình duyệt dùng máy chủ thật tại `127.0.0.1:8000`; những lần chạy demo tạo thêm phiên bản thử trong SQLite của máy phát triển.
- Mã kiểm thử máy chủ: `backend/tests/test_core.py`, `backend/tests/test_studio.py`, `backend/tests/test_roof_editor.py`.
- Kịch bản trình duyệt của lượt chạy này: `J:/vi/tmp/solaropt_browser_check.py` và `J:/vi/tmp/solaropt_ai_ui_check.py`. Playwright dùng để kiểm tra, chưa thêm vào thư viện bắt buộc của ứng dụng.
- Phần chỉnh mái mới: `J:/vi/tmp/solaropt_editor_check.py`, bằng chứng ảnh và kết quả tại `J:/vi/tmp/solaropt-editor/`.
- Bằng chứng tại `J:/vi/tmp/solaropt-browser/`: ảnh năm bước/điện thoại, `result.json`, `ai-ui-result.json`, `export-project.json`, `roof.svg`, `report.pdf`. Đây là dữ liệu kiểm tra và có thể bị xóa khi dọn thư mục tạm.

## Những gì chưa được xác nhận

- Groq đã gọi thật trên ảnh tự tạo; chưa chạy Ollama với mô hình đã tải. Chưa đo độ chính xác nhận diện mái/vật cản thật hoặc số bộ ảnh đọc được trong hạn mức tài khoản.
- Chưa đối chiếu bóng và sản lượng bằng khảo sát mái thực hoặc công cụ thiết kế chuẩn trên cùng bộ dữ liệu. Kiểm thử hình học không đồng nghĩa đã chứng minh độ chính xác ngoài thực tế.
- Chưa xác nhận kết nối PVGIS thực trong mọi điều kiện mạng; khi không có dữ liệu, ứng dụng giữ/ghi rõ giả định thay vì gắn nhãn dữ liệu lấy thành công.
- Chưa kiểm tra tải nhiều người dùng, tài khoản, phân quyền, trình duyệt khác và toàn bộ loại ảnh/PDF ngoài thực tế.

Các giới hạn công nghệ và thứ tự nâng cấp tiếp theo được mô tả trong `MVP_TECH_STATUS.md`.
