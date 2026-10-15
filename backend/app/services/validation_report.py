"""Offline HTML report; all supplied text is escaped, no external assets."""
from html import escape

LABELS={'SYNTHETIC_PASS':'Đạt ca nhân tạo','WITHIN_DECLARED_TOLERANCES':'Trong dung sai khai báo',
        'OUTSIDE_TOLERANCES':'Vượt dung sai','INCOMPLETE':'Chưa đủ dữ liệu'}
STAGES={'ai_initial':'Đề xuất AI ban đầu','engineer_corrected':'Sau khi kỹ sư sửa','simulation':'Mô phỏng hình học'}


def number(value,digits=3):
    return 'Chưa có' if value is None else f'{value:,.{digits}f}'


def _path(regions):
    parts=[]
    for region in regions:
        for ring in [region['boundary'],*region['openings']]:
            parts.append('M'+' L'.join(f'{x:.6f},{-y:.6f}' for x,y in ring)+'Z')
    return ''.join(parts)


def overlay(a,b):
    coords=[p for region in a+b for p in region['boundary']]
    if not coords:return '<p>Cả hai vùng đều rỗng.</p>'
    xs=[p[0] for p in coords];ys=[-p[1] for p in coords]
    w,h=max(xs)-min(xs),max(ys)-min(ys);pad=max(w,h,1)*.08
    view=f'{min(xs)-pad} {min(ys)-pad} {w+2*pad} {h+2*pad}'
    return f'<svg viewBox="{view}" role="img" aria-label="Lớp đối chiếu cùng tọa độ mét"><path d="{_path(b)}" fill="#26a5ad22" stroke="#18818b"/><path d="{_path(a)}" fill="#db9b2222" stroke="#bb7811" stroke-dasharray="5 3"/></svg>'


def render_report(results,created_at):
    synthetic=sum(r['kind']=='synthetic' for r in results)
    field=len(results)-synthetic
    field_ready=sum(r['kind']=='field' and not r['missing'] for r in results)
    cards=[]
    for case in results:
        title=escape(case['label']);source=escape(case['reference_source'])
        roof=case['roof'];energy=case['energy']
        roof_html='<p>Chưa có biên mái độc lập để đối chiếu.</p>'
        if roof:
            roof_html=f'''<div class="metrics"><div>Trùng diện tích mái<strong>{number(100*roof['iou'],2)}%</strong></div><div>Lệch biên xấp xỉ<strong>{number(roof['boundary_error_m'])} m</strong></div><div>Diện tích dự đoán / chuẩn<strong>{number(roof['predicted_area_m2'],2)} / {number(roof['reference_area_m2'],2)} m²</strong></div></div>'''
        shadow_html=''
        for sample in case['shadows']:
            shadow_html+=f'''<div class="shadow"><h4>{escape(sample['label'])}</h4><p>Trùng vùng bóng: <b>{number(100*sample['iou'],2)}%</b> · diện tích dự đoán / chuẩn: {number(sample['predicted_area_m2'],2)} / {number(sample['reference_area_m2'],2)} m²</p>{overlay(sample['predicted_regions'],sample['reference_regions'])}<p class="small">Nguồn: {escape(sample['source'])}</p></div>'''
        energy_html='<p>Chưa đối chiếu sản lượng.</p>' if not energy else f'''<p>Điện năng dự đoán / chuẩn: <b>{number(energy['predicted_kwh'],2)} / {number(energy['reference_kwh'],2)} kWh/năm</b> · sai lệch {number(energy['error_pct'],3)}%.<br>Nguồn: {escape(energy['source'])}</p>'''
        missing=''.join(f'<li>{escape(item)}</li>' for item in case['missing'])
        state=case['status'];tone='bad' if state=='OUTSIDE_TOLERANCES' else 'pending' if state=='INCOMPLETE' else 'ok'
        files=''.join(f'<li>{escape(name)}</li>' for name in case['evidence_files'])
        evidence=f"<details><summary>Thông tin hồ sơ khai báo</summary><p>Người đối chiếu: {escape(case['reviewed_by'] or 'Chưa có')}. Công cụ chưa tự xác minh nội dung các tệp nguồn.</p><ul>{files}</ul></details>"
        cards.append(f'''<article><div class="heading"><h2>{title}</h2><span class="badge {tone}">{LABELS[state]}</span></div><p class="small">{'Dữ liệu nhân tạo' if case['kind']=='synthetic' else 'Ca chờ đối chiếu mái thật' if case['missing'] else 'Mái thật do người nhập khai báo'} · giai đoạn: {STAGES[case['stage']]}</p><p>{source}</p>{evidence}<h3>Biên mái</h3>{roof_html}{overlay(case['predicted_roof'],case['reference_roof'])}<h3>Bóng che</h3>{shadow_html or '<p>Chưa có bóng tham chiếu.</p>'}<h3>Điện năng</h3>{energy_html}{'<h3>Còn thiếu</h3><ul>'+missing+'</ul>' if missing else ''}<p class="scope">{escape(case['scope'])}</p></article>''')
    return '''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SolarOpt — đối chiếu bộ tính</title><style>
*{box-sizing:border-box}body{margin:0;background:#f2f6ef;color:#264b3c;font:15px/1.7 system-ui,sans-serif}main{max-width:1080px;margin:auto;padding:35px 22px}header{background:#184e3b;color:#fff;padding:28px;border-radius:16px}h1{font-size:28px;margin:4px 0}header p{color:#d5e8da}h2{font-size:21px;margin:0}h3{font-size:17px;margin:24px 0 10px}h4{font-size:15px;margin:12px 0}.heading{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap}article{background:white;padding:26px;border:1px solid #dce7d7;border-radius:14px;margin-top:22px}.badge{font-size:12px;padding:5px 10px;border-radius:6px}.ok{background:#e6f2e2;color:#346d40}.pending{background:#fff0cd;color:#825f20}.bad{background:#fce5dc;color:#9c4031}.small{font-size:12px;color:#61776b}.metrics{display:flex;flex-wrap:wrap;gap:20px;background:#f4f8f0;padding:15px;border-radius:8px}.metrics>div{font-size:12px;flex:1;min-width:160px}strong{display:block;font-size:19px;margin-top:4px}svg{display:block;width:100%;height:240px;background:#f7f9f4;border-radius:8px;margin:15px 0}svg path{stroke-width:2;vector-effect:non-scaling-stroke;fill-rule:evenodd}.scope{border-left:3px solid #d5ac52;padding:8px 12px;font-size:13px;background:#fcf8ec}.legend{margin:18px 0}.legend span{margin-right:18px}.legend b{display:inline-block;width:12px;height:12px;margin-right:6px}.note{background:#fff4d8;padding:16px;border-radius:9px}.shadow{border-top:1px solid #e7eee1;padding-top:6px}footer{font-size:12px;margin:24px 0;color:#61776b}@media(max-width:600px){main{padding:16px 10px}article,header{padding:18px}h1{font-size:24px}svg{height:210px}}
</style><main><header><p>SOLAROPT · KIỂM CHỨNG BỘ TÍNH</p><h1>Đối chiếu bằng dữ liệu có nguồn</h1><p>'''+f'{synthetic} ca nhân tạo · {field_ready} ca mái thật đủ dữ liệu khai báo · {field-field_ready} ca chờ bổ sung · {escape(created_at)}'+'''</p></header><p class="note">Ca nhân tạo kiểm tra thuật toán, không chứng minh độ chính xác trên mái thật. Các nguồn, người đối chiếu và dung sai trong báo cáo do người nhập khai báo. Không tự dịch, xoay hoặc co giãn dữ liệu để làm kết quả đẹp hơn.</p><p class="legend"><span><b style="background:#18818b"></b>Tham chiếu</span><span><b style="background:#bb7811"></b>SolarOpt</span></p>'''+''.join(cards)+'''<footer>Lệch biên dùng khoảng cách Hausdorff rời rạc có chia nhỏ cạnh, là số xấp xỉ. Hệ tọa độ mặt bằng theo mét; không phải kiểm định đo đạc hoặc chứng nhận thi công. Báo cáo hoạt động ngoại tuyến.</footer></main></html>'''
