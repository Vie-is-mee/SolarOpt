# 5. Suất đầu tư và giả định kinh tế — bước Kinh tế, Trợ lý tư vấn

*Đọc ngày 07/11/2026.* Dùng ở: `frontend/src/economics.ts` (`marketCapex`, `marketDefaults`), `backend/app/services/advisor/scenarios.py` (`market_capex`), `backend/app/services/advisor/models.py`.

## Suất đầu tư trọn gói (EPC, gồm thuế)

| Nguồn | Số liệu |
|---|---|
| Bộ Công Thương, qua [Tinh tế 2026](https://tinhte.vn/thread/cap-nhat-gia-lap-dien-nang-luong-mat-troi-moi-nhat-2026.4175422/) | Hộ gia đình 12–15 tr/kWp; doanh nghiệp 7,5–13 tr/kWp |
| [Tuổi Trẻ 04/2026](https://tuoitre.vn/chao-moi-lap-dien-mat-troi-lai-soi-dong-du-goi-gia-nguoi-dan-thac-thom-chat-luong-20260404224958849.htm) | Gói 13–15 kW: 200–250 tr (≈ 15–17 tr/kWp); 3,3 kWp: hơn 63 tr (≈ 19 tr/kWp) |
| [Vietnam Solar](https://vietnamsolar.vn/chi-phi-lap-dien-mat-troi-hoa-luoi-10kwp-inverter-huawei-10kw-3-pha/) | Trọn gói 10 kWp 3 pha: 125–140 tr, đã gồm VAT 8% (12,5–14 tr/kWp) |

| Quy mô | App dùng (tr/kWp) | So với nguồn |
|---|---|---|
| Hộ ≤ 5 kWp | 13,5 | trong khoảng 12–15 |
| Hộ ≤ 15 kWp | 12 | trong khoảng 12–15 |
| Hộ > 15 kWp | 11 | thấp hơn khoảng 12–15, có lý vì hệ lớn |
| Kinh doanh ≤ 50 kWp | 10 | trong khoảng 7,5–13 |
| Kinh doanh ≤ 200 kWp | 8,5 | trong khoảng 7,5–13 |
| Kinh doanh > 200 kWp | 7,5 | trong khoảng 7,5–13 |
| Sản xuất ≤ 200 kWp | 8 | trong khoảng 7,5–13 |
| Sản xuất > 200 kWp | **7,5** | trước đây 7, thấp hơn sàn 7,5 → đã sửa |

## Thay inverter năm 12

Theo giá inverter hiện nay (xem [2_inverter_vat_tu.md](2_inverter_vat_tu.md)), chia hệ số DC/AC ≈ 1,15:

| Khách hàng | Trước | Nay |
|---|---|---|
| Hộ gia đình | 1,5 tr/kWp | **2,2 tr/kWp** |
| Kinh doanh | 1,5 tr/kWp | **1,5 tr/kWp** |
| Sản xuất | 1,5 tr/kWp | **1,0 tr/kWp** |

## Giả định chưa có nguồn công khai (hiện nhãn "Giả định" trong app)

| Giả định | Giá trị | Ghi chú |
|---|---|---|
| Bảo trì, vệ sinh | 150.000 đ/kWp/năm | Bước Bàn giao và Trợ lý tư vấn dùng chung. Cần báo giá dịch vụ O&M. Nguồn cho tần suất: vệ sinh 2–4 lần/năm ([VOV](https://vov.vn/cong-nghe/mot-viec-nhieu-gia-dinh-bo-quen-co-the-khien-dien-mat-troi-giam-toi-40-hieu-suat-post1320900.vov)) |
| Suy giảm tấm | 0,55%/năm | Dùng chung cho Bàn giao và Trợ lý. Trang chép datasheet LONGi ghi ~0,73%/năm sau năm đầu. Nên lấy theo bảo hành của đúng tấm mua |
| Tăng giá điện | 3%/năm | — |
| Chiết khấu | 8%/năm | — |
| Lãi nhà thầu | 15% | — |
| Dự phòng | 3% | — |
| Tỷ lệ tự dùng mặc định | hộ 50%, kinh doanh 80%, sản xuất 90% | Chỉ dùng khi chưa nhập hóa đơn; khi có hóa đơn, app tính theo từng giờ |
