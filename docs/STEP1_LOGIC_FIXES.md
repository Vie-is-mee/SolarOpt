# Bước 1 — sửa và kiểm chứng bộ tính toán

Ngày 15/10/2026. Phạm vi: năm vấn đề được tái hiện trong lần rà soát mã nguồn SolarOpt. Không dùng khóa AI hoặc gọi dịch vụ AI trong các phép kiểm tra của bước này.

## Kết quả sửa

| Vấn đề | Hành vi sau sửa | Bằng chứng |
|---|---|---|
| Đổi góc mái không đổi điện năng năm | Tính riêng nắng năm cho từng mặt mái theo độ dốc/hướng; công khai mặt tham chiếu dữ liệu nắng | Mái 10 × 8 m, lùi mép 0,35 m, 21 tấm: mái phẳng 15.790,3 kWh/năm; nghiêng 40° về Bắc 11.560,7 kWh/năm khi giữ các đầu vào khác |
| Thử sai số báo đạt dù có cảnh báo | PASS/WARN/FAIL riêng; chỉ PASS vào số đạt. Tăng chiều cao tính lại bóng đại diện kể cả không truyền giờ mặt trời hiện tại | Ca vật cản tăng 30% chuyển thành WARN khi bóng tức thời vượt 40%; có danh sách tấm và đề xuất xử lý |
| Không kiểm tra khe giữa tấm | Tính khoảng cách hình học giữa các tấm, gồm tấm xoay, ngưỡng sai số số học 0,003 mm | Thử 0°, 31°, 90°: khe 0 và 79 mm không đạt; khe 80 và 81 mm đạt khi yêu cầu 80 mm |
| Tin số tổng hợp từ bên gửi | Máy chủ tính lại bóng đại diện, điện năng từng tấm, công suất, tổng điện năng, diện tích sử dụng, số lượng và chi phí; đối chiếu mặt mái/ID tấm | Sửa riêng tổng hoặc sửa cả điện năng từng tấm và tổng đều bị từ chối; điểm lưu bản duyệt trả 409 |
| Mái chia thành các phần rời làm lỗi | Xét cạnh của mọi phần mái; xử lý mái rỗng thành không khả thi | Ca 12 × 9 m có khoảng trống xuyên giữa tìm được 18 tấm và qua kiểm chứng; thử cả góc tự động/thủ công |

Các số điện năng trên chỉ là kết quả của phép thử phần mềm, không phải phép đo mái thật.

## Cách tính điện năng hiện tại

1. Dữ liệu nắng năm đi kèm độ dốc/hướng mặt tham chiếu; mặc định là mặt ngang. Giao diện lấy PVGIS trên mặt ngang và ghi rõ điều này.
2. pvlib chuyển bức xạ trời quang sang từng mặt mái. Dùng ngày 15 của 12 tháng, 24 mốc giữa giờ mỗi ngày, trọng số số ngày trong tháng, năm tham chiếu 2026. Tỷ lệ tổng mặt mái/tổng mặt tham chiếu nhân với dữ liệu nắng năm đã nhập.
3. Bóng vẫn dùng chín thời điểm đại diện. Mức tổn thất vẫn là quy tắc sơ bộ của MVP, chưa hiệu chuẩn bằng dữ liệu điện thực.
4. Điện năng từng tấm = công suất × nắng năm trên mặt mái × hệ số hiệu năng × hệ số sau bóng. Bố trí, kiểm chứng và thử sai số gọi chung dịch vụ `backend/app/services/energy.py`.
5. Thử sai số giữ tọa độ/góc/số tấm gốc. Kịch bản dung sai tấm tăng kích thước; kịch bản mái giảm hình học mái; không chạy tối ưu lại để làm đẹp kết quả.

Khi mặt tham chiếu trùng với mặt mái thì tỷ lệ bằng 1, tránh tính tác động góc hai lần. Nếu PVGIS không trả bức xạ năm hợp lệ, hệ thống trả nhãn fallback, không gắn nguồn PVGIS cho giá trị suy đoán.

Nguồn phương pháp: [pvlib get_total_irradiance](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.irradiance.get_total_irradiance.html), [mô hình trời quang](https://pvlib-python.readthedocs.io/en/stable/user_guide/modeling_topics/clearsky.html).

## Kiểm tra đã chạy

- **100/100 kiểm thử Python đạt**: 61 ca trước và 39 ca mới. Ba ca cũ được sửa dữ liệu/điểm thay thế kiểm thử để phù hợp cách xử lý chung: đường dẫn giả lập mặt trời; xác nhận đầu vào trước khi kỳ vọng PASS không cảnh báo.
- TypeScript và đóng gói Vite đạt. `git diff --check` đạt.
- Trình duyệt Edge: tính đủ ba mục tiêu, kiểm chứng, thử tám tình huống, xem cảnh báo và hướng dẫn, xem nội dung in, kiểm tra màn hình 390 px không tràn ngang. Không ghi nhận lỗi JavaScript hoặc phản hồi API lỗi trong luồng này.
- Ca giao diện dùng mái 12 × 9 m, vật cản dạng vách: ba mục tiêu cho 12/12/9 tấm; phương án đang chọn có 4 tình huống PASS, 2 WARN, 2 FAIL. Đây là ca thử có chủ đích, không là kết quả chuẩn cho mọi mái.
- Máy chủ thử dùng SQLite riêng `J:/vi/tmp/solaropt-step1-ui.db`. Không sửa dữ liệu dự án thật để tạo bằng chứng.

Mã hồi quy: `backend/tests/test_logic_regressions.py`. Kịch bản và bằng chứng trình duyệt: `J:/vi/tmp/solaropt_step1_browser.py`, `J:/vi/tmp/solaropt-step1-browser/`. Các phép thử số: `J:/vi/tmp/solaropt_step1_results.py`, `J:/vi/tmp/solaropt-step1-results.json`. Thư mục tạm có thể bị dọn.

Môi trường kiểm tra dùng các thư viện sẵn trên máy và thư mục `J:/vi/tmp/solaropt-runtime`; chưa kiểm thử lại toàn bộ trong môi trường sạch với đúng mọi phiên bản ghim ở `requirements.txt`.

## Đánh giá sau bước 1

Đã khắc phục năm trường hợp sai được tái hiện và có kiểm thử chặn tái diễn. Đủ điều kiện chuyển sang đối chiếu dữ liệu thực. Chưa đủ bằng chứng để xác nhận độ chính xác thiết kế thi công hoặc so sánh độ chính xác với công cụ thương mại.

Chưa hoàn thành: thời tiết 8760 giờ, mô hình điện/bộ biến đổi điện/chuỗi pin, kích thước chiếu bằng của tấm trên mái dốc, bản vẽ 3D đầy đủ và kiểm chứng hiện trường. Tệp/dữ liệu cũ chưa lưu mặt tham chiếu sẽ mặc định ngang; phải kiểm tra lại nguồn nắng và tính lại phương án khi dùng bản mới.

## Bước 2 — quyết định bằng bằng chứng

1. Chọn ba mái được phép sử dụng: mái phẳng đơn giản; mái lõm/có sân trong; mái nhiều cao độ và nhà lân cận. Chuẩn bị ảnh gốc, hướng Bắc, số đo cạnh, cao độ, bản vẽ đối chiếu và nguồn thông số tấm pin.
2. Ghi riêng kết quả AI ban đầu và sau khi kỹ sư sửa: sai lệch biên theo mét, diện tích giao/hợp của biên, vật cản bỏ sót/nhận nhầm, thời gian chỉnh và nguồn từng số đo. Thống nhất dung sai sử dụng với kỹ sư.
3. Đối chiếu bóng ở nhiều giờ/ngày có ảnh hoặc số đo tham chiếu. So sản lượng trên cùng đầu vào với công cụ chuẩn, phân biệt khác biệt do nguồn thời tiết, mô hình bóng và mô hình điện.
4. Nếu lệch biên lớn: ưu tiên hiệu chuẩn, phối cảnh và điểm đối chiếu ảnh. Nếu lệch bóng: ưu tiên hướng Bắc, cao độ và mô hình mặt mái. Nếu lệch sản lượng: ưu tiên thời tiết theo giờ và mô hình điện; không bù sai bằng một hệ số không giải thích được.
5. Khi các ca thực đạt dung sai đã thống nhất, triển khai so sánh bản vẽ trước/sau bằng màu và ghim tấm/vùng đã thi công. Đây là nâng cấp tiếp theo phù hợp thế mạnh cập nhật phương án của SolarOpt.
