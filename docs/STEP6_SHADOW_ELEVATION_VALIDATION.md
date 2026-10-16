# Bước 6 — Kiểm chứng bóng che và cao độ

Ngày: 16/10/2026. Nhánh triển khai: `fix/shadow-elevation-validation`.

## Quy ước được giữ thống nhất

- Bản vẽ: X sang phải, Y lên trên, kích thước mặt bằng theo mét.
- Hướng địa lý: 0° Bắc, 90° Đông, 180° Nam, 270° Tây. `north_rotation_deg` là hướng địa lý của trục trên bản vẽ; hướng mặt trời trên bản vẽ bằng phương vị địa lý trừ góc này.
- Bóng kéo về phía đối diện nguồn nắng. Trên mái phẳng, độ kéo của một điểm bằng chênh cao với mái chia tan(góc cao mặt trời).
- Mái cơ sở: cao độ khai báo tại gốc (0,0). Mặt mái riêng: cao độ khai báo tại tâm hình học của phần mái đã cắt theo biên mái. Hướng dốc là hướng thấp dần theo địa lý.
- Chiều cao vật cản đo từ chân tới đỉnh. Cao độ chân và đỉnh tính từ mặt đất; không cộng cao độ mái thêm lần nữa khi đã nhập cao độ chân riêng.
- Nhà bên cạnh mặc định có chân ở mặt đất. Vật trên mái mặc định theo mặt mái chứa tâm mặt bằng vật. Vật bắc qua nhiều mặt mái hoặc vượt khỏi biên có cảnh báo và cần kỹ sư kiểm tra, nhập cao độ chân riêng nếu cần.

## Các lỗi đã tái hiện và sửa

| Tình huống | Trước | Sau |
| --- | --- | --- |
| Một phần đỉnh vật thấp hơn mái nghiêng | Toàn mặt bằng vật vẫn tham gia tạo bóng | Cắt phần không cao hơn mặt nhận trước khi chiếu |
| Mặt mái quay lưng với nắng trực tiếp | Một vật nhỏ có thể bị quy thành bóng toàn mái | Phân biệt không nhận nắng trực tiếp với bóng do vật; vẫn giữ bức xạ tán xạ trong phép tính trời quang |
| Vật trên mái không được gán mặt mái nguồn | Cao độ mặc định có thể đổi theo từng mái nhận bóng | Dùng mặt mái nguồn hoặc ngoại suy mái cơ sở độc lập với mái nhận; hiển thị cảnh báo |
| Vật có chân cao hơn mái nhận | Bóng bị nối dài tới vị trí mặt bằng gốc, lấp khoảng hở | Chiếu cả chân và đỉnh khối, giữ đúng khoảng hở |
| Chân khối cắt mặt mái nghiêng giữa hai đỉnh | Thiếu điểm đổi đoạn trong đường biên chiếu | Chèn giao điểm chân–mái trước phép chiếu; đối chiếu riêng bằng tia giao khối |
| Ban đêm | Tổng diện tích tối 100% nhưng ô lưới ghi tỷ lệ che 0 | Ô lưới thống nhất 100% không có nắng trực tiếp, bức xạ bằng 0 |
| Vùng bóng có lỗ hoặc nhiều phần | Dữ liệu vẽ chỉ giữ đường bao ngoài | Trả thêm các vùng có đường bao/lỗ; giao diện vẽ theo quy tắc chẵn lẻ |

Phép cắt phần vật cao hơn mái nhận thực hiện bằng giao với nửa mặt phẳng của chênh cao. Cách này áp dụng cho các mặt phẳng và khối đứng mà MVP đang hỗ trợ; giữ biên lõm, lỗ và các phần rời khi cắt.

## Giao diện giải thích

Trong bước Nắng và bóng che có bảng **Đọc bóng che và cao độ**:

- Nêu hướng nguồn nắng và hướng kéo bóng theo địa lý; người dùng đối chiếu la bàn khi bản vẽ đã xoay.
- Chọn vật cản để xem cao độ chân, chiều cao, cao độ đỉnh và nguồn xác định cao độ. Trên mái nghiêng, cao độ có thể là một khoảng từ thấp tới cao.
- Nêu rõ giả định khi vật bắc qua nhiều mặt mái, vượt biên hoặc có điểm thấp hơn mặt đất.
- Hiển thị diện tích bóng của từng nguồn. Tổng diện tích lấy hợp các vùng bóng, không cộng các dòng đang chồng nhau.
- Vùng bóng của vật đang chọn được làm nổi trên bản vẽ.

Khi đầu vào, ngày hoặc giờ đổi, kết quả cũ được xóa trong lúc chờ tính mới. Kiểm tra kết nối định kỳ không chạy lại bộ mô phỏng nếu trạng thái kết nối vẫn giữ nguyên.

## Đối chiếu và tái lập

`backend/tests/test_shadow_reference.py` có 28 ca: hướng nắng và bản vẽ xoay, năm góc cao mặt trời, bóng chéo, mái nghiêng cắt qua vật, mặt mái quay lưng, chân nâng cao, nhà bên cạnh, ô lưới ban đêm, vùng bóng chồng nhau, cảnh báo cao độ và giữ lỗ khi xuất vùng bóng. Bốn ca dùng phương pháp độc lập giao tia với khối hộp trên lưới 864 điểm mỗi ca để đối chiếu các hướng nắng và mái nghiêng khác nhau; bỏ qua điểm sát biên theo dung sai khai báo trong kiểm thử.

`sample_data/validation/shadow_cases.json` cung cấp 8 ca có công thức và đa giác đối chiếu độc lập để xuất báo cáo:

```powershell
# Từ thư mục gốc SolarOpt
python backend/scripts/validate_roofs.py sample_data/validation/shadow_cases.json --out output/validation/shadow_reference
```

Cả 8 ca đạt `SYNTHETIC_PASS`. Báo cáo có ảnh chồng đường biên tại `output/validation/shadow_reference/report.html`; không gọi AI, không ghi vào lịch sử dự án và không cần khóa API.

Toàn bộ máy chủ: **163 kiểm thử đạt**. Giao diện: **11 kiểm thử**, kiểm tra TypeScript và dựng bản phát hành đạt. Kiểm tra trình duyệt bao gồm đổi cao độ chân, cảnh báo vật qua nhiều mái, mặc định nhà bên cạnh, ban đêm, đường vùng bóng trên bản vẽ, màn hình nhỏ và tránh tính lại khi chỉ kiểm tra kết nối.

## Giới hạn còn lại

- Các ca trên là hình học nhân tạo có đầu vào biết trước. Chưa có ảnh bóng kèm ngày/giờ, hướng và số đo công trình thật để công bố sai số thực địa.
- Các phần mái được coi là các mặt phẳng có khối bên dưới để tính che giữa các phần cao/thấp. Chưa mô hình đầy đủ mái đua, nhà sàn, kết cấu rỗng, mái cong hoặc cây xuyên sáng. Vật cản có chân nâng cao dùng khối đứng kín giữa chân và đỉnh đã khai báo.
- Phép chiếu giới hạn độ kéo ở 10 km để giữ ổn định số; ánh nắng gần sát đường chân trời chưa được kiểm chứng thực địa.
- Bản đồ bức xạ hiện giảm theo phần diện tích bị che, chưa tách đầy đủ mức suy giảm ánh sáng tán xạ do vật cản. Sản lượng năm vẫn dùng các thời điểm đại diện và quy tắc tổn thất sơ bộ; chưa phải mô phỏng mạch điện hoặc thời tiết 8760 giờ.
- Phương án cũ cần được tạo và kiểm tra lại sau khi nâng cấp vì kết quả bóng, sản lượng và bố trí có thể thay đổi trong các tình huống đã sửa.
