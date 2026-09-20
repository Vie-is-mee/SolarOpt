# Tạo Gemini API key miễn phí cho SolarOpt

## Mô hình mặc định

```text
gemini-2.5-flash-lite
```

SolarOpt chỉ gọi Gemini ở bước Vision/OCR. Tối ưu, hình học, kiểm chứng và tự phục hồi không phụ thuộc mô hình ngôn ngữ.

## Các bước

1. Mở Google AI Studio: https://aistudio.google.com/
2. Đăng nhập tài khoản Google.
3. Vào Dashboard → API Keys.
4. Tạo API key mới. Các key mới hiện được Google tạo theo cơ chế auth key.
5. Copy key.
6. Trong source, copy:

```text
backend/.env.example
```

thành:

```text
backend/.env
```

7. Điền:

```env
GEMINI_API_KEY=PASTE_KEY_HERE
GEMINI_MODEL=gemini-2.5-flash-lite
```

8. Khởi động lại backend.
9. Mở `http://localhost:8000/api/health`. `gemini_configured` phải là `true`.

## Bảo mật

- Không điền key trong frontend.
- Không lưu key vào localStorage.
- Không commit `.env` lên GitHub.
- Không quay key trong video demo.
- Nếu key từng bị lộ, revoke và tạo key mới.

## Free tier

Google hiện công bố Gemini 2.5 Flash-Lite có bậc miễn phí cho text/image/video input và output, nhưng quota/rate limit có thể thay đổi. Kiểm tra trang pricing và rate limits trước ngày quay demo.

- Pricing: https://ai.google.dev/gemini-api/docs/pricing
- API key: https://ai.google.dev/gemini-api/docs/api-key
- Models: https://ai.google.dev/gemini-api/docs/models
- Rate limits: https://ai.google.dev/gemini-api/docs/rate-limits

Lưu ý: dữ liệu gửi ở free tier có điều khoản sử dụng dữ liệu riêng của Google. Chỉ dùng ảnh/bản vẽ demo hoặc dữ liệu được phép dùng; không gửi bản vẽ mật của khách hàng.
