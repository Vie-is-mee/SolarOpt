"""Actions grounded in failed checks; advice never changes or re-runs a layout."""
import math


def recommendations(sid, req, cfg, panel, checks):
    failures={c.id for c in checks}
    advice=[]
    if 'geometry_confirmation' in failures:
        advice.append('Đối chiếu và xác nhận biên mái, hướng Bắc cùng vị trí/chiều cao vật cản trước khi kết luận phương án đạt.')
    if {'shadow','shadow_samples'} & failures:
        advice.append('Kiểm tra tấm bị bóng được đánh dấu, xác nhận chiều cao vật cản và so các giờ/ngày khác. Cân nhắc chuyển hoặc bỏ tấm, rồi tính lại; cảnh báo bóng không được tính là đạt không cảnh báo.')
    if 'roof_boundary' in failures:
        if sid=='roof2':
            advice.append('Đo lại biên và hai kích thước mái. Nếu số đo nhỏ hơn, cập nhật ở bước Dữ liệu rồi tính lại; không sửa số đo để giữ bố trí cũ.')
        elif sid=='panel1':
            advice.append(f'Đối chiếu kích thước lớn nhất trong datasheet: kịch bản đang thử {panel.width_m:.3f} × {panel.height_m:.3f} m. Nhập kích thước này hoặc chừa dự phòng rồi tính lại.')
        elif sid=='setback':
            advice.append(f'Bố trí mới cần chịu được lùi mép {cfg.setback_m:.2f} m trong kịch bản này. Tăng dự phòng hoặc dùng mức lùi mép đó khi tính lại; kỹ sư xác nhận yêu cầu thực tế.')
        else:
            advice.append('Kiểm tra lại biên mái và các tấm được đánh dấu; di chuyển hoặc bỏ các tấm vượt vùng cho phép, rồi tính và kiểm chứng lại.')
    if 'obstacle_clearance' in failures:
        advice.append('Đo và xác nhận lại vị trí, mặt bằng vật cản; tăng khoảng cách tránh vật cản nếu cần, rồi tính lại bố trí.')
    if {'panel_overlap','panel_gap'} & failures:
        advice.append('Tăng khe giữa tấm theo kích thước lớn nhất thực tế; tính lại để các tấm không chồng nhau.')
    if 'budget' in failures:
        cost=len(req.design.panels)*panel.price_vnd
        remove=math.ceil(max(0,cost-cfg.budget_vnd)/panel.price_vnd) if panel.price_vnd>0 else 0
        advice.append(f'Ngân sách kịch bản còn {cfg.budget_vnd:,.0f} đ. Cần giảm ít nhất {remove} tấm với đơn giá hiện tại, hoặc xác nhận ngân sách mới rồi tính lại.')
    if {'panel_data','result_consistency'} & failures:
        advice.append('Đối chiếu model, kích thước, đơn giá và thông số điện tấm pin; nhập dữ liệu đúng rồi tính lại toàn bộ phương án.')
    if {'energy','solver'} & failures:
        advice.append('Kiểm tra dữ liệu nắng, vật cản và vùng mái khả dụng. Nếu không còn vị trí phù hợp, báo không khả thi thay vì giảm ràng buộc bắt buộc.')
    if 'energy_target' in failures:
        advice.append('Sản lượng trong tình huống này chưa đủ nhu cầu đã nhập. Kiểm tra nguồn nắng và tăng công suất trong giới hạn mái/ngân sách, hoặc xác nhận lại nhu cầu thực; không tự hạ mục tiêu để đổi thành Đạt.')
    if advice:
        advice.append('Sau khi chỉnh, chạy lại kiểm chứng và cả 8 tình huống. Đề xuất này chưa chứng minh phương án mới sẽ đạt.')
    return advice
