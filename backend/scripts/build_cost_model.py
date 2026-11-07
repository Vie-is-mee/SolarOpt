"""Build the SolarOpt cost, pricing and cash-flow workbook (output/report/SolarOpt_Mo_hinh_tai_chinh_v3.xlsx).

Every result is an Excel formula over the input cells, so the team can change a price, a model or a forecast and
the workbook recalculates. Blue = input, black = formula, green = link to another sheet, yellow fill = key
assumption to validate. Token counts come from scripts/measure_cost.py (04/11/2026); prices and competitor figures
carry their source and reading date next to them.
    python scripts/build_cost_model.py        (then open in Excel, or recalculate, before reading cached values)
"""
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as col
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

OUT = Path(__file__).resolve().parents[2] / "output" / "report" / "SolarOpt_Mo_hinh_tai_chinh_v3.xlsx"
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
title(ws, "SolarOpt — Mô hình chi phí, gói đề xuất, hòa vốn và dòng tiền (bản 3)", "Lập 08/11/2026 · đơn vị VND · tháng 1 của dòng tiền = tháng đầu bán (Gia_dinh: LAUNCH) · bảng giá ở đây là ĐỀ XUẤT, app vẫn chạy bảng 07/11")
rows = [
    ("Cách dùng", ""),
    ("1", "Chỉ sửa ô CHỮ XANH (đầu vào). Ô chữ đen là công thức; chữ xanh lá là liên kết sang sheet khác."),
    ("2", "Ô NỀN VÀNG là giả định then chốt chưa có dữ liệu thật: phải kiểm chứng bằng phỏng vấn khách / pilot trước khi đưa lên slide."),
    ("3", "Đổi mô hình AI cho từng tính năng ở Gia_dinh (ô chọn danh sách). Đổi giá gói ở sheet Goi cột C, bậc lưu trữ ở Luu_tru. Đổi dự báo số lượt mua ở Dong_tien (dòng chữ xanh). Đặt FIXED_STAFF trong Gia_dinh để cố định số nhân sự; để 0 thì tuyển theo mốc khách ở Chi_phi_co_dinh."),
    ("4", "Kết quả: Tong_hop (năm 1–3, tháng có lãi, tiền mặt thấp nhất), Hoa_von (số khách tối thiểu theo từng phương án nhân sự), Goi (lãi gộp và chi phí tối đa từng gói), Luu_tru (bậc phí và kho lạnh), Doi_thu (so giá đối thủ), Chi_phi_du_an (chi phí biến đổi 1 dự án)."),
    ("", ""),
    ("Thay đổi so với bản 07/11", "Bốn gói đề xuất (Dự án lẻ, Start, Team, Pro) thay Tháng·1, Tháng·2, Năm·3, Năm·7; giới hạn giờ hỗ trợ và chi phí tối đa theo gói; nhân sự 6 vị trí, tuyển theo mốc khách; thêm văn phòng và dự phòng 10%; phí lưu trữ theo bậc và kho lạnh; Thiết kế hộ; trừ tiền lẻ khi nâng gói; pilot 5 khách chỉ gói năm; sheet Hoa_von; năm 1 tính từ tháng đầu bán."),
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
put(ws, f"A{r+3}", "Ví dụ dòng nhập: gói Start, giá 17.900.000 đ, 12 tháng, 8 dự án, khách dùng 80% hạn mức.", GREY, italic=True)
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
         ("Tỷ lệ khách gói năm mới từng mua lẻ (được trừ tiền)", .3, "%", "UPGRADE_SHARE", True, "Tiền mua lẻ trong 30 ngày được trừ khi nâng lên gói năm"),
         ("Tỷ lệ khách đóng phí kho khi hết kỳ gói", .25, "%", "STORE_SHARE", True, "Phần lớn sẽ tải PDF/JSON về; thử 60% để xem mức cao"),
         ("Số tháng đóng phí kho bình quân", 12, "tháng", "STORE_MONTHS", True, ""),
         ("Tỷ lệ gia hạn gói năm", .6, "%", "RENEW", True, ""),
         ("Tỷ lệ lượt mua gói tháng là khách mới", .4, "%", "NEW_SHARE", True, "Còn lại là khách cũ mua lại khi có dự án mới"),
         ("CAC (chi phí có 1 khách mới)", 8_000_000, "đ", "CAC", True, "Bán B2B cho EPC: demo, khảo sát thử, đi gặp; chưa có số đo"),
         ("Giảm giá pilot (chỉ gói năm)", .3, "%", "PILOT_DISC", False, "Đổi lấy câu chuyện khách hàng và số đo thật"),
         ("Số khách pilot", 5, "khách", "PILOT_CUSTOMERS", False, "Năm khách gói năm đầu tiên"),
         ("Người dùng thử cho mỗi khách mới", 3, "người", "TRIALS_PER_CUSTOMER", True, "Mỗi người 1 dự án thử; chưa có số đo tỷ lệ chuyển đổi"),
         ("Thuế TNDN áp dụng", 0, "%", "TAX", True, "Giả định miễn 3 năm đầu (NQ 198/2025/QH15) — CẦN XÁC MINH; không được miễn thì 20%"),
         ("Hệ số kịch bản (0,5 thận trọng · 1 cơ sở · 1,5 lạc quan)", 1, "×", "SCENARIO", False, "")]
for i, (label, v, unit, n, assumed, note) in enumerate(sales, 53):
    put(g, f"A{i}", label)
    put(g, f"B{i}", v, BLUE, PCT if unit == "%" else (VND if v >= 100 else NUM), fill=YELLOW if assumed else None)
    put(g, f"C{i}", unit)
    put(g, f"E{i}", note, GREY)
    name(g, f"B{i}", n)

header(g, 66, ["Nhân sự, gói, dịch vụ thêm (bản 3)", "Giá trị", "Đơn vị", "", "Ghi chú"])
extra = [("Tháng bắt đầu bán", date(2027, 10, 1), "tháng", "LAUNCH", True, "Bài nói: pilot 04/2027, bán thương mại cuối 2027"),
         ("Cố định số nhân sự (0 = tuyển theo mốc khách)", 0, "người", "FIXED_STAFF", False, "Đặt 5 hoặc 6 để xem đội đủ người từ đầu"),
         ("Lãi mục tiêu năm đầu", 50_000_000, "đ", "TARGET_PROFIT", False, "Dùng ở Hoa_von"),
         ("Dự phòng trên chi phí cố định", .1, "%", "CONTINGENCY", True, ""),
         ("Tỷ lệ khách chọn Start", .5, "%", "MIX_START", True, "Chưa có dữ liệu"),
         ("Tỷ lệ khách chọn Team", .35, "%", "MIX_TEAM", True, "Chưa có dữ liệu"),
         ("Tỷ lệ khách chọn Pro", .15, "%", "MIX_PRO", True, "Chưa có dữ liệu"),
         ("Giá Thiết kế hộ", 3_900_000, "đ/dự án", "DFY_PRICE", True, "Nhóm chạy phần mềm, kỹ sư của khách ký"),
         ("Giờ làm 1 dự án Thiết kế hộ", 3, "giờ", "DFY_HOURS", True, ""),
         ("AI và ảnh của 1 dự án Thiết kế hộ", 50_000, "đ", "DFY_AI", True, ""),
         ("Giá kho lạnh", .01, "USD/GB-tháng", "COLD_PRICE", True, "Cloudflare R2 Infrequent Access; đối chiếu trang giá trước khi dùng"),
         ("Số bản sao kho lạnh", 2, "bản", "COLD_COPIES", False, ""),
         ("Chi phí có 1 khách, mức thấp", 3_000_000, "đ", "CAC_LOW", True, "Sáng lập viên tự bán; dùng ở Hoa_von")]
for i, (label, val, unit, n, assumed, note) in enumerate(extra, 67):
    put(g, f"A{i}", label)
    fmt = "mm/yyyy" if n == "LAUNCH" else PCT if unit == "%" else USD if unit.startswith("USD") else VND
    put(g, f"B{i}", val, BLUE, fmt, fill=YELLOW if assumed else None)
    put(g, f"C{i}", unit)
    put(g, f"E{i}", note, GREY)
    name(g, f"B{i}", n)

# ------------------------------------------------------------------------------------------------
# Chi_phi_du_an (variable cost per project)
# ------------------------------------------------------------------------------------------------
v = wb.create_sheet("Chi_phi_du_an")
title(v, "Chi phí biến đổi của 1 dự án", "Mọi ô là công thức từ Gia_dinh · đ/dự án")
widths(v, [48, 18, 18, 18, 60])
header(v, 4, ["Khoản", "Dự kiến (đ)", "Tối đa, mô hình đắt nhất (đ)", "Tối đa, ghim mô hình (đ)", "Cách tính"])


def ai_cost(key, model, uses):
    p_in = f"INDEX({MODEL_IN},MATCH({model},{MODEL_NAMES},0))"
    p_out = f"INDEX({MODEL_OUT},MATCH({model},{MODEL_NAMES},0))"
    return f"={uses}*({key}_IN*{p_in}+{key}_OUT*{p_out})/1000000*TOKEN_FACTOR*SAFETY*FX_USD"


WORST = '"Claude Opus 5.5"'
lines = [("AI đọc ảnh mái", ai_cost("VISION", "VISION_MODEL", "VISION_USES"), ai_cost("VISION", WORST, "VISION_MAX"), ai_cost("VISION", "VISION_MODEL", "VISION_MAX"), "lượt × (token vào × giá vào + token ra × giá ra) × hệ số token × an toàn × tỷ giá; xấu nhất: dùng hết hạn mức bằng Opus"),
         ("Tư vấn từ hóa đơn", ai_cost("ADVISOR", "ADVISOR_MODEL", "ADVISOR_USES"), ai_cost("ADVISOR", WORST, "ADVISOR_MAX"), ai_cost("ADVISOR", "ADVISOR_MODEL", "ADVISOR_MAX"), ""),
         ("Trợ lý hỏi đáp", ai_cost("CHAT", "CHAT_MODEL", "CHAT_USES"), ai_cost("CHAT", WORST, "CHAT_MAX"), ai_cost("CHAT", "CHAT_MODEL", "CHAT_MAX"), ""),
         ("Ảnh vệ tinh", f"=TILES_PER_PROJECT*INDEX({IMG_PRICE},MATCH(IMG_SOURCE,{IMG_NAMES},0))/1000*FX_USD", f"=TILES_PER_PROJECT*3*INDEX({IMG_PRICE},MATCH(IMG_SOURCE,{IMG_NAMES},0))/1000*FX_USD", f"=TILES_PER_PROJECT*3*INDEX({IMG_PRICE},MATCH(IMG_SOURCE,{IMG_NAMES},0))/1000*FX_USD", "ô ảnh × giá/1.000 × tỷ giá; xấu nhất ×3 ô ảnh"),
         ("CPU máy chủ", "=CPU_PROJECT", "=CPU_PROJECT*3", "=CPU_PROJECT*3", ""),
         ("Lưu trữ trong thời hạn gói", "=MB_PROJECT/1024*R2_PRICE*COPIES*FX_USD*PLAN_KEEP_MONTHS", "=MB_PROJECT*3/1024*R2_PRICE*COPIES*FX_USD*12", "=MB_PROJECT*3/1024*R2_PRICE*COPIES*FX_USD*12", "MB/1024 × giá GB-tháng × số bản sao × tỷ giá × số tháng"),
         ("Hỗ trợ kỹ sư", "=SUPPORT_HOURS*HOUR_COST", "=SUPPORT_HOURS*2*HOUR_COST", "=SUPPORT_HOURS*2*HOUR_COST", "")]
for i, (label, exp, worst, pinned, how) in enumerate(lines, 5):
    put(v, f"A{i}", label)
    put(v, f"B{i}", exp, fmt=VND)
    put(v, f"C{i}", worst, fmt=VND)
    put(v, f"D{i}", pinned, fmt=VND)
    put(v, f"E{i}", how, GREY)
end = 4 + len(lines)
put(v, f"A{end+1}", "TỔNG CHI PHÍ BIẾN ĐỔI / DỰ ÁN (chưa gồm phí thanh toán)", bold=True)
put(v, f"B{end+1}", f"=SUM(B5:B{end})", fmt=VND, bold=True)
put(v, f"C{end+1}", f"=SUM(C5:C{end})", fmt=VND, bold=True)
put(v, f"D{end+1}", f"=SUM(D5:D{end})", fmt=VND, bold=True)
name(v, f"D{end+1}", "VAR_COST_PINNED")
name(v, f"B{end+1}", "VAR_COST")
name(v, f"C{end+1}", "VAR_COST_WORST")
put(v, f"A{end+2}", "  trong đó AI")
put(v, f"B{end+2}", "=SUM(B5:B7)", fmt=VND)
put(v, f"C{end+2}", "=SUM(C5:C7)", fmt=VND)
put(v, f"D{end+2}", "=SUM(D5:D7)", fmt=VND)
name(v, f"B{end+2}", "AI_COST")
put(v, f"A{end+3}", "Chi phí lưu trữ thực 1 dự án / tháng (để so phí lưu trữ)")
put(v, f"B{end+3}", "=MB_PROJECT/1024*R2_PRICE*COPIES*FX_USD", fmt=NUM)
name(v, f"B{end+3}", "STORE_COST_MONTH")
put(v, f"E{end+3}", "Chi phí thật chỉ vài chục đồng: phí lưu trữ là giá của hồ sơ có niêm phong, không phải giá dung lượng (xem Luu_tru).", GREY)

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
title(p, "Gói đề xuất 08/11/2026 — kinh tế đơn vị", "Cột B–F và P là đầu vào; còn lại là công thức. App vẫn chạy bảng 07/11 trong backend/app/billing.py cho tới khi chốt.")
widths(p, [12, 22, 15, 10, 11, 12, 14, 15, 14, 14, 14, 12, 14, 15, 15, 12, 17, 10, 17, 10])
header(p, 4, ["Mã gói", "Tên gói", "Giá (đ)", "Kỳ (tháng)", "Dự án / kỳ", "Ghế", "Giá / dự án", "Dự án dùng thực / kỳ", "Doanh thu / dự án dùng",
              "Giá vốn / dự án dùng", "Lãi gộp / dự án", "Biên gộp", "Biên gộp xấu nhất", "Quy đổi đ/tháng", "So với neo đối thủ",
              "Giờ hỗ trợ / kỳ", "Tối đa cả gói: mô hình đắt nhất, không giới hạn giờ", "% giá", "Tối đa cả gói: ghim mô hình, giới hạn giờ", "% giá"])
plans = [("single", "Dự án lẻ", 5_990_000, 1, 1, 1, "NEO_MONTH", 3),
         ("start", "Start", 17_900_000, 12, 8, 2, "NEO_START", 6),
         ("team", "Team", 34_900_000, 12, 24, 5, "NEO_TEAM", 18),
         ("pro", "Pro", 54_900_000, 12, 60, 10, "NEO_PRO", 30)]
for i, (pid, nm, price, months, projects, seats, neo, hours) in enumerate(plans, 5):
    put(p, f"A{i}", pid, BLUE)
    put(p, f"B{i}", nm, BLUE)
    put(p, f"C{i}", price, BLUE, VND, note="Giá đề xuất 08/11/2026, chưa chốt")
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
    put(p, f"P{i}", hours, BLUE, VND)
    put(p, f"Q{i}", f"=E{i}*VAR_COST_WORST", fmt=VND)
    put(p, f"R{i}", f"=Q{i}/C{i}", fmt=PCT)
    put(p, f"S{i}", f"=E{i}*(VAR_COST_PINNED-SUPPORT_HOURS*2*HOUR_COST)+P{i}*HOUR_COST", fmt=VND)
    put(p, f"T{i}", f"=S{i}/C{i}", fmt=PCT)
    name(p, f"C{i}", f"PRICE_{pid.upper()}")
    name(p, f"E{i}", f"PROJ_{pid.upper()}")
put(p, "A10", "Thiết kế hộ", bold=True)
put(p, "B10", "Dịch vụ thêm, 1 dự án")
put(p, "C10", "=DFY_PRICE", GREEN, VND)
put(p, "J10", "=DFY_HOURS*HOUR_COST+DFY_AI+C10*PAY_FEE", fmt=VND)
put(p, "K10", "=C10-J10", fmt=VND)
put(p, "L10", "=K10/C10", fmt=PCT)
put(p, "A12", "Đọc bảng", bold=True)
notes = ["• Biên gộp cao vì AI, ảnh, máy chủ chỉ vài chục nghìn đồng/dự án. Khoản biến đổi lớn nhất là giờ hỗ trợ, nên gói năm có giới hạn giờ ở cột P.",
         "• Cột 'So với neo đối thủ': Dự án lẻ so Aurora Premium trả tháng; Start so PVsyst; Team so HelioScope Basic; Pro so Aurora Premium trả năm. Đó là sản phẩm 1 người, gói này cho 2–10 ghế.",
         "• Cột Q là trần lý thuyết. Cột S là trần sau khi không dùng mô hình đắt nhất cho khách và giới hạn giờ hỗ trợ.",
         "• Tính lượt theo quy mô chưa đưa vào mô hình: ≤ 30 kWp = 0,2 lượt, 30 kWp–1 MWp = 1 lượt, trên 1 MWp = 1 lượt mỗi MWp."]
for k, line in enumerate(notes, 13):
    put(p, f"A{k}", line, wrap=False)

# ------------------------------------------------------------------------------------------------
# Luu_tru (tiered storage and cold archive)
# ------------------------------------------------------------------------------------------------
l = wb.create_sheet("Luu_tru")
title(l, "Lưu trữ hồ sơ dự án theo bậc và kho lạnh", "Đề xuất 08/11/2026, chưa có trong app. Phí tính theo số dự án đang lưu ngoài phần gói năm đã bao gồm.")
widths(l, [46, 13, 13, 15, 17, 17, 17, 18, 44])
put(l, "A3", "Phí cũ (đ/dự án/tháng, đang chạy trong app)", GREY)
put(l, "D3", 1_000_000, BLUE, VND)
name(l, "D3", "OLD_STORE_FEE")
header(l, 4, ["Bậc", "Từ (dự án)", "Đến (dự án)", "Phí / tháng", "Trả cả năm (đóng 10 tháng)", "Bình quân đ/dự án/tháng", "Chi phí lưu thật / tháng", "Theo phí cũ (đ/tháng)", "Ghi chú"])
for i, (low, high, fee) in enumerate([(1, 8, 299_000), (9, 24, 599_000), (25, 60, 899_000), (61, 150, 1_490_000)], 5):
    put(l, f"A{i}", f"Bậc {i - 4}")
    put(l, f"B{i}", low, BLUE, VND)
    put(l, f"C{i}", high, BLUE, VND)
    put(l, f"D{i}", fee, BLUE, VND, fill=YELLOW)
    put(l, f"E{i}", f"=D{i}*10", fmt=VND)
    put(l, f"F{i}", f"=D{i}/C{i}", fmt=VND)
    put(l, f"G{i}", f"=C{i}*STORE_COST_MONTH", fmt=VND)
    put(l, f"H{i}", f"=C{i}*OLD_STORE_FEE", fmt=VND)
    name(l, f"D{i}", f"TIER_{i - 4}")
put(l, "A9", "Trên 150 dự án: báo giá riêng", GREY)
header(l, 11, ["Gói năm", "Dự án lưu miễn phí", "", "Bậc khi vượt mức", "Phí kho / năm", "Bằng % giá gói"])
for i, (nm, pid, tier) in enumerate([("Start", "START", 1), ("Team", "TEAM", 2), ("Pro", "PRO", 3)], 12):
    put(l, f"A{i}", nm)
    put(l, f"B{i}", f"=PROJ_{pid}", GREEN, VND)
    put(l, f"D{i}", f"=TIER_{tier}", GREEN, VND)
    put(l, f"E{i}", f"=D{i}*12", fmt=VND)
    put(l, f"F{i}", f"=E{i}/PRICE_{pid}", fmt=PCT)
header(l, 16, ["Chính sách khi không đóng phí", "Giá trị", "Đơn vị", "", "", "", "", "", "Ghi chú"])
policy = [("Thời gian chỉ xem và tải về sau hạn", 30, "ngày", "ARCHIVE_GRACE", False, "Nhắc 3 lần: 14 ngày trước, 3 ngày trước, ngày đến hạn"),
          ("Số tháng truy thu tối đa khi khôi phục", 6, "tháng", "RECOVER_MONTHS", True, "Có trần để không thành đòi tiền chuộc dữ liệu"),
          ("Phí khôi phục toàn bộ", 500_000, "đ", "RECOVER_FEE", True, ""),
          ("Phí lấy lẻ 1 dự án từ kho", 299_000, "đ", "RETRIEVE_ONE", True, ""),
          ("Thời hạn giữ trong kho lạnh", 5, "năm", "ARCHIVE_YEARS", True, "CHƯA XÁC MINH: luật sư chốt theo quy định lưu hồ sơ và dữ liệu cá nhân")]
for i, (label, val, unit, n, assumed, note) in enumerate(policy, 17):
    put(l, f"A{i}", label)
    put(l, f"B{i}", val, BLUE, VND, fill=YELLOW if assumed else None)
    put(l, f"C{i}", unit)
    put(l, f"I{i}", note, GREY)
    name(l, f"B{i}", n)
put(l, "A23", "Chi phí kho lạnh 1 dự án / tháng (đ)")
put(l, "B23", "=MB_PROJECT/1024*COLD_PRICE*COLD_COPIES*FX_USD", fmt=NUM)
name(l, "B23", "STORE_COLD_MONTH")
put(l, "A24", "Ví dụ: khách Team bỏ 12 tháng rồi khôi phục (đ)")
put(l, "B24", "=MIN(12,RECOVER_MONTHS)*TIER_2+RECOVER_FEE", fmt=VND)
put(l, "A26", "Điều kiện trước khi bán", bold=True)
for i, text in enumerate(["• Điều khoản ghi rõ dữ liệu được chuyển sang kho lưu trữ, thời hạn giữ và cách yêu cầu xóa thật; không gọi là đã xóa.",
                          "• Kho chỉ giữ phần cần truy vết: bản duyệt, báo cáo, dữ liệu đầu vào, mã niêm phong, thời điểm ký.",
                          "• Cơ quan có thẩm quyền yêu cầu thì cung cấp theo luật, không thu phí khôi phục. Khi có sự cố thật, khách lấy miễn phí bản duyệt đã ký.",
                          "• Chuyển máy chủ sang lưu trữ bền, có sao lưu ngoài và niêm phong SHA-256; đổi purge_expired_projects.py từ xóa hẳn sang chuyển kho.",
                          "• Doanh thu chưa tính phí khôi phục, để thận trọng."], 27):
    put(l, f"A{i}", text)

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
anchors = [("Neo Dự án lẻ: Aurora Premium trả theo tháng (đ/tháng)", "=G7", "NEO_MONTH"),
           ("Neo Start: PVsyst Professional (đ/tháng quy đổi)", "=G11", "NEO_START"),
           ("Neo Team: HelioScope Basic (đ/tháng quy đổi)", "=G9", "NEO_TEAM"),
           ("Neo Pro: Aurora Premium trả năm (đ/tháng quy đổi)", "=G8", "NEO_PRO")]
for j, (label, ref, n) in enumerate(anchors, a + 1):
    put(d, f"A{j}", label)
    put(d, f"G{j}", ref, fmt=VND)
    name(d, f"G{j}", n)
put(d, f"A{a+5}", "Mức rẻ hơn mục tiêu")
put(d, f"G{a+5}", .175, BLUE, PCT, note="Sáng lập viên yêu cầu rẻ hơn 15–20%; lấy giữa khoảng")
name(d, f"G{a+5}", "DISCOUNT_TARGET")
header(d, a + 7, ["Gói SolarOpt", "", "Giá", "", "", "Đ / dự án (SolarOpt)", "Giá đối thủ cùng kỳ", "Chênh theo tiền/kỳ", "Đ / dự án đối thủ (EPC)", "Chênh theo đ/dự án", "Giá cần đặt để rẻ hơn mục tiêu (theo tiền/kỳ)"])
for j, (pid, nm, price, months, projects, seats, neo, hours) in enumerate(plans):
    rr = a + 8 + j
    put(d, f"A{rr}", f"=Goi!B{5+j}", GREEN)
    put(d, f"C{rr}", f"=Goi!C{5+j}", GREEN, VND)
    put(d, f"F{rr}", f"=Goi!G{5+j}", GREEN, VND)
    put(d, f"G{rr}", f"={neo}*Goi!D{5+j}", fmt=VND)
    put(d, f"H{rr}", f"=C{rr}/G{rr}-1", fmt=PCT)
    put(d, f"I{rr}", f"={neo}/EPC_PROJECTS", fmt=VND)
    put(d, f"J{rr}", f"=F{rr}/I{rr}-1", fmt=PCT)
    put(d, f"K{rr}", f"=G{rr}*(1-DISCOUNT_TARGET)", fmt=VND)
put(d, f"A{a+13}", "Đọc bảng: ba gói năm rẻ hơn neo 15–20% theo tiền mỗi kỳ. Tính theo dự án, đối thủ vẫn rẻ hơn với khách làm nhiều dự án, vì họ cho 10–50 dự án/tháng.", wrap=False)

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
              ("Marketing cố định (nội dung, hội thảo, demo tại công trình)", 5_000_000, "tháng", "MKT_FIXED", False, ""),
              ("Văn phòng / chỗ ngồi chung", 5_000_000, "tháng", "OFFICE", True, "Giả định mới; cần báo giá")]
for i, (label, val, kind, n, assumed, src) in enumerate(comp_costs, h + 1):
    put(f, f"A{i}", label)
    put(f, f"B{i}", val, BLUE, VND, fill=YELLOW if assumed else None)
    put(f, f"C{i}", kind)
    put(f, f"E{i}", src, GREY)
    name(f, f"B{i}", n)

s = h + len(comp_costs) + 2
header(f, s, ["Nhân sự, theo thứ tự tuyển", "Lương gross (đ/tháng)", "Tuyển khi đạt (khách)", "Thứ tự", "Ghi chú"])
staff = [("Lập trình viên (backend, AI)", 11_570_000, 0, "Mặt bằng junior ITviec 2025–2026"),
         ("Lập trình viên (giao diện, sản phẩm)", 11_570_000, 0, ""),
         ("Bán hàng / chăm sóc khách hàng kỹ thuật", 11_570_000, 0, ""),
         ("Kỹ sư hỗ trợ điện mặt trời", 11_570_000, 15, "Tin tuyển dụng TP.HCM 2026 ghi 11–25 tr; đổi lương ở đây nếu cần"),
         ("Bán hàng thứ hai", 11_570_000, 30, ""),
         ("Vận hành, tài chính", 11_570_000, 60, "")]
for i, (label, pay, threshold, note) in enumerate(staff, s + 1):
    put(f, f"A{i}", label)
    put(f, f"B{i}", pay, BLUE, VND)
    put(f, f"C{i}", threshold, BLUE, VND, fill=YELLOW)
    put(f, f"D{i}", i - s, fmt="0")
    put(f, f"E{i}", note, GREY)
last_staff = s + len(staff)
STAFF_WAGE = f"Chi_phi_co_dinh!$B${s+1}:$B${last_staff}"
STAFF_FROM = f"Chi_phi_co_dinh!$C${s+1}:$C${last_staff}"
STAFF_ORDER = f"Chi_phi_co_dinh!$D${s+1}:$D${last_staff}"
put(f, f"A{last_staff+1}", "Đóng góp người sử dụng lao động")
put(f, f"B{last_staff+1}", .215, BLUE, PCT)
name(f, f"B{last_staff+1}", "EMPLOYER")
put(f, f"E{last_staff+1}", "BHXH 17,5% + BHYT 3% + BHTN 1%", GREY)
put(f, f"A{last_staff+2}", "Tỷ lệ lương trả bằng tiền năm đầu")
put(f, f"B{last_staff+2}", 1, BLUE, PCT, fill=YELLOW)
name(f, f"B{last_staff+2}", "PAY_RATIO_Y1")
put(f, f"A{last_staff+3}", "Quỹ lương khi đủ 6 người, đủ lương (đ/tháng)", bold=True)
put(f, f"B{last_staff+3}", f"=SUM(B{s+1}:B{last_staff})*(1+B{last_staff+1})", fmt=VND, bold=True)

# ------------------------------------------------------------------------------------------------
# Dong_tien (36-month cash flow)
# ------------------------------------------------------------------------------------------------
c = wb.create_sheet("Dong_tien")
title(c, "Dòng tiền 36 tháng (VND) — tháng 1 = tháng đầu bán (Gia_dinh: LAUNCH)", "Dòng chữ xanh là dự báo đầu vào (giả định); còn lại là công thức. Gói năm thu tiền ngay khi mua, nên đây là số theo tiền thu, không phân bổ doanh thu.")
c.column_dimensions["A"].width = 58
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


def ago(m, r, months):
    return f"{mc(m - months)}{r}" if m > months else "0"


def last12(m, r):
    return f"SUM({mc(max(1, m - 11))}{r}:{mc(m)}{r})"


row(3, "Tháng thứ", lambda m: m, "0")
row(4, "Kỳ", lambda m: f"=EDATE(LAUNCH,{mc(m)}3-1)", "mm/yyyy")
put(c, "A6", "KHÁCH VÀ LƯỢT MUA", bold=True)
row(7, "  Lượt mua Dự án lẻ — cơ sở", lambda m: tiers(m, 1, 2, 3, 4), NUM, BLUE)
row(8, "  Lượt mua Dự án lẻ — theo kịch bản", lambda m: f"={mc(m)}7*SCENARIO", NUM)
row(9, "  Khách gói năm mới — cơ sở", lambda m: tiers(m, 1.33, 2.33, 2.5, 3.33), NUM, BLUE)
row(10, "  Khách gói năm mới — theo kịch bản", lambda m: f"={mc(m)}9*SCENARIO", NUM)
row(11, "  Start mua mới", lambda m: f"={mc(m)}10*MIX_START", NUM)
row(12, "  Team mua mới", lambda m: f"={mc(m)}10*MIX_TEAM", NUM)
row(13, "  Pro mua mới", lambda m: f"={mc(m)}10*MIX_PRO", NUM)
row(14, "  Start gia hạn", lambda m: f"={ago(m, 17, 12)}*RENEW", NUM)
row(15, "  Team gia hạn", lambda m: f"={ago(m, 18, 12)}*RENEW", NUM)
row(16, "  Pro gia hạn", lambda m: f"={ago(m, 19, 12)}*RENEW", NUM)
row(17, "  Start tổng lượt mua", lambda m: f"={mc(m)}11+{mc(m)}14", NUM)
row(18, "  Team tổng lượt mua", lambda m: f"={mc(m)}12+{mc(m)}15", NUM)
row(19, "  Pro tổng lượt mua", lambda m: f"={mc(m)}13+{mc(m)}16", NUM)
row(20, "  Gói năm đang hiệu lực", lambda m: f"={last12(m, 17)}+{last12(m, 18)}+{last12(m, 19)}", NUM)
row(21, "Khách trả phí đang hoạt động", lambda m: f"={mc(m)}8+{mc(m)}20", NUM, bold=True)
row(22, "  Số khách cao nhất từ đầu (mốc tuyển người)", lambda m: f"=MAX({ago(m, 22, 1)},{mc(m)}21)", NUM)
row(23, "  Dự án Thiết kế hộ — cơ sở", lambda m: tiers(m, 2, 3, 3, 4), NUM, BLUE)
row(24, "  Dự án Thiết kế hộ — theo kịch bản", lambda m: f"={mc(m)}23*SCENARIO", NUM)
put(c, "A26", "DỰ ÁN", bold=True)
row(27, "  Dự án dùng từ Dự án lẻ", lambda m: f"={mc(m)}8*PROJ_SINGLE", NUM)
row(28, "  Dự án dùng từ gói năm (rải đều 12 tháng)", lambda m: f"=({last12(m, 17)}*PROJ_START+{last12(m, 18)}*PROJ_TEAM+{last12(m, 19)}*PROJ_PRO)/12*UTIL", NUM)
row(29, "  Tổng dự án dùng trong tháng", lambda m: f"={mc(m)}27+{mc(m)}28", NUM, bold=True)
row(30, "  Dự án tích lũy trong hệ thống", lambda m: f"={ago(m, 30, 1)}+{mc(m)}29", NUM)
row(31, "  Người dùng thử mới", lambda m: f"=({mc(m)}8*NEW_SHARE+{mc(m)}10)*TRIALS_PER_CUSTOMER", NUM)
put(c, "A32", "KHÁCH ĐÓNG PHÍ KHO LƯU TRỮ (phí năm đầu gần như bằng 0 vì gói năm chưa hết hạn)", bold=True)
row(33, "  Bậc 1: khách lẻ và Start", lambda m: f"={ago(m, 33, 1)}*(1-1/STORE_MONTHS)+({ago(m, 8, 1)}*NEW_SHARE+{ago(m, 17, 12)})*STORE_SHARE", NUM)
row(34, "  Bậc 2: khách Team", lambda m: f"={ago(m, 34, 1)}*(1-1/STORE_MONTHS)+{ago(m, 18, 12)}*STORE_SHARE", NUM)
row(35, "  Bậc 3: khách Pro", lambda m: f"={ago(m, 35, 1)}*(1-1/STORE_MONTHS)+{ago(m, 19, 12)}*STORE_SHARE", NUM)
put(c, "A37", "DOANH THU", bold=True)
row(38, "  Dự án lẻ", lambda m: f"={mc(m)}8*PRICE_SINGLE")
row(39, "  Gói năm (thu khi mua)", lambda m: f"={mc(m)}17*PRICE_START+{mc(m)}18*PRICE_TEAM+{mc(m)}19*PRICE_PRO")
row(40, "  Khách pilot trong tháng", lambda m: f"=MAX(0,MIN({mc(m)}10,PILOT_CUSTOMERS-{f'SUM($C10:{mc(m - 1)}10)' if m > 1 else '0'}))", NUM)
row(41, "  Giảm giá pilot (chỉ gói năm)", lambda m: f"=IF({mc(m)}10=0,0,-{mc(m)}40*PILOT_DISC*({mc(m)}11*PRICE_START+{mc(m)}12*PRICE_TEAM+{mc(m)}13*PRICE_PRO)/{mc(m)}10)")
row(42, "  Trừ tiền lẻ khi nâng lên gói năm", lambda m: f"=-{mc(m)}10*UPGRADE_SHARE*PRICE_SINGLE")
row(43, "  Thiết kế hộ", lambda m: f"={mc(m)}24*DFY_PRICE")
row(44, "  Phí kho lưu trữ", lambda m: f"={mc(m)}33*TIER_1+{mc(m)}34*TIER_2+{mc(m)}35*TIER_3")
row(45, "TỔNG DOANH THU", lambda m: f"=SUM({mc(m)}38:{mc(m)}39)+SUM({mc(m)}41:{mc(m)}44)", bold=True)
put(c, "A47", "GIÁ VỐN", bold=True)
row(48, "  Chi phí biến đổi dự án (gồm dùng thử)", lambda m: f"=({mc(m)}29+{mc(m)}31)*VAR_COST")
row(49, "  Thiết kế hộ", lambda m: f"={mc(m)}24*(DFY_HOURS*HOUR_COST+DFY_AI)")
row(50, "  Kho lạnh", lambda m: f"={mc(m)}30*STORE_COLD_MONTH")
row(51, "  Phí thanh toán", lambda m: f"={mc(m)}45*PAY_FEE")
row(52, "TỔNG GIÁ VỐN", lambda m: f"=SUM({mc(m)}48:{mc(m)}51)", bold=True)
row(53, "LÃI GỘP", lambda m: f"={mc(m)}45-{mc(m)}52", bold=True)
put(c, "A55", "CHI PHÍ HOẠT ĐỘNG", bold=True)
row(56, "  Hạ tầng (theo giai đoạn)", lambda m: f"=IF({mc(m)}21<=STAGE_2,INFRA_1,IF({mc(m)}21<=STAGE_3,INFRA_2,INFRA_3))*FX_USD")
row(57, "  Số nhân sự (theo mốc khách hoặc FIXED_STAFF)", lambda m: f'=IF(FIXED_STAFF>0,FIXED_STAFF,COUNTIF({STAFF_FROM},"<="&{mc(m)}22))', "0")
row(58, "  Nhân sự", lambda m: f"=SUMPRODUCT(({STAFF_ORDER}<={mc(m)}57)*{STAFF_WAGE})*(1+EMPLOYER)*IF({mc(m)}3<=12,PAY_RATIO_Y1,1)")
row(59, "  Pháp lý, tuân thủ, bảo hiểm, kỹ sư cố vấn, công cụ, văn phòng", lambda m: f"=IF({mc(m)}3=1,LEGAL_ONCE+PDPL_ONCE,0)+ACCOUNTING+INSURANCE/12+ADVISOR_ENG+IF({mc(m)}3>12,PENTEST/12,0)+MODEL_EVAL/12+TOOLS+OFFICE")
row(60, "  Marketing (cố định + chi phí có khách mới)", lambda m: f"=MKT_FIXED+CAC*({mc(m)}8*NEW_SHARE+{mc(m)}10)")
row(61, "  Dự phòng trên chi phí cố định", lambda m: f"=CONTINGENCY*({mc(m)}56+{mc(m)}58+{mc(m)}59+MKT_FIXED)")
row(62, "TỔNG CHI PHÍ HOẠT ĐỘNG", lambda m: f"={mc(m)}56+SUM({mc(m)}58:{mc(m)}61)", bold=True)
row(63, "EBITDA", lambda m: f"={mc(m)}53-{mc(m)}62", bold=True)
row(64, "  Thuế TNDN", lambda m: f"=MAX(0,{mc(m)}63)*TAX")
row(65, "LỢI NHUẬN RÒNG", lambda m: f"={mc(m)}63-{mc(m)}64", bold=True)
row(66, "  Vốn góp / gọi vốn", lambda m: {1: 250_000_000, 4: 200_000_000, 8: 150_000_000}.get(m, 0), VND, BLUE)
row(67, "TIỀN MẶT CUỐI THÁNG", lambda m: (f"={mc(m-1)}67+" if m > 1 else "=") + f"{mc(m)}65+{mc(m)}66", bold=True)
row(68, "  (phụ) tháng có EBITDA ≥ 0", lambda m: f"=IF({mc(m)}63>=0,{mc(m)}3,999)", "0")
c.freeze_panes = "C5"

# ------------------------------------------------------------------------------------------------
# Hoa_von (fewest buyers to break even in year one)
# ------------------------------------------------------------------------------------------------
b = wb.create_sheet("Hoa_von")
title(b, "Số khách tối thiểu để hòa vốn và đạt lãi mục tiêu năm đầu", "Một loại gói cho toàn bộ khách, để làm nền so sánh. Tối đa = mỗi dự án dùng hết hạn mức bằng mô hình đắt nhất (Chi_phi_du_an cột C). Chưa tính doanh thu lưu trữ và Thiết kế hộ.")
widths(b, [50, 12, 16, 15, 15, 15, 15, 15, 15])
put(b, "A4", "Lãi mục tiêu năm đầu")
put(b, "B4", "=TARGET_PROFIT", GREEN, VND)
put(b, "A5", "Số tháng bình quân khi khách lẻ vào rải đều trong năm")
put(b, "B5", 6.5, BLUE, NUM, fill=YELLOW)
put(b, "A6", "Giá gói Năm · 3 dự án của bảng giá 07/11 (để so)")
put(b, "B6", 15_000_000, BLUE, VND)
header(b, 8, ["Phương án nhân sự", "", ""] + ["6 người đủ lương", "5 người đủ lương", "6 người, lương 15 tr", "6 người nửa lương", "3 người đủ lương", "3 người nửa lương"])
cases = [(6, 11_570_000, 1), (5, 11_570_000, 1), (6, 15_000_000, 1), (6, 11_570_000, .5), (3, 11_570_000, 1), (3, 11_570_000, .5)]
CC = "DEFGHI"
labels = ["Số người", "Lương gross (đ/tháng)", "Tỷ lệ lương trả năm đầu", "Quỹ lương (đ/tháng)", "Chi phí cố định, tới 30 khách (đ/tháng)", "Chi phí cố định cả năm, tới 30 khách", "Chi phí cố định cả năm, 31–120 khách", "Chi phí cố định cả năm, trên 120 khách"]
for i, text in enumerate(labels, 9):
    put(b, f"A{i}", text)
OTHER_MONTH = "(ACCOUNTING+INSURANCE/12+ADVISOR_ENG+MODEL_EVAL/12+TOOLS+MKT_FIXED+OFFICE)"
for k, (people, wage, ratio) in zip(CC, cases):
    put(b, f"{k}9", people, BLUE, "0")
    put(b, f"{k}10", wage, BLUE, VND)
    put(b, f"{k}11", ratio, BLUE, PCT)
    put(b, f"{k}12", f"={k}9*{k}10*(1+EMPLOYER)*{k}11", fmt=VND)
    put(b, f"{k}13", f"={k}12+INFRA_1*FX_USD+{OTHER_MONTH}", fmt=VND)
    for r_, infra_ in ((14, "INFRA_1"), (15, "INFRA_2"), (16, "INFRA_3")):
        put(b, f"{k}{r_}", f"=(({k}12+{infra_}*FX_USD+{OTHER_MONTH})*12+LEGAL_ONCE+PDPL_ONCE)*(1+CONTINGENCY)", fmt=VND)
products = [("Mua lẻ mỗi tháng, đủ 12 tháng từ tháng 1", "Tối đa", "=12*(PRICE_SINGLE*(1-PAY_FEE)-VAR_COST_WORST)"),
            ("Mua lẻ mỗi tháng, đủ 12 tháng từ tháng 1", "Dự kiến", "=12*(PRICE_SINGLE*(1-PAY_FEE)-VAR_COST)"),
            ("Mua lẻ mỗi tháng, khách vào rải đều trong năm", "Tối đa", "=$B$5*(PRICE_SINGLE*(1-PAY_FEE)-VAR_COST_WORST)"),
            ("Mua lẻ mỗi tháng, khách vào rải đều trong năm", "Dự kiến", "=$B$5*(PRICE_SINGLE*(1-PAY_FEE)-VAR_COST)"),
            ("Mua lẻ 3 lần/năm", "Tối đa", "=3*(PRICE_SINGLE*(1-PAY_FEE)-VAR_COST_WORST)"),
            ("Mua lẻ 3 lần/năm", "Dự kiến", "=3*(PRICE_SINGLE*(1-PAY_FEE)-VAR_COST)"),
            ("Toàn gói Năm · 3 dự án (bảng giá 07/11)", "Tối đa", "=$B$6*(1-PAY_FEE)-3*VAR_COST_WORST"),
            ("Toàn gói Năm · 3 dự án (bảng giá 07/11)", "Dự kiến", "=$B$6*(1-PAY_FEE)-3*UTIL*VAR_COST"),
            ("Toàn gói Start (gói năm rẻ nhất)", "Tối đa", "=PRICE_START*(1-PAY_FEE)-PROJ_START*VAR_COST_WORST"),
            ("Toàn gói Start (gói năm rẻ nhất)", "Dự kiến", "=PRICE_START*(1-PAY_FEE)-PROJ_START*UTIL*VAR_COST"),
            ("Trộn Start, Team, Pro theo tỷ lệ ở Gia_dinh", "Dự kiến",
             "=(MIX_START*PRICE_START+MIX_TEAM*PRICE_TEAM+MIX_PRO*PRICE_PRO)*(1-PAY_FEE)-(MIX_START*PROJ_START+MIX_TEAM*PROJ_TEAM+MIX_PRO*PROJ_PRO)*UTIL*VAR_COST")]


def breakeven_block(top, cac, cac_note):
    put(b, f"A{top}", f"Chi phí có 1 khách: {cac_note}", bold=True)
    put(b, f"B{top}", cac, GREEN, VND)
    header(b, top + 1, ["Trường hợp", "Mức dùng", "Đóng góp / khách, chưa trừ chi phí có khách"] + [f"={k}8" for k in CC])
    for i, (label, level, formula) in enumerate(products, top + 2):
        put(b, f"A{i}", label)
        put(b, f"B{i}", level)
        put(b, f"C{i}", formula, fmt=VND)
        margin = f"($C{i}-$B${top}-TRIALS_PER_CUSTOMER*VAR_COST)"
        for k in CC:
            n1, n2, n3 = [f"ROUNDUP(({k}${r_}+$B$4)/{margin},0)" for r_ in (14, 15, 16)]
            put(b, f"{k}{i}", f'=IF({margin}<=0,"Không hòa vốn",IF({n1}<=STAGE_2,{n1},IF(MAX(STAGE_2+1,{n2})<=STAGE_3,MAX(STAGE_2+1,{n2}),MAX(STAGE_3+1,{n3}))))', fmt="#,##0")


breakeven_block(18, "=CAC", "mức trong Gia_dinh")
breakeven_block(32, "=CAC_LOW", "mức thấp, sáng lập viên tự bán")
put(b, "A46", "Đọc bảng", bold=True)
for k_, text in enumerate(["• Hai dòng mua lẻ đủ 12 tháng chỉ là nền lý thuyết: khách sẽ trả 71,9 tr cho 12 dự án, trong khi Team là 34,9 tr cho 24 dự án.",
                           "• Mức Tối đa tính cao hơn thực tế vì giờ hỗ trợ đã có người trong lương; số thật nằm giữa hai mức.",
                           "• Số khách là số phải có, không phải dự báo. Chưa có dữ liệu về số EPC tại TP.HCM và mức giá khách chấp nhận."], 47):
    put(b, f"A{k_}", text)

# ------------------------------------------------------------------------------------------------
# Tong_hop (summary)
# ------------------------------------------------------------------------------------------------
t = wb.create_sheet("Tong_hop", 1)
title(t, "Tổng hợp kết quả", "Năm 1 = 12 tháng đầu bán. Mọi số là công thức từ Dong_tien, Goi, Chi_phi_du_an")
widths(t, [50, 18, 18, 18, 50])
header(t, 4, ["Chỉ tiêu (VND)", "Năm 1", "Năm 2", "Năm 3", "Ghi chú"])
yr = [("C", "N"), ("O", "Z"), ("AA", "AL")]
summary = [("Lượt mua Dự án lẻ", [8]), ("Lượt mua gói năm (mới + gia hạn)", [17, 18, 19]), ("Dự án được tính", [29]),
           ("Doanh thu Dự án lẻ", [38]), ("Doanh thu gói năm, sau giảm giá và trừ tiền lẻ", [39, 41, 42]), ("Doanh thu Thiết kế hộ", [43]),
           ("Doanh thu kho lưu trữ", [44]), ("Tổng doanh thu", [45]), ("Giá vốn", [52]), ("Lãi gộp", [53]),
           ("Chi phí hoạt động", [62]), ("EBITDA", [63]), ("Lợi nhuận ròng", [65])]
for i, (label, rows_) in enumerate(summary, 5):
    put(t, f"A{i}", label, bold=label in ("Tổng doanh thu", "Lợi nhuận ròng"))
    for j, (a_, b_) in enumerate(yr):
        put(t, f"{'BCD'[j]}{i}", "=" + "+".join(f"SUM(Dong_tien!{a_}{r_}:{b_}{r_})" for r_ in rows_), GREEN, NUM if i <= 7 else VND)
REV, GROSS = 12, 14
put(t, "A18", "Biên lãi gộp")
put(t, "A19", "Tiền mặt cuối năm")
put(t, "A20", "Số nhân sự cuối năm")
put(t, "A21", "Khách trả phí đang hoạt động cuối năm")
for j, (a_, b_) in enumerate(yr):
    put(t, f"{'BCD'[j]}18", f"=IF({'BCD'[j]}{REV}=0,0,{'BCD'[j]}{GROSS}/{'BCD'[j]}{REV})", fmt=PCT)
    put(t, f"{'BCD'[j]}19", f"=Dong_tien!{b_}67", GREEN, VND)
    put(t, f"{'BCD'[j]}20", f"=Dong_tien!{b_}57", GREEN, "0")
    put(t, f"{'BCD'[j]}21", f"=Dong_tien!{b_}21", GREEN, NUM)
put(t, "A23", "Chỉ số then chốt", bold=True)
key = [("Tháng đầu tiên có EBITDA ≥ 0", "=IF(MIN(Dong_tien!C68:AL68)=999,\"Chưa có lãi trong 36 tháng\",INDEX(Dong_tien!C4:AL4,MATCH(MIN(Dong_tien!C68:AL68),Dong_tien!C3:AL3,0)))", "mm/yyyy"),
       ("Tiền mặt thấp nhất trong 36 tháng", "=MIN(Dong_tien!C67:AL67)", VND),
       ("Đủ vốn? (tiền mặt không âm)", "=IF(B25>=0,\"Đủ\",\"THIẾU VỐN\")", None),
       ("Tổng vốn góp", "=SUM(Dong_tien!C66:AL66)", VND),
       ("Vốn cần thêm để tiền mặt không âm", "=MAX(0,-B25)", VND),
       ("Chi phí biến đổi / dự án (dự kiến)", "=VAR_COST", VND),
       ("  trong đó AI", "=AI_COST", VND),
       ("Chi phí biến đổi / dự án (tối đa, ghim mô hình)", "=VAR_COST_PINNED", VND),
       ("Chi phí biến đổi / dự án (tối đa, mô hình đắt nhất)", "=VAR_COST_WORST", VND),
       ("Chi phí biến đổi / giá rẻ nhất mỗi dự án", "=VAR_COST/MIN(Goi!G5:G8)", '0.00%'),
       ("Mô hình đọc ảnh / tư vấn / trợ lý", "=VISION_MODEL&\" / \"&ADVISOR_MODEL&\" / \"&CHAT_MODEL", None),
       ("Hệ số kịch bản", "=SCENARIO", NUM)]
for i, (label, formula, fmt) in enumerate(key, 24):
    put(t, f"A{i}", label)
    put(t, f"B{i}", formula, GREEN, fmt)
put(t, "E24", "Theo giả định số lượt mua ở Dong_tien — chưa có dữ liệu khách", GREY)
put(t, "E33", "Chi phí AI, ảnh, máy chủ rất nhỏ so với giá gói: rủi ro nằm ở số khách và quỹ lương", GREY)

for sheet in wb.worksheets:
    sheet.sheet_view.showGridLines = False
    for rw in sheet.iter_rows():
        for cell in rw:
            if cell.font and cell.font.name != FONT:
                cell.font = Font(name=FONT, color=cell.font.color, bold=cell.font.bold, size=cell.font.size or 10, italic=cell.font.italic)

OUT.parent.mkdir(parents=True, exist_ok=True)
wb.save(OUT)
print("saved", OUT)
