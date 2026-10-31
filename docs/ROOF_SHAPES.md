# Mái đặc biệt: chiến lược để SolarOpt xử lý mọi dạng mái

Cập nhật 31/10/2026. Mã: `backend/app/services/roof_templates.py`, API `POST /api/roof/template`, giao diện `RoofShapePicker`.

## 1. Ý tưởng cốt lõi: mọi mái là tập hợp các mặt phẳng

SolarOpt không viết một thuật toán riêng cho từng loại mái. Mọi mái được đưa về **một ngôn ngữ chung: các mặt phẳng nhỏ (facet)**, mỗi mặt có biên trên mặt bằng, cao độ, độ dốc và hướng dốc.

| Dạng mái | Cách đưa về mặt phẳng |
|---|---|
| Mái bằng | 1 mặt ngang |
| Mái một dốc | 1 mặt nghiêng |
| Mái chữ A (2 dốc) | 2 mặt gặp nhau ở đường nóc |
| Mái 4 dốc | 2 hình thang + 2 tam giác đầu hồi; nếu mái vuông thành mái chóp 4 tam giác |
| Mái vòm cung, vòm parabol | Nhiều dải phẳng song song đường nóc; mỗi dải là dây cung của đường cong, độ lệch so với đường cong được tính và báo ra |
| Mái chữ L, mái ghép, mái nhiều cao độ | Vẽ phần mái riêng (đã có) hoặc tạo theo mẫu rồi cắt theo biên mái |

Khi đã là mặt phẳng, các phần sẵn có chạy được ngay mà không cần trường hợp đặc biệt: bức xạ theo độ dốc/hướng từng mặt (pvlib), bóng giữa các mặt (mặt cao che mặt thấp; mặt lồi tự nhiên không che nhau), xếp tấm, kiểm tra phương án và thử sai số.

## 2. Vai trò của AI: nhận dạng, không tự dựng hình 3D

Ảnh 2D không đủ để AI tự “nghĩ” ra hình học 3D chính xác, và mô hình ngôn ngữ thị giác hay đoán sai số đo. Nên chia việc:

1. **AI nhận dạng dạng mái và vài tham số** từ ảnh/bản vẽ: `roof_shape` (bằng, một dốc, chữ A, 4 dốc, vòm cung, parabol, khác), hướng đường nóc, và chiều cao đỉnh **chỉ khi bản vẽ ghi rõ**. Máy chủ loại bỏ giá trị ngoài danh sách thay vì tin mù quáng.
2. **Bộ sinh mặt mái tính hình học một cách xác định**: từ dạng mái + kích thước + chiều cao đỉnh → các mặt phẳng với cao độ, độ dốc, hướng đúng; có test kiểm tra đường nóc và diềm ở đúng cao độ.
3. **Kỹ sư xác nhận**: giao diện điền sẵn theo gợi ý AI, kỹ sư sửa rồi bấm “Tạo các mặt mái”, xem trên bản vẽ và xác nhận dữ liệu như mọi bước khác.

Hướng mở rộng khi có dữ liệu tốt hơn (chưa triển khai): ảnh drone nhiều góc hoặc LiDAR → đám mây điểm → tách mặt phẳng tự động (RANSAC) → cùng ngôn ngữ mặt phẳng ở trên. Khi đó AI không cần đoán loại mái; dạng mái lạ (răng cưa, mái chồng diêm, mái lượn sóng) tự thành các mặt phẳng.

## 3. Mái cong: chia dải bao nhiêu là đủ

- Dải được đặt sao cho đường ghép trùng mép hàng tấm (bắt đầu từ mép lùi + bội số bước tấm), để tấm không bị cắt ngang đường ghép.
- Ưu tiên dải rộng nhất mà dây cung vẫn lệch đường cong ≤ 5 cm (mặc định). Nếu đường cong quá gắt, vẫn chia mỗi dải một hàng tấm và **báo độ lệch thật** kèm gợi ý dùng ray uốn hoặc tấm dẻo.
- Dải dốc hơn 60° bị đánh dấu không lắp pin.
- Các dải cùng một vòm thuộc một **nhóm liền khối**: chỉ lùi mép quanh biên ngoài cả vòm, không lùi ở từng đường ghép bên trong (nếu không, mỗi dải mất 0,7 m và gần như không còn chỗ đặt tấm).

## 4. Kết quả thử (mái 16 × 10 m, tấm 1,13 × 2,28 m, không vật cản)

| Dạng mái | Số mặt | Số tấm | Ghi chú |
|---|---:|---:|---|
| Mái bằng | 1 | 42 | |
| Mái một dốc 8,5° | 1 | 42 | |
| Mái chữ A 26,6° | 2 | 35 | Mặt hướng Nam 21 tấm, hướng Bắc 14 tấm |
| Mái 4 dốc 26,6° | 4 | 17 | Lùi mép ở mọi đường nóc/đường hồi |
| Vòm cung cao 1,2 m | 8 | 42 | Lệch 3,5 cm |
| Vòm cung cao 2,5 m | 8 | 42 | Lệch 12,7 cm → cảnh báo ray uốn/tấm dẻo |
| Vòm parabol cao 3 m | 13 | 36 | Lệch 2,9 cm |

Mọi phương án trên đều đạt kiểm tra (biên mái, chồng tấm, khe, sản lượng).

## 5. Giới hạn hiện tại

- Kích thước tấm trên mặt dốc vẫn tính theo mặt bằng, chưa co theo độ dốc (cos góc dốc) → số tấm trên mái dốc có thể **thấp hơn** thực tế (an toàn). Sửa cần lưới xếp riêng cho từng mặt.
- Mái vòm cầu (dome), mái lượn sóng, mái răng cưa chưa có mẫu; có thể vẽ từng phần mái thủ công.
- Mẫu tạo theo khung chữ nhật rồi cắt theo biên mái; mái không vuông cần kiểm tra lại đường nóc.
- Độ chính xác nhận dạng dạng mái của AI chưa được đo trên ảnh thật.
