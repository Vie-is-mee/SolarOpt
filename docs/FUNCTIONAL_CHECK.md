# Kiểm tra chức năng ngày 10/10/2026

Kiểm tra tại http://127.0.0.1:5174, backend cổng 8001. Kết quả áp dụng cho bản mã hiện tại và dữ liệu thử tổng hợp; chưa phải nghiệm thu thiết kế điện mặt trời thực tế.

| Chức năng | Kết quả kiểm tra |
|---|---|
| Backend | 39 bài pytest đạt |
| Frontend | TypeScript và build đạt; không có lỗi JavaScript trong luồng thử |
| Nhập/xuất JSON | Tải dự án, nhập lại thành công; yêu cầu xác nhận lại |
| Upload | PNG hợp lệ trả 200; ảnh hỏng trả 422; quá 12 MB trả 413 |
| Ảnh sang biên mái | Biên thủ công 6 đỉnh qua API; upload, tách biên OpenCV và áp dụng mái qua UI thành công |
| Hiệu chỉnh phối cảnh | Kiểm thử tự động 4 góc với tỷ lệ hai cạnh đạt; chưa đánh giá ảnh công trình thực |
| AI | Groq/model đang cấu hình trả 200 trên ảnh mái tổng hợp; chưa đánh giá độ chính xác trên ảnh thực |
| Bức xạ | PVGIS trả dữ liệu thật tại TP.HCM: 1854 kWh/m²/năm, suất điện 1385 kWh/kWp/năm |
| Tối ưu | Ba mục tiêu đều trả phương án qua UI |
| Kiểm chứng | Ca mẫu đạt các điều kiện bộ kiểm chứng đã triển khai |
| Stress test | 7/8 đạt; ca tăng lùi mép 15 cm phát hiện vi phạm vùng mái |
| Độ nhạy chiều cao | API và giao diện chạy thành công |
| Repair | Tăng chiều cao vật cản từ 1,2 lên 4 m: 19 xuống 18 panel, giữ 18 vị trí, kiểm chứng hợp lệ |
| Lịch sử/bản duyệt | Lưu bản duyệt, xem phiên bản, khôi phục đầu vào và yêu cầu xác nhận lại thành công |
| Xuất báo cáo | SVG được tải; chế độ in tạo PDF thành công; chưa nghiệm thu trình bày mọi trường hợp báo cáo dài |
| Điện thoại | Trang thử ở 390 × 844 không tràn ngang; chưa thử toàn bộ thao tác chạm trên thiết bị thật |

Lỗi AI/PVGIS đầu phiên do backend được chạy trong môi trường hạn chế kết nối. Sau khởi động lại backend với quyền mạng phù hợp, hai API qua web hoạt động. Không thay khóa hoặc model.

## Các giới hạn còn lại

- Lịch sử nhóm theo tên dự án; chưa có mã dự án riêng và phân quyền từng người dùng.
- Repair chạy lại bộ tối ưu có ưu tiên giữ vị trí; chưa có tính lại chọn lọc thực sự.
- Sản lượng dùng các thời điểm bóng che đại diện, chi phí chỉ gồm panel; chưa đối chuẩn với dữ liệu EPC thực tế.
- Chưa kiểm thử Docker, HTTPS, tài khoản demo, tải đồng thời trên VPS hay phục hồi dữ liệu sau restart container.
- Thành công gọi AI không chứng minh độ chính xác nhận diện và đo kích thước; cần kỹ sư xác nhận hình học.

Kết luận: luồng prototype cục bộ hoạt động trên dữ liệu thử. Có thể demo quy trình; chưa đủ bằng chứng để kết luận sẵn sàng sử dụng cho thi công hoặc vận hành công khai.
