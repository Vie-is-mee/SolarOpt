# 4. Kết cấu, gió, PCCC — bước Kiểm tra & bàn giao → Khảo sát hiện trường

*Đọc ngày 07/11/2026.* Dùng ở: `backend/app/services/site.py`, `backend/app/services/geometry.py`, `backend/app/services/electrical.py`.

## Áp lực gió cơ sở W0 — TCVN 2737:2023

| Vùng | I | II | III | IV | V |
|---|---|---|---|---|---|
| W0 (daN/m²) | 65 | 95 | 125 | 155 | 185 |
| App (kPa) | 0,65 | 0,95 | 1,25 | 1,55 | 1,85 |

- Khớp từng số.
- Bản 2023 bỏ các vùng phụ IA, IIA, IIIA của bản 1995.
- Nguồn:
  - [TCVN 2737:2023, Thư viện pháp luật](https://thuvienphapluat.vn/TCVN/Xay-dung/TCVN-2737-2023-Tai-trong-va-tac-dong-920293.aspx);
  - [Tạp chí Xây dựng — tải gió nhà công nghiệp theo TCVN 2737:2023](https://vjol.info.vn/tcxd/article/view/107280);
  - [Hướng dẫn TCVN 2737:2023 phần 2 (IBST)](https://ibst.vn/upload/documents/file_upload/1746602210Huong-dan-TCVN-2737-2023-Phan-2-.pdf).
- TP.HCM thường thuộc vùng II. Tra vùng theo xã/phường trong phụ lục phân vùng.

## Hoạt tải mái

- App dùng: mái tôn/ngói không đi lại 30 daN/m², mái bằng bê tông 75 daN/m².
- Lấy theo bảng hoạt tải TCVN 2737. **Cần đối chiếu số trong bản gốc 2023** (chưa trích được bảng).

## Tải thử tấm pin

- Datasheet JA Solar JAM72S30 530–555/MR (AU_EN_20220223A): tải tĩnh mặt trước 5.400 Pa, **mặt sau 2.400 Pa**.
- App dùng 2.400 Pa với hệ số an toàn 1,5. Khớp.

## PCCC trên mái

| Quy định | Nguồn |
|---|---|
| Văn bản **3288/C07-P4** (08/9/2020) đã được thay bằng **207/C07-P4 (09/8/2024)** của Cục Cảnh sát PCCC & CNCH; 207 cũng thay 3289/C07-P4 | [Diễn đàn Doanh nghiệp](https://diendandoanhnghiep.vn/dien-mat-troi-mai-nha-cho-doanh-nghiep-dieu-kien-an-toan-pccc-ra-sao-10140597.html); [Vũ Phong](https://vuphong.vn/phong-chay-chua-chay-dien-mat-troi-mai-nha/) |
| Nhóm tấm ≤ 40 × 40 m, khoảng cách giữa 2 nhóm ≥ 1,5 m | các nguồn trên |
| Không lắp trên mái làm bằng vật liệu cháy hoặc có lớp hoàn thiện dễ cháy; tính tải trọng mái cả khi cháy | các nguồn trên |
| Thiết bị ngắt khẩn cấp tại inverter và tủ đóng cắt, có hướng dẫn niêm yết | [EVN — hướng dẫn của Cục Cảnh sát PCCC](https://www.evn.com.vn/d6/news/Cuc-Canh-sat-phong-chay-chua-chay-huong-dan-dam-bao-an-toan-cho-cong-trinh-dien-mat-troi-550-18-26521.aspx) |
| Không bố trí tấm trong 3 m quanh lối ra mái; cách lan can 2,5 m | lấy từ 3288 ([Báo Đồng Nai 2020](https://baodongnai.com.vn/bandoc/202009/quy-dinh-moi-ve-lap-he-thong-dien-mat-troi-mai-nha-3024165/); [Thư viện pháp luật — 3288](https://thuvienphapluat.vn/cong-van/Xay-dung-Do-thi/Cong-van-3288-C07-P4-2020-tham-duyet-thiet-ke-phong-chay-chua-chay-nha-may-dien-mat-troi-453461.aspx)). **Chưa xác nhận còn trong 207**; cần toàn văn 207 hoặc hỏi cơ quan PCCC địa phương |

App đã đổi các chỗ ghi nguồn sang 207/C07-P4 (ghi rõ thay 3288). Các khoảng cách giữ nguyên vì là mức an toàn hơn.
