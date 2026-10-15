# Bước 2 — đối chiếu có nguồn

Cập nhật 15/10/2026. Đội xác nhận **chưa có ảnh gốc kèm số đo/bản vẽ đối chiếu mái thật**. Vì vậy bước này hoàn thành công cụ đánh giá và kiểm tra hình học nhân tạo; chưa hoàn thành nghiệm thu độ chính xác ngoài hiện trường.

## Đã có thể làm gì?

- Đối chiếu biên mái dự đoán với biên tham chiếu trong cùng hệ tọa độ theo mét, gồm cả sân trong/giếng trời.
- Tính tỷ lệ diện tích giao/hợp, chênh diện tích và khoảng cách biên Hausdorff rời rạc có chia nhỏ cạnh. Khoảng cách này là số xấp xỉ, không phải giới hạn sai số đo đạc đã chứng nhận.
- Đối chiếu vùng bóng ở ngày/giờ cụ thể. Với ca nhân tạo mới cho phép nhập góc mặt trời để so với công thức tính tay.
- Đối chiếu điện năng trên bố trí tấm cố định khi người nhập xác nhận cùng bố trí và đầu vào nắng; nếu chưa xác nhận, báo chưa đủ dữ liệu thay vì cho tỷ lệ sai số gây hiểu nhầm.
- Xuất JSON và báo cáo HTML ngoại tuyến có lớp tham chiếu / SolarOpt chồng cùng tọa độ; không tự dịch, xoay hoặc kéo giãn hai lớp để làm tăng độ khớp.
- Tách ca nhân tạo và ca mái thật. Không có dữ liệu/ngưỡng dung sai thì giữ trạng thái thiếu; kết quả trong dung sai của ca khai báo không thay cho chứng nhận thiết kế.

Công cụ không đọc ảnh bằng AI, không tiêu tốn lượt API, không ghi lịch sử dự án và không thay đổi bộ tính sản xuất.

## Kết quả ba ca nhân tạo

| Ca | Tham chiếu độc lập | Kết quả |
|---|---|---|
| Mái phẳng 12 × 9 m, vật cản cao 2 m | Mặt trời cao 45° phía Đông: kéo bóng 2 m về Tây; cộng chân vật cản 1 × 1 m thành vùng che 3 m² | Vùng che 3 m², khớp tham chiếu. Kiểm tra đơn vị điện năng của một tấm không bị bóng: 751,92 kWh/năm so với công thức 751,9236 |
| Mái lõm chữ L có sân trong | 12 × 10 − 5 × 6 − 2 × 2 = 86 m²; không vật cản, không bóng cục bộ | Giữ biên lõm và lỗ sân trong; diện tích 86 m²; vùng bóng rỗng |
| Mái cao/thấp có nhà phía Đông | Bậc mái cao hơn 2 m che 18 m²; nhà lân cận che thêm 12 m² trên mặt mái cao ở góc 45° | Tổng vùng che 30 m², khớp hai vùng tính tay |

Các ca này kiểm tra hình học và công thức, **không phải thử nhận diện ảnh mái, đánh giá độ chính xác AI hoặc dự báo sản lượng thực**. Ngưỡng rất chặt trong tệp nhân tạo chỉ kiểm tra phép tính, không phải dung sai áp dụng ngoài hiện trường.

Mẫu mái thật chưa có nguồn đối chiếu trả `INCOMPLETE`, không trả đạt.

## Chạy trên Windows

Sau khi cài thư viện backend theo README, đứng ở thư mục gốc `SolarOpt`:

```powershell
.\backend\.venv\Scripts\python.exe backend\scripts\validate_roofs.py sample_data\validation\synthetic_cases.json --out output\validation\synthetic

.\backend\.venv\Scripts\python.exe backend\scripts\validate_roofs.py sample_data\validation\field_template.json --out output\validation\field_pending
```

Nếu đang dùng Python đã cài thư viện trực tiếp, thay đường dẫn Python bằng `python`. Mỗi thư mục kết quả có `report.html` để mở trong trình duyệt và `results.json` để lưu bằng chứng. Các báo cáo sinh ra nằm trong thư mục được Git bỏ qua.

Mã thoát: `0` = các điều kiện đã khai báo đều đạt; `1` = có ca vượt dung sai; `2` = thiếu dữ liệu hoặc đầu vào không hợp lệ. Trạng thái thiếu của mẫu mái thật là kết quả dự kiến, không phải lỗi bộ tính.

## Khi có một mái thật

1. Sao chép `sample_data/validation/field_template.json` thành tệp riêng. Đặt ID rõ cho mái và giai đoạn: `ai_initial` là đề xuất ban đầu; `engineer_corrected` là sau khi kỹ sư sửa. Hai giai đoạn dùng cùng tham chiếu để đo công sức chỉnh.
2. Lấy `config`, `panel`, `obstacles` từ JSON dự án xuất trong website, đưa vào `project`. Hai số đo và hướng Bắc phải được đối chiếu; không dùng khung mặc định như số đo thật.
3. Điền `reference_roof.boundary` từ bản vẽ/số đo độc lập, không sao chép lại kết quả SolarOpt để làm chuẩn. Gốc trái dưới, trục X/Y theo bản vẽ, đơn vị mét; `openings` chứa sân trong/giếng trời. Hai dữ liệu phải thống nhất gốc, hướng và tỷ lệ từ trước.
4. Mỗi `shadow_references` ghi `date`, `hour_local` theo giờ Việt Nam, `source` và `regions` đã đánh dấu từ ảnh/khảo sát độc lập. Ca mái thật không cho dùng `analytical_sun`. `regions: []` có nghĩa xác nhận không có bóng; bỏ phần tham chiếu có nghĩa chưa kiểm tra.
5. Nếu so sản lượng, sao chép `design.panels` từ dự án vào `panels`, bổ sung `energy_reference` cùng nguồn và phạm vi. Chỉ bật hai cờ xác nhận khi thực sự cùng bố trí và đầu vào nắng. So công cụ khác vẫn cần giải thích chênh do mô hình điện; khớp công thức sơ bộ không chứng minh khớp điện vận hành.
6. Ghi `reviewed_by`, danh sách `evidence_files` và người thống nhất dung sai `tolerances.agreed_by`. Công cụ ghi lại tên hồ sơ, không tự xác thực nội dung, giấy phép hay danh tính người ký. Đội chịu trách nhiệm đối chiếu nguồn.
7. Điền các ngưỡng đã thống nhất với kỹ sư: `roof_iou_min`, `boundary_error_m_max`, `shadow_iou_min`, `energy_error_pct_max`. Không sao chép dung sai phép tính nhân tạo sang khảo sát thực.

Mẫu một bóng đo thực (tọa độ minh họa, không dùng làm dữ liệu khảo sát):

```json
{
  "label": "Bóng lúc khảo sát",
  "source": "Tên ảnh gốc, thời điểm và cách đo/đánh dấu",
  "date": "2026-10-15",
  "hour_local": 9.5,
  "regions": [{"boundary": [
    {"x": 1, "y": 1}, {"x": 3, "y": 1},
    {"x": 3, "y": 2}, {"x": 1, "y": 2}
  ]}]
}
```

## Cách quyết định nâng cấp tiếp

- Ba ca nhân tạo khớp: chưa thấy sai trong các công thức cơ bản đã thử; giữ chúng làm bộ hồi quy.
- Chưa có ca thực: không công bố phần trăm chính xác mái thật, không kết luận SolarOpt vượt công cụ khác.
- Khi có dữ liệu: nếu lệch biên, ưu tiên số đo/phối cảnh; nếu lệch bóng, ưu tiên hướng Bắc/cao độ; nếu lệch điện năng, ưu tiên thời tiết và mô hình điện. Không đổi nguồn tham chiếu hoặc giảm ngưỡng chỉ để đổi trạng thái thành đạt.
- Sau khi các mái thực đạt dung sai thống nhất, tiếp tục tính năng so sánh trước/sau và ghim vị trí đã thi công.

Đếm vật cản nhận nhầm/bỏ sót, thời gian kỹ sư chỉnh và đối chiếu thiết bị điện vẫn cần ghi trong hồ sơ khảo sát; phiên bản công cụ này chưa tự chấm ba phần đó. Chưa đánh giá sai số chiều cao từ ảnh hoặc mô hình điện 8760 giờ.

## Bằng chứng phần mềm

Toàn bộ **116/116 kiểm thử Python đạt**, gồm 16 ca mới cho công cụ đối chiếu: sai lệch vị trí không tự căn lại, giữ lỗ sân trong, tham chiếu không bị cắt theo dự đoán sai, thiếu dữ liệu không được đạt, ca thật không nhận mặt trời giả lập, kiểm tra không thay dữ liệu và mã thoát công cụ. Báo cáo HTML được kiểm tra riêng bằng Edge ở màn hình rộng và 390 px.

Mã: `backend/app/services/validation.py`, `validation_report.py`, `backend/scripts/validate_roofs.py`, `backend/tests/test_validation.py`. Môi trường kiểm thử dùng các thư viện sẵn và `J:/vi/tmp/solaropt-runtime`; chưa xác nhận lại môi trường cài sạch theo toàn bộ phiên bản ghim.

Phương pháp khoảng cách: [Shapely Hausdorff distance](https://shapely.readthedocs.io/en/2.1.2/reference/shapely.hausdorff_distance.html).
