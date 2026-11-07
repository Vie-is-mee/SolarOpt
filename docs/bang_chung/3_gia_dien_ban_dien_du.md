# 3. Giá điện EVN và bán điện dư — bước Kinh tế, Trợ lý tư vấn

*Đọc ngày 07/11/2026.* Dùng ở: `frontend/src/tariff.ts`, `backend/app/services/advisor/tariff.py`, `frontend/src/economics.ts`, `backend/app/services/advisor/scenarios.py`.

## Biểu giá bán lẻ — Quyết định 2892/QĐ-BCT

- Ban hành 31/10/2026, hiệu lực 01/11/2026.
- Giá bình quân 2.159,9037 đ/kWh, chưa VAT.

Nguồn:

- Cổng Phổ biến giáo dục pháp luật Cần Thơ (đăng 03/11/2026): https://pbgdpl.cantho.gov.vn/quy-dinh-ve-gia-ban-dien
- Báo Lào Cai: https://baolaocai.vn/chinh-thuc-gia-dien-sinh-hoat-con-5-bac-cao-nhat-3844-dongkwh-post913529.html

**Sinh hoạt (đ/kWh)**

| Bậc | Mức dùng | Giá | Khớp app |
|---|---|---|---|
| 1 | 0–100 kWh | 1.901 | ✓ |
| 2 | 101–200 kWh | 2.289 | ✓ |
| 3 | 201–400 kWh | 2.894 | ✓ |
| 4 | 401–700 kWh | 3.456 | ✓ |
| 5 | từ 701 kWh | 3.844 | ✓ |

**Sản xuất và kinh doanh (bình thường / thấp điểm / cao điểm, đ/kWh)**

| Nhóm | Giá | Khớp app |
|---|---|---|
| Sản xuất ≥ 220 kV | 1.771 / 1.101 / 3.110 | (không dùng) |
| Sản xuất > 35 – < 220 kV | 1.792 / 1.123 / 3.218 | (không dùng) |
| Sản xuất trung áp (> 1 – 35 kV) | 1.814 / 1.166 / 3.348 | ✓ |
| Sản xuất hạ áp (≤ 1 kV) | 1.966 / 1.274 / 3.586 | ✓ |
| Kinh doanh khác trung áp | 2.829 / 1.577 / 4.924 | ✓ |
| Kinh doanh khác hạ áp | 3.089 / 1.880 / 5.313 | ✓ |
| Lưu trú du lịch trung áp / hạ áp | 1.814 / 1.166 / 3.348 · 1.966 / 1.274 / 3.586 | (không dùng) |
| Sạc xe điện trung áp / hạ áp | 2.549 / 1.534 / 3.758 · 2.700 / 1.620 / 4.212 | (không dùng) |

## Khung giờ

QĐ 963/QĐ-BCT (22/4/2026):

- cao điểm 17h30–22h30, thứ Hai đến thứ Bảy; Chủ nhật không có cao điểm;
- thấp điểm 0h–6h mỗi ngày;
- còn lại là giờ bình thường.

Nguồn: https://moit.gov.vn/tin-tuc/quy-dinh-moi-ve-gio-cao-diem-thap-diem-cua-he-thong-dien-quoc-gia.html

**Khung giờ mới có đang tính tiền không?**

- Thông tư 60/2025/TT-BCT chỉ cho áp khung giờ mới từ lần điều chỉnh giá bán lẻ bình quân gần nhất. Bộ Công Thương có dự thảo (5/2026) sửa quy định này để áp sớm hơn, nhưng chưa xác nhận được bản chính thức ([Tạp chí Công Thương 28/05/2026](https://tapchicongthuong.vn/bo-cong-thuong-sua-thong-tu-ve-gia-ban-dien-de-som-ap-dung-khung-gio-cao-diem--thap-diem-moi-521358.htm)).
- QĐ 2892 (01/11/2026) là một lần điều chỉnh giá bình quân. Vì vậy app dùng khung giờ mới từ 01/11/2026.
- Đây là suy luận từ văn bản. Cần xác nhận bằng hóa đơn EVN tháng 11/2026 của một khách có công tơ 3 giá.

## VAT

App dùng 8% (mức giảm thuế GTGT áp dụng đến hết 2026). Chưa lưu nguồn; kiểm tra lại trước 01/01/2027.

## Bán điện dư — NĐ 58/2025 sửa bởi NĐ 243/2026

- NĐ 243/2026/NĐ-CP ban hành ngày 26/6/2026. Trần bán điện dư nâng từ 20% lên **50% sản lượng** ([Báo Đấu thầu](https://baodauthau.vn/dien-mat-troi-mai-nha-noi-tran-ban-dien-du-thoat-canh-chay-bam-tai-post201837.html); [VCCI](https://www.vcci.com.vn/news/tp-ho-chi-minh-nghi-dinh-243-tao-cu-hich-moi-cho-dien-mat-troi-mai-nha)).
- **Giá mua** = giá điện năng thị trường bình quân năm trước liền kề, do đơn vị vận hành thị trường điện công bố ([Luật sư Việt Nam](https://lsvn.vn/nguoi-dan-duoc-ban-toi-da-50-dien-mat-troi-mai-nha-len-luoi-dien-quoc-gia-a175034.html)).
- **Năm 2026: 844,8 đ/kWh.** Đây là giá thị trường bình quân năm 2025, theo NSMO công văn số 205 ngày 16/01/2026 ([Thanh Niên 27/06/2026](https://thanhnien.vn/dien-mat-troi-du-duoc-ban-len-luoi-voi-gia-bao-nhieu-dong-mot-kwh-185260627160423229.htm); [Tuổi Trẻ](https://tuoitre.vn/dau-tu-tram-trieu-ban-dien-844-dong-kwh-khien-nguoi-dan-chi-lap-dien-mat-troi-du-dung-100260825093613263.htm)).
- App trước đây dùng 670 đ/kWh. Đó là mức đề xuất năm 2024, tính theo chi phí tránh được năm 2023. Nay sửa thành **845 đ/kWh**. Cập nhật mỗi tháng 1.
