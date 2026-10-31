# Bước 7 — So sánh bố trí SolarOpt với dãy pin đã lắp thật

Ngày thực hiện: 31/10/2026. Chương trình: `backend/scripts/benchmark_real_installs.py`. Dữ liệu: `sample_data/benchmark/osm_rooftop_pv_exeter.json`.

## Dữ liệu tham chiếu

- Nguồn: OpenStreetMap qua Overpass API, truy xuất 31/10/2026. Giấy phép ODbL 1.0, © OpenStreetMap contributors.
- Khu vực: Exeter (Anh), nơi có chiến dịch vẽ pin mặt trời áp mái trên OSM giai đoạn 2019–2020. Đã thử Munich, Freiburg, Bonn, Utrecht: quá ít mái có vẽ pin (0–4 đối tượng), không đủ để so sánh.
- Chọn 4 mái bằng có nhiều dãy pin nhất (way 733416878, 780007669, 516819627, 780007667). Bỏ way 516818735 vì chứa cùng các dãy pin với 780007669 (khối mái cao nằm trong tòa nhà), tránh đếm trùng. Bỏ mái dốc 827019720 vì OSM không có độ dốc và hướng mặt mái.
- Đường viền dãy pin do người đóng góp vẽ từ ảnh hàng không. Đây là **nơi đơn vị lắp đặt đã đặt pin**, không phải phương án tối ưu đã kiểm chứng. OSM **không có vật cản trên mái** (máy lạnh, cầu thang, giếng trời, lối đi).

## Cách đo

- Chiếu kinh/vĩ độ về mét theo phép chiếu phẳng cục bộ; biên tòa nhà làm biên mái. Tấm pin giả định 0,99 × 1,65 m, 300 W (loại phổ biến giai đoạn đó); lùi mép 0,5 m; khe 2 cm; bức xạ năm 1.100 kWh/m².
- **Cùng diện tích:** SolarOpt chỉ được đặt số tấm có tổng diện tích bằng diện tích dãy pin thật → so vị trí.
- **Tối đa:** không giới hạn ngân sách → SolarOpt coi phần nào của mái là đặt được.
- **Mốc so sánh “phủ kín mái”:** IoU giữa dãy pin thật và toàn bộ vùng mái khả dụng — điểm mà một cách làm ngây thơ đạt được.
- IoU = diện tích giao / diện tích hợp. “Phủ vùng thật” = phần trăm diện tích pin thật nằm dưới tấm SolarOpt.

## Kết quả

| OSM way | Mái (m²) | Pin thật (m²) | Cùng diện tích: IoU | Cùng diện tích: phủ vùng thật | Tối đa: số tấm | Tối đa: phủ vùng thật | Mốc phủ kín mái: IoU |
|---|---:|---:|---:|---:|---:|---:|---:|
| 733416878 | 2.156 | 596,5 | 0,192 | 32,3% | 1.059 | 95,6% | 0,300 |
| 780007669 | 368 | 197,0 | 0,506 | 67,3% | 168 | 87,8% | 0,581 |
| 516819627 | 197 | 69,3 | 0,331 | 49,5% | 73 | 78,4% | 0,420 |
| 780007667 | 230 | 48,0 | 0,000 | 0,0% | 105 | 96,5% | 0,242 |
| **Trung bình** | | | **0,257** | | | **89,6%** | **0,386** |

Chạy lại: `python scripts/benchmark_real_installs.py` (từ thư mục `backend`). Báo cáo HTML có hình từng mái tại `output/validation/real_installs/report.html`.

## Diễn giải trung thực

1. **Vùng đặt được của SolarOpt bao trùm nơi thợ đã lắp (89,6%).** Mô hình biên mái + lùi mép không loại bỏ vùng mà thực tế đã dùng. Phần thiếu chủ yếu là sát mép mái, nơi SolarOpt lùi 0,5 m.
2. **Khi giới hạn cùng diện tích, SolarOpt chưa chọn đúng chỗ thợ đặt (IoU 0,257, thấp hơn mốc 0,386).** Trên mái bằng không vẽ vật cản và không có bóng che, mọi vị trí cho sản lượng gần như bằng nhau, nên bộ tối ưu chọn vị trí gần như tùy ý. Đơn vị lắp đặt gom dãy pin theo lối đi, thiết bị trên mái, kết cấu và đường dây — những thứ SolarOpt chưa biết.
3. **Ở chế độ tối đa SolarOpt đặt gấp khoảng 3 lần diện tích pin thật.** Lý do: không có vật cản trong dữ liệu; mái bằng ở Anh thường dùng giá nghiêng xếp hàng có khoảng cách tránh bóng giữa các hàng, SolarOpt hiện đặt phẳng sát nhau; ngân sách, tải mái và nhu cầu điện của chủ công trình không có trong dữ liệu.
4. Không dùng kết quả này để quảng cáo “bố trí giống thực tế”. Kết luận đúng là: vùng khả dụng hợp lý, nhưng **thiếu quy tắc ưu tiên vị trí khi sản lượng ngang nhau** và **thiếu mô hình hàng giá nghiêng** cho mái bằng.

## Việc nên làm tiếp (đề xuất, chưa triển khai)

- Thêm tiêu chí phụ khi sản lượng ngang nhau: gom tấm thành khối liền, ưu tiên cách xa mép, giữ lối đi — rồi chạy lại benchmark này, không chỉnh riêng cho 4 ca.
- Mô hình hàng giá nghiêng trên mái bằng (khoảng cách hàng theo góc mặt trời thấp nhất), phần đã nêu trong lộ trình mục 11.
- Bổ sung ca có vật cản và ca tại Việt Nam có bản vẽ thi công từ đơn vị lắp đặt (cần xin phép sử dụng).
