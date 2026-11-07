# Accounts and private history

SolarOpt uses the existing SQLite database; no external auth or database service is required. Schema additions run automatically at backend startup and preserve existing versions.

Use **Đăng nhập / Đăng ký** above the workspace to open the dedicated auth popup and create an account with an email and a password of 10–128 characters. Signed-in design generation, repair, and approval save versions to that account. History shows the latest 50 versions across all projects; restoring a version also restores its source evidence. Guest calculations remain available but do not save server history. Approval requires login.

Browser drafts and image evidence are separated by account. They remain on that browser; saved server versions are available after login on another device. Existing guest drafts remain under the guest profile. Historical versions without an owner remain in the database and are not assigned to new accounts automatically.

## Configuration

- `SOLAROPT_DB_PATH`: SQLite file, default `backend/solaropt.db`. Existing backup and restore scripts cover accounts, sessions, and history together.
- `SOLAROPT_COOKIE_SECURE=true`: required for HTTPS hosting; already enabled in Docker Compose. Leave false for local HTTP development.
- Serve frontend and API on the same site through the existing Vite/Caddy proxy. For separate origins, explicitly allow the frontend in `CORS_ORIGINS`; wildcard origins are not supported with credentials. The request header `X-SolarOpt-Request: 1` is required for auth mutations and authenticated writes. Workspace requests also send `X-SolarOpt-User` with the displayed user ID or `guest`; the API rejects a mismatch with the cookie session before reading or saving history.

Passwords use salted scrypt hashes. Opaque session tokens are stored as SHA-256 hashes, expire after seven days, and are revoked on logout. Cookies use HttpOnly and SameSite=Lax. Login and registration share a persisted limit of 30 attempts per client IP per 15 minutes. Behind a proxy, configure trusted forwarding correctly; otherwise users may share a rate-limit bucket. Email verification and password recovery are not included in this lightweight implementation.

## API

- `POST /api/auth/register`, `POST /api/auth/login`: JSON `{ "email": "user@example.com", "password": "your-long-password" }`; return user ID/email and set session cookie.
- `GET /api/auth/me`: current user, or 401.
- `POST /api/auth/logout`: revoke current session and clear cookie.
- `GET /api/history`: latest 50 account-owned versions across projects.
- Existing project version list/detail endpoints now require login and enforce ownership; another user's version returns 404.

Reference: [Python scrypt](https://docs.python.org/3/library/hashlib.html#hashlib.scrypt), [Starlette cookie options](https://www.starlette.dev/responses/#set-cookie).

The popup supports Escape, backdrop dismissal, keyboard focus containment and a guest-mode action. Dismissal is disabled while an auth request is pending. See [Vercel deployment assessment](VERCEL_DEPLOYMENT.md) before deploying the SQLite-backed API to serverless hosting.

Account changes are synchronized between tabs and revalidated on focus. Expired or revoked sessions return 401 instead of silently downgrading a signed-in calculation to an unsaved guest calculation. Invalid cookies are cleared, and the UI offers login again. Browser drafts remain under their original account key.


## Gói theo dự án, phí lưu trữ và hạn mức

Mã: `backend/app/billing.py`, giao diện `frontend/src/components/PlanCenter.tsx`. Giá do sáng lập viên đặt ngày 07/11/2026; so sánh đối thủ và chi phí: [GIA_VA_CHI_PHI_THUONG_MAI.md](GIA_VA_CHI_PHI_THUONG_MAI.md).

| Gói (mã) | Giá | Chu kỳ | Dự án / chu kỳ | Ghế | AI đọc ảnh / câu hỏi trợ lý mỗi chu kỳ |
|---|---|---|---|---|---|
| Khách (chưa đăng nhập) | 0 đ | ngày | 2 dự án/ngày theo IP (`SOLAROPT_GUEST_DAILY_PROJECTS`) | — | Không (trợ lý trả lời bằng bộ quy tắc) |
| Dùng thử (`free`) | 0 đ | trọn đời | 1 dự án, dữ liệu giữ 7 ngày | 1 | 5 / 30 |
| Tháng · 1 dự án (`month_1`) | 5.990.000 đ | 30 ngày | 1 | 3 | 20 / 300 |
| Tháng · 2 dự án (`month_2`) | 7.990.000 đ | 30 ngày | 2 | 5 | 40 / 600 |
| Năm · 3 dự án (`year_3`) | 15.000.000 đ | 365 ngày | 3 | 5 | 60 / 900 |
| Năm · 7 dự án (`year_7`) | 30.000.000 đ | 365 ngày | 7 | 10 | 140 / 2.100 |

- **Chu kỳ tính từ ngày kích hoạt.** Gói tháng chỉ dùng trong 30 ngày đăng ký, gói năm trong 365 ngày; mua nhiều kỳ (ví dụ 3 tháng) thì mỗi 30 ngày cấp lại hạn mức. Dự án chưa dùng không cộng dồn.
- **Một lượt = một dự án mới được tính phương án thành công trong chu kỳ.** Dự án được nhận diện bằng **tên + vị trí (làm tròn ~1 km)**: giữ nguyên tên nhưng đổi sang mái ở nơi khác vẫn tính là dự án mới. Tính lại, sửa, so sánh 3 mục tiêu của cùng dự án trong chu kỳ không trừ thêm. Sang chu kỳ sau, dự án cũ dùng tiếp sẽ trừ một lượt.
- **Lưu trữ dữ liệu dự án:** dữ liệu (ảnh, biên mái, phương án, bản duyệt) được giữ đến hết chu kỳ đã dùng dự án đó (dùng thử: 7 ngày). Sau đó phí là **1.000.000 đ / dự án / tháng**. Quá hạn **2 ngày** (`SOLAROPT_STORAGE_GRACE_DAYS`) không gia hạn: dự án bị ẩn khỏi tài khoản (API trả 410), rồi `python scripts/purge_expired_projects.py --apply` xóa hẳn các phiên bản và ghi ngày xóa (`project_storage.purged_at`). Chạy không có `--apply` để xem trước. Khách gửi yêu cầu gia hạn ở nút **Lưu trữ**; quản trị viên bấm **Ghi nhận đã thu** sau khi nhận tiền.
- **Quản trị viên không bị giới hạn** và dự án của quản trị viên không bao giờ hết hạn lưu trữ. Quyền lưu trong cột `users.role` và **chỉ cấp trên máy chủ**:
  `python scripts/manage_admin.py grant email@cua-ban.com` (chạy trong thư mục `backend`, cùng `SOLAROPT_DB_PATH` với máy chủ; tài khoản phải đăng ký trên web trước). `revoke` để thu hồi, `list` để xem. Không cấp qua API hay theo danh sách email, vì chưa có xác minh email nên ai đăng ký trước bằng email đó sẽ chiếm quyền.
- **Admin dùng chung cho máy local và web:** đặt `SOLAROPT_ADMIN_EMAIL` và `SOLAROPT_ADMIN_PASSWORD` (≥ 10 ký tự) giống nhau trong `backend/.env` và trên host; khi khởi động, máy chủ tự tạo tài khoản đó và cấp quyền admin.
- **Mua gói:** chưa tích hợp thanh toán. Khách bấm "Gửi yêu cầu mua gói"; quản trị viên liên hệ, xuất hóa đơn, rồi đặt gói 1/3/6/12 tháng (gói tháng) hoặc 1/2/3 năm (gói năm) ở trang Quản trị. Hết hạn tự về gói Dùng thử.
- **Nhóm công ty:** người dùng tạo nhóm và là chủ nhóm; mọi gói trả phí đều gắn được cho nhóm (quản trị viên đặt gói cho nhóm). Khi nhóm có gói còn hạn: thành viên dùng chung số dự án và xem chung lịch sử. Số chỗ theo cột Ghế.
- AI đọc ảnh trừ một lượt mỗi lần gọi nhà cung cấp; kết quả lấy từ bộ nhớ đệm không trừ. Hết lượt trợ lý AI thì trợ lý vẫn trả lời bằng bộ quy tắc.

**Lưu ý vận hành:** bản web trên Render gói miễn phí dùng ổ đĩa tạm, nên SQLite (tài khoản, lịch sử, dữ liệu lưu trữ) mất khi máy chủ khởi động lại. Phải chuyển sang cơ sở dữ liệu bền trước khi thu phí lưu trữ (kế hoạch trong GIA_VA_CHI_PHI_THUONG_MAI.md).

API: `GET /api/account/usage`, `POST /api/account/upgrade-request`, `GET /api/account/storage`, `POST /api/account/storage-request`, `GET|POST /api/team`, `POST /api/team/members`, `POST /api/team/members/{id}/remove`, `POST /api/team/leave`, `GET /api/admin/users`, `GET /api/admin/teams`, `GET|POST /api/admin/storage`, `POST /api/admin/users/{id}/plan`, `POST /api/admin/teams/{id}/plan` (`{"plan": "...", "periods": n}`).
