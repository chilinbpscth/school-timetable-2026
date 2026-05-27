"""
Reads data.json and writes index.html with data embedded.
Run after editing data.json.
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data.json"
TEMPLATE = ROOT / "template.html"
OUT = ROOT / "index.html"

def main():
    data = json.loads(DATA.read_text(encoding='utf-8'))
    template = TEMPLATE.read_text(encoding='utf-8')
    # Embed data as JSON inside a <script type="application/json"> block.
    # JSON.parse(textContent) will then read it.
    data_json = json.dumps(data, ensure_ascii=False)
    # Defensively escape </script
    data_json = data_json.replace('</', '<\\/')
    html = template.replace('"__DATA_PLACEHOLDER__"', data_json)
    OUT.write_text(html, encoding='utf-8')
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes)")

if __name__ == '__main__':
    main()
