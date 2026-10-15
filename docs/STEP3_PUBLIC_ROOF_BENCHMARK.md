# Bước 3 — Đối chiếu đường biên với ảnh drone công khai

Ngày thực hiện: 15/10/2026. Phạm vi: `SolarOpt`, không phải bản sao `SolarOpt-main`.

## Đã thực hiện

Tìm và tải một ảnh kiểm tra Nacala cùng nhãn 52 mái từ kho chính thức của nhóm nghiên cứu: https://github.com/mosquito-risk/Nacala. Giấy phép trong kho: CC0-1.0. Chỉ dùng mẫu nhỏ, không tải toàn bộ bộ dữ liệu. Ảnh TIFF khoảng 44 MB; có bốn kênh int16, ba kênh màu thực tế nằm trong khoảng 0–255. Thư viện tifffile đọc ảnh gốc, không đổi tỷ lệ hai chiều độc lập.

Mã tham chiếu nguồn: `c48938260f1755089ac9510e500f5c93f8c465aa`. Từng tệp nguồn được kiểm tra SHA-256 trong chương trình; tệp khác nội dung sẽ bị từ chối. Không dùng đường dẫn `main` thay đổi theo thời gian để tải lại. Ảnh nguồn nằm trong `data/public/`, đã loại khỏi Git. Không cần khóa AI, không gọi dịch vụ AI, không ghi vào lịch sử dự án người dùng.

Đã xây dựng chương trình `backend/scripts/benchmark_public_roofs.py` để:

1. Đổi nhãn kinh/vĩ độ WGS84 sang tọa độ điểm ảnh theo thông tin địa lý của TIFF.
2. Lấy tất cả 52 nhãn, giữ rõ lý do loại những mái sát mép ảnh hoặc nhỏ hơn 12 điểm ảnh.
3. Dùng khung bao nhãn cộng biên ba điểm ảnh để mô phỏng kỹ sư khoanh mái. **Đây là điều kiện có hỗ trợ chọn đối tượng**, không phải tự phát hiện mái trong toàn cảnh. Đường đa giác và điểm giữ/loại từ nhãn không được đưa vào thuật toán.
4. Gọi đúng hàm `extract_roof` GrabCut đang dùng trong ứng dụng, không viết một thuật toán khác để làm đẹp số liệu.
5. So sánh đa giác đầu ra với mặt nạ tham chiếu trong cùng hệ tọa độ, không tự căn chỉnh hay kéo giãn dự đoán theo nhãn. Lỗ trong nhãn được giữ khi tính diện tích.
6. Xuất JSON và trang HTML với đường tham chiếu xanh, kết quả cam. Ca không tách được tính điểm 0; ca loại không tham gia mẫu số nhưng vẫn có trong JSON.

## Kết quả chạy thực tế

| Chỉ số | Kết quả |
| --- | ---: |
| Tổng nhãn | 52 |
| Mái đủ điều kiện | 50 |
| Mái bị loại theo quy tắc | 2 |
| Tách được đa giác | 49/50 |
| Không tách được | 1/50 |
| Độ chồng khớp trung bình (IoU), gồm cả ca lỗi | 0,8503 |
| Trung vị IoU | 0,8961 |
| Số mái có IoU từ 0,75 | 45/50 |

IoU là diện tích giao chia diện tích hợp; **0,85 không có nghĩa kích thước mái chính xác 85%**, cũng không phải tỷ lệ đúng của một mô hình AI. Ngưỡng 0,75 chỉ để thống kê, không phải tiêu chuẩn nghiệm thu kỹ thuật.

Các ca cần nhìn kỹ trong báo cáo: mái 15 (0,7197), 25 (0,7059), 35 (0,6720), 40 (0,6152), 51 (không tách được). Số mái là chỉ số bắt đầu từ 0 trong GeoJSON, không phải số nhà. Không loại các ca này khỏi kết quả.

## Nhận xét và quyết định phát triển

**Giữ GrabCut như công cụ tạo biên nháp có người chỉnh**, chưa thay toàn bộ bằng một mô hình nặng. Điều kiện khoanh vùng đã giúp thuật toán rất nhiều; cần thêm nhiều địa điểm và loại mái trước khi chọn công nghệ thay thế. Một ảnh duy nhất với 50 mái có tương quan với nhau, không phải 50 công trình khảo sát độc lập.

| Ưu tiên tiếp theo | Lý do và cách đánh giá |
| --- | --- |
| Thử thao tác giữ mái/loại nền trên năm ca yếu | Đo mức cải thiện sau cùng một ngân sách thao tác, lưu số lần chấm và thời gian; không dùng đường nhãn làm điểm gợi ý rồi gọi là tự động. |
| Hiển thị và chỉnh khoảng trống/sân trong rõ ràng | Hàm hiện tại lấy đường bao ngoài lớn nhất; mặt nạ có lỗ hoặc mái nhiều phần chưa được bảo toàn đầy đủ trong đa giác đầu ra. |
| Đánh giá khung chọn do người thật khoanh | Khung từ nhãn đang là điều kiện thuận lợi. Phải đo độ nhạy khi người dùng chọn rộng/hẹp hoặc lệch. |
| Thử mô hình phân vùng nhẹ nếu vẫn khó sửa | So sánh cùng ảnh, cùng cách chọn mái, cả ca lỗi, thời gian CPU và RAM; chỉ tích hợp khi có lợi ích đo được. Hiện chưa tải hay tích hợp MobileSAM. |
| Bổ sung ảnh tại Việt Nam có số đo | Bộ công khai chưa đủ kiểm chứng bản vẽ theo mét, mái nhiều cao độ và các mái vật liệu khác. |

## Giới hạn phải giữ khi trình diễn

- Nacala là dữ liệu ảnh thật có nhãn tham chiếu, **không phải bản đo nghiệm thu công trình**.
- Chỉ đánh giá đường bao trên mặt ảnh. Không suy ra độ cao mái, độ dốc hay kích thước thật từ điểm IoU.
- Không có nhãn bóng theo ngày giờ và số liệu điện đối chiếu. Chưa kiểm chứng bóng che hoặc sản lượng trên mái thật.
- Chưa đánh giá hợp nhất ba loại ảnh, ảnh nghiêng điện thoại và bản vẽ kiến trúc.
- Không có cơ sở quảng cáo “tự dựng bản vẽ chính xác cao” từ kết quả này.

## Chạy lại

Từ thư mục gốc `SolarOpt`, dùng môi trường Python đã cài phụ thuộc backend và thêm `tifffile` (phụ thuộc riêng của phép thử, không bắt buộc cho máy chủ):

```powershell
python -m pip install tifffile
python backend/scripts/benchmark_public_roofs.py
```

Nếu đã có ba tệp đúng mã kiểm tra trong `data/public/nacala`, chương trình không tải lại. Kết quả: `output/validation/public_nacala/report.html` và `results.json`. Mở HTML bằng trình duyệt để xem ảnh đối chiếu. Các bài kiểm tra trong `backend/tests/test_public_benchmark.py` không tải mạng hoặc cần ảnh nguồn.
