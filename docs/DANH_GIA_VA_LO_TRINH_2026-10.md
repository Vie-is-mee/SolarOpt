# SolarOpt — Đánh giá đề xuất tính năng và lộ trình (31/10/2026)

Tài liệu trả lời từng câu hỏi của đội, dựa trên mã nguồn hiện tại (`frontend/src`, `backend/app`) và các tài liệu `docs/STEP1…STEP6`, `MVP_TECH_STATUS.md`, `ROUND2_IMPROVEMENT_PLAN.md`. Các con số giá/chi phí dưới đây là **ước lượng để lập kế hoạch**, phải kiểm tra lại bằng báo giá thật (AWS Pricing Calculator, phỏng vấn khách hàng) trước khi đưa vào deck.

Ký hiệu ưu tiên: **P0** = nên làm trước vòng chấm tiếp theo · **P1** = sau khi có pilot · **P2** = khi có vốn/giải.

---

## 0. Tóm tắt nhanh

| # | Đề xuất của đội | Đánh giá | Ưu tiên | Công sức |
|---|---|---|---|---|
| 1 | Màn hình loading có logo khi mở web lần đầu | Nên làm, dễ | P0 | 0,5 ngày |
| 2 | Tài khoản cá nhân / doanh nghiệp / admin | Cần cho thương mại, dùng dịch vụ xác thực có sẵn | P1 (demo: P0 bản giả lập) | 3–7 ngày |
| 3 | Freemium 5 lần rồi thu phí theo gói | Đúng hướng, cần định nghĩa "1 lần" và thêm gói theo dự án | P0 (trên slide) | — |
| 4 | Tính chi phí cloud, bảo mật, mở rộng | Bắt buộc phải có trong P&L | P0 | 1 ngày |
| 5 | Chiến lược tìm bằng chứng độ chính xác | Quan trọng nhất hiện nay | P0 | liên tục |
| 6 | Biết phương án nào là tối ưu nhất | Cần cận trên + so với kỹ sư + tiêu chí kinh tế | P0 | 2–4 ngày |
| 7 | Doanh nghiệp có sẵn sàng trả tiền không | Phỏng vấn + LOI + pilot trả phí nhỏ | P0 | 2–3 tuần |
| 8 | Phát triển sau khi có giải | Lộ trình theo giai đoạn, mỗi chi phí mới gắn một nguồn thu | P1 | — |
| 9 | OCR đọc kích thước từ bản vẽ | Nên làm, dùng VLM đang có + kiểm tra chéo tỉ lệ | P0–P1 | 3–5 ngày |
| 10 | Ảnh rác (không phải mái nhà) | Phải chặn, dễ làm | P0 | 0,5–1 ngày |
| 11 | Pin xoay theo mặt trời (tracker) | Làm được dưới dạng mô phỏng; trên mái nhà thường **không** đáng tiền | P2 | 5–10 ngày |
| 12 | Đặt pin lên nóc vật cản phẳng | Hợp lý, tận dụng cơ chế "vùng mái cao" đã có | P1 | 2–3 ngày |
| 13 | Mái cong, vòm, parabol | Chia thành nhiều mặt phẳng nhỏ (facet) | P1–P2 | 4–7 ngày |
| 14 | Phóng to | Đã có nút +/−; thiếu cuộn chuột, chụm 2 ngón, kéo để dịch | P0 | 1 ngày |
| 15 | Tự gợi ý ngân sách | Rất nên — biến SolarOpt từ "công cụ vẽ" thành "cố vấn" | P0–P1 | 2–4 ngày |
| 16 | So IoU với mái lắp thật (3–4 ca) | Nên làm, có dataset công khai; cần đúng cách đo | P0 | 3–5 ngày |
| 17 | Nút "+" thêm loại pin | Dễ, nên có thư viện pin | P0 | 1 ngày |
| 18 | Thanh kéo giờ đặt ngay dưới bản vẽ | Đúng, hiện nó nằm dưới `ShadowInspector` | P0 | 1 giờ |

---

## 1. Màn hình loading khi mở lần đầu

**Hiện trạng:** chưa có splash. App là SPA (React + Vite), chuyển bước bên trong không tải lại trang.

**Cách làm đúng:**
- Đặt splash **ngay trong `frontend/index.html`** (HTML + CSS inline, logo `solaropt-mark.svg`, thanh chạy), để nó hiện *trước* khi JavaScript tải xong. Khi React mount xong (`main.tsx`) thì thêm class để mờ dần rồi gỡ.
- Chỉ hiện lần đầu trong một phiên: kiểm tra `sessionStorage` (bọc try/catch); lần sau vào lại trong cùng tab thì bỏ qua hoặc hiện tối đa ~300 ms.
- Dòng chữ chạy nên **phản ánh việc thật**: "Đang tải giao diện…", "Đang kiểm tra máy chủ tính toán…" (gọi `/api/health` vốn đã có). Không làm phần trăm giả — tài liệu `MVP_TECH_STATUS.md` của đội đã nói rõ không dùng "hiệu ứng tiến độ giả", giữ nguyên tắc này.
- Tối đa ~1,5 s; nếu máy chủ chưa sẵn sàng thì vào app và hiện badge "Máy chủ đang khởi động", không chặn người dùng.
- Các thao tác bên trong: không splash. Chỉ những phép tính lâu thật (tối ưu bố trí, stress test) mới có trạng thái chờ ngay tại nút/vùng kết quả (đã có `busy`).

---

## 2. Tài khoản và phân quyền

**Vai trò đề xuất:**

| Vai trò | Quyền |
|---|---|
| Quản trị hệ thống (admin SolarOpt) | Quản lý gói, hạn mức, người dùng, xem thống kê sử dụng, khóa tài khoản lạm dụng |
| Chủ tổ chức (doanh nghiệp/EPC) | Mời/xóa kỹ sư, mua gói, xem mọi dự án của công ty, đặt thư viện pin/giá chuẩn của công ty |
| Kỹ sư | Tạo/sửa dự án, chạy tối ưu, xuất báo cáo |
| Người xem (khách hàng cuối) | Mở link báo cáo chỉ đọc, bình luận/duyệt phương án |
| Cá nhân | Như kỹ sư nhưng không có tổ chức |

**Kỹ thuật:**
- **Không tự viết hệ thống mật khẩu.** Dùng dịch vụ có sẵn: AWS Cognito, Supabase Auth, Clerk hoặc Keycloak tự host. Được sẵn đăng nhập Google, quên mật khẩu, xác minh email, MFA, chống dò mật khẩu.
- Nếu tự làm thì tối thiểu: băm Argon2id, JWT ngắn hạn + refresh token httpOnly cookie, giới hạn số lần đăng nhập, ghi nhật ký đăng nhập.
- Backend: thêm `organization_id` và `owner_id` vào mọi bảng dự án/phiên bản (hiện là SQLite theo `project_name`), mọi API kiểm tra quyền. Chuyển SQLite → PostgreSQL khi có nhiều người dùng.
- Đếm hạn mức (free 5 lần) **ở máy chủ**, không ở trình duyệt.

---

## 3. Mô hình kinh doanh

### 3.1. Định nghĩa "một lần dùng"
Không đếm từng click. Đề xuất: **1 lượt = 1 dự án được chạy tối ưu bố trí thành công** (sửa/tính lại trong 30 ngày trên cùng dự án không tính thêm). Như vậy người dùng thử thoải mái nhưng phải trả tiền khi lấy giá trị thật.

### 3.2. Các gói (giá là giả thuyết cần kiểm chứng)

| Gói | Giá dự kiến | Gồm | Mục tiêu |
|---|---|---|---|
| Miễn phí | 0 đ | 5 dự án (trọn đời hoặc /tháng — thử cả hai), báo cáo có watermark, không xuất DXF, 1 loại pin mặc định | Kéo người dùng, thu dữ liệu |
| Trả theo dự án | 49.000–99.000 đ/dự án | Báo cáo đầy đủ, không watermark | Thợ lắp đặt nhỏ, dùng thất thường |
| Pro cá nhân | 299.000–499.000 đ/tháng | 30 dự án/tháng, thư viện pin riêng, xuất SVG/PDF/DXF | Kỹ sư tự do |
| Doanh nghiệp | 1,5–3 triệu đ/tháng cho 5 ghế, +250–400k/ghế thêm | Không giới hạn hợp lý, quản lý đội, mẫu báo cáo mang logo công ty, giá vật tư chung | EPC — **khách hàng chính** |
| Enterprise / API | Thỏa thuận | API, tích hợp CRM/ERP, SLA, triển khai riêng | EPC lớn, nhà phân phối thiết bị |

Giảm 15–20% khi trả theo năm (giúp dòng tiền và giảm rời bỏ).

### 3.3. Nguồn thu "thông minh" hơn phí thuê bao
1. **Báo cáo cho chủ nhà miễn phí → bán khách tiềm năng cho EPC.** Chủ nhà tải ảnh mái, nhận báo cáo sơ bộ (bao nhiêu tấm, tiết kiệm bao nhiêu). EPC trả phí theo khách hàng tiềm năng (lead) hoặc hoa hồng khi ký hợp đồng. Đây là mô hình hai phía: chủ nhà không trả tiền nhưng tạo ra giá trị cho phía trả tiền.
2. **Báo giá mang thương hiệu EPC**: EPC gửi link báo cáo đẹp cho khách; mỗi link có dòng "Thiết kế bằng SolarOpt" → tiếp thị lan truyền miễn phí.
3. **Thư viện thiết bị có tài trợ** (hãng pin/inverter trả phí để có datasheet chuẩn, ảnh, giá tham khảo). Phải giữ trung lập: không ảnh hưởng thứ hạng phương án, ghi rõ "tài trợ".
4. **Dịch vụ khảo sát/thiết kế thuê** (giai đoạn đầu do đội làm bằng tay với công cụ của mình — "concierge"): vừa có tiền vừa có dữ liệu thật.

### 3.4. Chiến lược tiếp thị
- Kênh: nhóm Facebook/Zalo "Điện mặt trời áp mái", hội chợ năng lượng, đối tác phân phối pin (họ có danh sách thợ lắp).
- Chương trình giới thiệu: mời 1 kỹ sư → cả hai được +3 dự án.
- Nội dung: video "từ ảnh mái tới báo giá trong 5 phút", so sánh trước/sau trên mái thật (sau khi có bằng chứng, xem mục 5).
- Chỉ số theo dõi: tỉ lệ đăng ký → chạy dự án đầu tiên → hết 5 lượt free → trả tiền; chi phí có một khách (CAC); doanh thu/khách/tháng (ARPA); tỉ lệ rời bỏ (churn). Mục tiêu SaaS hợp lý: LTV/CAC ≥ 3.

---

## 4. Chi phí hạ tầng cloud, bảo mật, mở rộng — đưa vào P&L ngay

### 4.1. Đặc điểm tải của SolarOpt
- Tối ưu bố trí (OR-Tools, Shapely, pvlib) **tốn CPU theo từng lần chạy**, vài giây đến ~25 s (`budget_seconds=25` trong `layout_search.py`). Lúc rảnh gần như không tốn.
- Ảnh/PDF tải lên ≤ 12 MB/tệp, cần lưu.
- Gọi AI nhận diện ảnh (Groq/Gemini) tính tiền theo lượt.

### 4.2. Ước lượng theo giai đoạn (vùng Singapore `ap-southeast-1`, giá tham khảo, cần kiểm tra lại)

| Hạng mục | Giai đoạn pilot (≤ 50 người dùng) | Giai đoạn tăng trưởng (~500 người dùng, ~3.000 dự án/tháng) |
|---|---|---|
| Máy chủ ứng dụng | 1 × EC2 t4g.medium/t3.medium ≈ 25–40 USD/tháng | 2–3 máy sau Load Balancer + 1–2 máy worker tối ưu tự co giãn ≈ 150–300 USD |
| Cân bằng tải (ALB) | không cần (Caddy như `deploy/Caddyfile`) | ≈ 20–30 USD |
| CSDL | PostgreSQL trên cùng máy hoặc RDS db.t4g.micro ≈ 15–25 USD | RDS db.t4g.medium Multi-AZ ≈ 100–150 USD |
| Lưu tệp (S3) | < 5 USD | 200 GB ≈ 5–10 USD + truyền tải |
| CDN (CloudFront) cho giao diện | gói miễn phí | 10–30 USD |
| Sao lưu (snapshot, S3) | 2–5 USD | 20–40 USD |
| Giám sát, log (CloudWatch) | 5 USD | 20–50 USD |
| Bảo mật (WAF, Secrets Manager) | 0–10 USD | 30–60 USD |
| AI nhận diện ảnh | theo lượt; ước tính vài trăm đến ~2.000 đ/ảnh tùy mô hình | ×3.000 dự án |
| Tên miền, email gửi thư | ~2 USD | ~10–20 USD |
| **Tổng** | **≈ 60–120 USD/tháng (1,5–3 triệu đ)** | **≈ 400–800 USD/tháng (10–20 triệu đ)** |

Cách quy ra **chi phí trên mỗi dự án** (con số quan trọng nhất cho định giá): đo thời gian CPU thật của 1 lần `/api/design/generate` + stress test + gọi AI, nhân giá giây CPU, cộng lưu trữ. Dự kiến vài trăm đến vài nghìn đồng/dự án → **biên lợi nhuận gộp > 80%** nếu giá gói như mục 3. Hãy chạy đo thật bằng `output/local/layout-performance` và ghi vào bảng.

**Lựa chọn trong nước:** Viettel Cloud, VNG Cloud, FPT Cloud có máy chủ đặt tại Việt Nam — có lợi khi khách doanh nghiệp yêu cầu dữ liệu lưu trong nước. So giá trước khi chọn; AWS có hệ sinh thái và gói tín dụng startup (AWS Activate) có thể xin được nhờ giải thưởng/vườn ươm.

### 4.3. Bảo mật và dữ liệu người dùng
- Pháp lý: Nghị định 13/2023/NĐ-CP và Luật Bảo vệ dữ liệu cá nhân (hiệu lực 01/01/2026) — địa chỉ, tọa độ nhà, ảnh mái là dữ liệu cá nhân. Cần: điều khoản sử dụng + chính sách quyền riêng tư, xin đồng ý khi gửi ảnh cho bên AI thứ ba (Groq/Gemini), cho phép xóa dữ liệu, hồ sơ đánh giá tác động xử lý dữ liệu. (Đội nên đọc văn bản gốc hoặc hỏi luật sư để xác nhận nghĩa vụ cụ thể.)
- Kỹ thuật: HTTPS (Caddy đã có), mã hóa khi lưu (S3/RDS encryption), khóa API trong Secrets Manager không trong `.env` trên máy chủ, phân quyền theo tổ chức ở mọi API, giới hạn tốc độ gọi API (chống lạm dụng free), quét virus/kiểm tra định dạng tệp tải lên (đã giới hạn 12 MB và loại tệp), sao lưu + thử khôi phục (`ops/backup.py`, `ops/restore.py` đã có — cần lên lịch tự động).
- Mở rộng: tách **worker tính toán** khỏi API (hàng đợi Redis/SQS + Celery/RQ), để một lần tối ưu 25 s không chặn người khác; worker tự co giãn theo độ dài hàng đợi.

### 4.4. Bảng P&L tối thiểu cần có trong deck
Doanh thu (theo gói × số khách) − chi phí hạ tầng (mục 4.2) − chi phí AI/lượt − phí cổng thanh toán (~2–3%) − hỗ trợ khách hàng − tiếp thị (CAC × khách mới) − lương = lãi/lỗ theo tháng, 24 tháng; kèm điểm hòa vốn (số khách doanh nghiệp cần có).

---

## 5. Chiến lược tìm bằng chứng cho độ chính xác

Chia thành 4 lớp bằng chứng, từ rẻ đến đắt:

| Lớp | Câu hỏi | Cách làm | Chỉ số |
|---|---|---|---|
| A. Đối chuẩn mô hình | Mô phỏng nắng/sản lượng có đúng không? | Cùng một mái, cùng thông số → chạy SolarOpt và PVGIS, NREL SAM (miễn phí), PVsyst (bản thử 30 ngày) | Sai lệch kWh/năm (%), sai lệch tổn thất bóng |
| B. Đối chuẩn hình học | Đọc mái/vật cản từ ảnh có đúng không? | Mở rộng benchmark Nacala (IoU 0,85 đã có) sang ảnh mái Việt Nam có số đo | IoU biên mái, sai số cạnh (m), tỉ lệ phát hiện vật cản |
| C. Đối chuẩn bố trí | Cách đặt pin có bằng kỹ sư thật không? | Mục 16 (IoU bố trí) + lấy 5–10 bản thiết kế đã thi công từ EPC | Số tấm, kWp, IoU bố trí, thời gian thiết kế |
| D. Đối chuẩn hiện trường | Sản lượng dự báo khớp sản lượng thật không? | Xin dữ liệu inverter (Huawei FusionSolar, SMA, Growatt…) của 3–5 hệ đã lắp ≥ 1 năm, nhập đúng mái đó | MAPE kWh theo tháng |

**Cách xin dữ liệu:** đề nghị EPC: "Anh/chị cho em 3 bản thiết kế cũ + số liệu inverter; em trả lại báo cáo so sánh miễn phí và miễn phí 3 tháng gói Doanh nghiệp". Ký thỏa thuận bảo mật đơn giản, ẩn danh địa chỉ.

**Thời gian thiết kế** là bằng chứng giá trị mạnh nhất cho EPC: bấm giờ kỹ sư làm cùng một mái bằng cách cũ (AutoCAD/Excel/PVsyst) và bằng SolarOpt; đếm số vòng sửa khi khách đổi yêu cầu.

---

## 6. Làm sao biết phương án đề xuất là tối ưu?

Cần tách hai câu hỏi:

**(a) Tối ưu theo mô hình** — trong không gian SolarOpt tìm, có đúng là tốt nhất không?
- Hiện `layout_search.py` so sánh một số lưới (theo 1–2 hướng cạnh mái chính và 0/90°), mỗi lưới chọn tấm bằng OR-Tools. Đây là **tối ưu trong lưới đã chọn**, chưa phải tối ưu toàn cục (chưa trộn nhiều lưới, chưa xét đặt tấm tự do).
- Bằng chứng nên làm:
  1. **Cận trên**: diện tích khả dụng ÷ diện tích tấm (kể cả khe) → "tối đa lý thuyết N tấm, SolarOpt đặt được M tấm = M/N%". Nếu ≥ 90–95% thì gần như không còn gì để cải thiện.
  2. **Vét cạn trên mái nhỏ**: với mái 10–20 tấm, quét dày độ lệch gốc lưới (bước 5 cm) và mọi góc → so với kết quả SolarOpt.
  3. **Kiểm tra độ nhạy**: dịch lưới vài cm có thêm tấm không? Nếu có, thêm quét độ lệch gốc vào bộ tìm.
- Hiển thị con số "đạt X% cận trên" ngay trên thẻ phương án — vừa trung thực vừa "wow".

**(b) Tối ưu cho khách hàng** — 3 phương án (nhiều điện nhất / ít bóng / cân bằng) không cái nào luôn đúng; tốt nhất phụ thuộc mục tiêu tiền.
- Tính cho mỗi phương án: NPV, thời gian hoàn vốn, LCOE (đ/kWh), tỉ lệ điện dùng tại chỗ (`economics.ts` đã có NPV/hoàn vốn nhưng chi phí phải do người dùng nhập).
- Vẽ biểu đồ **Pareto** (kWp ↔ tổn thất bóng ↔ chi phí) và đánh dấu "Khuyến nghị: phương án B vì NPV cao nhất trong ngân sách".
- Kỹ sư vẫn là người chốt; hệ thống giải thích lý do.

---

## 7. Doanh nghiệp có sẵn sàng trả tiền?

Không đoán — đo bằng hành động, theo bậc thang cam kết:

1. **Phỏng vấn 15–20 người** (kỹ sư thiết kế + chủ/trưởng kỹ thuật EPC), hỏi về **quá khứ**, không hỏi "anh có mua không":
   - "Tháng trước anh thiết kế bao nhiêu mái? Mỗi mái mất bao lâu? Khách đổi yêu cầu bao nhiêu lần?"
   - "Đang dùng công cụ gì, trả bao nhiêu tiền?" (PVsyst ≈ vài trăm USD/năm/giấy phép, Aurora/HelioScope đắt hơn nhiều)
   - "Lần gần nhất thiết kế sai phải sửa ngoài công trường tốn bao nhiêu?"
2. **Hỏi giá theo Van Westendorp** (4 câu: giá nào quá rẻ đến mức nghi ngờ / rẻ / đắt / quá đắt) → ra khoảng giá chấp nhận.
3. **Thư bày tỏ ý định (LOI)**: 2–3 EPC ký "sẽ dùng thử 2 tháng, nếu đạt KPI X thì mua gói Y". Đây là bằng chứng mà BGK vòng trước yêu cầu.
4. **Pilot trả phí nhỏ** (ví dụ 500k–1 triệu/tháng, hoặc trả trước giảm 50%): người trả tiền thật mới là bằng chứng thật.
5. **Tính ROI cho họ**: nếu kỹ sư lương ~15–20 triệu/tháng (~100k/giờ) tiết kiệm 2 giờ/mái × 20 mái/tháng = ~4 triệu/tháng/kỹ sư → gói 1,5–3 triệu cho 5 ghế là rẻ. Con số giờ tiết kiệm phải lấy từ phép bấm giờ ở mục 5.

---

## 8. Lộ trình sau khi có giải — mỗi khoản chi gắn một nguồn thu

| Giai đoạn | Thời gian | Đầu tư công nghệ | Chi phí thêm (ước) | Nguồn thu bù đắp |
|---|---|---|---|---|
| 1. Pilot | Tháng 0–3 | Tài khoản, hạn mức, thanh toán (VNPay/MoMo/PayOS), splash, OCR, chặn ảnh rác, thư viện pin | Hạ tầng ~2–3 tr/tháng | 3–5 EPC pilot trả phí nhỏ; dịch vụ thiết kế thuê |
| 2. Sản phẩm bán được | Tháng 3–9 | Đấu chuỗi + chọn inverter, BOM, báo giá mang logo EPC, nhập bản đồ vệ tinh theo địa chỉ, worker tính toán tách riêng | + 1 lập trình viên, hạ tầng ~5–10 tr | Gói Doanh nghiệp; thu từ báo giá → đây là tính năng EPC trả tiền |
| 3. Hai phía | Tháng 9–18 | Cổng cho chủ nhà (báo cáo free), ghép lead với EPC, đọc hóa đơn điện EVN bằng OCR để định cỡ hệ | Tiếp thị, hạ tầng ~10–20 tr | Phí lead/hoa hồng; gói Pro |
| 4. Chiều sâu kỹ thuật | Tháng 18+ | Dựng 3D từ ảnh drone/nhiều ảnh, mô phỏng theo giờ cả năm, giám sát sau lắp (so sản lượng thật với dự báo), API | GPU theo lượt, kỹ sư ML | Enterprise/API, tài trợ thư viện thiết bị, gói giám sát vận hành |

Nguyên tắc: **không xây tính năng đắt khi chưa có khách đang đòi.** Các tính năng tốn GPU (3D, mô hình phân vùng lớn) chỉ chạy theo lượt và tính vào gói cao. Xin tín dụng cloud (AWS Activate, Google for Startups, Microsoft for Startups) để giai đoạn 1–2 gần như không tốn hạ tầng.

---

## 9. OCR đọc kích thước trên bản vẽ

**Có nên?** Có, với bản vẽ kỹ thuật (đã có mẫu `ban-ve-ky-thuat.svg`). Nhưng cần làm đúng:

1. **Dùng VLM đang có** (Groq/Gemini trong `vision.py`): mở rộng prompt JSON để trả `dimension_labels: [{text, value_m, bbox, edge_hint}]`. Không cần thêm mô hình riêng. Phương án dự phòng không cần mạng: PaddleOCR/Tesseract chạy CPU.
2. **Ghép số với cạnh**: số đo nằm gần đường kích thước nào → cạnh mái nào. VLM gợi ý, thuật toán kiểm tra khoảng cách.
3. **Kiểm tra chéo tỉ lệ** — phần quan trọng nhất: tỉ lệ (m/pixel) suy ra từ mỗi kích thước phải gần bằng nhau. Nếu 2 số đo cho tỉ lệ lệch > 3–5% → cảnh báo "kích thước có thể đọc sai hoặc bản vẽ không theo tỉ lệ".
4. **Kỹ sư xác nhận**: điền sẵn vào ô `actualWidth/actualLength`, đánh dấu "đọc từ bản vẽ — cần xác nhận" (khớp với `dimensions_source`/`dimensions_verified` đã có trong `Config`).
5. Xử lý đơn vị: mm (bản vẽ VN thường ghi mm: 12000), cm, m.
6. Tốt hơn OCR: cho nhập **DXF** trực tiếp (thư viện `ezdxf`) — tọa độ chính xác tuyệt đối, không cần đoán. Đây là tính năng EPC rất muốn.

Đo độ chính xác: 20 bản vẽ thật → tỉ lệ đọc đúng giá trị, sai số tỉ lệ.

---

## 10. Ảnh rác (không phải mái nhà)

Hiện `vision.py` yêu cầu mô hình trả biên mái nhưng chưa có bước từ chối ảnh không liên quan. Đề xuất ba lớp:

1. **Thêm trường vào JSON của VLM**: `is_roof_or_plan: bool`, `image_type: "drone"|"drawing"|"partial_roof"|"other"`, `reject_reason`. Nếu `false` → không áp dụng đề xuất, hiện "Ảnh có vẻ không phải mái nhà hoặc bản vẽ (ví dụ: …). Vẫn muốn tiếp tục nhập tay?"
2. **Kiểm tra không cần AI** (khi chưa cấu hình AI): ảnh quá nhỏ/quá mờ (phương sai Laplacian thấp), GrabCut không tách được vùng đủ lớn, đa giác quá méo → cảnh báo.
3. **Kiểm tra hợp lý sau phân tích**: mái < 5 m² hoặc > 10.000 m², vật cản phủ > 80% mái → yêu cầu xác nhận.

Luôn cho người dùng **bỏ qua cảnh báo** (có thể là ảnh lạ nhưng hợp lệ), và không trừ lượt free khi ảnh bị từ chối. Thêm 10–20 ảnh rác (chó, mèo, bàn ghế, ảnh chụp màn hình) vào bộ kiểm thử.

---

## 11. Pin xoay theo mặt trời (tracker)

**Nói thẳng về kinh tế:** tracker 1 trục tăng ~15–25% sản lượng *mỗi tấm* trên mặt đất, nhưng trên mái nhà ở Việt Nam (vĩ độ 8–23°, mặt trời gần đỉnh đầu) thì:
- mái bị giới hạn diện tích → phải giãn hàng để tránh che → **ít tấm hơn**, sản lượng trên mỗi m² mái thường không tăng, có khi giảm;
- tải gió, trọng lượng, động cơ, bảo trì đắt; thêm tấm pin cố định thường rẻ hơn.

Vì vậy nên làm tracker như **công cụ so sánh** "cố định vs tracker" để chứng minh cho khách lựa chọn nào lợi hơn — đó chính là giá trị của SolarOpt.

**Thuật toán khoảng cách (giải đúng vấn đề đội nêu: hàng trước che hàng sau):**

- **Tracker 1 trục ngang (trục Bắc–Nam, xoay Đông–Tây):** gọi W là bề rộng tấm theo hướng xoay, P là khoảng cách tâm hàng (pitch), GCR = W/P.
  - Buổi trưa các hàng không che nhau; sáng sớm/chiều muộn, khi tấm xoay gần dựng đứng, bóng hàng trước đổ lên hàng sau. Cách xử lý chuẩn là **backtracking**: tấm xoay bớt lại đúng mức để bóng vừa chạm mép hàng sau (Lorenzo 2011, có sẵn trong `pvlib.tracking.singleaxis(..., backtrack=True, gcr=...)`). GCR càng nhỏ (hàng càng thưa) thì thời gian phải backtrack càng ngắn.
  - pvlib đã có sẵn hàm này → chỉ cần quét GCR (ví dụ 0,25 → 0,6), với mỗi GCR: số hàng đặt được trên mái × sản lượng/tấm (có backtracking) → chọn GCR cho **tổng kWh hoặc NPV** lớn nhất.
- **Tracker 2 trục:** đặt theo lưới, khoảng cách tối thiểu theo hướng bóng: `d ≥ H_eff / tan(α_min)` với H_eff là chiều cao hiệu dụng khi nghiêng tối đa, α_min là độ cao mặt trời thấp nhất trong khung giờ muốn không che (ví dụ 8h–16h ngày đông chí). Quét d và tính sản lượng có che thật bằng engine bóng hiện có.
- **Cố định có độ nghiêng (giá đỡ nghiêng trên mái bằng):** khoảng cách hàng `D = L·cos β + L·sin β · cos γ / tan α`, với L chiều dài tấm, β góc nghiêng, α độ cao và γ góc phương vị tương đối của mặt trời tại giờ thiết kế. Mục này **nên làm trước tracker** vì phổ biến hơn nhiều ở mái bằng VN.

Mấu chốt: không chọn khoảng cách "vừa đủ không che bao giờ" mà chọn khoảng cách **tối đa hóa tổng năng lượng** — chấp nhận che một chút sáng sớm/chiều muộn thường lời hơn.

---

## 12. Đặt pin lên nóc vật cản phẳng

Hợp lý (nóc tum thang, mái nhà kho, mái che). Cách làm tận dụng cái đã có:
- Backend đã có `roof_faces` với cao độ riêng (vùng mái cao/thấp). Thêm nút "**Cho phép đặt pin trên nóc vật thể này**" → chuyển vật cản thành một mặt mái phụ có cao độ = cao độ vật cản, setback riêng.
- Điều kiện kỹ sư phải xác nhận: kết cấu chịu tải (~15–25 kg/m²), lối tiếp cận để bảo trì, **không** áp dụng cho bồn nước (phải mở nắp vệ sinh), quạt thông gió, cột thu lôi, thiết bị cần khoảng hở.
- Thứ tự ưu tiên trong tối ưu: mái chính trước, nóc vật cản sau (thêm chi phí khung/nhân công cao hơn → trừ điểm nhỏ). Lợi phụ: tấm trên cao không bị chính vật đó che, nhưng có thể che mái chính — engine bóng hiện có sẽ tự tính.

---

## 13. Mái đặc biệt: nghiêng, cong, vòm, parabol

- **Mái nghiêng nhiều mặt**: đã có vùng mái + `roof_tilt_deg`; cần hoàn thiện kích thước chiếu bằng của tấm trên mặt nghiêng (tài liệu đã ghi là giới hạn).
- **Mái cong/vòm (tôn vòm nhà xưởng, mái parabol)**: nhập *nhịp* (span), *độ vồng* (rise), hướng trục → tự sinh đường cong (cung tròn hoặc parabol `y = 4h·x(L−x)/L²`) → **chia thành các dải phẳng (facet)** sao cho sai lệch giữa dây cung và cung < ngưỡng (ví dụ 2–3 cm, bằng độ võng cho phép của ray). Mỗi dải có góc nghiêng và hướng riêng → engine bức xạ/bóng hiện tại chạy được nguyên.
  - Tấm cứng đặt dọc theo trục vòm (cạnh dài song song với trục) để khớp độ cong tốt hơn.
  - Phần quá dốc (> ~60°) hoặc quay về hướng Bắc nhiều → loại vì sản lượng thấp.
  - Độ cong lớn → gợi ý tấm pin dẻo (thin-film), có thông số riêng.
- **Mái tròn trên mặt bằng (nhà vòm, bồn tròn)**: đa giác hóa đường tròn — `RoofCanvas` đã hỗ trợ đa giác/bầu dục.

---

## 14. Phóng to

Đã có nút `−`/`+`/đặt lại (70%–600%) trong `RoofCanvas.tsx`. Còn thiếu:
- Cuộn chuột để phóng **quanh vị trí con trỏ** (Ctrl + cuộn, để không xung đột cuộn trang).
- Chụm hai ngón trên điện thoại/tablet (kỹ sư dùng ngoài công trường).
- Kéo nền để dịch khung nhìn (pan) khi đang phóng to; phím tắt `0` để vừa khung.
- Bản đồ thu nhỏ (minimap) ở góc khi zoom > 200%.

---

## 15. Tự gợi ý ngân sách

Hiện kỹ sư nhập `budget_vnd` (mặc định 120 triệu) và giá chỉ gồm tấm pin. Đề xuất:
1. Chạy bố trí **không giới hạn ngân sách** → biết số tấm tối đa N_max.
2. Quét số tấm n = 4, 6, …, N_max (lấy n tấm tốt nhất trong phương án) → với mỗi n tính CAPEX đầy đủ (tấm + inverter theo kWp + khung + nhân công, dùng **bảng đơn giá mặc định có nguồn**, kỹ sư sửa được) và NPV/hoàn vốn/tỉ lệ tự dùng.
3. Nếu có **tiêu thụ điện của khách** (hóa đơn EVN — có thể OCR hóa đơn): định cỡ để điện tạo ra ≈ điện dùng ban ngày, vì bán điện dư áp mái ở VN hiện rất hạn chế (cơ chế tự sản tự tiêu — kiểm tra Nghị định 135/2024 và văn bản cập nhật).
4. Hiển thị: "**Gợi ý ngân sách: 85–95 triệu đ (≈ 7,5 kWp)** — hoàn vốn nhanh nhất; vượt mức này điện dư không được bán nên lợi ích giảm" + biểu đồ NPV theo quy mô.

Đây là điểm "wow" thật vì biến công cụ thành người cố vấn — và trả lời luôn câu hỏi của chủ nhà "nên lắp bao nhiêu?".

---

## 16. So IoU với mái đã lắp thật

**Dữ liệu tìm được (cần kiểm tra giấy phép từng bộ):**
- *Distributed Solar Photovoltaic Array Location and Extent Dataset* (Bradbury và cộng sự, 2016, Duke/figshare): ~19.000 hệ pin có đa giác trên ảnh máy bay 0,3 m ở 4 thành phố California.
- *Multi-resolution dataset for photovoltaic panel segmentation* (Jiang và cộng sự, 2021, Zenodo): ảnh vệ tinh/máy bay không người lái của Trung Quốc có mặt nạ pin.
- OpenStreetMap: các đối tượng `generator:source=solar` có đa giác (chất lượng không đều).
- **Tốt nhất:** 3–4 công trình của EPC Việt Nam có bản vẽ thi công + ảnh drone (xem mục 5).

**Cách đo đúng (quan trọng, nếu không thì con số vô nghĩa):**
1. Lấy ảnh mái **trước** hoặc che vùng pin đi, nhập mái + vật cản vào SolarOpt (kỹ sư khoanh như bình thường).
2. Dùng **cùng loại/kích thước tấm** với hệ thật, cùng số tấm (hoặc báo cả hai trường hợp: cùng số tấm và tự do).
3. Chiếu bố trí của SolarOpt về cùng hệ tọa độ ảnh → tính **IoU vùng pin** (hợp tất cả tấm), thêm **chênh lệch số tấm, kWp, sản lượng mô phỏng**.
4. Diễn giải đúng: IoU thấp **không có nghĩa SolarOpt sai** — thiết kế thật có thể bị ràng buộc bởi đấu chuỗi, lối đi, thẩm mỹ, ngân sách khách. Vì vậy báo song song: "SolarOpt đặt được ≥ số tấm của kỹ sư với tổn thất bóng ≤ … trong X/4 ca". Con số này thuyết phục hơn IoU đơn thuần.
5. Tái sử dụng khung `backend/scripts/benchmark_public_roofs.py` (đã có hàm `iou`, báo cáo HTML, kiểm SHA-256 nguồn).

---

## 17. Nút "+" thêm loại pin

Hiện chỉ có `DEFAULT_PANEL` (LONGi Hi-MO 6 580 W) sửa trực tiếp. Đề xuất:
- **Thư viện pin**: 5–10 mẫu phổ biến ở VN (LONGi, JA Solar, Jinko, Trina, Canadian Solar — lấy thông số từ datasheet chính hãng, ghi nguồn và ngày).
- Nút **+** mở form: hãng, model, rộng, dài, dày, khối lượng, Pmax, Voc, Isc, Vmp, Imp, hệ số nhiệt Pmax/Voc, hiệu suất, giá, bảo hành, loại (mono/bifacial/dẻo). Kiểm tra hợp lệ: Vmp < Voc, Imp < Isc, Pmax ≈ Vmp × Imp (lệch < 3%), kích thước 0,5–3 m.
- Lưu theo người dùng/tổ chức (khi có tài khoản; trước đó lưu localStorage + trong tệp JSON xuất dự án).
- Bonus "wow": tải PDF datasheet → VLM đọc thông số điền sẵn (cùng cơ chế OCR mục 9).
- Thêm nút "So sánh 2–3 loại pin trên cùng mái" → bảng kWp, số tấm, giá, NPV.

---

## 18. Thanh kéo giờ mặt trời ngay dưới bản vẽ

Đúng là bất tiện: ở bước Mô phỏng (`App.tsx` dòng ~237) thứ tự là `{canvas}` → `<ShadowInspector/>` → `<div className="time-machine">`. Sửa: đưa `time-machine` lên **ngay sau `{canvas}`**, hoặc tốt hơn là đặt thanh kéo **dính (sticky) ở đáy vùng bản vẽ** để luôn nhìn thấy bóng thay đổi khi kéo. Thêm phím ←/→ để bước 15 phút.

---

## 19. Đánh giá của "chuyên gia startup": còn thiếu gì, chỗ nào chưa đủ wow

### 19.1. Điểm mạnh hiện có (nên giữ và nói to hơn)
- Trung thực về giới hạn — hiếm đội làm được; BGK kỹ thuật đánh giá cao.
- Có benchmark thật (Nacala IoU 0,85), có kiểm thử tự động, có truy vết ảnh hưởng khi đổi đầu vào, có stress test 8 tình huống.

### 19.2. Lỗ hổng lớn nhất
1. **Chưa có bằng chứng khách hàng** (0 LOI, 0 pilot) → ưu tiên số 1, quan trọng hơn mọi tính năng.
2. **Chưa có thiết kế điện** (đấu chuỗi, chọn inverter, sơ đồ một sợi) và **BOM/báo giá** — đây là phần EPC thực sự trả tiền; không có thì SolarOpt chỉ là "công cụ vẽ sơ bộ".
3. **Chi phí đầu tư phải nhập tay** → người dùng phổ thông không dùng được phần kinh tế. Cần bảng đơn giá mặc định có nguồn.
4. **Sản lượng dùng 9 thời điểm đại diện** → so với PVsyst/HelioScope sẽ bị hỏi ngay. Nâng lên mô phỏng 8.760 giờ với dữ liệu PVGIS/TMY (pvlib làm được, chi phí CPU vẫn thấp nếu cache bóng theo lưới).
5. **Chưa nhập theo địa chỉ/bản đồ vệ tinh** — đối thủ đều có.

### 19.3. Tính năng tạo "wow" khi demo (xếp theo hiệu quả/công sức)
1. **Phối cảnh 3D** (three.js / react-three-fiber) mái + vật cản + tấm pin + bóng chạy theo thanh giờ. Dữ liệu cao độ đã có, chỉ cần dựng hình — 3–5 ngày, hiệu ứng trình diễn rất mạnh.
2. **"Gợi ý quy mô tối ưu"** (mục 15) với biểu đồ NPV theo số tấm.
3. **Đọc hóa đơn điện EVN** bằng ảnh → tự định cỡ hệ theo tiêu thụ.
4. **Báo giá một chạm** cho chủ nhà: PDF mang logo EPC, link xem trên điện thoại, nút "đồng ý phương án".
5. **"Đạt 96% cận trên lý thuyết"** trên thẻ phương án (mục 6).
6. **So sánh trước/sau khi đổi yêu cầu** (đã có nền tảng truy vết) — biến thành một màn hình diff trực quan: tấm giữ/thêm/bỏ tô 3 màu.

### 19.4. Những việc cần cho "thực tế và có bằng chứng"
- Một **bảng số liệu chuẩn duy nhất** cho deck/video/demo (đã đề xuất trong `ROUND2_IMPROVEMENT_PLAN.md` §2.8 — hãy hoàn thành).
- **Video ghi màn hình kỹ sư thật** dùng SolarOpt trên mái thật, kèm bấm giờ.
- Đối chuẩn sản lượng với PVGIS/SAM (lớp A mục 5) — rẻ, làm được trong 1–2 ngày.
- Trang **"Phương pháp và giới hạn"** công khai trong app (đã có nhiều ghi chú rời rạc; gom lại một chỗ).

---

## 20. Đề xuất thứ tự làm trong 2–3 tuần tới

1. **Việc giao diện nhanh (1–2 ngày):** thanh giờ dưới bản vẽ, splash, zoom cuộn chuột/chụm, nút "+" và thư viện pin, chặn ảnh rác.
2. **Bằng chứng (song song, cả đội):** phỏng vấn 15 EPC/kỹ sư, xin 3–4 bộ thiết kế thật, đối chuẩn PVGIS/SAM, chạy IoU bố trí trên 3–4 ca.
3. **Giá trị kinh tế (3–5 ngày):** bảng đơn giá mặc định có nguồn, gợi ý ngân sách/quy mô, NPV cho từng phương án, chỉ số % cận trên.
4. **Thương mại (trên slide trước, code sau):** gói giá, P&L 24 tháng có chi phí cloud mục 4, kế hoạch tài khoản.
5. **Wow demo:** phối cảnh 3D nếu còn thời gian.
