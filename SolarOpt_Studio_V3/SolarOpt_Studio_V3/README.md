# SolarOpt Studio V3 — GenD Arena demo

Bản demo này được thiết kế lại theo hướng **phần mềm kỹ thuật sáng, rõ, dễ dùng**, lấy cảm hứng từ cách các công cụ solar/CAD chuyên nghiệp tổ chức quy trình: nhập dữ liệu và linh kiện trước, canvas thiết kế ở trung tâm, thuộc tính theo ngữ cảnh ở bên phải, nhiều phương án để so sánh, và mô phỏng/kiểm chứng tách khỏi phần chỉnh sửa.

## Những gì V3 đã thay đổi

- Có **upload file thật**: PNG, JPG, WEBP, SVG, PDF (≤ 12 MB).
- Tấm pin, inverter, ngân sách và mục tiêu tối ưu được đưa lên **bước đầu**, không giấu ở cuối.
- Mỗi màn hình có mô tả “đang làm gì” và “vì sao cần”.
- Canvas tương tác: bấm mái, vật cản, panel để xem thuộc tính/bằng chứng.
- `Why here?`: bấm một panel để xem sản lượng biên, bóng và trạng thái hình học.
- `Why not here?`: chọn công cụ rồi bấm vùng trống để xem lý do loại vị trí.
- **Impact-aware uncertainty**: bất định nhỏ tự tiếp tục; có nút tạo case ảnh hưởng lớn để thấy AI buộc phải hỏi kỹ sư.
- **Solar Time Machine**: kéo thời gian để vùng bóng thay đổi trực quan.
- **What-if Lab**: tăng chiều cao bồn nước hoặc thay loại panel để kích hoạt Change Impact → Verify → Repair.
- **Stress-test** 8 tình huống, từng dòng có thể bấm để xem chi tiết.
- **Change Impact graph**: các nút phụ thuộc có trạng thái IDLE / DIRTY / VERIFIED và có giải thích khi bấm.
- **Version Diff**: mỗi lần redesign tạo phiên bản mới.
- **Ba phương án**: Tối đa sản lượng / Cân bằng khuyến nghị / Ưu tiên độ bền.

> Lưu ý: phần năng lượng, bóng và điện trong demo là mô hình nhẹ để chứng minh luồng sản phẩm/Agent. Không dùng kết quả này làm hồ sơ thi công hoặc chứng nhận kỹ thuật.

## Cài bằng Miniconda

```bash
conda env create -f environment.yml
conda activate solaropt-studio
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Mở:

```text
http://127.0.0.1:8000
```

### Nếu không muốn tạo môi trường Conda

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Kịch bản demo khuyến nghị

### 1. Thiết lập

- Có thể upload file riêng hoặc dùng bản vẽ mẫu.
- Giữ A–B = `5.40 m`.
- Panel: `LONGi Hi-MO 6 580W`.
- Mục tiêu: `Cân bằng`.
- Nhấn **Phân tích mái & kiểm tra dữ liệu**.

### 2. Kiểm tra mái

- Bấm từng vật cản trong danh sách hoặc trực tiếp trên canvas.
- Bấm `Vật thể chưa xác định` để xem confidence 52% nhưng impact thấp.
- Nhấn **Xem trường hợp bất định đủ lớn...** để kích hoạt một case mà AI phải dừng hỏi kỹ sư.
- Sau đó nhấn **Xác nhận & chạy Autopilot**.

### 3. Design Studio

- Bấm một tấm pin → `Why here?` hiện dữ liệu backend.
- Chọn công cụ `Vì sao không?` → bấm vùng trống trên mái.
- Kéo `Solar Time Machine` để xem bóng thay đổi theo giờ.
- Mở tab `Autopilot` ở bảng phải để xem chuỗi hành động.

### 4. What-if Lab — novelty chính

Mở **What-if Lab**:

**Case A — thay đổi hiện trường**

- Bồn nước: `1.2 m → 1.8 m`.
- Nhấn **Áp dụng & để SolarOpt tự phục hồi**.
- Xem các event `CHANGE → IMPACT → FAIL → REPAIR → FINAL`.
- Backend ưu tiên giữ layout cũ và chỉ thay vị trí cần thiết.

**Case B — hết hàng panel**

- Chọn `Trina Vertex N 600W`.
- Nhấn **Thay linh kiện & tự thiết kế lại**.
- Mở màn Kiểm chứng để xem các node phụ thuộc đã được cập nhật.

### 5. Kiểm chứng & so sánh

- So ba phương án.
- `Cân bằng khuyến nghị` và `Ưu tiên độ bền` được thiết kế để đạt toàn bộ stress-test của bộ demo.
- Bấm từng stress scenario để xem vi phạm.
- Bấm từng node Change Impact để xem nó phụ thuộc vào gì.
- Version Diff cho thấy lịch sử thay đổi.

## Source structure

```text
SolarOpt_Studio_V3/
├── app/
│   ├── main.py
│   ├── engine/
│   │   ├── dependency.py
│   │   ├── geometry.py
│   │   ├── models.py
│   │   ├── optimizer.py
│   │   ├── orchestrator.py
│   │   ├── solar.py
│   │   └── verifier.py
│   ├── static/
│   │   ├── index.html
│   │   ├── styles.css
│   │   └── app.js
│   └── uploads/
├── demo_input/
│   ├── roof_blueprint.svg
│   └── project.json
├── tests/
├── environment.yml
└── requirements.txt
```

## Backend endpoints chính

- `POST /api/upload`
- `POST /api/configure`
- `POST /api/autopilot`
- `POST /api/uncertainty`
- `POST /api/change/tank-height`
- `POST /api/change/panel`
- `POST /api/design/select`
- `GET /api/state`

## Tests

```bash
pytest -q
```

Bản đóng gói hiện tại đã được kiểm tra với toàn bộ test hiện có.
