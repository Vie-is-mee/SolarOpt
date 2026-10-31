# Chạy SolarOpt Studio trên web

## Chạy trên Windows

Thư mục gốc là `SolarOpt-main-1/SolarOpt-main/SolarOpt-main` (thư mục có README này, backend và frontend).
Chạy `run_backend.bat`, sau đó `run_frontend.bat`. Python 3.11 và Node 22.12 trở lên là điều kiện cần.
Mở http://127.0.0.1:5174. Backend chạy ở http://127.0.0.1:8001/api/health.
Vite chuyển các yêu cầu `/api` tới backend nên trình duyệt không cần cấu hình CORS riêng.
Các biến `SOLAROPT_WEB_PORT` và `SOLAROPT_API_URL` cho phép thay cổng frontend và địa chỉ backend.
AI cục bộ lấy cấu hình từ `backend/.env`. Không chia sẻ file này; không đưa key vào frontend.

## VPS Linux: Docker Compose + Caddy

1. Chuẩn bị VPS có Docker Compose, tên miền trỏ tới IP máy chủ, mở cổng 80/443.
2. Đưa mã nguồn lên máy chủ; loại bỏ `.env`, node_modules, .venv và các file database khỏi gói chia sẻ.
3. Sao chép `.env.example` ở thư mục gốc thành `.env`. Điền DOMAIN, DEMO_USER, AI_PROVIDER và model có quyền dùng trong tài khoản của bạn, cùng API key tương ứng.
4. Tạo mật khẩu băm: `docker run --rm -it caddy:2-alpine caddy hash-password`. Điền hash vào DEMO_PASSWORD_HASH trong dấu nháy đơn. Giữ `.env` chỉ cho chủ sở hữu đọc.
5. Chạy `docker compose config --quiet`, rồi `docker compose up -d --build`.
6. Truy cập tên miền qua HTTPS và đăng nhập. Kiểm tra `/api/health`, upload ảnh, xác nhận mái, sinh phương án, kiểm chứng, sửa vật cản, lịch sử và in báo cáo.

Caddy phục vụ frontend và chuyển `/api` tới backend nội bộ. Backend không công bố cổng ra Internet.
SQLite nằm trên volume `database`; chứng chỉ nằm trên `caddy_data`. Không dùng `docker compose down -v` vì lệnh đó xóa dữ liệu.
Upload qua proxy tối đa 40 MB cho cả yêu cầu; backend giới hạn từng ảnh 12 MB, tối đa ba ảnh. PDF chỉ xử lý trang đầu.
Máy chủ giới hạn tác vụ nặng đồng thời; quá tải trả 429 để người dùng thử lại.
Ollama không nằm trong bộ Compose này. Nếu muốn chạy AI tại máy chủ, cần tự triển khai Ollama và cấu hình mạng phù hợp; không dùng địa chỉ localhost trong container để truy cập máy chủ khác.

## Sao lưu và cập nhật

Dịch vụ backup tạo bản sao SQLite mỗi 24 giờ bằng SQLite Backup API, kiểm tra tính toàn vẹn và giữ 14 bản gần nhất trên volume backups.
Sao lưu ngay: `docker compose run --rm backup python ops/backup.py`.
Tải backup ra thiết bị khác; backup cùng VPS chưa bảo vệ khỏi mất toàn bộ máy chủ.
Trước cập nhật, ghi lại RELEASE_TAG và giữ image cũ. Dùng RELEASE_TAG mới khi build; nếu cần quay lại, đặt tag cũ và chạy `docker compose up -d --no-build`.
Chỉ rollback sau khi xác nhận phiên bản cũ tương thích cấu trúc database. Thử phục hồi backup trên một database riêng trước khi dùng cho demo.

## Phạm vi và giới hạn cần nghiệm thu

Tài khoản email/mật khẩu và lịch sử riêng đã được hỗ trợ; xem [hướng dẫn tài khoản](ACCOUNTS.md). Khách có thể tính phương án nhưng không lưu lịch sử máy chủ. Caddy Basic Auth vẫn là lớp truy cập demo bên ngoài, tách biệt với tài khoản cá nhân trong ứng dụng.
Biên mái từ ảnh cần người dùng hiệu chỉnh, đặt tỷ lệ và xác nhận. Không suy ra kích thước thật hoặc chiều cao đáng tin cậy chỉ từ một ảnh.
Repair hiện chạy lại tối ưu; đồ thị ảnh hưởng không chứng minh đã tính lại chọn lọc.
AI chỉ được coi là hoạt động sau khi thử với model và key thật trên máy chủ; không lấy việc có key làm bằng chứng gọi API thành công.
Trước công khai cần kiểm tra Docker build, HTTPS, đăng nhập, mất kết nối AI, restart giữ lịch sử, phục hồi backup và tải đồng thời.
