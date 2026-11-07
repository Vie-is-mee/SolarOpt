"""Build the SolarOpt cost, pricing and cash-flow workbook (output/report/SolarOpt_Mo_hinh_tai_chinh_v2.xlsx).

Every result is an Excel formula over the input cells, so the team can change a price, a model or a forecast and
the workbook recalculates. Blue = input, black = formula, green = link to another sheet, yellow fill = key
assumption to validate. Token counts come from scripts/measure_cost.py (04/11/2026); prices and competitor figures
carry their source and reading date next to them.
    python scripts/build_cost_model.py        (then open in Excel, or recalculate, before reading cached values)
"""
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as col
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

OUT = Path(__file__).resolve().parents[2] / "output" / "report" / "SolarOpt_Mo_hinh_tai_chinh_v2.xlsx"
FONT = "Arial"
BLUE, BLACK, GREEN, GREY = "0000FF", "000000", "008000", "666666"
YELLOW = PatternFill("solid", fgColor="FFFF00")
HEAD = PatternFill("solid", fgColor="E6F0E1")
TITLE = PatternFill("solid", fgColor="1F5E3F")
THIN = Border(bottom=Side(style="thin", color="C9D6C3"))
VND, PCT, NUM, USD = '#,##0;(#,##0);"-"', '0.0%;(0.0%);"-"', '#,##0.00;(#,##0.00);"-"', '#,##0.00'

wb = Workbook()
names: dict[str, str] = {}


def font(color=BLACK, bold=False, size=10, italic=False):
    return Font(name=FONT, color=color, bold=bold, size=size, italic=italic)


def name(ws, ref: str, label: str):
    """Workbook-level name for an absolute cell, e.g. FX_USD -> Gia_dinh!$B$5."""
    c, r = ref.rstrip("0123456789"), ref[len(ref.rstrip("0123456789")):]
    wb.defined_names[label] = DefinedName(label, attr_text=f"{ws.title}!${c}${r}")
    names[label] = f"{ws.title}!{ref}"


def put(ws, ref, value, color=BLACK, fmt=None, bold=False, fill=None, note=None, wrap=False, size=10, italic=False):
    cell = ws[ref]
    cell.value = value
    cell.font = font(color, bold, size, italic)
    if fmt:
        cell.number_format = fmt
    if fill:
        cell.fill = fill
    if note:
        cell.comment = Comment(note, "SolarOpt")
    if wrap:
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    return cell


def title(ws, text, sub):
    ws["A1"].value = text
    ws["A1"].font = Font(name=FONT, bold=True, size=14, color="FFFFFF")
    ws["A1"].fill = TITLE
    ws["A2"].value = sub
    ws["A2"].font = font(GREY, italic=True)


def header(ws, row, labels, start=1):
    for i, text in enumerate(labels):
        c = ws.cell(row=row, column=start + i, value=text)
        c.font = font(bold=True)
        c.fill = HEAD
        c.alignment = Alignment(wrap_text=True, vertical="center")


def widths(ws, values):
    for i, w in enumerate(values, 1):
        ws.column_dimensions[col(i)].width = w


# ------------------------------------------------------------------------------------------------
# Huong_dan
# ------------------------------------------------------------------------------------------------
ws = wb.active
ws.title = "Huong_dan"
title(ws, "SolarOpt — Mô hình chi phí, giá gói theo dự án và dòng tiền (bản 2)", "Lập 07/11/2026 · đơn vị VND · tháng 1 của dòng tiền = 01/2027 · thay bản 04/11/2026 (gói theo khách)")
rows = [
    ("Cách dùng", ""),
    ("1", "Chỉ sửa ô CHỮ XANH (đầu vào). Ô chữ đen là công thức; chữ xanh lá là liên kết sang sheet khác."),
    ("2", "Ô NỀN VÀNG là giả định then chốt chưa có dữ liệu thật: phải kiểm chứng bằng phỏng vấn khách / pilot trước khi đưa lên slide."),
    ("3", "Đổi mô hình AI cho từng tính năng ở Gia_dinh (ô chọn danh sách). Đổi giá gói ở sheet Goi cột C. Đổi dự báo số lượt mua ở Dong_tien (dòng chữ xanh)."),
    ("4", "Kết quả: Tong_hop (năm 1–3, tháng có lãi, tiền mặt thấp nhất), Goi (lãi gộp từng gói), Doi_thu (so giá đối thủ), Chi_phi_du_an (chi phí biến đổi 1 dự án)."),
    ("", ""),
    ("Thay đổi so với bản 04/11", "Gói bán theo SỐ DỰ ÁN (tháng: 1–2 dự án; năm: 3–7 dự án) thay cho gói theo khách; thêm phí lưu trữ dữ liệu dự án; AI dùng mô hình trả phí đủ mạnh (mặc định Claude Sonnet 5.5 cho đọc ảnh và tư vấn, Claude Haiku 5.5 cho trợ lý); thêm chi phí ảnh vệ tinh, cơ sở dữ liệu bền + sao lưu ngoài, email thông báo, bảo hiểm trách nhiệm, tuân thủ Luật Bảo vệ dữ liệu cá nhân, kỹ sư kết cấu cố vấn; thêm bảng giá đối thủ."),
    ("Nguồn số đo", "Token AI và giây CPU: backend/scripts/measure_cost.py chạy 04/11/2026 trên 5 mái mẫu (output/report/cost_measurements_2026-11-04.json)."),
    ("Nguồn giá", "Ghi cạnh từng ô (cột Nguồn). Tỷ giá Vietcombank bán ra 13:30 07/11/2026 (webgia.com); CHF và INR không đọc được, là giả định."),
    ("Giới hạn", "Số lượt mua gói, tỷ lệ dùng hạn mức, tỷ lệ trả phí lưu trữ, CAC, gia hạn là GIẢ ĐỊNH chưa có dữ liệu pilot. Bảo hiểm, pháp lý, lương là ước tính cần báo giá. Giá đối thủ lấy từ trang chính hãng khi đọc được, còn lại từ trang bên thứ ba (ghi rõ)."),
    ("", ""),
    ("Ví dụ màu", ""),
]
for i, (a, b) in enumerate(rows, 4):
    put(ws, f"A{i}", a, bold=bool(a) and not a.isdigit())
    put(ws, f"B{i}", b, wrap=True)
r = 4 + len(rows)
put(ws, f"A{r}", "Chữ xanh = đầu vào", BLUE)
put(ws, f"A{r+1}", "Nền vàng = giả định then chốt", fill=YELLOW)
put(ws, f"A{r+2}", "Chữ xanh lá = liên kết sheet khác", GREEN)
put(ws, f"A{r+3}", "Ví dụ dòng nhập: gói Năm · 3 dự án, giá 15.000.000 đ, 12 tháng, 3 dự án, khách dùng 80% hạn mức.", GREY, italic=True)
widths(ws, [26, 120])

# ------------------------------------------------------------------------------------------------
# Gia_dinh (assumptions)
# ------------------------------------------------------------------------------------------------
g = wb.create_sheet("Gia_dinh")
title(g, "Giả định đầu vào", "Chữ xanh = sửa được · Nền vàng = giả định then chốt cần kiểm chứng")
widths(g, [52, 16, 16, 12, 70])
header(g, 4, ["Tỷ giá (Vietcombank bán ra)", "VND", "", "", "Nguồn"])
fx = [("USD", 25780, "webgia.com/ty-gia/vietcombank, 13:30 07/11/2026", False),
      ("EUR", 29332, "như trên", False),
      ("AUD", 17874, "như trên", False),
      ("CHF", 31500, "GIẢ ĐỊNH: dòng CHF trên trang lỗi; tra lại trước khi trình bày", True),
      ("INR", 295, "GIẢ ĐỊNH: trang không hiện INR; tra lại", True)]
for i, (cur, v, src, assumed) in enumerate(fx, 5):
    put(g, f"A{i}", cur)
    put(g, f"B{i}", v, BLUE, VND, fill=YELLOW if assumed else None)
    put(g, f"E{i}", src, GREY)
    name(g, f"B{i}", f"FX_{cur}")
FX_CODES, FX_VALUES = "Gia_dinh!$A$5:$A$9", "Gia_dinh!$B$5:$B$9"

header(g, 11, ["Mô hình AI", "Vào (USD/1M token)", "Ra (USD/1M token)", "", "Nguồn"])
models = [("Claude Haiku 5.5", .10, .50, "Anthropic, bảng giá Claude API (bản lưu 06/10/2026)"),
          ("Claude Sonnet 5.5", 2.00, 10.00, "như trên"),
          ("Claude Opus 5.5", 4.00, 20.00, "như trên"),
          ("Gemini 3.5 Flash-Lite", .30, 2.50, "aistudio.google.com/docs/pricing, đọc 04/11/2026 (mô hình đang chạy)"),
          ("Gemini 3.6 Flash (từ 01/01/2027)", 1.50, 7.50, "như trên; giá tăng gấp đôi từ 01/01/2027"),
          ("GPT-5 mini", .25, 2.00, "Trang tổng hợp giá (pricepertoken, anotherwrapper) 11/2026 — đối chiếu trang OpenAI trước khi dùng")]
for i, (m, pin, pout, src) in enumerate(models, 12):
    put(g, f"A{i}", m)
    put(g, f"B{i}", pin, BLUE, USD)
    put(g, f"C{i}", pout, BLUE, USD)
    put(g, f"E{i}", src, GREY)
MODEL_NAMES, MODEL_IN, MODEL_OUT = "Gia_dinh!$A$12:$A$17", "Gia_dinh!$B$12:$B$17", "Gia_dinh!$C$12:$C$17"
dv = DataValidation(type="list", formula1="=$A$12:$A$17", allow_blank=False)
g.add_data_validation(dv)
choices = [("Mô hình đọc ảnh mái (AI đọc ảnh)", "Claude Sonnet 5.5", "VISION_MODEL"),
           ("Mô hình tư vấn từ hóa đơn (agent gọi công cụ)", "Claude Sonnet 5.5", "ADVISOR_MODEL"),
           ("Mô hình trợ lý hỏi đáp", "Claude Haiku 5.5", "CHAT_MODEL")]
for i, (label, m, n) in enumerate(choices, 19):
    put(g, f"A{i}", label)
    put(g, f"B{i}", m, BLUE, fill=YELLOW, note="Chọn trong danh sách A12:A17. Phải chạy bộ đánh giá trên 30–50 mái thật trước khi đổi mô hình trong máy chủ.")
    dv.add(f"B{i}")
    name(g, f"B{i}", n)
put(g, "E19", "Đọc ảnh và tư vấn quyết định số tấm/kWp: dùng mô hình mạnh; số lượt ít nên chi phí nhỏ.", GREY)
put(g, "E21", "Trợ lý hỏi đáp nhiều lượt, câu ngắn: mô hình nhỏ đủ dùng.", GREY)
put(g, "A22", "Hệ số quy đổi token theo mô hình mới")
put(g, "B22", 1.3, BLUE, NUM, fill=YELLOW, note="Token đo trên mô hình khác; tokenizer mới có thể dùng tới 1,35 lần số token.")
name(g, "B22", "TOKEN_FACTOR")
put(g, "A23", "Hệ số an toàn (gọi lại, hỏi nhiều hơn mẫu)")
put(g, "B23", 1.5, BLUE, NUM, note="Đo 04/11: 4/23 lượt bị 429 phải gọi lại.")
name(g, "B23", "SAFETY")

header(g, 25, ["Token đo thật mỗi lượt (04/11/2026)", "Token vào", "Token ra", "", "Ghi chú"])
tokens = [("AI đọc ảnh (1–2 ảnh)", 2230, 4497, "VISION", "2 lượt đo; 85% token ra là suy luận"),
          ("Trợ lý hỏi đáp (1 câu)", 2829, 341, "CHAT", "7 câu đo; 1,29 lượt gọi mô hình/câu"),
          ("Tư vấn từ hóa đơn (1 lượt)", 9369, 1988, "ADVISOR", "2 lượt đo; 4 lượt gọi mô hình/lượt")]
for i, (label, tin, tout, key, note) in enumerate(tokens, 26):
    put(g, f"A{i}", label)
    put(g, f"B{i}", tin, BLUE, VND)
    put(g, f"C{i}", tout, BLUE, VND)
    put(g, f"E{i}", note, GREY)
    name(g, f"B{i}", f"{key}_IN")
    name(g, f"C{i}", f"{key}_OUT")

header(g, 30, ["Số lượt AI mỗi dự án", "Dự kiến", "Tối đa theo hạn mức", "", "Ghi chú"])
uses = [("AI đọc ảnh", 5, 20, "VISION", "Gói cấp 20 lượt đọc ảnh/dự án"),
        ("Trợ lý hỏi đáp", 40, 300, "CHAT", "Gói cấp 300 câu/dự án"),
        ("Tư vấn từ hóa đơn", 3, 10, "ADVISOR", "")]
for i, (label, exp, mx, key, note) in enumerate(uses, 31):
    put(g, f"A{i}", label)
    put(g, f"B{i}", exp, BLUE, NUM, fill=YELLOW)
    put(g, f"C{i}", mx, BLUE, NUM)
    put(g, f"E{i}", note, GREY)
    name(g, f"B{i}", f"{key}_USES")
    name(g, f"C{i}", f"{key}_MAX")

header(g, 35, ["Ảnh vệ tinh / ảnh mái", "Miễn phí/tháng (ô ảnh)", "USD/1.000 ô ảnh", "", "Nguồn và điều khoản"])
imagery = [("Esri World Imagery (ArcGIS Location Platform)", 2_000_000, .15, "location.arcgis.com/help — 2.000.000 ô ảnh nền miễn phí/tháng, sau đó 0,15 USD/1.000; cho phép ứng dụng thương mại. Kiểm tra điều khoản số hóa từ ảnh trước khi dùng."),
           ("Google Map Tiles API (2D)", 100_000, .60, "developers.google.com/maps/billing-and-pricing/pricing. ⚠ Điều khoản Google cấm vẽ lại biên công trình từ ảnh vệ tinh: KHÔNG dùng cho trích biên mái."),
           ("Ảnh drone / ảnh khách tự cung cấp", 0, 0, "Không tốn phí cho SolarOpt; nhà thầu tự bay (lưu ý giấy phép bay)")]
for i, (label, free, price, src) in enumerate(imagery, 36):
    put(g, f"A{i}", label)
    put(g, f"B{i}", free, BLUE, VND)
    put(g, f"C{i}", price, BLUE, USD)
    put(g, f"E{i}", src, GREY, wrap=True)
IMG_NAMES, IMG_PRICE = "Gia_dinh!$A$36:$A$38", "Gia_dinh!$C$36:$C$38"
dv2 = DataValidation(type="list", formula1="=$A$36:$A$38", allow_blank=False)
g.add_data_validation(dv2)
put(g, "A39", "Nguồn ảnh dùng để tính")
put(g, "B39", "Esri World Imagery (ArcGIS Location Platform)", BLUE)
dv2.add("B39")
name(g, "B39", "IMG_SOURCE")
put(g, "A40", "Số ô ảnh tải mỗi dự án (xem, phóng, chụp lại)")
put(g, "B40", 400, BLUE, VND, fill=YELLOW, note="Ước tính: mái C&I xem ở mức phóng 19–20, nhiều lần mở lại.")
name(g, "B40", "TILES_PER_PROJECT")
put(g, "E40", "Tính theo giá khi đã vượt hạn mức miễn phí (thận trọng); trong hạn mức thì bằng 0.", GREY)

header(g, 42, ["Máy chủ, lưu trữ, vận hành", "Giá trị", "Đơn vị", "", "Nguồn / ghi chú"])
ops = [("CPU mỗi dự án (3 phương án, kiểm chứng, 8 tình huống, sửa vài lần)", 200, "đ", "CPU_PROJECT", True, "Đo 04/11: nhà xưởng 40×25 m ≈ 20 đ/lượt tính; nhân 10 cho nhiều lần sửa"),
       ("Dung lượng dữ liệu 1 dự án", 30, "MB", "MB_PROJECT", True, "Ảnh gốc 5–15 MB + ảnh hiệu chỉnh + ~50 phiên bản × 0,1 MB"),
       ("Lưu trữ đối tượng (Cloudflare R2)", .015, "USD/GB-tháng", "R2_PRICE", False, "developers.cloudflare.com/r2/pricing, đọc 04/11/2026"),
       ("Số bản sao dữ liệu (chính + sao lưu ngoài + bản điểm khôi phục)", 3, "bản", "COPIES", False, ""),
       ("Phí thanh toán (bình quân, % doanh thu)", .01, "%", "PAY_FEE", True, "Chuyển khoản B2B ≈ 0; cổng thẻ PayOS/VNPay 1–2,2%"),
       ("Giờ hỗ trợ / dự án", 1.5, "giờ", "SUPPORT_HOURS", True, "Hướng dẫn kỹ sư, xem lại biên mái C&I"),
       ("Chi phí 1 giờ hỗ trợ", 150000, "đ", "HOUR_COST", False, "≈ lương 20 tr gross × 1,215 / 176 giờ"),
       ("Số tháng dữ liệu được lưu trong gói (bình quân)", 4, "tháng", "PLAN_KEEP_MONTHS", True, "Gói tháng 1 tháng, gói năm còn lại bình quân ~6 tháng")]
for i, (label, v, unit, n, assumed, note) in enumerate(ops, 43):
    put(g, f"A{i}", label)
    put(g, f"B{i}", v, BLUE, PCT if unit == "%" else (USD if unit.startswith("USD") else NUM if v < 100 else VND), fill=YELLOW if assumed else None)
    put(g, f"C{i}", unit)
    put(g, f"E{i}", note, GREY)
    name(g, f"B{i}", n)

header(g, 52, ["Bán hàng, lưu trữ, kịch bản", "Giá trị", "Đơn vị", "", "Ghi chú"])
sales = [("Tỷ lệ dùng hạn mức dự án của gói", .8, "%", "UTIL", True, "Mua gói khi có dự án nên dùng gần hết; kiểm chứng ở pilot"),
         ("Phí lưu trữ (giá các sáng lập viên đặt)", 1_000_000, "đ/dự án/tháng", "STORE_FEE", False, "Theo chỉ đạo 07/11/2026"),
         ("Tỷ lệ dự án trả phí lưu trữ sau khi hết gói", .25, "%", "STORE_SHARE", True, "Phần lớn sẽ tải PDF/JSON về và để xóa"),
         ("Số tháng lưu trữ được trả bình quân", 6, "tháng", "STORE_MONTHS", True, ""),
         ("Tỷ lệ gia hạn gói năm", .6, "%", "RENEW", True, ""),
         ("Tỷ lệ lượt mua gói tháng là khách mới", .4, "%", "NEW_SHARE", True, "Còn lại là khách cũ mua lại khi có dự án mới"),
         ("CAC (chi phí có 1 khách mới)", 8_000_000, "đ", "CAC", True, "Bán B2B cho EPC: demo, khảo sát thử, đi gặp; chưa có số đo"),
         ("Giảm giá giai đoạn pilot", .5, "%", "PILOT_DISC", False, "Đổi lấy câu chuyện khách hàng và số đo thật"),
         ("Số tháng pilot (từ tháng 1)", 6, "tháng", "PILOT_MONTHS", False, ""),
         ("Dự án dùng thử mỗi người dùng thử", 1, "dự án", "TRIAL_PROJECTS", False, "Gói Dùng thử: 1 dự án, 5 lượt đọc ảnh"),
         ("Thuế TNDN áp dụng", 0, "%", "TAX", True, "Giả định miễn 3 năm đầu (NQ 198/2025/QH15) — CẦN XÁC MINH; không được miễn thì 20%"),
         ("Hệ số kịch bản (0,5 thận trọng · 1 cơ sở · 1,5 lạc quan)", 1, "×", "SCENARIO", False, "")]
for i, (label, v, unit, n, assumed, note) in enumerate(sales, 53):
    put(g, f"A{i}", label)
    put(g, f"B{i}", v, BLUE, PCT if unit == "%" else (VND if v >= 100 else NUM), fill=YELLOW if assumed else None)
    put(g, f"C{i}", unit)
    put(g, f"E{i}", note, GREY)
    name(g, f"B{i}", n)

# ------------------------------------------------------------------------------------------------
# Chi_phi_du_an (variable cost per project)
# ------------------------------------------------------------------------------------------------
v = wb.create_sheet("Chi_phi_du_an")
title(v, "Chi phí biến đổi của 1 dự án", "Mọi ô là công thức từ Gia_dinh · đ/dự án")
widths(v, [48, 18, 18, 18, 60])
header(v, 4, ["Khoản", "Dự kiến (đ)", "Xấu nhất (đ)", "", "Cách tính"])


def ai_cost(key, model, uses):
    p_in = f"INDEX({MODEL_IN},MATCH({model},{MODEL_NAMES},0))"
    p_out = f"INDEX({MODEL_OUT},MATCH({model},{MODEL_NAMES},0))"
    return f"={uses}*({key}_IN*{p_in}+{key}_OUT*{p_out})/1000000*TOKEN_FACTOR*SAFETY*FX_USD"


WORST = '"Claude Opus 5.5"'
lines = [("AI đọc ảnh mái", ai_cost("VISION", "VISION_MODEL", "VISION_USES"), ai_cost("VISION", WORST, "VISION_MAX"), "lượt × (token vào × giá vào + token ra × giá ra) × hệ số token × an toàn × tỷ giá; xấu nhất: dùng hết hạn mức bằng Opus"),
         ("Tư vấn từ hóa đơn", ai_cost("ADVISOR", "ADVISOR_MODEL", "ADVISOR_USES"), ai_cost("ADVISOR", WORST, "ADVISOR_MAX"), ""),
         ("Trợ lý hỏi đáp", ai_cost("CHAT", "CHAT_MODEL", "CHAT_USES"), ai_cost("CHAT", WORST, "CHAT_MAX"), ""),
         ("Ảnh vệ tinh", f"=TILES_PER_PROJECT*INDEX({IMG_PRICE},MATCH(IMG_SOURCE,{IMG_NAMES},0))/1000*FX_USD", f"=TILES_PER_PROJECT*3*INDEX({IMG_PRICE},MATCH(IMG_SOURCE,{IMG_NAMES},0))/1000*FX_USD", "ô ảnh × giá/1.000 × tỷ giá; xấu nhất ×3 ô ảnh"),
         ("CPU máy chủ", "=CPU_PROJECT", "=CPU_PROJECT*3", ""),
         ("Lưu trữ trong thời hạn gói", "=MB_PROJECT/1024*R2_PRICE*COPIES*FX_USD*PLAN_KEEP_MONTHS", "=MB_PROJECT*3/1024*R2_PRICE*COPIES*FX_USD*12", "MB/1024 × giá GB-tháng × số bản sao × tỷ giá × số tháng"),
         ("Hỗ trợ kỹ sư", "=SUPPORT_HOURS*HOUR_COST", "=SUPPORT_HOURS*2*HOUR_COST", "")]
for i, (label, exp, worst, how) in enumerate(lines, 5):
    put(v, f"A{i}", label)
    put(v, f"B{i}", exp, fmt=VND)
    put(v, f"C{i}", worst, fmt=VND)
    put(v, f"E{i}", how, GREY)
end = 4 + len(lines)
put(v, f"A{end+1}", "TỔNG CHI PHÍ BIẾN ĐỔI / DỰ ÁN (chưa gồm phí thanh toán)", bold=True)
put(v, f"B{end+1}", f"=SUM(B5:B{end})", fmt=VND, bold=True)
put(v, f"C{end+1}", f"=SUM(C5:C{end})", fmt=VND, bold=True)
name(v, f"B{end+1}", "VAR_COST")
name(v, f"C{end+1}", "VAR_COST_WORST")
put(v, f"A{end+2}", "  trong đó AI")
put(v, f"B{end+2}", "=SUM(B5:B7)", fmt=VND)
put(v, f"C{end+2}", "=SUM(C5:C7)", fmt=VND)
name(v, f"B{end+2}", "AI_COST")
put(v, f"A{end+3}", "Chi phí lưu trữ thực 1 dự án / tháng (để so phí lưu trữ)")
put(v, f"B{end+3}", "=MB_PROJECT/1024*R2_PRICE*COPIES*FX_USD", fmt=NUM)
name(v, f"B{end+3}", "STORE_COST_MONTH")
put(v, f"E{end+3}", "So với phí lưu trữ 1.000.000 đ/tháng: chi phí thật chỉ vài chục đồng — giá này là giá trị pháp lý, không phải chi phí.", GREY)

r0 = end + 6
put(v, f"A{r0-1}", "So sánh mô hình AI: chi phí AI của 1 dự án nếu dùng MỘT mô hình cho cả 3 tính năng (lượt dự kiến)", bold=True)
header(v, r0, ["Mô hình", "đ/dự án", "% giá gói Tháng·1", "", "Ghi chú"])
for j, (m, *_rest) in enumerate(models):
    rr = r0 + 1 + j
    put(v, f"A{rr}", f"=Gia_dinh!A{12+j}", GREEN)
    m_ref = f"$A{rr}"
    put(v, f"B{rr}", "=" + "+".join(ai_cost(k, m_ref, f"{k}_USES")[1:] for k in ("VISION", "ADVISOR", "CHAT")), fmt=VND)
    put(v, f"C{rr}", f"=B{rr}/Goi!$C$5", fmt='0.00%')
put(v, f"E{r0+1}", "Chênh lệch giữa mô hình rẻ nhất và mạnh nhất chỉ vài chục nghìn đồng/dự án: chọn theo độ chính xác, không theo giá.", GREY)

# ------------------------------------------------------------------------------------------------
# Goi (plans, unit economics)
# ------------------------------------------------------------------------------------------------
p = wb.create_sheet("Goi")
title(p, "Gói theo dự án — kinh tế đơn vị", "Cột B–F là đầu vào (giá sáng lập viên đặt 07/11/2026); từ cột G là công thức")
widths(p, [12, 22, 15, 10, 11, 12, 14, 15, 14, 14, 14, 12, 14, 15, 15])
header(p, 4, ["Mã gói", "Tên gói", "Giá (đ)", "Kỳ (tháng)", "Dự án / kỳ", "Ghế", "Giá / dự án", "Dự án dùng thực / kỳ", "Doanh thu / dự án dùng",
              "Giá vốn / dự án dùng", "Lãi gộp / dự án", "Biên gộp", "Biên gộp xấu nhất", "Quy đổi đ/tháng", "So với neo đối thủ"])
plans = [("month_1", "Tháng · 1 dự án", 5_990_000, 1, 1, 3, "NEO_MONTH"),
         ("month_2", "Tháng · 2 dự án", 7_990_000, 1, 2, 5, "NEO_MONTH"),
         ("year_3", "Năm · 3 dự án", 15_000_000, 12, 3, 5, "NEO_YEAR"),
         ("year_7", "Năm · 7 dự án", 30_000_000, 12, 7, 10, "NEO_YEAR")]
for i, (pid, nm, price, months, projects, seats, neo) in enumerate(plans, 5):
    put(p, f"A{i}", pid, BLUE)
    put(p, f"B{i}", nm, BLUE)
    put(p, f"C{i}", price, BLUE, VND, note="Giá sáng lập viên đặt ngày 07/11/2026")
    put(p, f"D{i}", months, BLUE, VND)
    put(p, f"E{i}", projects, BLUE, VND)
    put(p, f"F{i}", seats, BLUE, VND)
    put(p, f"G{i}", f"=C{i}/E{i}", fmt=VND)
    put(p, f"H{i}", f"=E{i}*UTIL", fmt=NUM)
    put(p, f"I{i}", f"=C{i}/MAX(H{i},0.0001)", fmt=VND)
    put(p, f"J{i}", f"=VAR_COST+I{i}*PAY_FEE", fmt=VND)
    put(p, f"K{i}", f"=I{i}-J{i}", fmt=VND)
    put(p, f"L{i}", f"=IF(I{i}=0,0,K{i}/I{i})", fmt=PCT)
    put(p, f"M{i}", f"=1-(VAR_COST_WORST+G{i}*PAY_FEE)/G{i}", fmt=PCT)
    put(p, f"N{i}", f"=C{i}/D{i}", fmt=VND)
    put(p, f"O{i}", f"=N{i}/{neo}-1", fmt=PCT, note="Âm = rẻ hơn đối thủ theo tiền mỗi tháng (CHƯA tính số dự án được dùng)")
    name(p, f"C{i}", f"PRICE_{pid.upper()}")
    name(p, f"E{i}", f"PROJ_{pid.upper()}")
put(p, "A10", "Lưu trữ", bold=True)
put(p, "B10", "Phí lưu trữ 1 dự án / tháng")
put(p, "C10", "=STORE_FEE", GREEN, VND)
put(p, "J10", "=STORE_COST_MONTH+C10*PAY_FEE", fmt=VND)
put(p, "K10", "=C10-J10", fmt=VND)
put(p, "L10", "=K10/C10", fmt=PCT)
put(p, "A12", "Đọc bảng", bold=True)
notes = ["• Biên gộp rất cao vì chi phí biến đổi (AI, ảnh, máy chủ) chỉ vài chục nghìn đồng/dự án: giá gói KHÔNG bị chi phí ràng buộc, mà bị đối thủ và giá trị khách nhận được ràng buộc.",
         "• Cột 'So với neo đối thủ' so tiền mỗi tháng với Aurora Premium (gói tháng) / HelioScope Basic (gói năm). Đối thủ cho 10–50 dự án/tháng với số tiền đó, nên tính theo từng dự án SolarOpt đắt hơn nhiều lần (xem Doi_thu).",
         "• Đề xuất xem docs/GIA_VA_CHI_PHI_THUONG_MAI.md: giữ giá cho công trình C&I nhưng tính lượt theo quy mô (dân dụng ≤ 30 kWp = 0,2 lượt), phí lưu trữ theo năm và ân hạn 30 ngày."]
for k, t in enumerate(notes, 13):
    put(p, f"A{k}", t, wrap=False)

# ------------------------------------------------------------------------------------------------
# Doi_thu (competitors)
# ------------------------------------------------------------------------------------------------
d = wb.create_sheet("Doi_thu")
title(d, "Giá đối thủ (đọc 07/11/2026) và quy đổi", "Giá trang chính hãng khi đọc được; trang Aurora/HelioScope chặn đọc tự động nên dùng nguồn bên thứ ba — ghi rõ ở cột Nguồn")
widths(d, [18, 22, 10, 8, 14, 34, 15, 16, 16, 16, 62])
header(d, 4, ["Đối thủ", "Gói", "Giá", "Tiền tệ", "Kỳ tính", "Giới hạn", "đ / tháng", "đ / năm", "đ / dự án (EPC C&I)", "đ / dự án (lắp dân dụng)", "Nguồn"])
put(d, "A3", "Số dự án/tháng của 1 công ty EPC C&I:", GREY)
put(d, "F3", 4, BLUE, VND, fill=YELLOW)
name(d, "F3", "EPC_PROJECTS")
put(d, "G3", "Dân dụng:", GREY)
put(d, "H3", 10, BLUE, VND, fill=YELLOW)
name(d, "H3", "RES_PROJECTS")
comp = [("Aurora Solar", "Basic", 159, "USD", "tháng", "1 người; ~50 dự án/tháng (nguồn thứ ba)", "heavengreenenergy.com/blog/aurora-solar-pricing (bên thứ ba; aurorasolar.com/pricing trả 403)"),
        ("Aurora Solar", "Basic, trả năm", 135, "USD", "tháng", "1 người", "như trên"),
        ("Aurora Solar", "Premium", 259, "USD", "tháng", "1 người; LIDAR, báo cáo bóng che bankable", "như trên"),
        ("Aurora Solar", "Premium, trả năm", 220, "USD", "tháng", "1 người", "như trên"),
        ("HelioScope (Aurora)", "Basic", 1620, "USD", "năm", "1 người; 10 dự án/tháng; ≤ 1,25 MWdc", "helioscope.aurorasolar.com/pricing (trích qua kết quả tìm kiếm; trang trả 403)"),
        ("HelioScope (Aurora)", "Pro", 2640, "USD", "năm", "1 người; 10 dự án/tháng", "như trên"),
        ("PVsyst 8", "Professional", 700, "CHF", "năm", "1 máy; không giới hạn dự án; phần mềm máy tính", "pvsyst.com/en/shop (đọc 07/11/2026)"),
        ("PV*SOL premium 2026", "1 năm", 845, "EUR", "năm", "1 người; chưa VAT", "shop.valentin-software.com (đọc 07/11/2026)"),
        ("Arka360", "Basic (Mỹ)", 1699, "USD", "năm", "1 người", "arka360.com/pricing (07/11/2026; trang có số mâu thuẫn $199/tháng)"),
        ("Arka360", "Premium (Mỹ)", 1999, "USD", "năm", "2 người", "như trên"),
        ("Arka360", "Basic (Ấn Độ)", 70000, "INR", "năm", "Không giới hạn dự án; + 18% GST", "arka360.com/pricing-in (07/11/2026)"),
        ("Pylon", "Standard", 4, "AUD", "dự án", "≤ 30 kWdc; không phí tháng", "getpylon.com/pricing (07/11/2026; trang không ghi tiền tệ, giả định AUD)"),
        ("Pylon", "Pro", 10, "AUD", "dự án", "Dự án thương mại, pin lưu trữ", "như trên"),
        ("OpenSolar", "Core", 0, "USD", "tháng", "Miễn phí; thu phí API/kết nối", "opensolar.com — 'OpenSolar Stays Free…' (02/2026)")]
for i, (who, plan, price, cur, per, lim, src) in enumerate(comp, 5):
    put(d, f"A{i}", who, BLUE)
    put(d, f"B{i}", plan, BLUE)
    put(d, f"C{i}", price, BLUE, NUM if price < 100 else VND)
    put(d, f"D{i}", cur, BLUE)
    put(d, f"E{i}", per, BLUE)
    put(d, f"F{i}", lim, BLUE)
    fxv = f"INDEX({FX_VALUES},MATCH(D{i},{FX_CODES},0))"
    put(d, f"G{i}", f'=IF(E{i}="tháng",C{i}*{fxv},IF(E{i}="năm",C{i}*{fxv}/12,C{i}*{fxv}*EPC_PROJECTS))', fmt=VND)
    put(d, f"H{i}", f"=G{i}*12", fmt=VND)
    put(d, f"I{i}", f'=IF(E{i}="dự án",C{i}*{fxv},G{i}/EPC_PROJECTS)', fmt=VND)
    put(d, f"J{i}", f'=IF(E{i}="dự án",C{i}*{fxv},G{i}/RES_PROJECTS)', fmt=VND)
    put(d, f"K{i}", src, GREY)
last = 4 + len(comp)
put(d, f"A{last+1}", "Công cụ của hãng biến tần (SolarEdge Designer, SMA Sunny Design, Huawei…)", GREY, italic=True)
put(d, f"F{last+1}", "Miễn phí; kỹ sư VN đang dùng kèm AutoCAD + PVsyst", GREY, italic=True)

a = last + 3
put(d, f"A{a}", "Neo giá để so (cùng phân khúc C&I)", bold=True)
put(d, f"A{a+1}", "Neo gói tháng: Aurora Premium trả theo tháng (đ/tháng)")
put(d, f"G{a+1}", "=G7", fmt=VND)
name(d, f"G{a+1}", "NEO_MONTH")
put(d, f"A{a+2}", "Neo gói năm: HelioScope Basic (đ/tháng quy đổi)")
put(d, f"G{a+2}", "=G9", fmt=VND)
name(d, f"G{a+2}", "NEO_YEAR")
put(d, f"A{a+3}", "Mức rẻ hơn mục tiêu")
put(d, f"G{a+3}", .175, BLUE, PCT, note="Sáng lập viên yêu cầu rẻ hơn 15–20%; lấy giữa khoảng")
name(d, f"G{a+3}", "DISCOUNT_TARGET")
header(d, a + 5, ["Gói SolarOpt", "", "Giá", "", "", "Đ / dự án (SolarOpt)", "Giá đối thủ cùng kỳ", "Chênh theo tiền/kỳ", "Đ / dự án đối thủ (EPC)", "Chênh theo đ/dự án", "Giá cần đặt để rẻ hơn mục tiêu (theo tiền/kỳ)"])
for j, (pid, nm, price, months, projects, seats, neo) in enumerate(plans):
    rr = a + 6 + j
    put(d, f"A{rr}", f"=Goi!B{5+j}", GREEN)
    put(d, f"C{rr}", f"=Goi!C{5+j}", GREEN, VND)
    put(d, f"F{rr}", f"=Goi!G{5+j}", GREEN, VND)
    put(d, f"G{rr}", f"={neo}*Goi!D{5+j}", fmt=VND)
    put(d, f"H{rr}", f"=C{rr}/G{rr}-1", fmt=PCT)
    put(d, f"I{rr}", f"={neo}/EPC_PROJECTS", fmt=VND)
    put(d, f"J{rr}", f"=F{rr}/I{rr}-1", fmt=PCT)
    put(d, f"K{rr}", f"=G{rr}*(1-DISCOUNT_TARGET)", fmt=VND)
put(d, f"A{a+11}", "Đọc bảng: theo tiền mỗi kỳ, gói năm của SolarOpt đã rẻ hơn HelioScope; gói tháng chỉ rẻ hơn Aurora Premium khoảng 11%. Nhưng tính theo từng dự án, SolarOpt đắt hơn nhiều lần vì đối thủ cho 10–50 dự án/tháng.", wrap=False)

# ------------------------------------------------------------------------------------------------
# Chi_phi_co_dinh (fixed monthly costs)
# ------------------------------------------------------------------------------------------------
f = wb.create_sheet("Chi_phi_co_dinh")
title(f, "Chi phí cố định", "Hạ tầng theo giai đoạn (theo số khách trả phí đang hoạt động), tuân thủ, nhân sự")
widths(f, [58, 16, 16, 16, 64])
header(f, 4, ["Hạ tầng (USD/tháng)", "Thử nghiệm", "Tăng trưởng", "Mở rộng", "Nguồn / ghi chú"])
infra = [("Vercel Pro (giao diện web)", 20, 20, 40, "vercel.com/pricing, đọc 04/11/2026"),
         ("Render: workspace + máy chủ 2 GB (Standard)", 50, 110, 250, "render.com/pricing 04/11/2026; tăng trưởng: 2 CPU/4 GB + worker"),
         ("Cơ sở dữ liệu Postgres có sao lưu theo thời điểm", 19, 55, 150, "Render Postgres 04/11/2026; mở rộng: bản dự phòng HA (ước tính)"),
         ("Lưu trữ đối tượng R2 + sao lưu ngoài", 5, 15, 40, "Cloudflare R2 0,015 USD/GB-tháng; ước tính theo số dự án lưu"),
         ("Email giao dịch (hóa đơn, nhắc hết hạn, thông báo xóa)", 20, 20, 50, "Ước tính — cần cho chính sách xóa sau hạn"),
         ("Bản đồ nền / ảnh vệ tinh (phần cố định)", 0, 0, 0, "Esri: 2 triệu ô ảnh miễn phí/tháng; phần vượt đã tính vào chi phí dự án")]
for i, (label, a1, a2, a3, src) in enumerate(infra, 5):
    put(f, f"A{i}", label)
    for c, val in zip("BCD", (a1, a2, a3)):
        put(f, f"{c}{i}", val, BLUE, VND, fill=YELLOW if c != "B" else None)
    put(f, f"E{i}", src, GREY)
ie = 4 + len(infra)
put(f, f"A{ie+1}", "Tổng hạ tầng (USD/tháng)", bold=True)
for c in "BCD":
    put(f, f"{c}{ie+1}", f"=SUM({c}5:{c}{ie})", fmt=VND, bold=True)
name(f, f"B{ie+1}", "INFRA_1")
name(f, f"C{ie+1}", "INFRA_2")
name(f, f"D{ie+1}", "INFRA_3")
put(f, f"A{ie+2}", "Ngưỡng chuyển sang Tăng trưởng (khách trả phí đang hoạt động)")
put(f, f"B{ie+2}", 30, BLUE, VND, fill=YELLOW)
name(f, f"B{ie+2}", "STAGE_2")
put(f, f"A{ie+3}", "Ngưỡng chuyển sang Mở rộng")
put(f, f"B{ie+3}", 120, BLUE, VND, fill=YELLOW)
name(f, f"B{ie+3}", "STAGE_3")

h = ie + 5
header(f, h, ["Tuân thủ, pháp lý, vận hành (đ)", "Giá trị", "Kiểu", "", "Nguồn / ghi chú"])
comp_costs = [("Pháp lý một lần (điều khoản dịch vụ, chính sách dữ liệu, hợp đồng mẫu B2B)", 15_000_000, "một lần", "LEGAL_ONCE", False, "Bản 04/11"),
              ("Hồ sơ đánh giá tác động xử lý & chuyển dữ liệu cá nhân ra nước ngoài", 20_000_000, "một lần", "PDPL_ONCE", True, "Luật Bảo vệ dữ liệu cá nhân 2025 (hiệu lực 01/01/2026); máy chủ ở nước ngoài — ước tính, cần luật sư"),
              ("Kế toán, hóa đơn điện tử, thuế", 2_000_000, "tháng", "ACCOUNTING", False, "Dịch vụ kế toán thuê ngoài"),
              ("Bảo hiểm trách nhiệm nghề nghiệp / sản phẩm phần mềm", 24_000_000, "năm", "INSURANCE", True, "Ước tính — CẦN BÁO GIÁ; bảo vệ khi lỗi tính toán dẫn tới thiệt hại"),
              ("Kỹ sư kết cấu / điện mặt trời cố vấn (rà soát phương pháp, quy trình ký duyệt)", 5_000_000, "tháng", "ADVISOR_ENG", True, "Bán thời gian; cần cho độ tin cậy với khách C&I"),
              ("Kiểm thử xâm nhập (từ tháng 13)", 30_000_000, "năm", "PENTEST", True, "Ước tính — cần báo giá"),
              ("Bộ đánh giá khi đổi/nâng mô hình AI (token + giờ công)", 10_000_000, "năm", "MODEL_EVAL", True, "Mô hình đổi giá/ngừng 6–12 tháng/lần"),
              ("Công cụ phát triển, giám sát lỗi, tên miền", 1_100_000, "tháng", "TOOLS", False, "GitHub, Sentry, tên miền .vn ~1 tr/năm"),
              ("Marketing cố định (nội dung, hội thảo, demo tại công trình)", 5_000_000, "tháng", "MKT_FIXED", False, "")]
for i, (label, val, kind, n, assumed, src) in enumerate(comp_costs, h + 1):
    put(f, f"A{i}", label)
    put(f, f"B{i}", val, BLUE, VND, fill=YELLOW if assumed else None)
    put(f, f"C{i}", kind)
    put(f, f"E{i}", src, GREY)
    name(f, f"B{i}", n)

s = h + len(comp_costs) + 2
header(f, s, ["Nhân sự", "Lương gross (đ/tháng)", "Số người", "", "Ghi chú"])
staff = [("Lập trình viên (backend, giao diện, AI)", 11_570_000, 2, "Mặt bằng junior ITviec 2025–2026"),
         ("Bán hàng / chăm sóc khách hàng kỹ thuật", 11_570_000, 1, "")]
for i, (label, pay, cnt, note) in enumerate(staff, s + 1):
    put(f, f"A{i}", label)
    put(f, f"B{i}", pay, BLUE, VND)
    put(f, f"C{i}", cnt, BLUE, VND)
    put(f, f"E{i}", note, GREY)
put(f, f"A{s+3}", "Đóng góp người sử dụng lao động")
put(f, f"B{s+3}", .215, BLUE, PCT)
put(f, f"E{s+3}", "BHXH 17,5% + BHYT 3% + BHTN 1%", GREY)
put(f, f"A{s+4}", "Tỷ lệ lương trả bằng tiền năm đầu")
put(f, f"B{s+4}", .5, BLUE, PCT, fill=YELLOW)
name(f, f"B{s+4}", "PAY_RATIO_Y1")
put(f, f"A{s+5}", "Tổng chi phí nhân sự đủ lương (đ/tháng)", bold=True)
put(f, f"B{s+5}", f"=(B{s+1}*C{s+1}+B{s+2}*C{s+2})*(1+B{s+3})", fmt=VND, bold=True)
name(f, f"B{s+5}", "STAFF")

# ------------------------------------------------------------------------------------------------
# Dong_tien (36-month cash flow)
# ------------------------------------------------------------------------------------------------
c = wb.create_sheet("Dong_tien")
title(c, "Dòng tiền 36 tháng (VND) — tháng 1 = 01/2027", "Dòng chữ xanh là dự báo đầu vào (giả định); còn lại là công thức. Gói năm thu tiền ngay khi mua.")
c.column_dimensions["A"].width = 52
c.column_dimensions["B"].width = 4
M = list(range(1, 37))
C0 = 3  # column C = month 1
for m in M:
    c.column_dimensions[col(C0 + m - 1)].width = 13


def mc(m):
    return col(C0 + m - 1)


def row(r, label, f, fmt=VND, color=BLACK, bold=False, fill=None):
    put(c, f"A{r}", label, bold=bold)
    for m in M:
        put(c, f"{mc(m)}{r}", f(m), color, fmt, bold=bold, fill=fill)


def tiers(m, a, b, d_, e):
    return a if m <= 6 else b if m <= 12 else d_ if m <= 24 else e


row(3, "Tháng thứ", lambda m: m, "0")
row(4, "Kỳ", lambda m: f"T{(m - 1) % 12 + 1:02d}/{2027 + (m - 1) // 12}", "@")
row(5, "Đang trong pilot (1/0)", lambda m: f"=IF({mc(m)}3<=PILOT_MONTHS,1,0)", "0")
put(c, "A7", "GÓI THÁNG (mua theo lượt, khi có dự án)", bold=True)
row(8, "  Lượt mua Tháng·1 dự án — cơ sở", lambda m: tiers(m, 1, 2, 3, 4), NUM, BLUE)
row(9, "  Lượt mua Tháng·1 dự án — theo kịch bản", lambda m: f"={mc(m)}8*SCENARIO", NUM)
row(10, "  Lượt mua Tháng·2 dự án — cơ sở", lambda m: tiers(m, 0, .5, 1, 1.5), NUM, BLUE)
row(11, "  Lượt mua Tháng·2 dự án — theo kịch bản", lambda m: f"={mc(m)}10*SCENARIO", NUM)
put(c, "A13", "GÓI NĂM", bold=True)
row(14, "  Năm·3 dự án mua mới — cơ sở", lambda m: tiers(m, .3, .5, 1, 1.5), NUM, BLUE)
row(15, "  Năm·3 dự án mua mới — theo kịch bản", lambda m: f"={mc(m)}14*SCENARIO", NUM)
row(16, "  Năm·3 dự án gia hạn", lambda m: f"={mc(m-12)}17*RENEW" if m > 12 else "=0", NUM)
row(17, "  Năm·3 dự án tổng lượt mua", lambda m: f"={mc(m)}15+{mc(m)}16", NUM)
row(18, "  Năm·7 dự án mua mới — cơ sở", lambda m: tiers(m, 0, .25, .5, 1), NUM, BLUE)
row(19, "  Năm·7 dự án mua mới — theo kịch bản", lambda m: f"={mc(m)}18*SCENARIO", NUM)
row(20, "  Năm·7 dự án gia hạn", lambda m: f"={mc(m-12)}21*RENEW" if m > 12 else "=0", NUM)
row(21, "  Năm·7 dự án tổng lượt mua", lambda m: f"={mc(m)}19+{mc(m)}20", NUM)
row(22, "  Gói năm đang hiệu lực", lambda m: f"=SUM({mc(max(1, m-11))}17:{mc(m)}17)+SUM({mc(max(1, m-11))}21:{mc(m)}21)", NUM)
row(23, "Khách trả phí đang hoạt động (gói tháng tháng này + gói năm còn hạn)", lambda m: f"={mc(m)}9+{mc(m)}11+{mc(m)}22", NUM, bold=True)
put(c, "A25", "DỰ ÁN", bold=True)
row(26, "  Dự án dùng từ gói tháng", lambda m: f"=({mc(m)}9*PROJ_MONTH_1+{mc(m)}11*PROJ_MONTH_2)*UTIL", NUM)
row(27, "  Dự án dùng từ gói năm (rải đều 12 tháng)", lambda m: f"=(SUM({mc(max(1, m-11))}17:{mc(m)}17)*PROJ_YEAR_3+SUM({mc(max(1, m-11))}21:{mc(m)}21)*PROJ_YEAR_7)/12*UTIL", NUM)
row(28, "  Tổng dự án dùng trong tháng", lambda m: f"={mc(m)}26+{mc(m)}27", NUM, bold=True)
row(29, "  Dự án hết thời hạn gói trong tháng", lambda m: ("=0" if m == 1 else f"={mc(m-1)}26") + (f"+({mc(m-12)}17*PROJ_YEAR_3+{mc(m-12)}21*PROJ_YEAR_7)*UTIL" if m > 12 else ""), NUM)
row(30, "  Dự án đang trả phí lưu trữ", lambda m: (f"={mc(m-1)}30*(1-1/STORE_MONTHS)+" if m > 1 else "=") + f"{mc(m)}29*STORE_SHARE", NUM)
row(31, "  Người dùng thử mới — cơ sở", lambda m: tiers(m, 5, 5, 10, 15), NUM, BLUE)
put(c, "A33", "DOANH THU", bold=True)
row(34, "  Gói tháng", lambda m: f"=({mc(m)}9*PRICE_MONTH_1+{mc(m)}11*PRICE_MONTH_2)*(1-{mc(m)}5*PILOT_DISC)")
row(35, "  Gói năm (thu khi mua)", lambda m: f"=({mc(m)}17*PRICE_YEAR_3+{mc(m)}21*PRICE_YEAR_7)*(1-{mc(m)}5*PILOT_DISC)")
row(36, "  Phí lưu trữ dự án", lambda m: f"={mc(m)}30*STORE_FEE")
row(37, "TỔNG DOANH THU", lambda m: f"=SUM({mc(m)}34:{mc(m)}36)", bold=True)
put(c, "A39", "GIÁ VỐN", bold=True)
row(40, "  Chi phí biến đổi dự án (gồm dự án dùng thử)", lambda m: f"=({mc(m)}28+{mc(m)}31*SCENARIO*TRIAL_PROJECTS)*VAR_COST")
row(41, "  Lưu trữ dữ liệu dự án đã hết gói", lambda m: f"={mc(m)}30*STORE_COST_MONTH")
row(42, "  Phí thanh toán", lambda m: f"={mc(m)}37*PAY_FEE")
row(43, "TỔNG GIÁ VỐN", lambda m: f"=SUM({mc(m)}40:{mc(m)}42)", bold=True)
row(44, "LÃI GỘP", lambda m: f"={mc(m)}37-{mc(m)}43", bold=True)
put(c, "A46", "CHI PHÍ HOẠT ĐỘNG", bold=True)
row(47, "  Hạ tầng (theo giai đoạn)", lambda m: f"=IF({mc(m)}23<=STAGE_2,INFRA_1,IF({mc(m)}23<=STAGE_3,INFRA_2,INFRA_3))*FX_USD")
row(48, "  Nhân sự", lambda m: f"=STAFF*IF({mc(m)}3<=12,PAY_RATIO_Y1,1)")
row(49, "  Pháp lý, tuân thủ, bảo hiểm, kỹ sư cố vấn, công cụ", lambda m: f"=IF({mc(m)}3=1,LEGAL_ONCE+PDPL_ONCE,0)+ACCOUNTING+INSURANCE/12+ADVISOR_ENG+IF({mc(m)}3>12,PENTEST/12,0)+MODEL_EVAL/12+TOOLS")
row(50, "  Marketing (cố định + CAC khách mới)", lambda m: f"=MKT_FIXED+CAC*(({mc(m)}9+{mc(m)}11)*NEW_SHARE+{mc(m)}15+{mc(m)}19)")
row(51, "TỔNG CHI PHÍ HOẠT ĐỘNG", lambda m: f"=SUM({mc(m)}47:{mc(m)}50)", bold=True)
row(52, "EBITDA", lambda m: f"={mc(m)}44-{mc(m)}51", bold=True)
row(53, "  Thuế TNDN", lambda m: f"=MAX(0,{mc(m)}52)*TAX")
row(54, "LỢI NHUẬN RÒNG", lambda m: f"={mc(m)}52-{mc(m)}53", bold=True)
row(55, "  Vốn góp / gọi vốn", lambda m: {1: 250_000_000, 4: 200_000_000, 8: 150_000_000}.get(m, 0), VND, BLUE)
row(56, "TIỀN MẶT CUỐI THÁNG", lambda m: (f"={mc(m-1)}56+" if m > 1 else "=") + f"{mc(m)}54+{mc(m)}55", bold=True)
row(57, "  (phụ) tháng có EBITDA ≥ 0", lambda m: f"=IF({mc(m)}52>=0,{mc(m)}3,999)", "0")
c.freeze_panes = "C5"

# ------------------------------------------------------------------------------------------------
# Tong_hop (summary)
# ------------------------------------------------------------------------------------------------
t = wb.create_sheet("Tong_hop", 1)
title(t, "Tổng hợp kết quả", "Mọi số là công thức từ Dong_tien, Goi, Chi_phi_du_an")
widths(t, [48, 18, 18, 18, 50])
header(t, 4, ["Chỉ tiêu (VND)", "Năm 1 (2027)", "Năm 2 (2028)", "Năm 3 (2029)", "Ghi chú"])
yr = [("C", "N"), ("O", "Z"), ("AA", "AL")]
summary = [("Lượt mua gói tháng", 9, 11), ("Lượt mua gói năm (mới + gia hạn)", 17, 21), ("Dự án được tính", 28, None),
           ("Doanh thu gói tháng", 34, None), ("Doanh thu gói năm", 35, None), ("Doanh thu lưu trữ", 36, None), ("Tổng doanh thu", 37, None),
           ("Giá vốn", 43, None), ("Lãi gộp", 44, None), ("Chi phí hoạt động", 51, None), ("EBITDA", 52, None), ("Lợi nhuận ròng", 54, None)]
for i, (label, r_, extra) in enumerate(summary, 5):
    put(t, f"A{i}", label, bold=label in ("Tổng doanh thu", "Lợi nhuận ròng"))
    for j, (a_, b_) in enumerate(yr):
        other = f"+SUM(Dong_tien!{a_}{extra}:{b_}{extra})" if extra else ""
        put(t, f"{'BCD'[j]}{i}", f"=SUM(Dong_tien!{a_}{r_}:{b_}{r_}){other}", GREEN, NUM if r_ in (9, 17, 28) else VND)
put(t, "A17", "Biên lãi gộp")
for j in range(3):
    put(t, f"{'BCD'[j]}17", f"=IF({'BCD'[j]}11=0,0,{'BCD'[j]}13/{'BCD'[j]}11)", fmt=PCT)
put(t, "A18", "Tiền mặt cuối năm")
for j, (a_, b_) in enumerate(yr):
    put(t, f"{'BCD'[j]}18", f"=Dong_tien!{b_}56", GREEN, VND)
put(t, "A20", "Chỉ số then chốt", bold=True)
key = [("Tháng đầu tiên có EBITDA ≥ 0", "=IF(MIN(Dong_tien!C57:AL57)=999,\"Chưa có lãi trong 36 tháng\",INDEX(Dong_tien!C4:AL4,MATCH(MIN(Dong_tien!C57:AL57),Dong_tien!C3:AL3,0)))", None),
       ("Tiền mặt thấp nhất trong 36 tháng", "=MIN(Dong_tien!C56:AL56)", VND),
       ("Đủ vốn? (tiền mặt không âm)", "=IF(B22>=0,\"Đủ\",\"THIẾU VỐN\")", None),
       ("Tổng vốn góp", "=SUM(Dong_tien!C55:AL55)", VND),
       ("Chi phí biến đổi / dự án (dự kiến)", "=VAR_COST", VND),
       ("  trong đó AI", "=AI_COST", VND),
       ("Chi phí biến đổi / dự án (xấu nhất)", "=VAR_COST_WORST", VND),
       ("Chi phí biến đổi / giá rẻ nhất mỗi dự án", "=VAR_COST/MIN(Goi!G5:G8)", '0.00%'),
       ("Mô hình đọc ảnh / tư vấn / trợ lý", "=VISION_MODEL&\" / \"&ADVISOR_MODEL&\" / \"&CHAT_MODEL", None),
       ("Hệ số kịch bản", "=SCENARIO", NUM)]
for i, (label, formula, fmt) in enumerate(key, 21):
    put(t, f"A{i}", label)
    put(t, f"B{i}", formula, GREEN, fmt)
put(t, "E21", "Theo giả định số lượt mua ở Dong_tien — chưa có dữ liệu khách", GREY)
put(t, "E28", "Chi phí AI + ảnh + máy chủ rất nhỏ so với giá gói: rủi ro nằm ở số khách và giá đối thủ, không ở chi phí vận hành", GREY)

for sheet in wb.worksheets:
    sheet.sheet_view.showGridLines = False
    for rw in sheet.iter_rows():
        for cell in rw:
            if cell.font and cell.font.name != FONT:
                cell.font = Font(name=FONT, color=cell.font.color, bold=cell.font.bold, size=cell.font.size or 10, italic=cell.font.italic)

OUT.parent.mkdir(parents=True, exist_ok=True)
wb.save(OUT)
print("saved", OUT)
