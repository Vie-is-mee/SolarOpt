# 1. Tấm pin — bước Bố trí tấm pin

*Đọc ngày 07/11/2026. Giá như trang in, đơn vị VND/tấm. Cột đ/Wp là giá chia công suất do SolarOpt tính. Không trang nào ghi rõ đã gồm VAT hay chưa.*

Dùng ở: `frontend/src/panelLibrary.ts`, `frontend/src/App.tsx` (tấm mặc định), `backend/app/schemas.py` (giá mặc định).

## Solar Saigon — https://solarsaigon.vn/gia-pin-nang-luong-mat-troi (ghi "Cập nhật: 26/05/2026", đơn giá bán sỉ lẻ)

| Tấm | Wp | Giá | đ/Wp |
|---|---|---|---|
| LONGi 580W Hi-MO 6 | 580 | 2.650.000 | 4.569 |
| LONGi 560W | 560 | 2.240.000 | 4.000 |
| LONGi 575W Hi-MO 5 | 575 | 2.300.000 | 4.000 |
| LONGi 2 mặt kính Bifacial 545W | 545 | 2.150.000 | 3.945 |
| Canadian Solar 550W Hiku6 | 550 | 2.270.000 | 4.127 |
| Canadian Solar 665W BiHiku7 | 665 | 2.400.000 | 3.609 |
| Jinko 550W Mono | 550 | 2.170.000 | 3.945 |
| Jinko 555W Mono | 555 | 2.190.000 | 3.946 |
| Jinko Tiger Neo N-type 580W | 580 | 2.380.000 | 4.103 |
| Jinko Tiger Neo N-type 600W | 600 | 2.200.000 | 3.667 |
| Jinko 475W Mono | 475 | 2.100.000 | 4.421 |
| JA Solar (khoảng theo hãng) | — | — | 3.400–4.100 |
| Trina (khoảng theo hãng) | — | — | 3.300–4.100 |

## DHC Solar — https://www.dhcsolar.com/gia-tam-pin-nang-luong-mat-troi-moi-nhat/ (tiêu đề "năm 2026", không có ngày cạnh bảng)

Trùng từng dòng với Solar Saigon. Có thêm:

| Tấm | Wp | Giá | đ/Wp |
|---|---|---|---|
| JA Solar 550 Wp | 550 | 2.200.000 | 4.000 (trang in "4.000 đ/Wp") |
| LONGi 450W | 450 | 1.800.000 | 4.000 |

## TC Energy — https://tcenergy.vn/danh-muc/tam-pin-nang-luong-mat-troi/ (tiêu đề "Bảng Giá Mới Nhất 11/2026"; giá đang bán, giá gốc trong ngoặc)

| Tấm | Wp | Giá | đ/Wp |
|---|---|---|---|
| LONGi 540W Hi-MO X10 | 540 | 2.270.800 (2.387.880) | 4.205 |
| LONGi 615W Hi-MO X7 2 mặt kính | 615 | 2.418.550 (2.550.405) | 3.933 |
| LONGi 620W 2 mặt kính | 620 | 2.437.400 (2.571.140) | 3.931 |
| LONGi 650W Hi-MO X10 | 650 | 2.648.000 (2.802.800) | 4.074 |
| Canadian 615W 2 mặt kính | 615 | 2.387.800 | 3.883 |
| Canadian 620W 2 mặt kính | 620 | 2.400.000 | 3.871 |
| Canadian 710W 2 mặt kính | 710 | 2.741.200 | 3.861 |
| JA Solar 625W 2 mặt kính | 625 | 2.343.750 | 3.750 |

## Kitawa — https://kitawa.com.vn/tam-pin-nang-luong-mat-troi (tiêu đề "6/2026")

| Tấm | Wp | Giá | đ/Wp |
|---|---|---|---|
| Jinko 555W | 555 | 2.497.500 | 4.500 |
| Jinko 580W | 580 | 2.610.000 | 4.500 |
| Jinko 585W | 585 | 2.325.375 | 3.975 |
| Jinko 610W (lưới sản phẩm) | 610 | 1.917.840 | 3.144 |
| LONGi 615Wp (lưới sản phẩm) | 615 | 2.169.720 | 3.528 |
| JA Solar 550W / LONGi 545W / Canadian 450W (bảng) | — | 3.795.000 / 3.760.500 / 3.105.000 | 6.900 — **bị loại**, gấp gần đôi mọi nguồn khác |

## Kết luận

- Tấm 540–720 W bán lẻ ở mức **3.144–4.569 đ/Wp**, trung vị **≈ 3.946 đ/Wp** (bỏ 3 dòng 6.900 đ/Wp của Kitawa).
- App dùng khoảng **3.100–4.600 đ/Wp** để cảnh báo giá bất thường.
- Tấm mặc định LONGi Hi-MO 6 580 W: **2.650.000 đ** (Solar Saigon, DHC).

## Thông số kỹ thuật

| Tấm | Số liệu | Nguồn |
|---|---|---|
| LONGi LR5-72HTH-580M | Voc 52,21 V · Vmp 44,06 V · Imp 13,17 A · Isc 14,20 A · 1134 × 2278 mm · hệ số nhiệt Voc −0,23 %/°C, Pmax −0,29 %/°C · năm đầu 97,5%, sau đó ~0,73%/năm (trang ghi xấp xỉ) | https://solarproof.com.au/products/LR5-72HTH-580MHi-MOX6Explorer.php (chép datasheet; longi.com chặn đọc tự động) |
| JA Solar JAM72S30 530–555/MR | Tải tĩnh mặt trước 5.400 Pa, mặt sau 2.400 Pa | Datasheet AU_EN_20220223A qua https://solarproof.com.au/product_brands/panels/ShanghaiJASolarTechnologyCoLtd.php |
| JA 550 W, Canadian CS6R-410MS | Bảng điện trong PDF là hình, không trích được chữ; giữ thông số hiện có, cần đối chiếu bản giấy | — |
