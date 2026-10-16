# Bước 5 — Lưu ảnh đối chiếu và hồ sơ số đo cùng dự án

Ngày: 16/10/2026.

## Vấn đề đã xử lý

Trước đây, tải lại trang, xuất/nhập JSON hoặc khôi phục lịch sử chỉ giữ hình học. Ảnh nền mái bị mất; thông tin hiệu chuẩn không giữ vị trí các điểm đo và hai số đo khung bao ban đầu. Đợt này bổ sung lưu trữ các căn cứ đó để kỹ sư mở lại và đối chiếu.

## Cách sử dụng

1. Chọn ảnh, trích/sửa biên và đo tham chiếu như bước 4.
2. Sau khi áp dụng biên, mở **Ảnh và hồ sơ số đo**. Ảnh có đoạn tham chiếu màu xanh và đoạn kiểm tra màu tím; bảng chữ giữ số đo đã nhập, kích thước suy từ ảnh và độ chênh lúc trích biên.
3. **Lưu dự án** tải một tệp JSON định dạng `solaropt-project-v3`, chứa đầu vào hình học, thông số pin, vật cản, mục tiêu, ảnh nguồn đã chuẩn hóa/hiệu chỉnh, ảnh nền đã cắt và hồ sơ đo.
4. **Nhập dự án JSON** mở lại gói đó. Hình học và ảnh được kiểm tra trước khi thay dự án đang mở. Phải xác nhận lại đầu vào và tính lại phương án.
5. Tải lại trang trên cùng trình duyệt: hình học lấy từ bản nháp, ảnh lấy từ IndexedDB nếu khớp chính xác dấu đối chiếu đầu vào. Trạng thái lưu được hiển thị cạnh tên dự án; lỗi lưu không bị bỏ qua im lặng.
6. Khi tạo, sửa hoặc duyệt phương án trên máy chủ, hồ sơ ảnh được gắn vào phiên bản. **Khôi phục** tải chi tiết phiên bản đó, giữ ảnh tương ứng và yêu cầu xác nhận/tính lại.

## Dữ liệu được giữ

| Thành phần | Nội dung |
| --- | --- |
| Ảnh dùng trích biên | Ảnh đã chuẩn hóa hoặc đã hiệu chỉnh phối cảnh, tên nguồn và loại đầu vào |
| Ảnh nền bản vẽ | Ảnh cắt khớp khung tọa độ mái |
| Hồ sơ hiệu chuẩn | Thời điểm, phương pháp, kích thước ảnh, tọa độ hai đầu đoạn tham chiếu và chiều dài thật |
| Kiểm tra độc lập | Tọa độ đoạn kiểm tra, số đo thật và độ chênh nếu đã khai báo |
| Số đo khung bao | Giữ hai số đo ban đầu riêng với hai kích thước suy từ ảnh |

Hồ sơ đo phản ánh thời điểm trích biên. Sửa hình học sau đó không biến hồ sơ cũ thành một lần đo mới. Mở lại hồ sơ không tự cấp trạng thái đã kiểm chứng ngoài hiện trường.

## Tương thích và giới hạn

- Tệp `solaropt-project-v2` vẫn nhập được. Tệp cũ không có ảnh sẽ xóa ảnh của dự án đang mở, tránh gắn nhầm ảnh cũ.
- Gói JSON tối đa 10 MB; mỗi ảnh nhúng tối đa 4 triệu ký tự mã hóa và 4 triệu điểm ảnh trên máy chủ. Chỉ chấp nhận JPEG, PNG và WEBP có dữ liệu hợp lệ; không tải ảnh từ địa chỉ bên ngoài trong tệp dự án.
- Hồ sơ đo phải có hai điểm tương ứng chiều dài; kích thước ảnh phải trùng với ảnh hiệu chuẩn đi kèm.
- Danh sách lịch sử không trả toàn bộ ảnh của mọi phiên bản. Ảnh chỉ được trả qua yêu cầu chi tiết của một phiên bản thuộc đúng tên dự án.
- Ảnh/PDF gốc chất lượng đầy đủ, các trang PDF khác và ảnh bổ sung không được đóng gói; cần giữ các tệp gốc riêng. Có thể tiếp tục trích biên từ ảnh đã khôi phục; muốn gửi lại bộ tệp gốc cho AI thì chọn lại các tệp đó.
- Ảnh tự lưu nằm trong trình duyệt trên máy hiện tại. Xóa dữ liệu trình duyệt có thể xóa bản nháp; gói JSON và phiên bản máy chủ là các bản lưu riêng.
- Máy chủ hiện lưu ảnh trong nội dung mỗi phiên bản SQLite; chưa có kho ảnh dùng chung để loại bản sao, tài khoản hoặc phân quyền nhiều người dùng.

## Kiểm tra

- Kiểm thử ảnh nhúng hỏng, URL ngoài, SVG, đoạn đo thiếu điểm, kích thước ảnh mâu thuẫn, đọc phiên bản sai tên dự án và tương thích đầu vào không có hồ sơ.
- Kiểm thử tạo phương án và duyệt phương án cùng giữ được hồ sơ hiệu chuẩn, bao gồm thời điểm được chuyển thành JSON hợp lệ.
- Kiểm thử giao diện về gói cũ/mới, giới hạn ảnh, mục tiêu không hợp lệ và dấu đối chiếu đầu vào không phụ thuộc thứ tự khóa JSON.
- Thử trình duyệt: xuất gói sau hiệu chuẩn; tải lại trang; làm lại từ đầu; nhập gói mới; nhập gói cũ; khôi phục lịch sử; từ chối gói sai mà không mất dự án hiện tại; kiểm tra màn hình nhỏ.

Các lệnh kiểm thử: `python -m pytest -q` trong `backend`; `npm test`, `npm run typecheck`, `npm run build` trong `frontend`.
