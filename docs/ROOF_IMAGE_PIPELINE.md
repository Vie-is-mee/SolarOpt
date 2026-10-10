# Ảnh mái → bản vẽ có thể sửa → bóng che

Bản nâng cấp ngày 10/10/2026. Mục tiêu là giữ được đường biên theo điểm ảnh, hiệu chuẩn bằng số đo thật và để kỹ sư sửa trực tiếp. Không coi một câu trả lời AI là bản đo đạc.

## Công nghệ đang dùng

- **Groq / Qwen:** đọc ngữ cảnh, đề xuất vùng mái và vật cản trên ảnh chính, tham khảo tối đa hai ảnh bổ sung, ghi những thông tin chưa biết. Khóa ở máy chủ; giao diện không nhận khóa. Đã gọi dịch vụ thật thành công trên ảnh kiểm thử tự tạo.
- **OpenCV chạy CPU:** ảnh drone dùng GrabCut để tách vùng theo màu/cạnh; bản vẽ dùng phát hiện cạnh và đường bao; cả hai có phương án chấm biên trực tiếp. Đường bao chuyển thành đa giác, giữ góc lõm, tối đa 50 đỉnh.
- **Hiệu chuẩn:** cắt sát biên mái, giữ một tỷ lệ điểm ảnh cho cả hai chiều. Chiều rộng nhập tay chỉ là giả định cho tới khi có số đo. Chấm hai đầu đoạn đã đo thật để tính tỷ lệ mét/điểm ảnh. Ảnh xiên có công cụ hiệu chỉnh bốn góc của một mặt phẳng hình chữ nhật, cần nhập chiều dài thật của cả hai cạnh.
- **Hình học:** Shapely tính giao vùng, khoảng lùi, mặt bằng vật thể xoay và bóng chiếu; pvlib tính mặt trời và bức xạ trời quang; OR-Tools chọn vị trí pin trong lưới ứng viên. Mỗi tấm phải nằm trọn trong một mặt mái cho phép lắp.

Đây là sự kết hợp AI nhận biết ngữ cảnh, xử lý điểm ảnh và số đo kỹ sư. Chưa tích hợp MobileSAM, dựng 3D từ ảnh hay mô hình học riêng cho mái nhà. Luồng tách biên trực tiếp không dùng lượt Groq, không tải mô hình lớn và không cần GPU; ảnh được thu nhỏ tối đa 1200 × 1200 điểm ảnh trước khi tách.

Nguồn mở: [OpenCV trên GitHub](https://github.com/opencv/opencv), [hướng dẫn GrabCut](https://docs.opencv.org/4.x/d8/d83/tutorial_py_grabcut.html), [Shapely](https://github.com/shapely/shapely), [pvlib](https://github.com/pvlib/pvlib-python), [OR-Tools](https://github.com/google/or-tools). OpenCV dùng giấy phép Apache 2.0. Không có bằng chứng hiện trường để khẳng định độ chính xác cao hơn công cụ thương mại.

## Ba loại đầu vào có vai trò khác nhau

| Loại | Cách dùng tốt nhất | Phần cần bổ sung |
|---|---|---|
| Drone thẳng xuống | Làm ảnh chính để trích biên toàn mái, xem vị trí vật cản | Một đoạn đo thật, hướng Bắc thật; ảnh phải đủ nét, tránh mái bị cây che. Mái nhiều cao độ vẫn có thể lệch vị trí do phối cảnh |
| Bản vẽ mái | Đối chiếu biên và số đo; ảnh/PDF dùng trang đầu | Chọn đúng đường bao mái, tránh khung giấy/chữ. Đường bao tự động chưa hiểu mọi ký hiệu CAD; số đo từ kỹ sư ưu tiên hơn chữ AI đọc |
| Ảnh một phần / ảnh xiên | Nhận biết và bổ sung một vật thể, chi tiết hoặc bằng chứng cao độ | Không dùng làm toàn mái. Kỹ sư phải đặt chi tiết vào mặt bằng chung, nhập kích thước và chiều cao |

Một ảnh chính + hai ảnh chi tiết được gửi cho AI cùng ngữ cảnh, nhưng **chưa tự đăng ký, ghép tọa độ giữa ba ảnh hoặc dựng lại 3D**. Bản vẽ hiện lấy hệ tọa độ từ ảnh chính. Nếu chỉ có ảnh một phần, cần vẽ toàn mái từ số đo hoặc bổ sung ảnh tổng thể. Không thể cam kết suy ra hình học đầy đủ từ dữ liệu không có trong ảnh.

## Thử trên mái của đội

1. Mở `http://127.0.0.1:5173`, tải lại trang nếu đang dùng giao diện cũ. Chọn loại đầu vào và ảnh chính; thêm ảnh chi tiết nếu có.
2. Bấm **Đọc ảnh và đề xuất bản vẽ**, kiểm tra phần AI quan sát. **Áp dụng và chỉnh bản vẽ** đưa đề xuất sang vùng làm việc. AI thiếu độ cao thì giá trị tạm được gắn nhãn; phải sửa trước khi xác nhận.
3. Nếu biên sai, mở **Ảnh nguồn để đối chiếu bản vẽ** hoặc trở lại Dữ liệu. Trong **Trích biên đúng theo ảnh**, kéo khung sát mái rồi **Tách biên từ vùng chọn**. Thêm điểm **Giữ mái + / Loại nền −**, tách lại; hoặc **Chấm biên** lần lượt mọi góc lồi/lõm rồi **Dùng biên đã chấm**. Kiểm tra lớp phủ trước khi áp dụng.
4. Dùng **Đo tham chiếu**, chọn hai đầu đoạn đã đo thật, nhập độ dài rồi trích lại. Ảnh xiên: chọn bốn góc theo vòng, nhập cả hai cạnh thật, hiệu chỉnh, rồi đo tham chiếu trên ảnh mới. Cách này chỉ phù hợp một mặt phẳng, không sửa được cả mái nhiều tầng bằng một phép biến đổi.
5. **Áp dụng biên và tỷ lệ**. Kéo thanh **Ảnh nền để canh biên** để so bản vẽ với ảnh cắt sát mái. Nếu đã có vật cản từ lần nhận diện trước, phải kiểm tra lại vị trí vì hệ tọa độ ảnh có thể đã thay đổi.
6. Ở Bản vẽ mái hoặc Mô phỏng: kéo nút trắng tại đỉnh; kéo nút giữa cạnh để thêm đỉnh; bấm đôi đỉnh để bỏ (giữ ít nhất ba đỉnh). Có thể vẽ lại toàn biên. Biên tự cắt hoặc vùng nằm ngoài mái bị từ chối.
7. Chọn vật cản: kéo để di chuyển; kéo bốn góc để đổi kích thước; kéo nút tím để xoay. Bảng **Chỉnh hình học & cao độ** cho nhập số đo, đổi chữ nhật/tròn-bầu dục/đa giác, nhân đôi hoặc xóa. Đa giác có thể kéo từng đỉnh. **Hoàn tác / Làm lại** và Ctrl+Z / Ctrl+Shift+Z dùng ngoài ô nhập.
8. Dùng **Vẽ phần mái cao/thấp**, chấm vùng rồi **Khép biên**. Nhập cao độ tính từ mặt đất tại tâm vùng, độ dốc và hướng dốc; có thể tắt cho phép đặt pin. Dùng **Vẽ khoảng trống** cho sân trong/giếng trời. Các vùng cao/thấp không được chồng diện tích.
9. Khai báo nhà bên cạnh, khoảng cách, chiều cao, hướng Bắc và cao độ mái cơ sở. Xác nhận toàn bộ. Đổi giờ/ngày trong Mô phỏng để xem bóng; việc sửa hình học làm mất xác nhận và đánh dấu phương án cũ cần tính lại.
10. Tạo phương án, chạy kiểm tra, xuất JSON/SVG hoặc báo cáo PDF. Bản vẽ và số đo phải được kỹ sư đối chiếu trước khi trình bày như kết quả của mái thực.

## Mái cao thấp được biểu diễn đến đâu?

Mặt bằng hiển thị đường biên, khoảng trống, vùng màu riêng cho từng phần mái, tên/cao độ/độ dốc và vật cản theo hình dạng đã nhập. Bộ mô phỏng cho vùng cao đổ bóng xuống vùng thấp và lấy cao độ phần mái chứa tâm vật thể làm chân vật thể mặc định. Có thể nhập cao độ chân riêng cho trường hợp đặc biệt.

Chưa tự tìm đủ sườn mái, sống mái, độ cao và độ dốc từ ảnh. Các mặt mái được coi là những mặt phẳng và khối đỡ thẳng đứng; chưa dựng kết cấu mái cong, mái vòm hoặc liên kết 3D phức tạp. Tấm pin đang dùng kích thước trên mặt bằng ngang, chưa biến đổi kích thước chiếu bằng theo độ nghiêng. Ước lượng điện năng năm vẫn dùng dữ liệu nắng năm và chín thời điểm bóng đại diện, chưa phải mô phỏng điện từng giờ cả năm.

## Cách đo độ chính xác trước khi đi thi

Chọn ít nhất một mái có ảnh được phép sử dụng và bản vẽ/số đo đối chiếu. Đánh dấu biên đúng và vật cản đúng bằng tay, rồi ghi: tỷ lệ diện tích giao/hợp của biên, sai lệch chiều dài theo mét, vật cản bỏ sót/nhận nhầm, sai lệch vị trí, số phút kỹ sư phải sửa. Tách kết quả AI ban đầu và kết quả sau khi sửa. Kiểm thử ảnh tự tạo chỉ chứng minh thuật toán và hệ tọa độ vận hành; không dùng thay cho kết quả trên mái thật.
