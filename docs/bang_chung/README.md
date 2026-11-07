# Bằng chứng số liệu thị trường — SolarOpt

*Đối chiếu ngày 07/11/2026. Danh sách đầy đủ, hiện trong app ở mục **Nguồn lấy số liệu**, lấy từ một file duy nhất: `frontend/src/dataSources.ts`.*

Mỗi file dưới đây ứng với một nhóm trong app. Mỗi file ghi số liệu thô từ trang nguồn (giá như trang in, đường dẫn, ngày đọc), để kiểm lại khi cần.

| File | Nhóm trong app | Nội dung |
|---|---|---|
| [1_tam_pin.md](1_tam_pin.md) | Bố trí tấm pin | Bảng giá tấm của 4 nhà phân phối; thông số LONGi, JA |
| [2_inverter_vat_tu.md](2_inverter_vat_tu.md) | Kiểm tra & bàn giao → Thiết kế điện | Giá inverter theo hãng, giá vật tư phụ |
| [3_gia_dien_ban_dien_du.md](3_gia_dien_ban_dien_du.md) | Kiểm tra & bàn giao → Kinh tế; Trợ lý tư vấn | Biểu giá EVN QĐ 2892, khung giờ, giá mua điện dư |
| [4_ket_cau_gio_pccc.md](4_ket_cau_gio_pccc.md) | Kiểm tra & bàn giao → Khảo sát hiện trường | Gió TCVN 2737:2023, hoạt tải, tải thử tấm, PCCC |
| [5_suat_dau_tu_kinh_te.md](5_suat_dau_tu_kinh_te.md) | Kiểm tra & bàn giao → Kinh tế | Suất đầu tư/kWp, thay inverter, giả định chưa có nguồn |
| [gia_thi_truong_2026-11-07.csv](gia_thi_truong_2026-11-07.csv) | — | Mọi điểm giá dạng bảng tính |
| [../GIA_VA_CHI_PHI_THUONG_MAI.md](../GIA_VA_CHI_PHI_THUONG_MAI.md) | Gói dự án, Lưu trữ | Giá đối thủ, giá mô hình AI, ảnh vệ tinh, tỷ giá |

## Số đã sửa sau khi đối chiếu

| Số liệu | Trước | Sau | Nguồn |
|---|---|---|---|
| Giá mua điện dư 2026 | 670 đ/kWh (đề xuất 2024) | **845 đ/kWh** (844,8, giá thị trường bình quân 2025) | NSMO công văn 205, 16/01/2026 (Thanh Niên 27/06/2026) |
| Tấm LONGi Hi-MO 6 580 W | 2.200.000 đ | **2.650.000 đ** | Solar Saigon 26/05/2026, DHC Solar |
| Thông số LONGi 580 W | Voc 52,1 · Vmp 43,6 · Imp 13,3 | **52,21 · 44,06 · 13,17** | Solar Proof (chép datasheet) |
| Tấm JA Solar 550 W | 2.000.000 đ | **2.200.000 đ** | DHC Solar |
| Tấm Canadian 410 W | 1.500.000 đ | **1.650.000 đ** | theo đ/Wp Canadian 550 W |
| Khoảng giá tấm (cảnh báo) | 2.700–4.600 đ/Wp | **3.100–4.600 đ/Wp** | 4 nhà phân phối |
| Inverter Huawei 3 kW / 10 kW / 15 kW / 20 kW / 30 kW / 40 kW / 100 kW | 13,5 / 30 / 40 / 45 / 60 / 72 / 120 tr | **15,5 / 27 / 38,2 / 46,2 / 55,5 / 59,2 / 107 tr** | DHC Solar, Megasolar |
| Growatt 6 kW / 10 kW 3 pha | 13,5 / 20 tr | **12,6 / 21 tr** | DHC Solar |
| Sungrow 50 kW / 110 kW | 85 / 135 tr | **67 / 106 tr** | DHC Solar (110 kW nội suy từ 125 kW) |
| Cáp DC 6 mm² | 26.000 đ/m | **24.000 đ/m** | DHC, TC Energy |
| Chống sét DC / AC | 650.000 / 550.000 đ | **350.000 / 250.000 đ** | DHC Solar |
| Tủ DC | 900.000 đ | **700.000 đ** | DHC 420k, TC 1,0 tr |
| Ray nhôm | 135.000 đ/m | **93.000 đ/m** | TC Energy 390k/thanh 4,2 m |
| Kẹp giữa / biên | 15.000 đ | **12.000 đ** | DHC, TC Energy |
| Dây / cọc tiếp địa | 22.000 đ/m · 1,5 tr | **25.000 đ/m · 840.000 đ** | TC Energy |
| Công tơ chống phát ngược 1 pha / 3 pha | 2,5 / 3,5 tr | **2,7 / 4,5 tr** | DHC Solar |
| Suất đầu tư sản xuất > 200 kWp | 7 tr/kWp | **7,5 tr/kWp** | mức thấp nhất báo chí 2026 (7,5–13) |
| Thay inverter năm 12 | 1,5 tr/kWp mọi loại | **2,2 / 1,5 / 1,0 tr/kWp** (hộ / KD / SX) | giá inverter hiện nay |
| Văn bản PCCC | 3288/C07-P4 (2020) | **207/C07-P4 (09/8/2024)**, thay 3288 | Diễn đàn Doanh nghiệp, EVN |

## Đã đối chiếu, giữ nguyên

- Biểu giá EVN QĐ 2892/QĐ-BCT (từ 01/11/2026): 5 bậc sinh hoạt; giá kinh doanh và sản xuất hạ áp, trung áp. Khớp từng số.
- Bán điện dư tối đa 50% sản lượng (NĐ 243/2026).
- Áp lực gió W0 TCVN 2737:2023: 65 / 95 / 125 / 155 / 185 daN/m².
- Tải thử mặt sau tấm 2.400 Pa (datasheet JA Solar).
- Nhóm tấm PCCC ≤ 40 × 40 m, cách nhau 1,5 m.
- Suất đầu tư hộ gia đình 11–13,5 tr/kWp; kinh doanh 7,5–10 tr/kWp.
- Giá cáp DC 4 mm², MC4, chân đỡ.

## Chưa có nguồn công khai (giữ là giả định, ghi rõ trong app)

- Bảo trì 150.000 đ/kWp/năm.
- Suy giảm 0,55%/năm. Trang chép datasheet LONGi ghi năm đầu −2,5%, sau đó ~0,73%/năm; cần datasheet gốc.
- Tăng giá điện 3%/năm; chiết khấu 8%/năm.
- VAT 8% (giảm thuế đến hết 2026).
- Bảng tổn thất sản lượng.
- Giá CB DC, cầu dao cách ly, nút dừng khẩn, cáp AC nhiều lõi, kết nối điều độ.
- Ngưỡng điện áp 253 V.
- Trong PCCC: khoảng cách 3 m tới lối ra mái và 2,5 m tới lan can lấy từ 3288; cần đối chiếu toàn văn 207/C07-P4.

## Cách cập nhật

1. Sửa số ở file trong cột "Dùng ở" của mục Nguồn lấy số liệu.
2. Sửa `value`, `sources`, `checked` trong `frontend/src/dataSources.ts`.
3. Thêm dòng vào file bằng chứng tương ứng ở thư mục này. Ghi số như trang in, kèm đường dẫn và ngày đọc.
4. Chạy kiểm thử (`pytest`, `npm test`) rồi commit cùng lúc.

Việc định kỳ:

- **Tháng 1 hằng năm:** cập nhật giá mua điện dư theo công bố của NSMO.
- **Khi Bộ Công Thương điều chỉnh giá điện:** cập nhật biểu giá EVN.
- **Mỗi quý:** đọc lại giá tấm pin và inverter.

**Lưu ý trang nguồn:** các trang thương mại có thể đổi giá hoặc gỡ bài. Khi cần làm bằng chứng chính thức, mở từng đường dẫn và lưu thành PDF (Ctrl+P → Lưu PDF) vào thư mục này, đặt tên theo ngày đọc.
