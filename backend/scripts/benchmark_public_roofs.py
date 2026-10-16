"""Reproducible image-outline benchmark; optional dependency: tifffile.

Uses annotated bounding boxes to simulate engineer target selection, never uses
reference polygons as foreground seeds. This is NOT automatic roof detection.
"""
from pathlib import Path
import argparse
import hashlib
import html
import json
import sys
import urllib.request
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.roof_extract import TraceRequest, data_url, extract_roof

REV = 'c48938260f1755089ac9510e500f5c93f8c465aa'
FILES = {
    'LICENSE': ('LICENSE', 'a2010f343487d3f7618affe54f789f5487602331c0a8d03f49e9a7c547cf0499'),
    '01.geojson': ('datasets/sample/test/01.geojson', '95595a16046282abea1bcc427a561f3492cac6daeb5cd232f689e15a4ce24a59'),
    '01.tif': ('datasets/sample/test/01.tif', '22640a3a013fa1aa589b513d94ee398073d2b4b877e26e2b038e729e8414687f'),
}


def fetch(root):
    root.mkdir(parents=True, exist_ok=True)
    for name, (remote, digest) in FILES.items():
        path = root / name
        if not path.exists():
            url = f'https://raw.githubusercontent.com/mosquito-risk/Nacala/{REV}/{remote}'
            with urllib.request.urlopen(url, timeout=60) as response:
                content = response.read(48_000_001)
            if len(content) > 48_000_000:
                raise ValueError('File exceeds download limit')
            if hashlib.sha256(content).hexdigest() != digest:
                raise ValueError(f'Checksum mismatch: {name}')
            path.write_bytes(content)
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f'Checksum mismatch: {name}')


def pixel_ring(ring, scale, tie):
    return np.array([[(p[0]-tie[3])/scale[0]+tie[0],
                      (tie[4]-p[1])/scale[1]+tie[1]] for p in ring])


def iou(reference, prediction):
    union = np.count_nonzero(reference | prediction)
    return float(np.count_nonzero(reference & prediction) / union) if union else 0.0


def run(root, out):
    import tifffile
    fetch(root)
    out.mkdir(parents=True, exist_ok=True)
    with tifffile.TiffFile(root/'01.tif') as t:
        meta = t.geotiff_metadata
        # This fixture is geographic WGS84, north-up, with 4 signed-int16 bands.
        if int(meta['GeographicTypeGeoKey']) != 4326:
            raise ValueError('Unsupported fixture CRS')
        if 'ModelTransformation' in meta:
            raise ValueError('Rotated georeferencing requires another transform')
        raw = t.asarray()
    rgb = raw[:, :, :3]
    valid = np.all((rgb >= 0) & (rgb <= 255), axis=2)
    print('RGB range:', int(rgb.min()), int(rgb.max()), 'valid fraction:', float(valid.mean()), flush=True)
    image = np.clip(rgb, 0, 255).astype(np.uint8)[:, :, ::-1].copy()
    features = json.loads((root/'01.geojson').read_text())['features']
    results, cards = [], []
    for index, feature in enumerate(features):
        geom = feature['geometry']
        polygons = geom['coordinates'] if geom['type']=='MultiPolygon' else [geom['coordinates']]
        rings = [[pixel_ring(r, meta['ModelPixelScale'], meta['ModelTiepoint']) for r in poly] for poly in polygons]
        points = np.concatenate([p[0] for p in rings])
        lo, hi = np.floor(points.min(axis=0)).astype(int), np.ceil(points.max(axis=0)).astype(int)
        row = {'index': index, 'fid': feature['properties'].get('fid'), 'status': 'excluded'}
        # Keep clipped roofs in the manifest, not in misleading accuracy totals.
        if np.any(lo < 2) or hi[0] >= image.shape[1]-2 or hi[1] >= image.shape[0]-2 or np.any(hi-lo < 12):
            row['reason'] = 'clipped_or_smaller_than_12px'
            results.append(row)
            continue
        pad = max(12, int(max(hi-lo)*.2))
        x0,y0 = np.maximum(lo-pad, 0)
        x1,y1 = np.minimum(hi+pad, [image.shape[1], image.shape[0]])
        crop = image[y0:y1,x0:x1].copy()
        h,w = crop.shape[:2]
        ref = np.zeros((h,w), np.uint8)
        for poly in rings:
            cv2.fillPoly(ref, [np.rint(poly[0]-[x0,y0]).astype(np.int32)], 1)
            for hole in poly[1:]:
                cv2.fillPoly(ref, [np.rint(hole-[x0,y0]).astype(np.int32)], 0)
        # Fixed 3px margin around the labelled bbox; no reference boundary/seed.
        left,top = np.maximum(lo-[x0,y0]-3, 1)
        right,bottom = np.minimum(hi-[x0,y0]+3, [w-1,h-1])
        rect = [left/w*100,top/h*100,(right-left)/w*100,(bottom-top)/h*100]
        pred = np.zeros_like(ref)
        try:
            cv2.setRNGSeed(2026+index)
            result = extract_roof(TraceRequest(image_data_url=data_url(crop), rect=rect))
            vertices = np.array([[p['x']*w/100,p['y']*h/100] for p in result['polygon_image_pct']])
            cv2.fillPoly(pred, [np.rint(vertices).astype(np.int32)], 1)
            for ring in result.get('openings_image_pct', []):
                hole=np.array([[p['x']*w/100,p['y']*h/100] for p in ring])
                cv2.fillPoly(pred,[np.rint(hole).astype(np.int32)],0)
            row.update(status='evaluated',elapsed_ms=result['elapsed_ms'])
        except ValueError as exc:
            row.update(status='failed',reason=str(exc))
        row['iou'] = round(iou(ref.astype(bool), pred.astype(bool)), 5)
        overlay = crop.copy()
        for mask,color in [(ref,(70,210,80)),(pred,(20,130,255))]:
            contours,_ = cv2.findContours(mask,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(overlay,contours,-1,color,1)
        name=f'roof_{index:02}.png'
        cv2.imwrite(str(out/name), overlay)
        cards.append(f'<article><h3>Mái {index} · IoU {row["iou"]:.3f}</h3><img src="{name}" alt="Đường biên đối chiếu mái {index}"><p>{html.escape(row["status"])}</p></article>')
        results.append(row)
        print(index, row['status'], row['iou'], flush=True)
    eligible = [r for r in results if r['status']!='excluded']
    report = {'dataset':'Nacala public test/01', 'source': 'https://github.com/mosquito-risk/Nacala',
              'revision': REV, 'license':'CC0-1.0', 'protocol':'GT-bbox-conditioned GrabCut; no polygon seeds; failures count as IoU zero',
              'total':len(results), 'eligible':len(eligible), 'failed':sum(r['status']=='failed' for r in eligible),
              'mean_iou':float(np.mean([r['iou'] for r in eligible])) if eligible else None,
              'median_iou':float(np.median([r['iou'] for r in eligible])) if eligible else None,
              'iou_ge_075':sum(r['iou']>=.75 for r in eligible), 'cases':results,
              'limits':['Single location and image; annotated target boxes supplied', 'Pixel outline only; no surveyed lengths, heights, shadow or energy validation']}
    (out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    intro=f'<h1>SolarOpt · Đối chiếu ảnh mái công khai</h1><p>{len(eligible)}/{len(results)} mái đủ điều kiện; IoU trung bình {report["mean_iou"]:.3f}; {report["failed"]} ca tách thất bại.</p>'
    (out/'report.html').write_text('<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SolarOpt · Kiểm chứng biên mái</title><style>body{font:16px system-ui;background:#f5f7f3;color:#183b32;margin:24px auto;max-width:1100px;padding:16px}section{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px}article{background:white;padding:16px;border-radius:16px}img{max-width:100%;image-rendering:auto}</style>'+intro+'<p>Nguồn: <a href="https://github.com/mosquito-risk/Nacala">Nacala (CC0)</a>. Xanh: nhãn tham chiếu; cam: kết quả SolarOpt.</p><p>Khung chọn mái được lấy từ nhãn để mô phỏng kỹ sư khoanh vùng. Không phải phép đo khả năng tự tìm mái. Ca lỗi tính điểm 0. Chưa kiểm chứng kích thước thực, bóng che hay sản lượng.</p><section>'+''.join(cards)+'</section></html>',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='cases'},ensure_ascii=False),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,default=Path('data/public/nacala'))
    parser.add_argument('--out',type=Path,default=Path('output/validation/public_nacala'))
    args=parser.parse_args()
    run(args.data,args.out)
