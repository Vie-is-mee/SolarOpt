"""Record the live vision answer for the bundled drone photo so demo mode can replay it on stage.

Run from backend/ with the AI keys in backend/.env:
    python scripts/record_demo_vision.py ../frontend/public/demo/anh-drone-mai-nha.png 12 9
The width and depth must match what the presenter types in step 1, or the replay will not match.
"""
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app import demo  # noqa: E402
from app.services.vision import VisionError, analyze_images  # noqa: E402

image, width, depth = Path(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3])
files = [(image.read_bytes(), "image/png" if image.suffix.lower() == ".png" else "image/jpeg")]
# Free shared models are often busy or answer badly; try a few times and keep the first valid answer.
for attempt in range(1, 5):
    try:
        result = analyze_images(files, "drone", width, depth)
        break
    except VisionError as exc:
        print(f"attempt {attempt}: {exc}")
else:
    sys.exit("No valid answer; nothing recorded.")
if result.mode == "manual":
    sys.exit("AI is not configured; nothing recorded.")
key = demo.vision_key(files, "drone", width, depth)
demo.save("vision", key, result.model_dump(), result.model, result.elapsed_ms)
print(f"vision-{key}.json · {result.model} · {result.elapsed_ms / 1000:.0f} s · {len(result.obstacles)} obstacles · {result.roof_shape}")
for event in result.events:
    print(" ", event["stage"], event["status"], event["detail"][:120])
