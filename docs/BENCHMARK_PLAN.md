# Kế hoạch benchmark SolarOpt

**Cập nhật 15/10/2026:** đã có [công cụ đối chiếu hình học, bóng và điện năng](STEP2_REFERENCE_VALIDATION.md), tách ca nhân tạo và ca mái thật. Đội chưa có bộ đối chiếu hiện trường. Kế hoạch hiệu năng bên dưới là công việc khác; tỷ lệ nút đồ thị phụ thuộc không phải thời gian tiết kiệm đã đo. Repair hiện chạy lại bố trí có ưu tiên giữ vị trí, chưa triển khai tính lại chọn lọc.

## Bộ scenario tối thiểu

- 5 mái × 5 thay đổi = 25 scenario (tối thiểu trước deadline).
- Tốt hơn: 10 mái × 5 = 50 scenario.

### 5 thay đổi
1. Chiều cao vật cản.
2. Kích thước mái.
3. Đổi model panel.
4. Giảm ngân sách.
5. Tăng setback.

## Baseline
- Full recompute.
- Incremental không preservation bonus.
- Full SolarOpt với Dependency Graph + Minimal Repair.

## KPI
- Runtime.
- Recomputation Ratio.
- Layout Preservation Rate.
- Panel count.
- Annual Energy.
- Constraint violations.
- Stress pass rate.
- Human escalations (khi bổ sung uncertainty module đầy đủ).

## Quy tắc báo cáo
- Không dùng số demo có kiểm soát như benchmark toàn hệ thống.
- Mọi số trong proposal/video phải có CSV hoặc log tương ứng.
