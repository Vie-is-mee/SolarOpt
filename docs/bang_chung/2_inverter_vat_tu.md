# 2. Inverter và vật tư — bước Kiểm tra & bàn giao → Thiết kế điện

*Đọc ngày 07/11/2026. Giá như trang in (VND). Không trang nào ghi ngày cạnh giá hay ghi rõ VAT. DHC Solar có bảng "Bảng giá" lệch với giá niêm yết của chính trang đó; ở đây ghi cả hai.*

Dùng ở: `backend/app/services/electrical.py` (`CATALOG`, `PRICES`, `DC_SIZES`), `frontend/src/economics.ts` (thay inverter năm 12).

## Inverter hòa lưới

| Model | Giá niêm yết (bảng giá) | Nguồn | App dùng |
|---|---|---|---|
| Huawei SUN2000-3KTL-L1, 3 kW 1 pha | 15.500.000 | DHC Huawei | 15,5 tr |
| Huawei SUN2000-5KTL-L1, 5 kW 1 pha | 19.200.000 (DHC) · 15.000.000 (Megasolar) | DHC; megasolar.vn | 17 tr (trung bình) |
| Huawei SUN2000-5KTL-M1, 5 kW 3 pha | 22.000.000 | DHC | — |
| Huawei SUN2000-10KTL-M1, 10 kW 3 pha | 31.900.000 (DHC) · 22.000.000 (Megasolar) | DHC; Megasolar | 27 tr (trung bình) |
| Huawei SUN2000-15KTL-M2 | 38.200.000 | DHC | 38,2 tr |
| Huawei SUN2000-20KTL-M2 | 46.200.000 | DHC | 46,2 tr |
| Huawei SUN2000-30KTL-M3 | 55.500.000 | DHC | 55,5 tr |
| Huawei 40 kW (không ghi model) | 59.200.000 (bảng: SUN2000-40KTL-M1 42.000.000) | DHC | 59,2 tr |
| Huawei SUN2000-50KTL-M3 | 67.000.000 | DHC | — |
| Huawei SUN2000-100KTL-M1 | 107.000.000 (gạch 124–125 tr; bảng 96.000.000) | DHC | 107 tr |
| Huawei SUN2000-115KTL-M2 · 150K-MG0 | 121.000.000 · 162.000.000 | DHC | — |
| Growatt MIN 6000TL-X, 6 kW 1 pha | 12.600.000 (bảng 12.500.000) | DHC Growatt | 12,6 tr |
| Growatt MOD 10KTL3-X, 10 kW 3 pha | 21.000.000 | DHC Growatt | 21 tr |
| Growatt MOD 15KTL3-X · MID 20KTL3-X | 23.000.000 · 26.900.000 | DHC Growatt | — |
| Growatt MAC 50KTL3-X · MAX 110KTL3-LV | 60.000.000 · 88.000.000 | DHC Growatt | — |
| Sungrow SG50CX | 67.000.000 | DHC | 67 tr |
| Sungrow SG125CX-P2 · SG150CX | 121.000.000 · 155.000.000 | DHC Sungrow | SG110CX nội suy **106 tr** |
| Solis 6 kW 1 pha (bảng) | 14.000.000 | DHC Solis | Solis 5 kW giữ 12,5 tr |

Nguồn:

- DHC Huawei: https://www.dhcsolar.com/danh-muc-san-pham/bien-tan-nang-luong-mat-troi/inverter-huawei/ và https://www.dhcsolar.com/san-pham/inverter-huawei-5kw-1-pha/
- DHC Growatt: https://www.dhcsolar.com/danh-muc-san-pham/bien-tan-nang-luong-mat-troi/inverter-growatt/
- DHC Sungrow: https://www.dhcsolar.com/danh-muc-san-pham/bien-tan-nang-luong-mat-troi/inverter-sungrow/
- DHC Solis: https://www.dhcsolar.com/danh-muc-san-pham/bien-tan-nang-luong-mat-troi/inverter-solis/
- Megasolar: https://megasolar.vn/san-pham/inverter-huawei-5kw-1-pha/

Chưa có niêm yết, giữ giá lập kế hoạch: Huawei 6 kW L1 (19 tr), 8 kW M1 (26 tr), 12 kW M2 (36 tr).

**Giá theo kW AC:**

| Loại inverter | Giá/kW AC |
|---|---|
| 1 pha 3–6 kW | 2,1–5,2 tr |
| 3 pha 10–20 kW | 1,35–3,2 tr |
| 30–50 kW | 1,2–1,85 tr |
| ≥ 100 kW | 0,77–1,07 tr |

Từ đó app tính chi phí thay inverter năm 12 (chia hệ số DC/AC ≈ 1,15): hộ gia đình 2,2 tr/kWp, kinh doanh 1,5 tr/kWp, sản xuất 1,0 tr/kWp.

## Vật tư phụ

| Vật tư | Giá trang in | Nguồn | App dùng |
|---|---|---|---|
| Cáp DC 4 mm² | 20.000 (TC, gạch 25.000) · 12.000 (DHC) · 18.000 (DHC Leader) | tcenergy.vn/san-pham/cap-solar-dc-leader-4-0-tiet-dien-4mm2/ ; dhcsolar.com/san-pham/cap-dc-leader/ | 18.000 đ/m |
| Cáp DC 6 mm² | 27.500 (TC) · 20.000 (DHC) | tcenergy.vn/san-pham/cap-solar-dc-leader-6mm/ ; dhcsolar.com/san-pham/day-cap-dc-dien-mat-troi-6mm2/ | 24.000 đ/m |
| Đầu nối MC4 1500 V | 25.000/bộ (TC) · 18.000 (DHC) | tcenergy.vn/san-pham/bo-dau-noi-jack-mc4-1500v-dc-leader-chinh-hang/ ; dhcsolar.com/san-pham/dau-noi-mc4-1500v/ | 25.000/cặp |
| Chống sét DC 1000 V | 350.000 | dhcsolar.com/san-pham/chong-set-lan-truyen-1000v-3p/ | 350.000 |
| Chống sét AC 275 V 2P | 250.000 (gạch 350.000) | dhcsolar.com/san-pham/chong-set-lan-truyen-ac-275v-2p-feeo/ | 250.000 |
| Tủ điện | 420.000 (DHC 8 way) · 1.000.000 (TC vỏ 500×700) | dhcsolar.com/san-pham/tu-dien-mat-troi-8-way/ ; tcenergy.vn/san-pham/vo-tu-dien-mat-troi-500x700x250-son-tinh-dien/ | 700.000 |
| Ray nhôm 4,2 m | 390.000/thanh (≈ 93.000 đ/m) | tcenergy.vn/san-pham/thanh-rail-nhom-pin-nang-luong-mat-troi-26x50-dai-4-2m/ | 93.000 đ/m |
| Kẹp giữa / biên | 12.000 / 10.000 (DHC) · 13.500 (TC) | dhcsolar.com/san-pham/kep-lien-ket-giua-tam-pin-nang-luon-mat-troi/ ; tcenergy.vn/san-pham/kep-giua-tam-pin-35mm-40mm/ | 12.000 |
| Chân đỡ | kẹp xà gồ inox 36.000 · kẹp U inox 26.000 (mái tôn) · chân L mái ngói 95.000–97.000 | tcenergy.vn ; dhcsolar.com/san-pham/moc-mai-ngoi-xa-go/ | 45.000 (nhân hệ số theo loại mái) |
| Dây tiếp địa Cadivi CV-4 mm² | 25.000 | tcenergy.vn/san-pham/day-cap-tiep-dia-cadivi-cv-4mm²-loi-dong-boc-nhua/ | 25.000 đ/m |
| Cọc tiếp địa mạ đồng 1,8 m | 280.000 × 3 cọc | tcenergy.vn/san-pham/coc-tiep-dia-ma-dong-1m8/ | 840.000/bộ |
| Thiết bị chống phát ngược / smart meter | Growatt 1 pha 1.750.000 · Sofar 2.700.000 · Goodwe 1 pha 3.000.000 · Goodwe GM3000 (3 pha) 4.500.000 | dhcsolar.com/san-pham/goodwe-smart-meter/ … | 2,7 tr (1 pha) · 4,5 tr (3 pha) |

Chưa tìm thấy giá công khai (giữ giá lập kế hoạch):

- CB DC 2 cực cho chuỗi PV;
- cáp AC Cu/XLPE nhiều lõi;
- cầu dao cách ly DC;
- nút dừng khẩn;
- bộ kết nối điều độ (≥ 100 kW).
