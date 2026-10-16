# Bước 4 — Chỉnh biên trên ảnh và giữ đúng tỷ lệ

Ngày: 15/10/2026.

## Những thay đổi đã triển khai

### Chỉnh ngay trên ảnh nguồn

- Kết quả biên được vẽ thành lớp phủ trên ảnh gốc, có thanh chỉnh độ rõ. Không cần đọc một ảnh kết quả đã tô kín để sửa.
- Chọn **Kéo sửa biên** để lấy kết quả nhận diện thành các đỉnh có thể kéo. Bấm đúp nút giữa cạnh để thêm đỉnh; bấm đúp đỉnh để xóa, giữ tối thiểu ba đỉnh.
- Có hoàn tác/làm lại riêng cho đường biên và khoảng trống trên ảnh. Lịch sử này độc lập với hoàn tác bản vẽ đã áp dụng.
- Chọn **Vẽ sân trong**, chấm các góc và **Khép khoảng trống**. Có thể kéo đỉnh, thêm/xóa đỉnh khoảng trống hoặc xóa riêng từng khoảng trống.
- Sau khi sửa, bấm **Dùng biên đã chấm** để máy chủ kiểm tra lại hình học, rồi mới **Áp dụng biên và tỷ lệ**.

### Giữ khoảng trống khi chuyển sang bản vẽ

Trước đây công cụ chỉ lấy đường bao ngoài. Hiện công cụ đọc quan hệ đường bao và lỗ trong mặt nạ, trả cả tọa độ trên ảnh và tọa độ trong khung mái. Khi áp dụng, chúng trở thành `roof_openings`, được bộ hình học hiện có loại khỏi diện tích lắp đặt và vùng bố trí pin.

Đường biên thủ công có khoảng trống tự cắt, nằm ngoài mái, chồng hoặc chạm khoảng trống khác bị từ chối. Các lỗ tự động quá nhỏ bị bỏ qua; những lỗ không thể giữ hợp lệ sau đơn giản hóa được cảnh báo. Có giới hạn 24 khoảng trống và 80 đỉnh mỗi khoảng trống để khớp dữ liệu dự án.

**Vùng tối không đồng nghĩa sân trong.** Kỹ sư vẫn phải kiểm tra và xóa vùng nhận nhầm. Vật cản có lỗ chưa được hỗ trợ: ứng dụng chặn áp dụng loại hình này và yêu cầu chia thành các vật cản riêng.

### Một tỷ lệ cho cả hai chiều

- Có đoạn tham chiếu: mét/điểm ảnh = chiều dài thật / chiều dài đoạn trên ảnh. Cả chiều rộng và chiều dài mái dùng cùng tỷ lệ này.
- Chưa có đoạn tham chiếu: lấy chiều rộng khung bao để suy ra tỷ lệ; chiều dài nhập ở bước 1 dùng để đối chiếu.
- Tính khoảng cách theo điểm ảnh gốc, không lấy khoảng cách phần trăm trên ảnh chữ nhật làm khoảng cách thật.
- Nếu số đo đối chiếu lệch quá **3%**, chặn áp dụng và yêu cầu kiểm tra số đo, biên mái hoặc phối cảnh. Không tự kéo riêng trục ngang và dọc để khớp số đo.
- Có thêm **Đo kiểm tra**: dùng một đoạn khác với đoạn hiệu chuẩn, nhập chiều dài thật để so sánh. Nếu đã khai báo đoạn kiểm tra hợp lệ mà sai lệch trên 3%, cũng chặn áp dụng.
- Thay số đo ở bước Dữ liệu sau khi đã trích ảnh cũng được kiểm tra tỷ lệ trước khi quy đổi lại bản vẽ.
- Nguồn kích thước suy từ đoạn tham chiếu được lưu đúng là `reference`; không bị đổi thành `measured` khi chuyển bước.

Ngưỡng 3% là kiểm tra tính nhất quán nội bộ, **không phải cam kết sai số đo đạc**. Các đoạn phải thuộc cùng mặt phẳng phù hợp sau hiệu chỉnh. Ảnh nghiêng, nhiều độ cao hoặc thiếu số đo không thể được khôi phục chính xác chỉ nhờ một đoạn tham chiếu.

### Chỉnh bản vẽ và kết quả phụ thuộc

Kéo đỉnh mái, mặt mái và khoảng trống trong bản vẽ được giới hạn trong khung số đo hiện có; thao tác kéo không tự nới khung và làm giãn ảnh nền. Có thể đổi kích thước tại bước Dữ liệu sau khi đối chiếu số đo.

Đầu vào mới từ ảnh được kiểm tra trên máy chủ trước khi thay bản vẽ. Thay biên/khoảng trống yêu cầu xác nhận lại; các phương án cũ bị đánh dấu cần tính lại và không thể lưu bản kỹ sư duyệt như thể vẫn dùng dữ liệu mới.

## Kiểm tra đã thực hiện

- 127 kiểm thử máy chủ đạt, gồm bảy ca mới về khoảng trống và vùng rời: giữ sân trong với biên thủ công/GrabCut, tọa độ đồng nhất, từ chối lỗ sai và cảnh báo khi có nhiều vùng rời.
- Sáu kiểm thử giao diện về tính tỷ lệ: ảnh chữ nhật, đo chéo, số đo mâu thuẫn, đoạn tham chiếu, làm tròn và dữ liệu không hợp lệ.
- Kiểm tra TypeScript và dựng giao diện.
- Trình duyệt Edge: trích sân trong, chặn khung số đo mâu thuẫn, đo tham chiếu sau nhận diện không mất kết quả, đoạn kiểm tra mâu thuẫn bị chặn, kéo đỉnh mái/sân trong, hoàn tác/làm lại, áp dụng sang bản vẽ và giữ nguồn `reference`.
- Cả ba phương án bố trí tránh khoảng trống; thêm khoảng trống làm phương án cũ mất hiệu lực và chặn lưu bản duyệt. Không có lỗi JavaScript; không tràn ngang ở màn hình 390 px.
- Chạy lại 50 mái Nacala theo cùng điều kiện khoanh vùng của bước 3, lần này tính cả lỗ trong dự đoán: IoU trung bình **0,85024**, so với **0,85031** trước đó; vẫn 45/50 mái từ 0,75 và một ca không tách được. Một vùng tối bị nhận thành khoảng trống làm điểm giảm nhẹ. Đây là kiểm tra tác động, **không phải bằng chứng tăng độ chính xác nhận diện**.

Lệnh kiểm tra:

```powershell
# Trong backend
python -m pytest -q

# Trong frontend
npm test
npm run typecheck
npm run build

# Từ thư mục SolarOpt, khi đã có dữ liệu và tifffile
python backend/scripts/benchmark_public_roofs.py --out output/validation/public_nacala_openings
```

## Phần còn lại

Chưa tự dựng đầy đủ nhiều phần mái rời từ một ảnh: chỉ cảnh báo vùng rời bị bỏ lại, không tự nối chúng. Chưa hợp nhất nhiều ảnh, suy cao độ tự động hoặc kiểm chứng bóng/sản lượng bằng khảo sát thật. Việc lưu tệp dự án vẫn lưu hình học, không đóng gói ảnh nguồn. Bước tiếp theo nên tập trung lưu nguồn đo và ảnh đối chiếu theo phiên bản, sau đó đánh giá việc sửa các mái khó bằng thao tác của kỹ sư.
