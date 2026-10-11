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


## Kiểm tra chỉnh vật cản trực tiếp — 10/10/2026

- Nhập rộng, sâu và góc xoay: hình mặt bằng đổi ngay khi ô nhập còn được chọn, không cần Enter hoặc chuyển sang ô khác.
- Hai bảng chỉnh vật cản đồng bộ kích thước, vị trí và chiều cao; đổi kích thước đa giác co giãn các đỉnh theo đúng trục.
- Chuyển chữ nhật/bầu dục/đa giác, nhân đôi, xóa và hoàn tác/làm lại: đã kiểm tra trong trình duyệt.
- Giá trị ngoài giới hạn không được đưa vào mô hình; rời ô nhập sẽ trả lại giá trị hợp lệ trước đó.
- Cao độ chân mặc định khi bật nhập tay: vật trên mái lấy cao độ mái cơ sở, nhà bên cạnh lấy 0 m từ mặt đất.
- Ca nhà bên cạnh cao 18,25 m, chân cao 1,5 m, rộng 4 m được API mô phỏng thật chấp nhận (HTTP 200).
- TypeScript và build frontend đạt. Hình mặt bằng cập nhật trực tiếp; bóng che/bức xạ cập nhật sau phản hồi bộ mô phỏng, có debounce 180 ms.


## Kéo vật cản trên ảnh nền và hiển thị bóng — 10/10/2026

- Tái hiện bằng ảnh mái Nhà A do người dùng cung cấp: nhập 15 × 20 m, trích biên OpenCV, áp dụng rồi thêm nhà bên cạnh.
- Bước 2 mặc định hiển thị Bóng che. Chế độ Bản vẽ có lời nhắc và nút Hiện bóng che.
- Giữ cố định phép biến đổi khung nhìn trong suốt thao tác kéo; kiểm tra tâm vật cản bám theo con trỏ trong sai số 3 pixel trước khi thả.
- Kéo nhà phía Đông từ X = 18 m vào X = 5,2 m thành công; có đa giác bóng từ phản hồi mô phỏng thật, không có lỗi giao diện/API trong ca này.
- TypeScript và build đạt. Bóng che vẫn phụ thuộc ngày/giờ, hướng và cao độ; vật thể có thể không đổ bóng vào mái ở một số thời điểm.


## Bố trí thích nghi với mái chéo — 10/10/2026

- Tự động lấy tối đa hai hướng cạnh chủ đạo và hướng trục bản vẽ; thử hai chiều đặt pin cùng bốn pha dịch lưới. Các lưới là phương án độc lập, không trộn để tránh chồng tấm.
- Mỗi tấm lưu rotation_deg, vẫn giữ kích thước vật lý. Hình học, kiểm chứng, stress test, sửa bố trí và bản vẽ SVG/PDF dùng cùng góc xoay.
- Có cấu hình góc thủ công và bảng so sánh góc, pha dịch, số tấm, sản lượng ước tính của các lưới thực sự đã thử. Góc mặt bằng không thay hướng Bắc hoặc độ nghiêng mái.
- Kiểm thử hồi quy: 44 tests đạt, gồm mái hẹp chéo 45° mà lưới 0° không đặt được tấm, ngân sách, kiểm chứng góc xoay, stress, giữ vị trí khi sửa và fallback.
- Trình duyệt trên ảnh Nhà A: tự động thử 16 lưới, chọn 139,6°. Chuyển góc thủ công 45°, chạy kiểm chứng đều đạt; xuất SVG thành công; không tràn ngang ở 390 px.
- TypeScript và build đạt. Backend đang chạy phiên bản mới ở cổng 8001.
- Giới hạn: tối ưu theo điểm mục tiêu trong các lưới đã thử; chưa trộn nhiều hướng hoặc làm mô phỏng sản lượng từng giờ trong năm. Kết quả phụ thuộc biên mái, vật cản và số đo đã nhập.


## Tinh chỉnh lưới và hướng dẫn xử lý stress — 10/10/2026

- Giữ toàn bộ lưới ban đầu; thêm pha dịch ¼ bước và các góc ±1°/±2° quanh phương án tốt nhất ở chế độ tự động. Chế độ góc thủ công chỉ tinh chỉnh pha dịch, không đổi góc đã chọn.
- Ca hồi quy mái chữ L xoay 37°, vật cản 2 × 2 m tại (5,6; 5): 7 → 8 tấm, điểm mục tiêu tăng và vẫn qua kiểm chứng. Ca thử theo ảnh không tăng điểm được giữ nguyên phương án đầu; không tuyên bố mọi mái đều tăng số tấm.
- Phản hồi stress lưu các kiểm tra FAIL, ID tấm vi phạm và đề xuất xử lý cụ thể; giữ nguyên thiết kế đầu vào, không tự tối ưu để biến kết quả kiểm tra thành PASS.
- Giao diện có đề xuất xử lý, nút đánh dấu tấm lỗi màu đỏ và tùy chọn đưa khoảng dự phòng vào cấu hình. Sau đó người dùng phải tính và kiểm chứng lại.
- Dự phòng là biên thêm khi tìm vị trí pin, độc lập với lùi mép bắt buộc. Có thể giảm số tấm/sản lượng; không tự thay số đo mái hoặc thông số tấm pin.
- Trình duyệt với ca hồi quy: 96 lưới; 5/8 trước sửa; 3 thẻ đề xuất; đánh dấu tấm lỗi hoạt động. Dự phòng 0,58 m rồi tính lại đạt 8/8 trong ca này. Không đảm bảo mọi đầu vào đạt cùng kết quả.
- 47 backend tests đạt; TypeScript/build đạt; không có lỗi JS và không tràn ngang ở 390 px trong ca kiểm tra.

## Kiểm tra ba mục tiêu bố trí (10/10/2026)

- `max_energy`: tối đa điện năng sơ bộ, vẫn áp dụng ngưỡng bóng lớn chung.
- `balanced`: tối đa điện năng với tổn thất bóng mỗi tấm không quá 18%; bỏ khoản trừ cố định 35% điện năng cơ sở khỏi điểm mục tiêu vì không phản ánh tiêu chí đã công bố.
- `durability`: tổn thất mỗi tấm không quá 10%, thêm trọng số ưu tiên ít bóng. Đây không phải bảo đảm độ bền cơ học hoặc PASS mọi stress test.
- Mỗi thẻ hiển thị bóng trung bình, tấm chịu bóng nhiều nhất, góc xếp và số vị trí bị loại do bóng trên lưới chọn. So sánh bố trí bằng hình học thực, không bằng ID ứng viên hay chỉ các tổng chỉ số.
- Giải thích khi ba bố trí giống nhau; phân biệt tổng chỉ số giống nhưng vị trí khác, chưa có đủ ba lựa chọn sau repair và cả ba không chọn được tấm.
- Khóa lựa chọn và ẩn chỉ số cũ khi đầu vào đổi hoặc đang tính. Loại phản hồi generate nếu đầu vào đổi giữa lúc tính. Đổi ngân sách/quy tắc xếp không buộc xác nhận lại hình học; đổi biên/hướng/cao độ vẫn phải xác nhận.
- Browser với dữ liệu mẫu mái 12 x 9 m, ngân sách đủ: sản lượng 21 tấm / 15.500 kWh; cân bằng 20 tấm / 14.918,7 kWh; ít bóng 19 tấm / 14.278,9 kWh. Bóng trung bình lần lượt 1,86%, 0,8%, 0,05%. Đây là ca minh họa, không phải kết quả mặc định của mọi mái.
- Browser: chuyển thẻ đổi đúng bản vẽ 21/20/19 tấm, đổi đầu vào làm các thẻ cần tính lại; đổi ngân sách trong khi tính không áp dụng kết quả cũ.
- Thêm 5 kiểm thử cho mái không bóng có kết quả giống nhau, mái có bóng tạo khác biệt giữa mục tiêu, ngưỡng từng tấm, thống kê loại vị trí và solver/fallback trong ngân sách. Toàn bộ backend: 52 kiểm thử đạt.

## Ba mục tiêu sản phẩm (11/10/2026)

- Web chuyển sang `max_energy`, `min_cost`, `robust`; API vẫn nhận `balanced` và `durability` cho dự án/công cụ cũ.
- `target_energy_kwh_year` do người dùng nhập, không tự đặt số nhu cầu. Bắt buộc có mục tiêu dương khi gọi `min_cost`. Với cùng model/đơn giá, chọn số tấm ít nhất đủ mục tiêu trong ngân sách và các lưới đã thử; điện năng là tiêu chí phụ khi số tấm bằng nhau. Fallback giữ cùng quy tắc.
- Khi mục tiêu chưa khả thi, trả bố trí có sản lượng tìm được, `target_met=false`, lượng điện thiếu và cảnh báo. Verifier thêm kiểm tra bắt buộc `energy_target`, API duyệt từ chối kết quả chưa đạt. Chi phí chỉ gồm tấm pin, chưa phải tổng chi phí EPC.
- `robust` kiểm tra vị trí ứng viên với mái thu nhỏ 2%, tấm tăng kích thước 1%, lùi mép tăng 15 cm; tăng bước lưới để tránh chồng lấn khi tấm lớn hơn và dùng tối đa 85% ngân sách. Sau chọn bố trí, chạy đúng 8 stress scenarios trên bố trí giữ nguyên; hiển thị PASS/FAIL thực. Chưa bảo đảm mọi sai số hoặc các sai số xảy ra đồng thời.
- Ca browser mái chữ nhật 12 x 9 m, không vật cản/bóng che, ngân sách 120 triệu, mục tiêu 10.000 kWh/năm: tối đa sản lượng 27 tấm / 20,30 MWh / 113,4 triệu; đáp ứng nhu cầu 14 tấm / 10,53 MWh / 58,8 triệu; dự phòng 24 tấm / 18,05 MWh / 100,8 triệu, 8/8 tình huống đạt.
- Browser bấm từng thẻ cập nhật đúng số tấm. Mục tiêu 100.000 kWh hiển thị Chưa đáp ứng và lượng thiếu, chặn nút bàn giao của phương án này. Viewport 390 px không tràn ngang.
- Backend regression: 61 kiểm thử đạt, gồm API thiếu mục tiêu (422), API từ chối duyệt (409), solver/fallback, mái chéo có vật cản, ca không khả thi và bảo toàn đầu vào. TypeScript và production build đạt.
