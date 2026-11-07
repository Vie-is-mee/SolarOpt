# SolarOpt thương mại: giá theo dự án, chi phí thật, đối thủ và lỗ hổng kinh doanh

*Lập 07/11/2026. Số liệu tính trong `output/report/SolarOpt_Mo_hinh_tai_chinh_v2.xlsx` (dựng lại bằng `backend/scripts/build_cost_model.py`). Tỷ giá Vietcombank bán ra 13:30 07/11/2026: 1 USD = 25.780 đ, 1 EUR = 29.332 đ, 1 AUD = 17.874 đ; CHF (31.500 đ) và INR (295 đ) là giả định vì trang tỷ giá lỗi hai dòng này.*

## 1. Trả lời ngắn

1. **Chi phí không phải vấn đề.** Một dự án tốn khoảng **246.000 đ** chi phí biến đổi (AI ~19.000 đ, ảnh vệ tinh ~1.500 đ, máy chủ ~200 đ, lưu trữ ~140 đ, giờ hỗ trợ kỹ sư 225.000 đ). Xấu nhất ~870.000 đ. Biên gộp mọi gói **≥ 94%**. Giá bị giới hạn bởi đối thủ và giá trị khách nhận, không bởi chi phí.
2. **So với đối thủ, giá của bạn đúng hay sai tùy cách khách tính:**
   - **Theo tiền mỗi kỳ:** gói năm đã rẻ hơn HelioScope 28–64%. Gói Tháng·1 dự án chỉ rẻ hơn Aurora Premium 10%; muốn đạt mức rẻ hơn 15–20% cần ≈ **5,49 triệu**. Gói Tháng·2 dự án đắt hơn Aurora Premium 20%.
   - **Theo từng dự án** (cách kỹ sư EPC sẽ tính): SolarOpt **đắt gấp 2,4–5,7 lần**, vì với cùng số tiền đối thủ cho 10–50 dự án mỗi tháng.
3. **Giá hợp lý cho công trình C&I lớn, không hợp lý cho nhà dân.** 4–6 triệu/dự án chỉ bằng 0,1–0,6% hợp đồng C&I 1–5 tỷ đồng. Với nhà dân 10 kWp (~130 triệu hợp đồng, lãi nhà thầu vài chục triệu), mức đó ăn 15–25% tiền lãi. Đề xuất: tính lượt theo quy mô công trình (mục 7).
4. **Phí lưu trữ 1 triệu/dự án/tháng và xóa sau 2 ngày là chỗ yếu nhất.** Chi phí lưu thật chỉ khoảng 34 đ/dự án/tháng. Đối thủ không thu riêng phí lưu trữ. Hạn 2 ngày quá ngắn cho thanh toán B2B và dễ gây tranh chấp (mục 5).
5. **Cơ sở dữ liệu đã có, nhưng chưa bền.** Máy chủ đã lưu tài khoản và lịch sử phiên bản (kèm ảnh) trong SQLite. Bản web chạy Render gói miễn phí dùng ổ đĩa tạm, nên khởi động lại hoặc deploy là **mất hết**. Phải sửa trước khi bán gói lưu trữ (mục 6).
6. **AI không bảo đảm "không sập nhà".** SolarOpt là công cụ thiết kế sơ bộ. Kết cấu phải do kỹ sư có chứng chỉ khảo sát và ký (mục 8).
7. **Kịch bản cơ sở chưa đủ vốn.** Với dự báo lượt mua giả định, 600 triệu gọi vốn chưa đủ: tiền mặt thấp nhất **−136 triệu** (12/2028), có lãi EBITDA từ 01/2029. Số khách là giả định, chưa có dữ liệu pilot.

## 2. Đối thủ (giá đọc 07/11/2026)

| Đối thủ | Gói | Giá gốc | đ/tháng | đ/năm | Ghi chú | Nguồn |
|---|---|---|---|---|---|---|
| Aurora Solar | Basic | 159 USD/tháng (135 trả năm) | 4,10 tr (3,48 tr) | 49,2 tr (41,8 tr) | 1 người; khoảng 50 dự án/tháng | [heavengreenenergy.com](https://www.heavengreenenergy.com/blog/aurora-solar-pricing) (bên thứ ba; trang Aurora chặn đọc tự động) |
| Aurora Solar | Premium | 259 USD/tháng (220 trả năm) | 6,68 tr (5,67 tr) | 80,1 tr (68,1 tr) | Có LIDAR, báo cáo bóng che | như trên |
| HelioScope | Basic | 1.620 USD/năm | 3,48 tr | 41,8 tr | 1 người; 10 dự án/tháng; ≤ 1,25 MW | [helioscope.aurorasolar.com/pricing](https://helioscope.aurorasolar.com/pricing/) (qua kết quả tìm kiếm) |
| HelioScope | Pro | 2.640 USD/năm | 5,67 tr | 68,1 tr | | như trên |
| PVsyst 8 | Professional | 700 CHF/năm | ~1,84 tr | ~22,1 tr | Phần mềm máy tính, không giới hạn dự án | [pvsyst.com/en/shop](https://www.pvsyst.com/en/shop/) |
| PV*SOL premium 2026 | 1 năm | 845 EUR/năm | 2,07 tr | 24,8 tr | Chưa VAT | [shop.valentin-software.com](https://shop.valentin-software.com/en/products/pv-sol-premium-one-year-named-user-license) |
| Arka360 | Basic / Premium (Mỹ) | 1.699 / 1.999 USD/năm | 3,65 / 4,29 tr | 43,8 / 51,5 tr | Trang có số mâu thuẫn | [arka360.com/pricing](https://arka360.com/pricing) |
| Arka360 | Basic (Ấn Độ) | 70.000 INR/năm + GST | ~1,72 tr | ~20,7 tr | Không giới hạn dự án | [arka360.com/pricing-in](https://arka360.com/pricing-in) |
| Pylon | Standard / Pro | 4 / 10 (AUD?)/dự án | — | — | **72.000–179.000 đ/dự án**; ≤ 30 kW / thương mại | [getpylon.com/pricing](https://getpylon.com/pricing/) |
| OpenSolar | Core | Miễn phí | 0 | 0 | Thu phí API, kết nối, tài chính | [opensolar.com](https://www.opensolar.com/?p=15493) |
| Công cụ hãng biến tần | SolarEdge Designer, SMA Sunny Design… | Miễn phí | 0 | 0 | Kỹ sư VN dùng kèm AutoCAD + PVsyst | |

**Hệ quả:** không thể "rẻ hơn 15–20%" so với OpenSolar hay công cụ hãng, vì chúng miễn phí. Đối thủ thật để so giá là **Aurora, HelioScope, Arka360** (trả phí, có bố trí tấm và bóng che) và bộ **PVsyst + AutoCAD** mà kỹ sư đang trả.

## 3. Đánh giá bảng giá các sáng lập viên đặt

| Gói | Giá | đ/dự án | So tiền/kỳ với đối thủ | So đ/dự án (EPC 4 dự án/tháng) | Giá để rẻ hơn 17,5% theo kỳ |
|---|---|---|---|---|---|
| Tháng · 1 dự án | 5,99 tr | 5,99 tr | **−10%** so với Aurora Premium tháng | **+259%** | 5,51 tr |
| Tháng · 2 dự án | 7,99 tr | 4,00 tr | **+20%** | +139% | 5,51 tr |
| Năm · 3 dự án | 15 tr | 5,00 tr | **−64%** so với HelioScope Basic năm | +475% | 34,5 tr |
| Năm · 7 dự án | 30 tr | 4,29 tr | **−28%** | +393% | 34,5 tr |
| Lưu trữ | 1 tr/dự án/tháng | — | Đối thủ: đi kèm thuê bao | Chi phí thật ~34 đ/tháng | — |

Nhận xét:

- Cấu trúc gói theo dự án là điểm khác biệt có lý cho thị trường Việt Nam: nhà thầu trả tiền khi có công trình, không phải trả thuê bao tháng không dùng. Đó là cách kể chuyện với ban giám khảo và khách.
- Nhưng kỹ sư EPC đã quen Aurora/HelioScope sẽ chia tiền cho số dự án. Một công ty làm 4 dự án/tháng trả HelioScope Basic khoảng **0,87 triệu/dự án**, SolarOpt **4–6 triệu**. Khách chỉ trả mức đó khi SolarOpt làm được việc mà đối thủ không làm: biểu giá EVN mới theo giờ, thủ tục NĐ 58/2025, PCCC 3288, vùng gió TCVN 2737:2023, báo cáo tiếng Việt, kiểm chứng 12 điều kiện, 8 tình huống sai số. Cần chứng minh bằng 3–5 khách pilot có số giờ tiết kiệm đo được.
- "Dự án mới chưa ai dùng mà giá cao" là rủi ro thật. Cách giảm: pilot giảm 50% trong 6 tháng (đã có trong mô hình), cam kết hoàn tiền dự án đầu nếu kết quả sai lệch so với khảo sát thực tế, đổi giảm giá lấy quyền dùng tên khách làm câu chuyện.

## 4. Chi phí thật của một dự án và chọn mô hình AI

| Khoản | Dự kiến | Xấu nhất | Cách tính |
|---|---|---|---|
| AI đọc ảnh mái (Claude Sonnet 5.5, 5 lượt) | 12.400 đ | 99.400 đ (20 lượt, Opus) | token đo 04/11 × giá × hệ số token 1,3 × an toàn 1,5 |
| Tư vấn từ hóa đơn (Claude Sonnet 5.5, 3 lượt) | 5.800 đ | 38.800 đ | |
| Trợ lý hỏi đáp (Claude Haiku 5.5, 40 câu) | 900 đ | 273.500 đ (300 câu, Opus) | |
| Ảnh vệ tinh (Esri, 400 ô ảnh) | 1.500 đ | 4.600 đ | Giá khi vượt hạn mức miễn phí 2 triệu ô/tháng |
| Máy chủ, lưu trữ trong gói | ~340 đ | ~1.800 đ | |
| Giờ hỗ trợ kỹ sư (1,5 giờ) | 225.000 đ | 450.000 đ | khoản lớn nhất |
| **Tổng** | **~246.000 đ** | **~868.000 đ** | |

Chi phí AI của 1 dự án nếu dùng một mô hình cho cả 3 tính năng: Claude Haiku 5.5 ~1.800 đ · GPT-5 mini ~6.100 đ · Gemini 3.5 Flash-Lite ~7.600 đ · Gemini 3.6 Flash (giá 2027) ~27.000 đ · **Claude Sonnet 5.5 ~36.500 đ** · Claude Opus 5.5 ~73.000 đ.

**Khuyến nghị mô hình:** chênh lệch giữa rẻ nhất và mạnh nhất chỉ vài chục nghìn đồng/dự án, chưa tới 1,3% giá gói. Vì vậy chọn theo độ chính xác, không theo giá:

- Đọc ảnh mái và tư vấn (quyết định số tấm, kWp, vốn): mô hình mạnh như **Claude Sonnet 5.5**.
- Trợ lý hỏi đáp: mô hình nhỏ như **Claude Haiku 5.5**.
- **Chưa đổi mô hình trong máy chủ.** Trước khi đổi phải chạy bộ đánh giá trên 30–50 mái thật (đã có `benchmark_public_roofs.py`, `benchmark_real_installs.py`) so với Gemini hiện tại, rồi mới quyết.
- Giá Claude lấy từ bảng giá Claude API (bản lưu 06/10/2026). Giá Gemini lấy từ AI Studio (04/11/2026). Giá GPT-5 mini lấy từ trang tổng hợp và cần đối chiếu trang OpenAI.

**Ảnh vệ tinh:**

- Esri World Imagery (ArcGIS Location Platform) miễn phí 2 triệu ô ảnh/tháng, sau đó 0,15 USD/1.000 ô, cho phép ứng dụng thương mại ([location.arcgis.com](https://location.arcgis.com/help/deployment/)).
- Google Map Tiles miễn phí 100.000 ô/tháng, sau đó 0,60 USD/1.000 ô. Nhưng **điều khoản Google cấm vẽ lại biên công trình từ ảnh vệ tinh**, và hướng dẫn thương hiệu Google cấm dùng ảnh Google Earth cho mục đích thương mại ([about.google](https://about.google/brand-resource-center/products-and-services/geo-guidelines/)).
- Hiện app gợi ý kỹ sư dùng Google Maps để đo và lấy ảnh. Khi bán thương mại phải chuyển sang ảnh có giấy phép (Esri, Mapbox) hoặc ảnh drone của nhà thầu. Bay drone cần xin phép theo quy định quản lý tàu bay không người lái.

## 5. Phí lưu trữ và chính sách xóa

Đã làm trong code theo đúng yêu cầu:

- Dữ liệu được giữ đến hết chu kỳ gói đã dùng dự án.
- Sau đó thu 1 triệu/dự án/tháng.
- Quá hạn 2 ngày: dự án bị ẩn, rồi script `purge_expired_projects.py --apply` xóa hẳn và ghi ngày xóa.

Vấn đề và đề xuất:

| Vấn đề | Vì sao | Đề xuất |
|---|---|---|
| Giá 12 triệu/dự án/năm | Chi phí thật ~400 đ/năm. Đối thủ lưu không giới hạn trong thuê bao. Khách sẽ tải PDF/JSON về và để xóa (mô hình giả định chỉ 25% trả phí) | Gói năm kèm lưu **24 tháng**. Sau đó **1,2 triệu/dự án/năm**. Bán như "lưu hồ sơ có niêm phong" (mã băm + dấu thời gian cho bản duyệt), không bán như dung lượng |
| Xóa sau 2 ngày | Thanh toán B2B cần duyệt chi, có Tết và ngày nghỉ. Xóa nhầm hồ sơ khách đã trả tiền trước đó sẽ thành tranh chấp | Ân hạn **30 ngày**. Gửi 3 email nhắc (−14, −3, 0 ngày). Thời gian ân hạn chỉ cho xem. Cho tải xuống miễn phí. Ghi chính sách vào điều khoản dịch vụ |
| "Không trả thì đội ngũ chịu trách nhiệm" | Quy định quản lý chất lượng công trình (NĐ 06/2021/NĐ-CP) giao việc lưu hồ sơ công trình cho chủ đầu tư và nhà thầu — cần luật sư xác nhận cho ĐMT mái nhà. Xóa dữ liệu không làm họ hết trách nhiệm, chỉ làm họ mất bằng chứng và quay sang trách SolarOpt | Điều khoản ghi rõ: SolarOpt không phải nơi lưu hồ sơ pháp lý duy nhất. Khách phải tự lưu bản xuất. SolarOpt lưu nhật ký xóa (đã có `purged_at`) |

## 6. Cơ sở dữ liệu: hiện trạng và kế hoạch

**Đã có:**

- SQLite gồm tài khoản, phiên đăng nhập, nhóm, gói, sự kiện sử dụng, và `project_versions`. Bảng này lưu toàn bộ cấu hình, phương án, bản duyệt và ảnh bằng chứng.
- API lịch sử: `/api/history`, `/api/projects/{tên}/versions`.
- Bảng mới `project_storage` (hạn lưu, phí, ngày xóa) và `storage_requests`.
- Docker compose có sao lưu SQLite hằng ngày, giữ 14 bản.

**Thiếu:**

- Bản web Render dùng gói miễn phí, không có ổ đĩa bền. Commit ngày 06/11 ghi nhận máy chủ bị khởi động lại vì hết RAM. Mỗi lần như vậy là mất tài khoản và lịch sử.
- Ảnh lưu thẳng trong cơ sở dữ liệu dạng base64, cơ sở dữ liệu sẽ phình nhanh.
- Chưa có sao lưu ra nơi khác. Chưa có thử khôi phục định kỳ.

**Kế hoạch (theo thứ tự):**

1. **Trước khi thu phí (1–2 ngày):** chuyển backend Render sang gói có ổ đĩa bền, hoặc chạy `compose.yaml` trên một VPS. Bật sao lưu hằng ngày ra Cloudflare R2. Thử khôi phục bằng `ops/restore.py`.
2. **Trước khi bán gói lưu trữ (1–2 tuần):**
   - Chuyển sang Postgres có quản lý, có khôi phục theo thời điểm (Render Postgres, Neon hoặc Supabase).
   - Ảnh chuyển sang lưu đối tượng (R2/S3); cơ sở dữ liệu chỉ giữ đường dẫn và mã băm.
   - Bản duyệt được niêm phong bằng mã băm SHA-256 và thời điểm ký.
3. **Tuân thủ:**
   - Ảnh mái, địa chỉ, tên chủ nhà là dữ liệu cá nhân theo Luật Bảo vệ dữ liệu cá nhân 2025 (hiệu lực 01/01/2026).
   - Máy chủ ở nước ngoài thì cần hồ sơ đánh giá tác động chuyển dữ liệu ra nước ngoài, hoặc đặt máy chủ tại Việt Nam (Viettel IDC, FPT Cloud, VNPT). Cần luật sư.
4. **Vận hành:** chạy script xóa dữ liệu quá hạn bằng cron hằng ngày, gửi email báo trước, lưu nhật ký xóa.

## 7. Lỗ hổng kinh doanh (xếp theo mức nguy hiểm)

1. **Hứa lưu hồ sơ nhưng dữ liệu đang mất mỗi lần khởi động lại.** Bán gói lưu trữ khi chưa sửa mục 6 là bán thứ không giao được.
2. **Trách nhiệm khi công trình gặp sự cố.** Thiếu điều khoản giới hạn trách nhiệm, bảo hiểm trách nhiệm nghề nghiệp và bước kỹ sư ký thì một vụ sập mái có thể kéo SolarOpt vào kiện tụng. Mô hình đã cộng 24 triệu/năm bảo hiểm (ước tính, cần báo giá).
3. **Giá theo dự án đắt gấp nhiều lần đối thủ khi khách chia theo dự án** (mục 3). Sửa: tính lượt theo quy mô:
   - ≤ 30 kWp = 0,2 lượt (5 nhà dân = 1 lượt);
   - 30 kWp – 1 MWp = 1 lượt;
   - trên 1 MWp: 1 lượt mỗi MWp.

   Thêm một gói **Năm · không giới hạn dự án (1 ghế) ≈ 34,5 triệu** (rẻ hơn HelioScope Basic 17,5%) cho EPC làm nhiều dự án, để họ không bỏ sang HelioScope.
4. **Công trình C&I kéo dài 2–6 tháng, gói tháng hết hạn giữa chừng.** Theo quy tắc "chỉ dùng trong tháng đăng ký", sang tháng sau sửa lại cùng dự án sẽ trừ lượt mới. Khách sẽ thấy bị thu hai lần cho một công trình. Đề xuất: dự án đã tính được sửa tiếp tới 6 tháng mà không trừ lượt, miễn là còn một gói đang hiệu lực.
5. **Lách lượt dự án.** Trước đây dự án nhận diện chỉ bằng tên: giữ tên là dùng một lượt cho nhiều mái. Đã sửa: tên + vị trí (~1 km). Còn lỗ hổng nếu cố tình để vị trí mặc định. Theo dõi bằng nhật ký quản trị (số mái khác nhau trong một dự án).
6. **Ảnh vệ tinh không có giấy phép thương mại** (mục 4).
7. **Thanh toán và hóa đơn thủ công.** Hiện quản trị viên kích hoạt tay, chưa có hợp đồng mẫu, chưa có hóa đơn điện tử. Cần xác minh thuế GTGT cho dịch vụ phần mềm (có thể không chịu thuế) với kế toán. Khi có 20+ khách, cần cổng thanh toán (PayOS/VNPay) và hóa đơn tự động.
8. **Phụ thuộc nhà cung cấp AI.** Mô hình đổi giá hoặc ngừng sau 6–12 tháng: Gemini 2.5 Flash tự chuyển sang 3.5 Flash-Lite từ 01/12/2026; Gemini 3.6 Flash tăng giá gấp đôi từ 01/01/2027. Phải ghim phiên bản, có bộ đánh giá, và có mô hình dự phòng (code đã hỗ trợ nhiều nhà cung cấp).
9. **Không có lý do để trả tiền nếu chỉ "bố trí tấm".** OpenSolar và công cụ hãng làm miễn phí. Giá trị phải nằm ở phần kiểm chứng: 12 điều kiện, 8 tình huống sai số, sửa tối thiểu khi hiện trường đổi, pháp lý Việt Nam, báo cáo bàn giao. Slide và trang bán hàng phải nói điều này, không nói "AI thiết kế".
10. **Một người vận hành mọi thứ.** Kích hoạt gói, gia hạn lưu trữ, chạy script xóa đều phụ thuộc một quản trị viên. Cần quy trình viết sẵn, người thay thế, và cảnh báo tự động.

## 8. "Lắp theo AI có an toàn, có sập nhà không?"

AI không bảo đảm. SolarOpt kiểm hình học, bóng che, điện, tải gió theo TCVN 2737:2023 và cảnh báo khi:

- mái quá 15 năm tuổi;
- mái có rỉ hoặc dột;
- dùng xà gồ gỗ;
- tải hệ pin vượt ngưỡng (khoảng 13 kg/m², so với hoạt tải mái tôn 30 daN/m²).

SolarOpt **không thấy** những gì nằm trong kết cấu thật: tiết diện xà gồ, liên kết, mức rỉ bên trong, tải đã có trên mái. Quy trình bắt buộc khi bán:

1. Khảo sát tại chỗ và đo kiểm (ảnh chỉ để thiết kế sơ bộ).
2. Kỹ sư kết cấu có chứng chỉ hành nghề kiểm tra khả năng chịu lực mái; với C&I, có hồ sơ tính toán ký tên.
3. Trong app: bản duyệt chỉ xuất được khi đã nhập tên kỹ sư, số chứng chỉ, ngày khảo sát; báo cáo luôn ghi "thiết kế sơ bộ, không thay thế thẩm tra kết cấu". Hiện app đã ghi "không phải chứng nhận đủ điều kiện thi công"; nên nâng thành bước ký bắt buộc.
4. Điều khoản dịch vụ giới hạn trách nhiệm ở mức phí đã trả, kèm bảo hiểm trách nhiệm nghề nghiệp.
5. PCCC theo hướng dẫn 3288/C07-P4 và thủ tục EVN/NĐ 58/2025 do nhà thầu thực hiện. SolarOpt chỉ nhắc và lập danh mục.

## 9. Dòng tiền kịch bản cơ sở (giả định, chưa có pilot)

Dự báo lượt mua:

- **Tháng·1:** 1 → 4 lượt/tháng;
- **Tháng·2:** 0 → 1,5 lượt/tháng;
- **Năm·3:** 0,3 → 1,5 lượt/tháng;
- **Năm·7:** 0 → 1 lượt/tháng.

Giả định khác:

- gia hạn gói năm 60%;
- 25% dự án trả phí lưu trữ, trả 6 tháng;
- pilot giảm 50% trong 6 tháng đầu;
- 3 nhân sự, năm đầu trả 50% lương.

| | 2027 | 2028 | 2029 |
|---|---|---|---|
| Doanh thu | 230 tr | 812 tr | 1,49 tỷ |
| Biên gộp | 90% | 92% | 93% |
| EBITDA | −426 tr | −310 tr | +138 tr |
| Tiền mặt cuối năm | 174 tr | **−136 tr** | 2 tr |

- Có lãi EBITDA từ **01/2029**. Với 600 triệu vốn, thiếu khoảng 140 triệu vào cuối 2028.
- Cách bù: gọi ~750 triệu, giảm nhân sự năm 2, hoặc tăng số khách năm·7. Đổi hệ số kịch bản ở `Gia_dinh!B64` để xem.
- Mọi số khách là giả định. Phỏng vấn 5 EPC về số dự án/tháng và mức giá chấp nhận được là việc đầu tiên cần làm.

## 10. Việc cần quyết

1. Giữ bảng giá hiện tại hay áp các chỉnh ở mục 3 và 7: tính lượt theo quy mô, Tháng·1 = 5,49 triệu, thêm gói năm không giới hạn, sửa dự án qua chu kỳ không trừ lượt.
2. Phí lưu trữ: giữ 1 triệu/tháng + 2 ngày, hay chuyển sang 1,2 triệu/năm + 30 ngày ân hạn.
3. Chuyển máy chủ sang ổ đĩa bền (bắt buộc trước khi thu phí).
4. Chạy bộ đánh giá mô hình AI trước khi đổi sang Claude.

`docs/SO_LIEU_CHUAN.md` mục 5 vẫn ghi bảng giá cũ (790k / 3,49 tr / 9,9 tr). Nếu thuyết trình bảng giá mới, sửa ở đó trước.

## 11. Đề xuất bản 3 (08/11/2026, chưa chốt)

Số liệu trong `output/report/SolarOpt_Mo_hinh_tai_chinh_v3.xlsx` (dựng lại bằng `backend/scripts/build_cost_model.py`). App vẫn chạy bảng giá 07/11 trong `backend/app/billing.py`. Số khách, tỷ lệ gói và tỷ lệ gia hạn là giả định, chưa có dữ liệu pilot.

**Lỗi bảng giá 07/11:** Tháng·2 (4,0 tr/dự án) rẻ hơn cả hai gói năm, nên nếu khách gom được 2 dự án mỗi tháng thì mua gói tháng luôn rẻ hơn gói năm.

| Gói đề xuất | Giá | Dự án | Ghế | Giờ hỗ trợ/kỳ | Giá/dự án | Neo giá |
|---|---|---|---|---|---|---|
| Dự án lẻ | 5,99 tr / 30 ngày | 1 | 1 | 3 | 5,99 tr | Rẻ hơn Aurora Premium tháng 10% |
| Start | 17,9 tr/năm | 8 | 2 | 6 | 2,24 tr | Rẻ hơn PVsyst 19% |
| Team | 34,9 tr/năm | 24 | 5 | 18 | 1,45 tr | Rẻ hơn HelioScope Basic 16% |
| Pro | 54,9 tr/năm | 60 | 10 | 30 | 0,92 tr | Rẻ hơn Aurora Premium năm 19% |

Dịch vụ thêm: Thiết kế hộ 3,9 tr/dự án. Tiền mua lẻ được trừ khi nâng lên gói năm. Pilot giảm 30% cho 5 khách gói năm đầu.

**Chi phí một dự án:** dự kiến 246.000 đ, tối đa 532.000 đ khi ghim mô hình, 868.000 đ nếu dùng mô hình đắt nhất. Trần cả gói Pro là 52,1 tr nếu không giới hạn, 9,4 tr (17% giá gói) khi ghim mô hình và giới hạn giờ hỗ trợ.

**Hòa vốn năm đầu, lãi 50 tr, chưa tính lưu trữ và Thiết kế hộ.** Số khách ở mức dùng dự kiến, chi phí có 1 khách 8 tr:

| Nhân sự | Cố định/năm | Toàn Start | Trộn 50/35/15 |
|---|---|---|---|
| 6 người đủ lương | 1,47 tỷ | 224 | 97 |
| 5 người đủ lương | 1,28 tỷ | 199 | 85 |
| 6 người nửa lương | 910 tr | 149 | 62 |
| 3 người đủ lương | 910 tr | 149 | 62 |
| 3 người nửa lương | 632 tr | 97 | 45 |

**Dòng tiền, tuyển theo mốc 15, 30, 60 khách, đủ lương, vốn 600 tr:**

| Kịch bản | Doanh thu năm 1 | EBITDA năm 1 / 2 / 3 | Tiền mặt thấp nhất |
|---|---|---|---|
| Cơ sở: 22 khách năm mới, 18 lượt lẻ, 30 dự án Thiết kế hộ | 789 tr | −509 / −258 / +174 tr | −168 tr |
| Gấp đôi | 1,62 tỷ | −139 / +567 / +1.607 tr | +146 tr |
| Gấp 2,5 lần | 2,04 tỷ | +62 / +1.044 / +2.343 tr | +187 tr |
| Cơ sở, nhưng 6 người ngay từ đầu | 789 tr | −1.004 / −475 / +81 tr | −879 tr |

**Lưu trữ theo bậc:** 299.000 đ/tháng tới 8 dự án, 599.000 đ tới 24, 899.000 đ tới 60, 1,49 tr tới 150; trên 150 báo giá. Gói năm lưu miễn phí bằng số dự án của gói. Khách không đóng thì có 30 ngày chỉ xem, sau đó dữ liệu chuyển sang kho lạnh, không xóa ngay. Khôi phục: truy thu tối đa 6 tháng cộng 500.000 đ, hoặc 299.000 đ mỗi dự án.

Trước khi bán: luật sư chốt thời hạn giữ và điều khoản; không gọi là đã xóa khi còn giữ; cơ quan có thẩm quyền yêu cầu thì cung cấp, không thu phí; chuyển sang lưu trữ bền, có niêm phong; đổi `purge_expired_projects.py` từ xóa hẳn sang chuyển kho.
