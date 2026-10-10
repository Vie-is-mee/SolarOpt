# SolarOpt Studio — hiện trạng công nghệ và kịch bản demo

Cập nhật 10/10/2026. Tài liệu này mô tả bản đang chạy trong `frontend/src/App.tsx` và `backend/app`. Giao diện cũ được lưu tham khảo trong `docs/legacy/App.v1.tsx`; những mô tả Gemini/fallback trong tài liệu phiên bản cũ không còn phản ánh luồng hiện tại.

## Các phần đã triển khai

| Phần | Cách hoạt động hiện tại | Điều cần nói rõ khi demo |
|---|---|---|
| Đầu vào | Một ảnh chính dạng drone/bản vẽ/ảnh một phần; tối đa hai ảnh chi tiết; JPG, PNG, WEBP, PDF; 12 MB/tệp | PDF dùng trang đầu cho AI; ảnh không tự cung cấp kích thước mét hay hướng Bắc |
| AI đọc ảnh | Chọn Groq, Ollama hoặc Gemini qua cấu hình máy chủ; gợi ý biên mái, hộp vật cản, chữ, mức tự đánh giá và ghi chú | Đã gọi Groq thật thành công trên ảnh tự tạo; chưa đo độ chính xác mái thật. Độ tin cậy là tự đánh giá, chưa hiệu chỉnh |
| Kỹ sư sửa dữ liệu | OpenCV tách biên CPU; chấm biên/đo tham chiếu; kéo đỉnh mái, kéo góc/xoay vật thể, đa giác/bầu dục, vùng mái cao/thấp, khoảng trống và hoàn tác; sửa được ở màn hình mô phỏng | Số đo/cao độ do kỹ sư cung cấp. Hiệu chỉnh bốn góc chỉ cho một mặt phẳng chữ nhật, cần biết hai cạnh thật; chưa ghép tọa độ nhiều ảnh |
| Nhà bên cạnh | Chọn hướng, khoảng cách, số tầng ước lượng; chỉnh lại mặt bằng và chiều cao từ đất | 3,3 m/tầng là giá trị gợi ý. Cần đo/xác nhận; chiều cao trên mái và chiều cao từ đất là hai cách nhập khác nhau |
| Mặt trời và bóng | Tính vị trí theo tọa độ, ngày, giờ Việt Nam; xoay đúng hướng bản vẽ; chiếu bóng vật thể chữ nhật/bầu dục/đa giác lên các phần mái phẳng/nghiêng riêng; mái cao đổ bóng lên mái thấp | Mặt trời không luôn mọc đúng hướng Đông/lặn đúng hướng Tây; thay đổi theo ngày và địa điểm |
| Bức xạ | Mô hình trời quang pvlib; ô bản đồ tính che khuất; có nút lấy dữ liệu nắng năm từ PVGIS | Không phải đo nắng thực tế hoặc dự báo mây; PVGIS cần mạng, lỗi được gắn nhãn |
| Bố trí | Tạo ba phương án với ngưỡng bóng khác nhau bằng lưới ứng viên và OR-Tools; xét biên mái, vật cản, khoảng cách, giá tấm và ngân sách | Tối ưu trong lưới cố định, một chiều đặt tấm; chưa tối ưu mọi góc xoay/phương án đấu điện |
| Kiểm tra | 10 điều kiện về xác nhận, biên mái, va chạm, chồng tấm, bóng, ngân sách, thông số, sản lượng, phương án và tính nhất quán | Điều kiện đạt trong phạm vi đã lập trình; chưa chứng nhận thi công |
| Thử sai số | Tám tình huống áp vào bố trí gốc, giữ số tấm để xem điều kiện nào không đạt | Không tự bố trí lại trong phép thử; đạt tám tình huống không có nghĩa đạt mọi điều kiện thực tế |
| Cập nhật thiết kế | Truy vết các nhóm đầu vào đổi, chạy lại bộ bố trí có ưu tiên giữ vị trí, thống kê trước/sau và tỷ lệ giữ lại | Chưa chỉ tính lại một phần; chưa chứng minh nhanh hơn công cụ đối thủ |
| Bàn giao | Lưu bản kỹ sư duyệt, lịch sử SQLite, nhập/xuất JSON, bản vẽ SVG, in báo cáo PDF có bản vẽ | Phiên bản khôi phục phải xác nhận/tính lại; bản duyệt nội bộ không thay thế hồ sơ kỹ thuật |
| Giao diện | Năm bước, nền sáng xanh lá, bản vẽ tương tác, các trạng thái lỗi/chờ và nhật ký từ hoạt động thật, dùng được trên điện thoại | Dữ liệu mẫu luôn có nhãn; chưa có AI thì không giả kết quả nhận diện |

## Ý tưởng của đội: phần hợp lý và phần cần bổ sung

Hướng cho kỹ sư nhìn và sửa kết quả AI là phù hợp. Giá trị thực tế nằm ở việc biến ảnh thành dữ liệu có thể đối chiếu, sửa rồi tính lại được. Nhật ký hiển thị bước đã hoàn thành, quan sát và dữ liệu đầu ra; không cần trình bày suy luận ẩn của mô hình hoặc hiệu ứng tiến độ giả.

Thông tin Đông/Tây/Nam/Bắc và số tầng chỉ là điểm bắt đầu. Một công trình 5 tầng cách 3 m có tác động khác công trình cùng chiều cao cách 20 m. Bản demo dùng thêm chiều cao mái nhà mình, khoảng cách, vị trí và kích thước mặt bằng nhà bên cạnh. Vật thể có mặt bằng chữ nhật, bầu dục hoặc đa giác xoay được, nhưng vẫn là khối đứng; chưa gồm cây có tán 3D phức tạp hoặc kính phản xạ.

Ảnh chụp một phần giúp nhận biết vật cản, nhưng không xác định duy nhất hình dạng toàn mái, tỷ lệ, cao độ và vị trí vật cản bị che. Luồng hiện tại yêu cầu kỹ sư đặt vị trí và nhập số đo thay cho việc để AI đoán. Một ảnh 2D không đủ để dựng lại chính xác mọi công trình 3D xung quanh.

## Những giới hạn cần ưu tiên tiếp sau demo

| Ưu tiên | Công việc | Bằng chứng hoàn thành cần có |
|---|---|---|
| 1 | Đánh giá Groq + OpenCV trên mái thật (kết nối Groq đã thử) | Bộ ảnh được phép sử dụng, bản vẽ đối chiếu, số vật cản đúng/sai, sai lệch vị trí, thời gian và hạn mức thực dùng |
| 1 | Kiểm tra với kỹ sư và một mái khảo sát thực | Số đo, ảnh, hướng Bắc thật, cao độ và mặt bằng nhà lân cận; giải thích từng sai lệch |
| 2 | Mô phỏng sản lượng theo giờ cả năm và đối chiếu công cụ chuẩn | Dữ liệu thời tiết ghi nguồn, mô hình điện/bóng che phù hợp, báo cáo sai số. Hiện sản lượng dùng 9 thời điểm đại diện và công thức sơ bộ |
| 2 | Kiểm chứng mái nhiều mặt đã nhập, phối cảnh, địa hình, kích thước chiếu bằng của tấm trên mái nghiêng | Dữ liệu hình học được đo/hiệu chỉnh; so sánh với bản CAD hoặc khảo sát. Hiện tọa độ là mặt bằng ngang; đã có vùng cao/thấp nhập tay và hiệu chỉnh một mặt phẳng, chưa tự suy ra 3D từ nhiều ảnh |
| 3 | Đấu chuỗi tấm, chọn bộ biến đổi điện, kiểm tra tải mái và các yêu cầu thi công | Quy tắc chuyên môn được kỹ sư xác nhận, thông số thiết bị và bộ kiểm thử riêng |
| 3 | Tài khoản, nhiều dự án, phân quyền, vận hành trên máy chủ | Kiểm tra truy cập, sao lưu, theo dõi lỗi và chi phí; hiện ứng dụng dành cho demo trên máy cá nhân |

Phần thương mại, tiếp thị và triển khai thực tế được giữ trong `output/pdf/SolarOpt_Thuong_mai_Tiep_thi_Trien_khai_thuc_te.pdf`, để đội quay lại sau. Hiện giá hiển thị trong thiết kế chỉ gồm tấm pin, không dùng làm tổng chi phí đầu tư hoặc dự báo lợi nhuận.

Hướng dẫn chi tiết phần ảnh và chỉnh mái: [ROOF_IMAGE_PIPELINE.md](ROOF_IMAGE_PIPELINE.md).

## Kịch bản demo khoảng 5 phút

1. **30 giây:** mở website, nói rõ dự án mẫu hay mái thực. Chỉ ba loại đầu vào và số đo cần bổ sung. Nếu có khóa, đọc ảnh đã chuẩn bị và đối chiếu đề xuất; nếu chưa, dùng mẫu có nhãn.
2. **60 giây:** mở bản vẽ, chỉnh bồn nước, thêm nhà phía Đông, nhập khoảng cách, số tầng rồi sửa chiều cao từ số đo. Giải thích cao độ mái và hướng Bắc; xác nhận dữ liệu.
3. **60 giây:** mở bóng che, kéo từ buổi sáng sang chiều, đổi ngày và chuyển bản đồ bức xạ. Chỉ rõ bóng nhà bên cạnh và nắng trời quang.
4. **60 giây:** tính ba phương án, so số tấm, công suất, sản lượng sơ bộ và giá riêng tấm pin. Giải thích tiêu chí loại các vị trí bị bóng.
5. **45 giây:** chạy kiểm tra, tám tình huống sai số, lưu bản duyệt và xuất SVG/báo cáo.
6. **45 giây:** quay lại đổi chiều cao bồn nước, chỉ cảnh báo kết quả cũ, xác nhận rồi cập nhật. Xem số vị trí giữ lại và trước/sau; mở lịch sử phiên bản.

## Nguồn tham khảo kỹ thuật và sản phẩm

- [Groq Vision](https://console.groq.com/docs/vision) và [hạn mức](https://console.groq.com/docs/rate-limits): chọn mô hình ảnh và giới hạn thực tế.
- [Ollama Qwen3-VL](https://ollama.com/library/qwen3-vl), [API chat](https://docs.ollama.com/api/chat): lựa chọn chạy tại máy.
- [OpenSolar Auto Design](https://www.opensolar.com/auto-design/) và [luồng ứng dụng](https://support.opensolar.com/hc/en-us/articles/13211447430799-Application-Flow): tham khảo cách đưa dữ liệu vào thiết kế và trình bày phương án. Chưa có phép đo để khẳng định SolarOpt vượt OpenSolar.
- [pvlib](https://pvlib-python.readthedocs.io/en/stable/) và [PVGIS](https://re.jrc.ec.europa.eu/pvg_tools/en/): vị trí mặt trời, bức xạ và dữ liệu nắng.
