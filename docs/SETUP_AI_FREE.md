# Bật AI miễn phí cho SolarOpt Studio

Cập nhật ngày 10/10/2026. Đội đã cấu hình khóa riêng và kiểm thử Groq thật thành công trên một ảnh tự tạo; chưa đánh giá độ chính xác mái thật. Phần vẽ mái, nhập vật cản, tính mặt trời, bóng che, bố trí và kiểm tra vẫn hoạt động với dữ liệu nhập tay hoặc dự án mẫu có nhãn.

## Lựa chọn mặc định: Groq + Qwen

Đã tích hợp mô hình `qwen/qwen3.8-27b`. Mô hình đọc được ảnh và trả dữ liệu có cấu trúc; phù hợp với việc gợi ý biên mái, vật cản và đọc chữ trên bản vẽ. Đây là lựa chọn để thử nghiệm, chưa phải kết luận rằng mô hình chính xác hơn Gemini trên ảnh mái nhà của đội.

1. Tạo tài khoản ở [Groq Console](https://console.groq.com/keys), tạo khóa trên gói miễn phí. Xem hạn mức thực tế trong trang Limits của tài khoản.
2. Tạo `backend/.env` từ `backend/.env.example` nếu chưa có. Giữ lại các thiết lập khác, điền:

```dotenv
AI_PROVIDER=groq
AI_MODEL=qwen/qwen3.8-27b
GROQ_API_KEY=điền_khóa_của_bạn_tại_đây
```

3. Khởi động lại máy chủ Python. Tải lại website; mục AI sẽ hiển thị tên mô hình và cho phép đọc ảnh khi đã chọn tệp.
4. Dùng ảnh mái được phép sử dụng. Nhập chiều rộng, chiều sâu thật trước khi đọc ảnh. Xem đề xuất, áp dụng, chỉnh lại vị trí và chiều cao rồi xác nhận.

Khóa chỉ nằm ở máy chủ, không đưa vào mã giao diện, tệp dự án JSON hoặc tin nhắn. Chọn Groq đồng nghĩa ảnh dùng để phân tích được gửi tới dịch vụ này.

Theo [tài liệu giới hạn Groq](https://console.groq.com/docs/rate-limits), bảng miễn phí công bố cho mô hình này là 30 yêu cầu/phút, 1.000 yêu cầu/ngày, 8.000 đơn vị văn bản/phút và 200.000/ngày. Các giới hạn cùng áp dụng, không có nghĩa đọc được 1.000 bộ ảnh mỗi ngày: [mỗi ảnh đã chiếm 2.048 đơn vị đầu vào](https://console.groq.com/docs/vision), chưa kể câu hướng dẫn và câu trả lời. Giới hạn tài khoản có thể khác hoặc thay đổi.

SolarOpt thu nhỏ ảnh, ghép hai ảnh chi tiết thành một bảng ảnh khi cần, giới hạn câu trả lời và lưu lại tối đa 24 kết quả trong bộ nhớ máy chủ. Đọc lại đúng bộ ảnh, loại ảnh, số đo và mô hình sẽ dùng kết quả đã lưu. Bộ nhớ này mất khi khởi động lại máy chủ. Lỗi hạn mức 429 được báo rõ; ứng dụng không thay bằng kết quả nhận diện giả.

## Lựa chọn chạy trên máy: Ollama + Qwen3-VL

Không cần khóa hoặc hạn mức API đám mây. Cần tải mô hình, đủ bộ nhớ và thời gian xử lý; đây không phải tài nguyên tính toán miễn phí vô hạn. Bản `4b` có tệp tải khoảng 3,3 GB, bộ nhớ lúc chạy còn phụ thuộc ảnh và thiết lập. Xem [thư viện chính thức Ollama](https://ollama.com/library/qwen3-vl).

Sau khi cài Ollama, mở cửa sổ lệnh và chạy:

```powershell
ollama pull qwen3-vl:4b
```

Đảm bảo dịch vụ Ollama đang chạy. Nếu chưa chạy, mở một cửa sổ riêng:

```powershell
ollama serve
```

Sửa `backend/.env`, rồi khởi động lại máy chủ SolarOpt:

```dotenv
AI_PROVIDER=ollama
AI_MODEL=qwen3-vl:4b
OLLAMA_BASE_URL=http://127.0.0.1:11434
```

Website hiển thị cấu hình Ollama không đồng nghĩa mô hình đã được tải và dịch vụ đã sẵn sàng; nút đọc ảnh sẽ trả lỗi nếu chưa kết nối được. Phần tích hợp này chưa được chạy với mô hình thật trên máy hiện tại.

## Kiểm tra trước khi dùng để thuyết trình

- Chuẩn bị ảnh chụp thẳng xuống, bản vẽ có tỷ lệ hoặc ít nhất một số đo đã kiểm tra. Ảnh chụp xiên/một phần không đủ để tự suy ra toàn mái và độ cao.
- Dùng cùng ảnh để đối chiếu đề xuất AI với bản vẽ kỹ sư. Ghi số vật cản đúng/sai, sai lệch vị trí và thời gian xử lý; chưa công bố tỷ lệ chính xác nếu chưa đo.
- Không tự suy ra hướng Bắc hoặc chiều cao nhà bên cạnh từ một ảnh. Nhập hướng bản vẽ, cao độ mái, khoảng cách, mặt bằng và chiều cao công trình lân cận.
- Chiều cao AI không đọc được được trả về trống. Khi áp dụng, UI tạm đặt 1 m và yêu cầu kỹ sư sửa/xác nhận. Ảnh một phần luôn yêu cầu đặt lại vị trí.
- Đọc ảnh tốn yêu cầu AI; kéo giờ mặt trời, chỉnh vật cản, bố trí, kiểm tra và xuất bản vẽ đều dùng bộ tính toán, không gọi mô hình ngôn ngữ.

Giữ một dự án mẫu đã kiểm tra để trình diễn khi mạng hoặc hạn mức gặp vấn đề, và nói rõ đó là dữ liệu mẫu. Tích hợp API đã được kiểm thử bằng phản hồi mô phỏng và gọi Groq thật trên ảnh tự tạo; chưa xác nhận chất lượng trên bộ ảnh mái thật. Tách biên trực tiếp bằng OpenCV không tiêu tốn lượt Groq; xem [hướng dẫn ảnh và bản vẽ](ROOF_IMAGE_PIPELINE.md).
