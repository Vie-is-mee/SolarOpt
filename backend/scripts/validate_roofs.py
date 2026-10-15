"""Offline reference comparison: python scripts/validate_roofs.py manifest.json --out output_dir"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.validation import ValidationCase,evaluate_case
from app.services.validation_report import render_report


def main():
    parser=argparse.ArgumentParser(description='Đối chiếu mái SolarOpt với dữ liệu có nguồn, không gọi AI.')
    parser.add_argument('manifest',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    try:
        if args.manifest.stat().st_size>10_000_000:raise ValueError('Tệp đối chiếu tối đa 10 MB.')
        raw=json.loads(args.manifest.read_text(encoding='utf-8-sig'))
        if raw.get('format')!='solaropt-validation-v1':raise ValueError('Sai định dạng solaropt-validation-v1.')
        cases=[ValidationCase.model_validate(case) for case in raw['cases']]
        if not 1<=len(cases)<=100 or len({case.id for case in cases})!=len(cases):
            raise ValueError('Cần 1–100 ca với ID riêng.')
        results=[evaluate_case(case) for case in cases]
    except (OSError,ValueError,KeyError,TypeError) as exc:parser.error(str(exc))
    created=datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).isoformat(timespec='seconds')
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'results.json').write_text(json.dumps({'format':'solaropt-validation-result-v1','created_at':created,'cases':results},ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    (args.out/'report.html').write_text(render_report(results,created),encoding='utf-8')
    for result in results:print(f"{result['id']}: {result['status']}")
    print(f"HTML: {args.out.resolve()/'report.html'}")
    return 1 if any(r['status']=='OUTSIDE_TOLERANCES' for r in results) else 2 if any(r['status']=='INCOMPLETE' for r in results) else 0


if __name__=='__main__':raise SystemExit(main())
