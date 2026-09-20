from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.schemas import VisionObstacle, VisionResult


def _fallback() -> VisionResult:
    return VisionResult(
        mode="demo",
        roof_width_m=10.0,
        roof_height_m=8.0,
        roof_confidence=0.72,
        obstacles=[
            VisionObstacle(id="tank", label="Bồn nước", x_pct=57, y_pct=46, width_pct=12, depth_pct=14, height_m=1.2, confidence=0.88),
            VisionObstacle(id="vent", label="Ống thông gió", x_pct=25, y_pct=28, width_pct=7, depth_pct=8, height_m=0.7, confidence=0.74),
        ],
        extracted_text=[],
        notes=["Chưa cấu hình GEMINI_API_KEY nên dùng hình học demo. Bạn vẫn có thể chỉnh thủ công trước khi tối ưu."],
    )


def _pdf_to_png(data: bytes) -> tuple[bytes, str]:
    try:
        import fitz
        doc = fitz.open(stream=data, filetype="pdf")
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
        return pix.tobytes("png"), "image/png"
    except Exception:
        return data, "application/pdf"


def analyze_image(data: bytes, mime_type: str) -> VisionResult:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite").strip()
    if not key:
        return _fallback()

    if mime_type == "application/pdf":
        data, mime_type = _pdf_to_png(data)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=key)
        prompt = """
Bạn là mô-đun thị giác của SolarOpt, hỗ trợ kỹ sư đọc ảnh/bản vẽ mái nhà để thiết kế điện mặt trời.
Hãy trả về JSON duy nhất với schema:
{
  "roof_width_m": number,
  "roof_height_m": number,
  "roof_confidence": 0..1,
  "obstacles": [
    {"id":"...","label":"...","x_pct":0..100,"y_pct":0..100,"width_pct":0..100,"depth_pct":0..100,"height_m":number,"confidence":0..1}
  ],
  "extracted_text": ["..."],
  "notes": ["..."]
}
Quy ước x_pct/y_pct là góc trái dưới của bounding box trong hệ tọa độ mái đã chuẩn hóa. Nếu không đọc được kích thước thật, ước lượng roof_width_m=10 và roof_height_m=8 và ghi rõ trong notes. Chỉ nhận diện vật cản có ảnh hưởng lắp pin như bồn nước, tum, giếng trời, ống thông gió, cây/công trình che bóng sát mái. Không bịa độ chính xác tuyệt đối; confidence phải phản ánh mức chắc chắn.
"""
        response = client.models.generate_content(
            model=model_name,
            contents=[types.Part.from_bytes(data=data, mime_type=mime_type), prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.1),
        )
        raw = json.loads(response.text)
        obstacles = [VisionObstacle(**o) for o in raw.get("obstacles", [])]
        return VisionResult(
            mode="gemini",
            roof_width_m=float(raw.get("roof_width_m", 10.0)),
            roof_height_m=float(raw.get("roof_height_m", 8.0)),
            roof_confidence=float(raw.get("roof_confidence", 0.5)),
            obstacles=obstacles,
            extracted_text=[str(x) for x in raw.get("extracted_text", [])],
            notes=[str(x) for x in raw.get("notes", [])],
        )
    except Exception as exc:
        result = _fallback()
        result.notes.insert(0, f"Gemini lỗi ({type(exc).__name__}); chuyển sang demo fallback để không chặn luồng.")
        return result
