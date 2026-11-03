# Kịch bản demo SolarOpt (pitching 22/11)

Mục tiêu: trình bày trọn luồng **ảnh mái → AI đọc ảnh → mô phỏng bóng → trợ lý đề xuất theo nhu cầu khách → xếp pin → thiết kế điện → báo cáo** trong khoảng 3 phút, không phụ thuộc vào việc mô hình AI miễn phí có đang nghẽn hay không.

## Chế độ demo hoạt động thế nào

- Bấm nút **Demo** ở góc phải tiêu đề dự án để bật. Một thanh "Kịch bản demo" hiện các bước, bước kế tiếp được viền xanh, bước nào app tự làm được thì có nút bấm.
- Kết quả AI của **ảnh drone mẫu** và của **trợ lý cho khách mẫu** đã được ghi lại từ một lần gọi mô hình thật. Khi đầu vào khớp đúng, app phát lại ngay và ghi rõ: *"Phát lại kết quả AI thật đã ghi lúc … · mô hình … · lần gọi thật mất … giây"*.
- Đầu vào khác (sửa vật cản, đổi tiền điện, góp ý khác) thì app gọi AI thật như bình thường; trợ lý được giới hạn 30 giây, quá thời gian thì dùng các kịch bản đã thử và lý do của bộ quy tắc.
- Phát lại không cần internet, không cần đăng nhập và không trừ lượt. Bộ tối ưu, mô phỏng nắng và thiết kế điện vẫn tính thật trên máy.

> Khi giám khảo hỏi "AI có chạy thật không?": trả lời thẳng là bản ghi lấy từ lần chạy thật (nhãn ghi ngày, mô hình, thời gian), và có thể đổi một con số để app gọi AI trực tiếp.

## Chuẩn bị (tối hôm trước và 30 phút trước giờ thi)

1. Chạy máy chủ và giao diện như thường lệ (`run_backend.bat`, `run_frontend.bat`), mở `http://localhost:5174`.
2. **Đăng nhập tài khoản.** Chế độ khách chỉ tính được 6 dự án mỗi ngày; nếu chưa đăng nhập, bước xếp pin có thể bị chặn ngay trên sân khấu (thanh demo sẽ nhắc).
3. Bấm **Làm lại từ đầu** để xóa bản nháp cũ, rồi bấm **Demo**.
4. Chạy thử toàn bộ một lần theo các bước dưới; kiểm tra nhãn "Phát lại" xuất hiện ở bước đọc ảnh và trợ lý.
5. Bấm **Làm lại từ đầu** lần nữa trước khi lên sân khấu (chế độ Demo vẫn giữ nguyên).
6. Phóng to trình duyệt 110–125% cho khán phòng; tắt thông báo hệ điều hành.

## Các bước trên sân khấu (~3 phút)

| # | Thao tác | Nói gì (gợi ý) |
|---|---|---|
| 1 | **Nạp ảnh** (thanh demo) | "Kỹ sư chỉ cần một ảnh drone chụp thẳng mái và hai số đo khung mái 12 × 9 m." |
| 2 | **Đọc ảnh** | "AI nhận dạng mái 4 dốc, các vật cản và cả số đo in trên ảnh. Đây là đề xuất, kỹ sư luôn xác nhận." Chỉ vào nhãn bản ghi nếu cần. |
| 3 | **Áp dụng** → **Dựng mái** → tick "Tôi đã kiểm tra…" | "AI nhận ra mái 4 dốc; kỹ sư dựng các mặt mái theo đó. Dàn nóng AI chưa chắc vị trí nên được đánh dấu *vị trí tạm*; không có con số nào đi tiếp khi kỹ sư chưa xác nhận." Không kéo vật cản trên sân khấu: đổi vị trí thì trợ lý sẽ gọi AI thật thay vì phát lại. |
| 4 | **Mô phỏng**, mở 3D, kéo giờ trong ngày | "Bóng của từng vật cản được tính theo giờ, theo vị trí thật của mặt trời." |
| 5 | **Điền khách mẫu** → **Đề xuất phương án** | "Khách trả 2,5 triệu tiền điện mỗi tháng, muốn giảm chi phí. Trợ lý thử nhiều kịch bản trên chính mái này; mọi con số do bộ tối ưu và dòng tiền tính, AI chỉ chọn và giải thích." Chỉ vào các ô số liệu trích dẫn trong lý do. Ý hay: không có vật cản mái chứa 13 tấm, bốn vật cản AI tìm thấy (kèm khoảng cách an toàn và bóng) chỉ còn 6 — tự tính tay rất dễ bỏ sót. |
| 6 | Bấm gợi ý **"Khách sắp mua xe điện…"** → **Soạn lại đề xuất** | "Kỹ sư góp ý có lý do; trợ lý soạn lại bản v2 và giữ v1 để so sánh." |
| 7 | **Áp dụng S… và tính phương án** | "Một bấm: ngân sách, sản lượng mục tiêu và khoảng lùi mép được áp dụng, bộ tối ưu xếp pin lên mái." |
| 8 | **Đến bàn giao** → khung Thiết kế điện → **Đưa vật tư vào dự toán** → mở báo cáo | "Chia chuỗi, chọn inverter, kiểm tra điện áp lúc trời lạnh, bảng vật tư đưa thẳng vào dự toán và báo cáo PDF cho khách." |

## Khi có sự cố

- **Bị chặn ở bước xếp pin ("Chế độ khách…"):** đăng nhập rồi bấm lại **Áp dụng**.
- **Không có nhãn "Phát lại" ở bước 2:** kiểm tra số đo đúng 12 × 9 và đã nạp ảnh bằng nút **Nạp ảnh** (ảnh khác sẽ gọi AI thật).
- **Trợ lý không phát lại:** khách mẫu phải điền bằng nút **Điền khách mẫu**, mái phải dựng bằng nút **Dựng mái**, và vật cản không bị kéo sau khi áp dụng kết quả AI. Nếu đã sửa, cứ chạy tiếp: trợ lý gọi AI thật, tối đa khoảng 30 giây, hoặc dùng bộ quy tắc.
- **Máy chủ không phản hồi:** dùng **Dùng dự án mẫu** ở bước 1 để trình bày phần mô phỏng, tối ưu và thiết kế điện (không cần AI).

## Ghi lại bản ghi demo (khi đổi ảnh mẫu hoặc mô hình)

Bản ghi nằm trong `backend/demo_recordings/` và được commit cùng mã nguồn.

1. Ảnh drone (từ thư mục `backend/`):

   ```bash
   python scripts/record_demo_vision.py ../frontend/public/demo/anh-drone-mai-nha.png 12 9
   ```

2. Trợ lý: chạy máy chủ với `SOLAROPT_DEMO_RECORD=1`, bật Demo, đi hết bước 1–6 ở trên. Mỗi đề xuất do mô hình AI lập (không phải bộ quy tắc) được lưu thành một tệp `advisor-*.json`, kèm đầu vào để dò khi bản ghi không còn khớp. Khi ghi, trợ lý được đủ thời gian suy luận (không bị cắt ở 30 giây) và không bị giới hạn lượt khách.
3. Chạy lại toàn bộ một lần ở chế độ Demo để chắc các bản ghi khớp, rồi commit thư mục `backend/demo_recordings/`.
