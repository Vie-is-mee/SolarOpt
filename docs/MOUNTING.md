# Cách lắp trên mái bằng: sát mái, giá nghiêng, pin xoay theo mặt trời

Cập nhật 31/10/2026. Mã: `backend/app/services/geometry.py` (khoảng cách hàng, hình chiếu), `energy.py` (bức xạ), `mounting.py` (so sánh), giao diện `MountingPicker`.

Chỉ áp dụng cho **mặt mái bằng** (độ dốc ≤ 1°). Mặt dốc vẫn lắp sát mái.

## 1. Giá nghiêng xếp hàng

- Tấm nghiêng góc β về hướng chọn (mặc định Nam). Bức xạ tính trên mặt tấm (pvlib, cùng 12 ngày trời quang đại diện như các mặt mái).
- Hình chiếu bằng của tấm: cạnh chạy theo chiều dốc nhân cos β.
- **Khoảng cách hàng** (tâm đến tâm, trên mặt bằng) để hàng trước **không che hàng sau ngày đông chí 9h–15h** (khung thiết kế phổ biến cho giá cố định):

  D = L·cos β + max( L·sin β · cos(γ) / tan(α) )

  với L là cạnh tấm theo chiều dốc, α là độ cao mặt trời, γ là góc lệch giữa phương vị mặt trời và hướng tấm, lấy cực đại trên các thời điểm 9h, 9h30, …, 15h. Ngoài khung giờ này (sáng sớm, chiều muộn mùa đông) vẫn có thể có che nhẹ; chưa tính phần tổn thất đó.
- Ví dụ tấm 2,278 m, β = 15°: D ≈ 2,76 m ở TP.HCM, ≈ 3,00 m ở Hà Nội (mặt trời mùa đông thấp hơn).

## 2. Pin xoay 1 trục (tracker)

- Trục nằm ngang hướng Bắc–Nam, tấm quay từ Đông sang Tây theo mặt trời, góc xoay tối đa mặc định ±55°.
- **Lùi góc tránh che (backtracking):** khi mặt trời thấp, tấm xoay bớt lại để bóng hàng trước vừa chạm mép hàng sau, không che lên tấm (pvlib `singleaxis(backtrack=True, gcr=…)`).
- Khoảng cách hàng = bề rộng tấm theo hướng Đông–Tây / GCR. GCR nhỏ → hàng thưa, ít phải lùi góc, nhưng ít tấm.
- Hình chiếu bằng lấy bằng tấm nằm ngang (lớn nhất, lúc giữa trưa).

## 3. So sánh trên cùng mái

Nút “So sánh các cách lắp” chạy đầy đủ bộ xếp tấm cho 7 cách: sát mái, giá nghiêng 10°/15°/20°, pin xoay GCR 0,3/0,4/0,5 (cùng mái, vật cản, tấm, ngân sách; mục tiêu sản lượng cao nhất) và xếp hạng theo **tổng sản lượng năm**.

Mái 16 × 10 m không vật cản, TP.HCM, tấm 580 W:

| Cách lắp | Số tấm | kWh/năm | kWh mỗi tấm | So với sát mái |
|---|---:|---:|---:|---:|
| Sát mái | 42 | 31.581 | 752 | 0% |
| Giá nghiêng 10° | 42 | 32.009 | 762 | **+1,4%** |
| Giá nghiêng 15° | 36 | 27.381 | 761 | −13,3% |
| Giá nghiêng 20° | 36 | 27.168 | 755 | −14,0% |
| Pin xoay, GCR 0,3 | 14 | 12.907 | 922 | −59,1% |
| Pin xoay, GCR 0,4 | 21 | 19.184 | 914 | −39,3% |
| Pin xoay, GCR 0,5 | 21 | 18.857 | 898 | −40,3% |

**Kết luận:** pin xoay tăng khoảng 20% sản lượng mỗi tấm nhưng phải giãn hàng nên mất nhiều tấm; trên mái nhà bị giới hạn diện tích, tổng sản lượng thường **thấp hơn** lắp sát mái hoặc giá nghiêng nhẹ. Giá nghiêng 10° là điểm cân bằng tốt ở vĩ độ Việt Nam (thêm sản lượng nhẹ, nước mưa tự rửa bụi). Kết quả phụ thuộc kích thước mái; luôn chạy so sánh trên mái thật.

## 4. Giới hạn

- Chưa tính chi phí giá đỡ, bộ xoay, gia cố mái, tải gió và bảo trì — pin xoay trên mái thường đắt hơn đáng kể.
- Bóng vật cản lên tấm vẫn tính trên mặt bằng mái, chưa tính độ cao của tấm trên giá.
- Chưa có pin xoay 2 trục; chưa tính tấm hai mặt (bifacial).
