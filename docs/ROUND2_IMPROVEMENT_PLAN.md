# SolarOpt: phân tích phiếu chấm và kế hoạch nâng cấp vòng 2

Ngày đối chiếu: 10/10/2026, giờ Việt Nam. Tài liệu là đề xuất triển khai; không khẳng định các tính năng đề xuất đã được xây dựng hay EPC đã đồng ý hợp tác.

## 1. Căn cứ và kết luận

- Phiếu chấm: `I:/Downloads/Axiom_ (1).pdf`, 1 trang; tổng điểm BTC ghi 8,1.
- Proposal vòng DREAM: 19 trang; deck cũ: 15 trang; mã nguồn tại `SolarOpt-main/SolarOpt-main`.
- Nhận xét kỹ thuật dựa trên đọc source, chưa phải chứng nhận đã chạy thành công toàn bộ ứng dụng.
- Thể lệ vòng 2 trong ảnh người dùng cung cấp: deck tối đa 15 slide, hạn 21:00 ngày 10/10/2026; video tối đa 90 giây gồm intro BTC, hạn 10:00 ngày 11/10/2026; 12 phút cho pitching và Q&A.
- Trọng số dưới đây thuộc vòng sơ loại. Chưa có căn cứ xác nhận vòng 2 dùng cùng trọng số.

| Tiêu chí sơ loại | Trọng số | Điểm | Việc nâng cấp |
|---|---:|---:|---|
| Thấu hiểu vấn đề | 25% | 8,5 | Bổ sung bằng chứng từ kỹ sư/EPC Việt Nam, lượng hóa việc sửa thiết kế |
| Chất lượng giải pháp | 30% | 8,5 | Luồng chạy thật và đầu ra phù hợp công việc EPC |
| Đổi mới và công nghệ | 20% | 8 | Chứng minh truy vết, sửa và kiểm chứng; làm rõ giới hạn |
| Thị trường và khách hàng | 15% | 7,5 | TAM/SAM/SOM bằng doanh thu phần mềm, đối thủ có tên, phản hồi khách hàng |
| Định hướng triển khai | 10% | 7 | Pilot có người, dữ liệu, thời gian, KPI, điều kiện nghiệm thu và P&L |

BGK khen bài toán sửa thiết kế, impact-aware review và giao diện sát công việc kỹ sư. Các điểm yếu BTC nêu là: thiếu TAM/SAM/SOM định lượng, thiếu so sánh chi tiết với PVsyst/HelioScope, Pilot -> Retain -> Expand còn lý thuyết, thiếu bảng P&L và bằng chứng EPC đồng ý dùng thử. BGK khuyến khích tiếp cận 1-2 EPC.

Proposal đã có thảo luận đối thủ và bảng dự phóng tài chính sơ bộ ở trang 10-13; deck chưa thể hiện rõ chúng. Vì vậy cần nâng chất lượng bằng chứng và cách trình bày, đồng thời lấy xác nhận khách hàng, thay vì chỉ thêm nội dung từ đầu.

Định vị đề xuất: **SolarOpt hỗ trợ đội kỹ thuật EPC đánh giá tác động thay đổi, sửa thiết kế với ít xáo trộn và kiểm chứng lại trước khi kỹ sư phê duyệt.** Ban đầu xử lý một nhóm mái và thay đổi xác định; kết nối quy trình xuất/nhập dữ liệu phổ biến sau khi kiểm chứng nhu cầu.

## 2. Điểm yếu sâu hơn và hành động khắc phục

### 2.1. Chưa xác định được tập khách hàng có thể trả tiền

Số hệ thống điện mặt trời hoặc tổng công suất lắp đặt chỉ là bối cảnh ngành. Chúng không cho biết có bao nhiêu tổ chức sẽ mua phần mềm, mua bao nhiêu giấy phép, hoặc có nhu cầu sửa thiết kế thường xuyên.

Chọn phân khúc đầu tiên bằng điều kiện kiểm chứng: EPC mái nhà có người thiết kế nội bộ, có nhiều yêu cầu sửa mỗi tháng, có dữ liệu dự án và người quyết định mua sẵn sàng tham gia thử nghiệm. Số nhân sự, số dự án và mức giá là giả thuyết cần phỏng vấn, không phải dữ kiện thị trường hiện tại.

Phân biệt: người dùng = kỹ sư thiết kế; người mua = chủ EPC/trưởng kỹ thuật; người phối hợp = kỹ sư kinh doanh/quản lý dự án; người hưởng lợi cuối = chủ công trình.

### 2.2. Quy mô thị trường chưa quy đổi đúng sang doanh thu phần mềm

Lập bảng doanh nghiệp có tên, website, địa bàn, loại công trình, có thiết kế nội bộ hay không, tần suất sửa, công cụ đang dùng và khả năng mua. Gộp trùng theo pháp nhân, xác nhận tình trạng hoạt động. Danh bạ và công bố doanh nghiệp là nguồn tìm khách hàng; không mặc định mọi mục đều là khách hàng phù hợp.

Nguồn khởi đầu: [ENF Vietnam installer directory](https://www.enfsolar.com/directory/installer/vietnam). Kết quả truy xuất tiếng Anh ghi 196 mục, các trang ngôn ngữ/tổng hợp khác có số khác; đây không phải tổng số EPC Việt Nam đã được kiểm kê. Không dùng con số này như TAM quốc gia.

| Phạm vi | Công thức | Cách kiểm chứng |
|---|---|---|
| TAM Việt Nam | Tổng tổ chức phù hợp trên toàn quốc × doanh thu phần mềm bình quân/tổ chức/năm | Danh sách và phương pháp ước lượng; công khai phạm vi thiếu |
| SAM ban đầu | Tổ chức trong địa bàn, nhóm mái, quy trình và khả năng phục vụ hiện tại × doanh thu năm | Lọc từ danh sách theo điều kiện rõ |
| SOM 24 tháng | Tổ chức trả phí có thể đạt từ năng lực bán hàng/pilot × doanh thu năm | Mô hình phễu, thời gian triển khai, churn, nhân lực hỗ trợ |

Giá 2,9 triệu đồng/tháng trong proposal tương đương 34,8 triệu đồng/năm/tổ chức, vẫn là giả định. Với 196 mục và giả định tất cả phù hợp, mua một gói đủ năm, phép nhân cho 6,8208 tỷ đồng/năm. Đây chỉ là doanh thu giả định trên danh sách, không phải TAM được xác nhận. Phải loại trùng và xác minh trước khi dùng trong deck.

Không tính trùng thuê bao theo tổ chức và thuê bao theo người dùng; không cộng phí dự án đã nằm trong hạn mức gói. Nếu thị trường ngách nội địa nhỏ, trình bày đúng rồi mở rộng theo phân khúc kề cận hoặc dịch vụ tích hợp có bằng chứng nhu cầu.

### 2.3. Lợi thế cạnh tranh chưa được chứng minh

Không dùng bảng đánh dấu rằng đối thủ không có AI, không có mô phỏng, không có nhiều phương án, hoặc không tự động hóa. Nghiên cứu chính thức cho thấy họ đã có các năng lực đó.

| Sản phẩm | Năng lực được tài liệu chính thức xác nhận | Bài học cho SolarOpt |
|---|---|---|
| [PVsyst 8](https://www.pvsyst.com/en/products/pvsyst/) | Mô phỏng sản lượng, bóng che, cấu hình điện, nhiều tổn thất, đánh giá kinh tế và batch | Công khai giả định, tổn thất và phạm vi kiểm chứng; đối chuẩn mô hình |
| [PVsystCLI](https://www.pvsyst.com/help-cli/use-cases/simulation.html) | Chạy mô phỏng cho project/variant đã chuẩn bị, xuất CSV/report, chạy batch | Có thể nghiên cứu kết nối về sau; cần dự án hợp lệ, định dạng và giấy phép; chưa phải tích hợp hiện có |
| [HelioScope reports](https://help-center.helioscope.com/hc/en-us/articles/8198806782483-Production-Report-Summary) | Sản lượng, PR, tổn thất, giả định điện/cơ khí, BOM, dữ liệu theo giờ | Báo cáo thay đổi phải có số liệu, giả định và vật tư, vượt quá ảnh bố trí |
| [Aurora configuration](https://help.aurorasolar.com/hc/en-us/articles/32757795077523-Admin-Configuration-Checklist) | Thiết lập linh kiện, khoảng cách, mục tiêu AutoDesigner, mô phỏng và giá | Bộ quy tắc theo EPC, nguồn và phiên bản quy tắc là hữu ích |
| [OpenSolar Ada](https://support.opensolar.com/hc/en-us/articles/13780099656719-Designing-using-Ada-Auto-Design) | Tự thiết kế theo template, linh kiện và giá; sửa thủ công; chế độ mái vẽ tay khi thiếu 3D tốt | Dùng template của đội kỹ thuật và giữ quyền duyệt của người dùng |
| [OpenSolar interval data](https://support.opensolar.com/hc/en-us/articles/13183853699215-How-to-upload-interval-data) | Nạp dữ liệu tiêu thụ theo chu kỳ 15/30/60 phút | Tối ưu theo phụ tải và giá trị kinh tế thực, không chỉ tổng kWh |
| [Scanifly SolarAI](https://help.scanifly.com/solarai-automated-remote-solar-designs) | Tự tạo thiết kế sơ bộ từ dữ liệu từ xa, vật cản, bóng che, sản lượng; khuyến nghị kiểm tra đầu ra | Phân biệt thiết kế sơ bộ và dữ liệu đã đo tại hiện trường |

[OpenSolar công bố ứng dụng lõi miễn phí](https://www.opensolar.com/post/free-platform-data-export-pricing/), phí áp dụng cho kết nối API/connectors. Vì vậy lợi thế giá của SolarOpt cần gắn với lợi ích vận hành đo được.

Trong bảng deck, ghi rõ ba trạng thái SolarOpt: đã chạy và có log; đã có module nhưng chưa tích hợp/đối chuẩn; đang đề xuất. Với tính năng đối thủ chưa xác minh, dùng 'chưa xác minh' thay vì 'không có'. Nghiên cứu tính năng công khai không đủ để kết luận lợi thế độc quyền.

### 2.4. Giao diện chưa phản ánh phép tính backend

`frontend/src/App.tsx` có `DESIGN_OPTIONS`, `STRESS`, `VERSION_HISTORY` và `LOG_SCRIPT` mẫu. API được gọi ở bước phân tích ảnh; các bước thiết kế, kiểm chứng, stress và repair chưa nối tương ứng. Nối state dự án xuyên suốt: cấu hình -> mái/vật cản -> thiết kế -> kiểm chứng -> thay đổi -> repair -> phiên bản. Mọi chỉ số hiển thị lấy từ đầu ra có nguồn; lỗi mạng không được hiển thị thành kết quả chạy thành công.

### 2.5. Truy vết phụ thuộc chưa đồng nghĩa tái tính chọn lọc

`trace_impact` duyệt đồ thị để xác định affected/reused; endpoint repair vẫn gọi lại `generate_design`. Tỷ lệ nút affected hiện không phải tỷ lệ thời gian thực thi hay tài nguyên tiết kiệm.

Nâng cấp theo thứ tự: nhận diện thay đổi thực -> cache theo input và phiên bản -> vô hiệu hóa kết quả phụ thuộc -> chỉ chạy module cần thiết -> ghi hit/miss, module đã chạy và thời gian -> so với full recompute cùng mô hình. Cho tới khi hoàn thành, dùng mô tả 'truy vết ảnh hưởng và tái tối ưu ưu tiên giữ bố trí cũ'.

### 2.6. Tối ưu, hình học và mô phỏng còn đơn giản

- Mái backend hiện là hình chữ nhật; hình học đa giác trên UI chưa đồng nghĩa engine hỗ trợ đa mái.
- Khi setback làm vùng mái rỗng, `geometry.py` gán lại toàn bộ mái: cần trả không khả thi, giữ nguyên ràng buộc.
- Bóng che dùng 9 thời điểm đại diện, trọng số heuristic; chưa đủ để gọi sản lượng là mô phỏng chi tiết đã đối chuẩn.
- Hướng/độ nghiêng có trong schema nhưng chưa được sử dụng đầy đủ trong pipeline sinh thiết kế.
- Mục tiêu balanced chủ yếu nhân điểm năng lượng với 0,98; không tạo đánh đổi kinh tế độc lập. Chưa thể mặc định ba mục tiêu sẽ cho ba phương án khác nhau.
- Minimal repair có preservation bonus; chưa bảo đảm sửa tối thiểu theo một chi phí thực tế đã định nghĩa.

Ưu tiên định nghĩa phạm vi mái được hỗ trợ, fail đúng khi không khả thi, sửa mục tiêu tối ưu và kiểm thử thay đổi. Sau đó mới mở đa giác, nhiều mặt mái, chuỗi thời tiết theo giờ và đối chuẩn sản lượng.

### 2.7. Kiểm chứng chưa bao phủ các tuyên bố an toàn/độ bền

`verifier.py` kiểm tra hình học và một số dữ liệu; điều kiện điện chủ yếu là P/Voc/Imp dương. Chưa kiểm tra đầy đủ string, MPPT, điện áp theo nhiệt độ, inverter và quy tắc hiện trường. PASS chỉ áp dụng bộ điều kiện đã triển khai, không phải xác nhận kết cấu/PCCC hoặc đủ điều kiện thi công.

`stress.py` sinh lại thiết kế trước khi kiểm tra từng kịch bản. Tách thành: (1) thiết kế gốc chịu thay đổi ra sao; (2) sau sửa đạt gì, mất gì và thay đổi bao nhiêu. Khi dữ liệu bắt buộc thiếu hoặc sửa không đạt, trả trạng thái cần kỹ sư xem xét, không tự duyệt.

### 2.8. Dữ liệu và định nghĩa KPI chưa nhất quán

- Slide so 12,1 với 14,3 MWh là tăng khoảng 2,2 MWh; ví dụ 5 MWh và CO2 là kịch bản riêng.
- Hoàn vốn 2,2 năm trên deck khác 5,2 năm trong giao diện; phải đồng bộ giả định.
- 'Hiệu suất mái 82%' cần định nghĩa; không trộn roof utilization với performance ratio.
- Backend chi phí hiện là số tấm × đơn giá tấm, chưa phải CAPEX gồm inverter, khung, dây, thi công và chi phí khác.
- Không dùng confidence từ AI như xác suất chính xác đã hiệu chuẩn.
- '8/8' phải chỉ rõ 8 điều kiện hay 8 tình huống; '38 giây' cần là số đo, không phải nhãn giao diện.

Lập một bảng dữ liệu chuẩn dùng chung cho deck, video và demo: chỉ số, đơn vị, định nghĩa, công thức, nguồn, dữ liệu gốc, ngày đo, phạm vi và trạng thái minh họa/thực đo.

## 3. Tính năng nâng cấp ưu tiên

### A. Báo cáo thay đổi thiết kế và vật tư

Đầu vào: hai phiên bản dự án và nguyên nhân thay đổi. Đầu ra: phần bị ảnh hưởng, panel giữ/thêm/bỏ/di chuyển, chênh lệch kWh/kWp, vật tư, giá và trạng thái kiểm chứng. Kỹ sư duyệt hoặc từ chối; lưu lý do.

Học cách xuất báo cáo/BOM của HelioScope; giá trị SolarOpt đề xuất là giải thích ảnh hưởng của một thay đổi thành công việc và chi phí. MVP bắt đầu bằng panel và các dòng vật tư có số lượng xác định; phần chưa tính được ghi rõ. Không suy diễn dây/khung đầy đủ chỉ từ số tấm.

Nghiệm thu: đổi chiều cao hoặc model pin trên dữ liệu thật; báo cáo được tạo từ hai output backend; tổng chênh lệch khớp; giữ được dữ liệu đầu vào để chạy lại. Ưu tiên P0 cho bản đơn giản, P1 cho BOM đầy đủ hơn.

### B. Danh sách dữ kiện cần xác minh theo tác động

Đầu vào: độ cao/kích thước chưa chắc chắn và khoảng giá trị có căn cứ. Chạy các giả thuyết; trả dữ kiện nên đo, vùng ảnh cần chụp và quyết định thiết kế nào có thể thay đổi. Ghi nguồn khoảng giá trị, ngày đo và người xác nhận.

MVP có thể tận dụng `uncertainty.py`, nhưng hai đầu mút không bảo đảm tìm được mọi thay đổi ở giữa: bổ sung lấy mẫu khoảng và kiểm tra ngưỡng/ràng buộc. Bất định liên quan an toàn hoặc dữ liệu bắt buộc luôn chuyển người xem xét theo quy tắc, không tự bỏ qua vì impact score nhỏ. 'Không cần khảo sát lại' chỉ được khẳng định sau đối chiếu thực tế.

Nghiệm thu: một trường hợp thay đổi giá trị không đổi quyết định và một trường hợp làm thay đổi; lý do hỏi kỹ sư rõ; nhiệm vụ có trạng thái và người chịu trách nhiệm. Ưu tiên P1, đưa vào roadmap nếu chưa chạy.

### C. Sửa thiết kế theo chi phí thay đổi thực tế

Cho phép kỹ sư khóa khu vực/vị trí đã chốt. Tối ưu có ưu tiên: đạt ràng buộc bắt buộc -> đạt ngưỡng năng lượng/kinh tế -> giảm chi phí chỉnh sửa. Phạt panel thêm/bỏ/di chuyển và thay đổi linh kiện theo chi phí EPC cung cấp. So với tái tối ưu hoàn toàn; công khai phần năng lượng hy sinh để giảm xáo trộn.

Nghiệm thu: giữ đúng khóa; không trả phương án vi phạm để giữ thiết kế cũ; cho biết không khả thi khi cần; số thay đổi và năng lượng đo được. Bản trước thi dùng bonus và mô tả đúng; mô hình chi phí thực triển khai P1.

### D. Tối ưu theo tự tiêu thụ và hiệu quả đầu tư

Học từ OpenSolar: nạp CSV phụ tải, dữ liệu phát theo cùng bước thời gian và biểu giá do khách hàng cung cấp. Tính điện tự dùng, điện dư, tiền tiết kiệm và độ nhạy CAPEX/O&M/giá điện. Không mặc định mọi kWh phát ra đều bán được hoặc thay thế điện mua cùng giá. Nếu thiếu phụ tải, hiển thị kịch bản giả định thay vì ROI chính xác.

Nghiệm thu: cân bằng năng lượng theo bước thời gian; nguồn giá và thời điểm hiệu lực rõ; tổng tiền kiểm tra bằng phép tính độc lập. Battery sizing/dispatch để giai đoạn sau. Ưu tiên P2 sau dữ liệu và mô phỏng.

### E. Bộ quy tắc và hồ sơ bằng chứng theo EPC

Học từ Aurora: template linh kiện, khoảng cách, vùng cấm, ngưỡng bóng, hạn mức chi phí. Mỗi quy tắc ghi người xác nhận, nguồn và phiên bản; phân biệt quy tắc nội bộ với quy định pháp lý. Báo cáo ghi nguyên nhân mỗi PASS/FAIL/WARN và dữ liệu sử dụng. Phân quyền, quản lý nhiều tổ chức và kết nối công cụ chuẩn là việc cần cho pilot thương mại.

Nguồn hình học cần phân loại: ảnh thô, ảnh trực giao, bản vẽ có tỷ lệ, đo thủ công. [Scanifly giải thích hạn chế của ảnh từ trên xuống chưa hiệu chỉnh](https://help.scanifly.com/warning-scaling-not-the-same-as-drone-model). Một ảnh với một kích thước chuẩn không chứng minh được mô hình 3D hay chiều cao vật cản chính xác.

## 4. Kế hoạch lấy bằng chứng khách hàng và pilot

Không tự gửi tin nhắn, email hay gọi điện theo tài liệu này. Đội chủ động liên hệ và xin phép sử dụng phản hồi/tên doanh nghiệp.

### 4.1. Phễu tiếp cận đề xuất

Danh sách 20 EPC phù hợp -> mục tiêu 5 cuộc trao đổi -> 2 buổi xem demo/dữ liệu -> 1-2 pilot. Đây là mục tiêu công việc, chưa phải phễu đã đạt.

Ưu tiên người có thể cung cấp bản vẽ và yêu cầu sửa gần đây. Các website [Vũ Phong](https://vuphong.com/apac/) và [GPECC](https://gpecc.com.vn/) xác nhận có hoạt động EPC; chỉ là ví dụ đầu mối nghiên cứu, không phải đối tác SolarOpt. EPC nhỏ có đường tiếp cận qua giảng viên/cố vấn có thể phù hợp hơn cho thử nghiệm nhanh.

### 4.2. Câu hỏi phỏng vấn

1. Lần gần nhất anh/chị phải sửa thiết kế vì dữ liệu thay đổi là khi nào?
2. Yêu cầu nào thay đổi, ai phát hiện và ở giai đoạn nào?
3. Đã sửa những file/bước nào? Có thể cho xem dữ liệu đã ẩn danh không?
4. Mất bao nhiêu phút làm việc và bao nhiêu thời gian chờ? Một tháng xảy ra bao nhiêu lần?
5. Công cụ hiện tại xử lý được phần nào, phần nào vẫn phải làm bằng tay?
6. Kết quả nào cần kỹ sư ký/duyệt? Loại sai sót nào không chấp nhận?
7. Nếu công cụ xử lý được tình huống này, ai duyệt mua và ngân sách lấy từ đâu?
8. Anh/chị có thể dành thời gian thử trên dự án nào, ngày nào, với người phụ trách nào?

Ghi cả phản hồi không muốn dùng và lý do. Không thay bằng câu hỏi dẫn dắt 'anh/chị có thích AI không'.

### 4.3. Pilot có thể nghiệm thu

- Phạm vi đề xuất: 1-2 EPC, 3-5 dự án mỗi đơn vị, 2-3 thay đổi mỗi dự án trong 2-4 tuần; điều chỉnh theo dữ liệu và lịch đối tác.
- Đối tác chỉ định kỹ sư và người đánh giá; thống nhất dữ liệu được dùng, cách ẩn danh, thời gian và bộ điều kiện kiểm tra.
- Lấy baseline quy trình hiện tại, cùng loại nhiệm vụ và cùng chất lượng đầu ra. Phân biệt thời gian thao tác, chờ người và thời gian máy.
- Đổi thứ tự làm thủ công/SolarOpt giữa các ca nếu có thể để giảm hiệu ứng học; ghi người thực hiện và lỗi phải sửa.
- Ngưỡng mục tiêu đề xuất để đàm phán: giảm trung vị thời gian thao tác >=30%, không bỏ sót vi phạm ràng buộc bắt buộc trong bộ test, chất lượng đầu ra được kỹ sư chấp nhận, có ít nhất một đơn vị muốn tiếp tục thử trả phí. Đây là ngưỡng thử nghiệm, chưa phải thành tích.
- Nếu số ca nhỏ, công khai n và danh sách ca; không suy rộng thành kết quả toàn ngành.

Bằng chứng tăng dần: liên hệ -> xác nhận có nhu cầu -> đồng ý chia sẻ dữ liệu -> xác nhận lịch/phạm vi pilot -> hoàn thành pilot -> đồng ý trả phí. Không gọi trao đổi ban đầu là pilot đã triển khai; thư quan tâm không phải doanh thu.

Nếu chưa có phản hồi trước deadline, deck ghi đúng trạng thái: kế hoạch tiếp cận, số cuộc đã thực hiện và bước tiếp theo. Không tự tạo logo đối tác hay lời chứng thực.

## 5. Benchmark kỹ thuật và vận hành

Bản trước deadline: chạy 3-5 ca đủ input/output; ghi n nhỏ. Sau đó mở 5 mái × 5 thay đổi = 25 ca: đổi chiều cao vật cản, kích thước mái, model panel, ngân sách, setback. Nếu engine chưa hỗ trợ loại thay đổi nào thì bổ sung trước hoặc loại khỏi phạm vi báo cáo.

So sánh ba baseline khi đã triển khai: full recompute; sửa ưu tiên giữ bố trí; tái tính chọn lọc + sửa ưu tiên giữ bố trí. Cùng dữ liệu, giới hạn thời gian, engine và điều kiện chất lượng. Khi chưa có tái tính chọn lọc, chỉ so hai bản đầu và ghi phần còn thiếu.

| KPI | Định nghĩa |
|---|---|
| Thời gian sửa | Thao tác kỹ sư và thời gian máy báo riêng; trung vị, khoảng biến thiên, n |
| Giảm thời gian | (Baseline - SolarOpt) / Baseline; chỉ tính trên ca so sánh hợp lệ |
| Vi phạm bắt buộc | Số lỗi hình học/ngân sách/quy tắc triển khai; thiếu dữ liệu không coi là PASS |
| Giữ bố trí | Số vị trí cũ còn được giữ / số vị trí cũ; dùng tọa độ và model, không chỉ ID |
| Năng lượng đánh đổi | (Năng lượng full recompute - năng lượng repair) / full recompute trên cùng giả định |
| Độ bền thiết kế | Tỷ lệ ca thiết kế gốc vẫn đạt sau thay đổi, trước khi sửa |
| Khả năng sửa | Tỷ lệ ca được sửa thành phương án hợp lệ; báo cả số lần chuyển người |
| Tái sử dụng tính toán | Cache hit/miss, module thực chạy, thời gian thực; không dùng tỷ lệ nút graph thay runtime |
| Chất lượng yêu cầu đo lại | Số yêu cầu thực sự làm đổi quyết định; kiểm tra cả trường hợp bỏ sót |

Lưu `case_id`, input gốc/mới, baseline, output, engine/model/version, seed nếu có, solver status, thời gian, lỗi, người duyệt. Lưu ca thất bại. Đối chuẩn sản lượng phải cùng thời tiết, hướng, độ nghiêng, linh kiện và tổn thất; so với phần mềm khác là đối chiếu mô hình, chưa thay thế dữ liệu phát điện đo thực. [Scanifly có checklist kiểm soát các khác biệt này](https://help.scanifly.com/comparing-solar-production).

Kiểm tra quan trọng trước demo: đầu vào thật đi qua UI; thay đổi làm output đổi; setback không khả thi trả lỗi; ràng buộc không bị nới tự động; stress kiểm tra thiết kế gốc; repair sai bị chặn duyệt; fallback AI/bức xạ/solver có nhãn; phiên bản lưu và mở lại được.

## 6. Mô hình kinh doanh, BMC và tài chính

### 6.1. BMC cần đủ 9 ô

1. Khách hàng: phân khúc EPC đã chọn và người mua/người dùng.
2. Giá trị: giảm thao tác sửa và minh bạch tác động; định lượng bằng pilot.
3. Kênh: giới thiệu từ kỹ sư/cố vấn, tiếp cận trực tiếp, demo ca thực, đối tác thiết bị khi có xác nhận.
4. Quan hệ khách hàng: onboarding có hỗ trợ, pilot, đánh giá định kỳ, hỗ trợ kỹ thuật.
5. Doanh thu: thuê bao tổ chức và phí triển khai/tích hợp có phạm vi; chưa mặc định thu phí ở mọi dòng.
6. Nguồn lực: nhóm phát triển, kỹ sư cố vấn, engine và bộ dữ liệu được phép sử dụng.
7. Hoạt động: phát triển, đối chuẩn, onboarding, hỗ trợ và bán hàng B2B.
8. Đối tác: EPC thử nghiệm, cố vấn điện mặt trời, nguồn dữ liệu/công cụ; chỉ nêu 'đã có' khi được xác nhận.
9. Chi phí: nhân lực, compute/API, dữ liệu, kỹ sư kiểm tra, bán hàng, hỗ trợ, vận hành và bảo mật.

### 6.2. Xác nhận willingness-to-pay

Giá trị giờ công tháng = số yêu cầu sửa × thời gian tiết kiệm/yêu cầu × chi phí giờ kỹ sư. Phân biệt lợi ích ước tính từ công suất xử lý với tiền thực giảm chi. Chưa đo thì ghi giả định.

Ví dụ thuần giả định: 20 yêu cầu/tháng × 1 giờ × 200.000 đồng = 4 triệu đồng giá trị giờ công. Gói 5,9 triệu không được biện minh chỉ bằng lợi ích này. Đội phải chứng minh thêm giá trị hoặc chọn mức giá/phân khúc khác. Với 5,9 triệu và 200.000 đồng/giờ, cần 29,5 giờ tiết kiệm/tháng để bằng phí.

### 6.3. P&L phải có mô hình phía sau

Proposal đã dự phóng (đơn vị tỷ đồng): năm 1 doanh thu 0,53, chi phí 0,85, chênh lệch -0,32; năm 2 là 3,10/2,20/0,90; năm 3 là 10,50/6,40/4,10. Đây là dự phóng cũ, chưa phải doanh thu hay lợi nhuận thực, cũng chưa đủ chi tiết để gọi lợi nhuận ròng sau thuế.

Kiểm tra năm 1: 12 tổ chức × 4 triệu/tháng × 8 tháng = 384 triệu; để tới 530 triệu còn 146 triệu phí pilot/tích hợp. Cần số hợp đồng × đơn giá và thời điểm ghi nhận cho khoản này. Xác định 12 là số bình quân hay cuối kỳ; tránh tính đủ tháng cho khách mới vào cuối năm.

Mô hình mới theo tháng 12 tháng đầu, tổng hợp 3 năm, có ba kịch bản thấp/cơ sở/cao:

- Khách đầu kỳ + khách mới - khách rời = khách cuối kỳ; doanh thu theo cohort/tháng thực trả.
- Thuê bao + phí triển khai/tích hợp = doanh thu; tách khoản một lần và định kỳ.
- Compute/API/lưu trữ và chi phí trực tiếp triển khai/hỗ trợ -> giá vốn -> lợi nhuận gộp.
- R&D, bán hàng, quản lý và các chi phí vận hành -> kết quả hoạt động.
- Thu/chi tiền, vốn đầu tư và dự phòng -> số dư tiền; không đồng nhất lợi nhuận với tiền mặt.
- CAC theo chi phí tiếp cận/bán hàng thực và số khách mới; chi phí onboarding mỗi EPC; tỷ lệ pilot sang trả phí; retention.
- Vốn cần = mức thiếu hụt tiền tích lũy lớn nhất + dự phòng; giải thích nguồn vốn thay vì lặp lại 500 triệu.

Đối chiếu SOM với mô hình khách trả phí. Không dùng '30 doanh nghiệp trong 24 tháng' và '50 doanh nghiệp năm 2' mà không giải thích khác phạm vi/thời điểm.

## 7. Backlog và mốc thực hiện

Ước lượng dưới đây cần hiệu chỉnh theo khả năng và thời gian còn lại; không cam kết hoàn thành mọi tính năng trước 21:00.

| Ưu tiên | Công việc | Người phụ trách gợi ý | Đầu ra / điều kiện xong |
|---|---|---|---|
| P0, trước chốt deck | Bảng claim/evidence, thống nhất số | Nội dung + kỹ thuật | Mỗi số có nguồn hoặc nhãn giả định |
| P0 | Nối một luồng UI-backend xuyên suốt | 2 người kỹ thuật | Nhập -> thiết kế -> verify -> thay đổi -> repair -> phiên bản |
| P0 | Sửa các lỗi ràng buộc/nhãn kết quả | Kỹ thuật | Không tự bỏ setback; thiếu dữ liệu/lỗi không thành PASS |
| P0 | 3-5 ca chạy có log | Kỹ thuật + nội dung | Input/output, thời gian, ca thất bại và giới hạn |
| P0 | Tiếp cận EPC và lập hồ sơ pilot | Kinh doanh | Phản hồi có thật hoặc trạng thái đang tiếp cận rõ |
| P0 | TAM/SAM/SOM, so sánh đối thủ, BMC, P&L | Kinh doanh + deck | Tất cả công thức và giả định đọc được |
| P0 | Deck 15 slide và video thống nhất | Deck + video | Đủ nội dung bắt buộc, nộp đúng hạn |
| P1, 1-2 tuần | Báo cáo thay đổi + chi phí sửa; nhiệm vụ xác minh | Kỹ thuật + kỹ sư cố vấn | Hai tính năng hoạt động trên dữ liệu pilot |
| P1, 2-4 tuần | Pilot 1-2 EPC, 25 ca kỹ thuật nếu đủ dữ liệu | Cả đội | Case study, baseline, kết quả và phản hồi mua |
| P1/P2, 3-6 tuần | Cache/invalidation thật, bộ quy tắc, đa giác theo nhu cầu | Kỹ thuật | So full recompute, kiểm tra chất lượng và hit/miss |
| P2, 6-12 tuần | Mô phỏng theo giờ, phụ tải/ROI, xuất/nhập công cụ | Kỹ thuật + EPC | Đối chuẩn có kiểm soát, dữ liệu được cấp phép |

Phân công 5 người gợi ý: 2 kỹ thuật, 1 thị trường/tài chính, 1 nội dung/deck, 1 video/pitch và quản lý checklist. Người pitch cần hiểu cả công nghệ và kinh doanh, không chỉ học lời thoại.

Chưa ưu tiên trước deadline: photogrammetry 3D đầy đủ, điều khiển inverter, digital twin vận hành thời gian thực, marketplace thiết bị, blockchain hoặc chatbot chung. Những phần này cần dữ liệu và vận hành riêng, chưa giải quyết trực tiếp nhận xét BGK.

## 8. Cấu trúc deck mới: 15 slide

| Slide | Nội dung | Tiến bộ cần cho BGK thấy |
|---:|---|---|
| 1 | Tổng quan, Axiom, khách hàng, lời hứa giá trị; video theo BTC | Một định vị rõ |
| 2 | Vấn đề, người dùng/người mua, bằng chứng khách hàng | Dữ liệu thực Việt Nam hoặc trạng thái đang kiểm chứng |
| 3 | TAM/SAM/SOM và công thức | Doanh thu phần mềm, nguồn và giả định |
| 4 | Giải pháp và luồng sử dụng | Từ thay đổi tới quyết định kỹ sư |
| 5 | MVP và mức hoàn thiện | Chạy thật / chưa tích hợp / roadmap phân biệt rõ |
| 6 | Công nghệ, vai trò AI, phần đội xây | Đầu vào/đầu ra, engine, quyền duyệt |
| 7 | Ca thay đổi trước/sau và báo cáo ảnh hưởng | Output thật, số đo và phần giữ lại |
| 8 | Benchmark và giới hạn | n, baseline, lỗi, kết quả có log |
| 9 | PVsyst, HelioScope, OpenSolar, Aurora/Scanifly và SolarOpt | So sánh cụ thể, không phủ nhận năng lực đối thủ |
| 10 | Business Model Canvas đủ 9 ô | Người mua, kênh, chi phí, doanh thu rõ |
| 11 | Marketing/bán hàng, pilot, giữ khách | Danh sách, phễu, lịch, KPI, trạng thái xác nhận |
| 12 | P&L, dòng tiền, vốn và độ nhạy | Mô hình tính nhất quán với SOM |
| 13 | Roadmap, mở rộng và rủi ro | Mỗi mốc có điều kiện nghiệm thu và người phụ trách |
| 14 | Team, vai trò và năng lực; nhu cầu cố vấn | Ai chịu trách nhiệm cho rủi ro nào |
| 15 | Giá trị vận hành/môi trường, thông điệp và nhu cầu hỗ trợ | Kết quả đo tách khỏi kỳ vọng |

Không thêm tính năng đề xuất vào danh sách 'đã hoàn thành'. Mockup phải có nhãn. Nếu tính năng mới chưa kịp làm, đưa vào roadmap có mốc và lý do từ phỏng vấn.

## 9. Điều kiện chốt bản vòng 2

- Deck <=15 slide, đủ 12 nội dung handbook; mỗi nhận xét BGK có slide/bằng chứng trả lời.
- Đầu ra MVP đúng source và đúng trạng thái triển khai.
- TAM/SAM/SOM là thị trường phần mềm, không phải giá trị toàn bộ ngành solar.
- Có bảng cạnh tranh với PVsyst/HelioScope; tính năng chưa xác minh không ghi 'không có'.
- Có P&L, giả định doanh thu, chi phí và nhu cầu tiền mặt; khớp mục tiêu khách.
- Pilot trình bày đúng mức xác nhận, không biến thư quan tâm thành doanh thu.
- Số liệu năng lượng, chi phí, hoàn vốn, CO2, số panel và thời gian thống nhất.
- Video <=90 giây gồm intro BTC; deck/video/pitch thống nhất.
- Pitch và Q&A nằm trong 12 phút; chuẩn bị trả lời giới hạn kỹ thuật và cách đo.

Thông điệp nâng cấp có thể dùng khi có bằng chứng: **Từ nguyên mẫu minh họa quy trình, SolarOpt tiến tới công cụ xử lý thay đổi được đo bằng thời gian kỹ sư, chất lượng thiết kế và khả năng khách hàng trả tiền.**
