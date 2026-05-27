"""
One-time extractor: four .docx files -> data.json
Run once to seed; after that, data.json is maintained by hand.
"""

from __future__ import annotations
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

DOCX_DIR = Path("/Volumes/PublicFolders/2025-2026/0各項會議文件及通告存放/a教師備忘/教師備忘存檔")
FILES = {
    "T151": "T151_25-26_六月全日制上課人總表(A)(T151_25-26).docx",
    "T152": "T152_25-26_六至七月半天上課人總表(B)(T152_25_26).docx",
    "T153": "T153_25-26_六至七月班總表(C)(T153_25_26).docx",
    "T154": "T154_25-26_六至七月整體課堂安排(D)(T154_25_26).docx",
}
OUT = Path(__file__).parent / "data.json"

YEAR = 2026
CLASSES = ["1A","1B","1C","2A","2B","2C","3A","3B","3C",
           "4A","4B","4C","4D","5A","5B","5C","5D",
           "6A","6B","6C","6D","6E"]


# ---------- docx primitives ----------

def _para_text(p) -> str:
    return ''.join((t.text or '') for t in p.iter(W + 't'))

def _cell_text(tc) -> str:
    # Preserve paragraph boundaries with '\n' — UI uses white-space: pre-wrap
    # so multi-line cells (activities, footnotes) render with proper line breaks.
    return '\n'.join(
        _para_text(p).strip()
        for p in tc.findall('w:p', NS)
        if _para_text(p).strip()
    )

def _cell_grid_span(tc) -> int:
    """Horizontal merge span; 1 if not merged."""
    tcPr = tc.find('w:tcPr', NS)
    if tcPr is None: return 1
    gs = tcPr.find('w:gridSpan', NS)
    if gs is None: return 1
    return int(gs.get(W + 'val', '1'))

def _row_cells_expanded(row) -> list[str]:
    """Return cells in display order with merged cells repeated across spans."""
    out = []
    for tc in row.findall('w:tc', NS):
        txt = _cell_text(tc)
        span = _cell_grid_span(tc)
        for _ in range(span):
            out.append(txt)
    return out

def extract_blocks(xml_path: Path):
    """Yield ('para', text) or ('table', rows) in document order."""
    root = ET.parse(xml_path).getroot()
    body = root.find('w:body', NS)
    out = []
    for child in body:
        tag = child.tag.split('}')[-1]
        if tag == 'p':
            t = _para_text(child).strip()
            if t:
                out.append(('para', t))
        elif tag == 'tbl':
            rows = [_row_cells_expanded(r) for r in child.findall('w:tr', NS)]
            out.append(('table', rows))
    return out

def unzip_to(docx_path: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(docx_path) as z:
        z.extractall(out_dir)
    return out_dir / "word" / "document.xml"


# ---------- date helpers ----------

WEEKDAY_CN = {0:'一',1:'二',2:'三',3:'四',4:'五',5:'六',6:'日'}

def parse_date_para(s: str):
    """Return (iso_date, weekday_cn, label) from strings like '6月10日(三)' or '6月10日(星期三)'."""
    m = re.search(r'(\d{1,2})月(\d{1,2})日', s)
    if not m: return None
    month, day = int(m.group(1)), int(m.group(2))
    import datetime
    d = datetime.date(YEAR, month, day)
    wk = WEEKDAY_CN[d.weekday()]
    return d.isoformat(), wk, f"{month}月{day}日({wk})"


# ---------- T154 parser ----------

def parse_t154(blocks):
    """Extract bell schedules, morning special duty, activities, and duty rosters."""
    result = {
        "bellSchedules": {"full-day": [], "half-day": []},
        "morningDuties": {},   # iso_date -> {title, notes, stations, footnotes}
        "activities": {},      # iso_date -> activity text
        "dutyRosters": {       # per-iso-date duty cells
            # iso_date -> { recess1, recess2, lunch, lunchRecess, dismissal }
        },
    }

    i = 0
    n = len(blocks)
    while i < n:
        kind, content = blocks[i]
        # Bell schedules — table may appear 1 or 2 blocks after the heading
        if kind == 'para' and content.startswith('6月10日(三)至6月18日'):
            tbl = _find_next_table(blocks, i, max_skip=3)
            if tbl:
                result['bellSchedules']['full-day'] = _parse_bell_table(tbl)
        if kind == 'para' and content.startswith('6月22日(一)至7月14日'):
            tbl = _find_next_table(blocks, i, max_skip=3)
            if tbl:
                result['bellSchedules']['half-day'] = _parse_bell_table(tbl)

        # Morning special duty: para like "6月12日(五)(早操)(課室)(...)" followed by table
        if kind == 'para':
            md = re.match(r'(\d{1,2}月\d{1,2}日\([一二三四五六日]\))(.*)$', content)
            if md and i+1 < n and blocks[i+1][0] == 'table':
                # confirm next table has header "時間 | 地點 | 人手"
                table = blocks[i+1][1]
                if table and len(table[0]) >= 3 and table[0][0].strip() == '時間' \
                        and table[0][1].strip() == '地點' and table[0][2].strip() == '人手':
                    date_label = md.group(1)
                    suffix = md.group(2).strip()
                    iso = parse_date_para(date_label)
                    if iso:
                        # Collect following footnote paragraphs (註1, 註2, 註3, 備註)
                        footnotes = []
                        j = i + 2
                        while j < n and blocks[j][0] == 'para':
                            p = blocks[j][1]
                            if re.match(r'^(註\d|備註)', p):
                                footnotes.append(p)
                                j += 1
                            else:
                                break
                        stations = _parse_morning_duty_table(table)
                        # Extract bracketed parts from suffix: (早操)(課室)(*仁/杰...)
                        parts = re.findall(r'\(([^()]+)\)', suffix)
                        title = parts[0] if parts else suffix
                        subtitle = '；'.join(parts[1:]) if len(parts) > 1 else ''
                        result['morningDuties'][iso[0]] = {
                            'title': title,
                            'subtitle': subtitle,
                            'stations': stations,
                            'footnotes': footnotes,
                        }
                        i = j; continue

        # Activities tables: header "日期 | 活動"
        if kind == 'table':
            t = content
            if t and len(t[0]) >= 2 and t[0][0].strip() == '日期' and t[0][1].strip() == '活動':
                for row in t[1:]:
                    if len(row) < 2: continue
                    # Skip stray header rows
                    if row[0].strip() == '日期': continue
                    date_iso = _extract_date_from_activity_cell(row[0])
                    if date_iso:
                        result['activities'][date_iso] = _clean_activity_lines(row[1])

        # Recess/lunch/dismissal duty tables — handled separately below
        i += 1

    # Parse duty rosters
    _parse_duty_rosters(blocks, result['dutyRosters'])

    return result


def _find_next_table(blocks, start_idx, max_skip=3):
    for k in range(1, max_skip + 1):
        j = start_idx + k
        if j >= len(blocks): break
        if blocks[j][0] == 'table':
            return blocks[j][1]
    return None


def _parse_bell_table(table):
    out = []
    for row in table[1:]:
        if not row or not row[0].strip(): continue
        time_str = row[0].strip()
        name = row[1].strip() if len(row) > 1 else ''
        note = row[2].strip() if len(row) > 2 else ''
        # Parse "08:00 – 08:15 (15分鐘)" → start, end
        m = re.match(r'(\d{1,2}[:：]\d{2})\s*[–-]\s*(\d{1,2}[:：]\d{2})', time_str)
        start, end = ('', '')
        if m:
            start, end = m.group(1).replace('：',':'), m.group(2).replace('：',':')
        out.append({'name': name, 'start': start, 'end': end, 'time': time_str, 'note': note})
    return out


def _parse_morning_duty_table(table):
    """Return list of {time, location, people, role?}.

    The 時間 column may be empty (continuation of a previous time block) — fill forward.
    """
    stations = []
    current_time = ''
    for row in table[1:]:
        if not row: continue
        if len(row) >= 3:
            t, loc, ppl = row[0].strip(), row[1].strip(), row[2].strip()
            if t:
                current_time = t.replace('：', ':')
            stations.append({
                'time': current_time,
                'location': loc,
                'people': ppl,
            })
    return stations


def _clean_activity_lines(cell_text: str) -> str:
    """Merge continuation lines starting with '(' into the previous line.

    The docx wraps long activity items across multiple paragraphs; reconstruct
    each item onto a single visual line.
    """
    lines = [ln.strip() for ln in cell_text.split('\n') if ln.strip()]
    merged = []
    for ln in lines:
        if merged and (ln.startswith('(') or ln.startswith('（')):
            merged[-1] = merged[-1] + ' ' + ln
        else:
            merged.append(ln)
    return '\n'.join(merged)


def _extract_date_from_activity_cell(cell: str):
    """Extract iso date from '10/6(三) (全日)' format."""
    m = re.match(r'\s*(\d{1,2})/(\d{1,2})', cell)
    if not m: return None
    day, month = int(m.group(1)), int(m.group(2))
    import datetime
    try:
        return datetime.date(YEAR, month, day).isoformat()
    except ValueError:
        return None


def _parse_duty_rosters(blocks, target):
    """Parse the recess/lunch/dismissal duty tables that appear after activities.

    These tables have the pattern: first row is dates as column headers
    (or first column is date, e.g. label rows), and body is duty assignments.
    Implementation strategy: scan tables and identify by header content.
    """
    i = 0
    n = len(blocks)
    current_section = None   # 'recess1' | 'recess2' | 'lunch' | 'lunch_recess' | 'dismissal'
    while i < n:
        kind, content = blocks[i]
        if kind == 'para':
            p = content
            if '小息一當值安排' in p: current_section = 'recess1'
            elif '小息二當值安排' in p: current_section = 'recess2'
            elif '小息當值安排' in p and '半天' in p: current_section = 'recess1_half'  # half-day single recess
            elif '各班午膳當值表' in p: current_section = 'lunch_sup'
            elif '午息當值安排' in p: current_section = 'lunch_recess'
            elif '放學當值安排' in p: current_section = 'dismissal'
        elif kind == 'table' and current_section:
            _ingest_duty_table(content, current_section, target)
        i += 1


def _ingest_duty_table(table, section, target):
    """Ingest a single duty table into target[iso_date][section].

    Header detection: first row contains date cells like '10/6(三)' OR
    first cell is empty + remaining are dates (recess2/lunch tables) OR
    first cell is a category (recess1).
    """
    if not table: return

    header = table[0]
    # Find columns whose header matches date pattern
    date_cols = {}  # col_idx -> iso_date
    for idx, cell in enumerate(header):
        m = re.match(r'\s*(\d{1,2})/(\d{1,2})', cell)
        if m:
            day, month = int(m.group(1)), int(m.group(2))
            import datetime
            try:
                iso = datetime.date(YEAR, month, day).isoformat()
                date_cols[idx] = iso
            except ValueError:
                pass
    if not date_cols: return

    # Body rows: collect (label_cells, value_cells_per_date)
    for row in table[1:]:
        # Label is the cell(s) before the first date column index
        first_date_col = min(date_cols.keys())
        label = ' '.join(c.strip() for c in row[:first_date_col] if c.strip())
        for idx, iso in date_cols.items():
            if idx >= len(row): continue
            value = row[idx].strip()
            if not value: continue
            target.setdefault(iso, {}).setdefault(section, []).append({
                'label': label,
                'value': value,
            })


# ---------- T153 parser (class -> per-period) ----------

def parse_t153(blocks):
    """Return {iso_date: {class: {period: cell}}} and the day's weekday/type info."""
    days = {}
    i = 0
    n = len(blocks)
    while i < n:
        kind, content = blocks[i]
        if kind == 'para' and re.search(r'^\d{1,2}月\d{1,2}日\(星期', content):
            iso_info = parse_date_para(content)
            if iso_info and i+1 < n and blocks[i+1][0] == 'table':
                table = blocks[i+1][1]
                day_data = _parse_class_table(table)
                days[iso_info[0]] = {
                    'weekday': iso_info[1],
                    'label': iso_info[2],
                    'classes': day_data,
                    'period_count': len(table[0]) - 1 if table else 0,  # header cols minus class col
                }
                i += 2; continue
        i += 1
    return days


def _parse_class_table(table):
    """Header: (三) | 第1節 ... | 第N節. Body: class | cells."""
    if not table: return {}
    header = table[0]
    n_periods = len(header) - 1
    result = {}
    for row in table[1:]:
        if not row: continue
        cls = row[0].strip()
        if cls not in CLASSES: continue
        slots = {}
        for p in range(n_periods):
            col = p + 1
            if col < len(row):
                slots[f'p{p+1}'] = row[col].strip()
            else:
                slots[f'p{p+1}'] = ''
        result[cls] = slots
    return result


# ---------- T151/T152 parser (teacher -> per-slot) ----------

T151_SLOTS = ['homeroom','p1','p2','recess1','p3','recess2','p4','lunch','p5','p6','duty']
T151_FRIDAY_SLOTS = ['homeroom','p1','p2','recess1','p3','recess2','p4','lunch','p5','duty']  # no p6
T152_SLOTS = ['homeroom','p1','p2','recess1','p3','p4','duty']


def parse_teacher_doc(blocks, doc_type):
    """Parse T151 or T152.

    Returns {iso_date: {teacher_short: {slot: cell}}}.
    Multiple tables per date are merged.
    """
    days = {}
    i = 0
    n = len(blocks)
    while i < n:
        kind, content = blocks[i]
        if kind == 'para':
            iso_info = parse_date_para(content)
            if iso_info and i+1 < n and blocks[i+1][0] == 'table':
                table = blocks[i+1][1]
                if not _looks_like_teacher_table(table):
                    i += 1; continue
                iso = iso_info[0]
                days.setdefault(iso, {
                    'weekday': iso_info[1],
                    'label': iso_info[2],
                    'teachers': {},
                })
                _ingest_teacher_table(table, days[iso]['teachers'], doc_type, iso_info[1])
                i += 2; continue
        i += 1
    return days


def _looks_like_teacher_table(table):
    if not table or not table[0]: return False
    h = table[0]
    # header row first cell often contains "(三)" or "(四)" etc, or empty
    # Easier: 2nd col header should be "早上"
    if len(h) >= 2 and '早上' in h[1]:
        return True
    return False


def _ingest_teacher_table(table, target_teachers, doc_type, weekday):
    if not table: return

    # Determine slot mapping by inspecting header row
    header = table[0]
    n_cols = len(header)

    if doc_type == 'T151':
        slots = T151_FRIDAY_SLOTS if weekday == '五' else T151_SLOTS
    else:
        slots = T152_SLOTS

    # Sanity: number of slots should equal n_cols-1 (col 0 is teacher name)
    # If not, just use min length.
    n_slots = min(len(slots), n_cols - 1)

    for row in table[1:]:
        if not row or not row[0].strip(): continue
        name = row[0].strip()
        # Skip rows that look like header repeats
        if name in ('(三)','(四)','(五)','(一)','(二)') or '早上' in name:
            continue
        # 早課 老師 ("潔") - keep
        slot_map = {}
        for k in range(n_slots):
            col = k + 1
            slot_map[slots[k]] = row[col].strip() if col < len(row) else ''
        # Merge if same teacher appears twice (should not for the same date but defensive)
        if name in target_teachers:
            for k, v in slot_map.items():
                if v and not target_teachers[name].get(k):
                    target_teachers[name][k] = v
        else:
            target_teachers[name] = slot_map


# ---------- merge & build data.json ----------

def build():
    print("Extracting docx files...")
    extract_root = Path('/tmp/timetable_extract')
    extract_root.mkdir(parents=True, exist_ok=True)
    xmls = {}
    for key, fname in FILES.items():
        src = DOCX_DIR / fname
        if not src.exists():
            raise FileNotFoundError(src)
        xml_path = unzip_to(src, extract_root / key)
        xmls[key] = extract_blocks(xml_path)
        print(f"  {key}: {len(xmls[key])} blocks")

    print("Parsing T154 (master / activities / duties)...")
    t154 = parse_t154(xmls['T154'])
    print(f"  bell schedules: full-day={len(t154['bellSchedules']['full-day'])} half-day={len(t154['bellSchedules']['half-day'])}")
    print(f"  morningDuties: {sorted(t154['morningDuties'].keys())}")
    print(f"  activities: {len(t154['activities'])} dates")
    print(f"  dutyRosters: {len(t154['dutyRosters'])} dates")

    print("Parsing T153 (per-class)...")
    t153 = parse_t153(xmls['T153'])
    print(f"  class days: {sorted(t153.keys())}")

    print("Parsing T151 (full-day teacher)...")
    t151 = parse_teacher_doc(xmls['T151'], 'T151')
    print(f"  T151 days: {sorted(t151.keys())}")

    print("Parsing T152 (half-day teacher)...")
    t152 = parse_teacher_doc(xmls['T152'], 'T152')
    print(f"  T152 days: {sorted(t152.keys())}")

    # Collect teacher set + infer homeroom from T151 first
    teacher_set = {}  # short -> homeroom
    for iso, dd in sorted(t151.items()):
        for short, slots in dd['teachers'].items():
            if short not in teacher_set:
                teacher_set[short] = slots.get('homeroom', '').strip()
    for iso, dd in sorted(t152.items()):
        for short, slots in dd['teachers'].items():
            if short not in teacher_set:
                teacher_set[short] = slots.get('homeroom', '').strip()

    teachers = [{'short': s, 'homeroom': h} for s, h in sorted(teacher_set.items())]

    # Build days
    all_iso = set(t151.keys()) | set(t152.keys()) | set(t153.keys())
    days = []
    for iso in sorted(all_iso):
        in_t151 = iso in t151
        in_t152 = iso in t152
        day_info = t151.get(iso) or t152.get(iso) or t153.get(iso)
        label = day_info['label']
        weekday = day_info['weekday']
        day_type = 'full-day' if in_t151 else 'half-day'

        teacher_schedules = {}
        src = t151.get(iso, {}).get('teachers') or t152.get(iso, {}).get('teachers') or {}
        for short, slots in src.items():
            homeroom = slots.pop('homeroom', '') if 'homeroom' in slots else slots.get('homeroom','')
            # Note: slots may have been mutated; re-grab homeroom
            if 'homeroom' not in slots and src[short].get('homeroom'):
                homeroom = src[short]['homeroom']
            teacher_schedules[short] = {
                'homeroom': homeroom,
                'slots': {k: v for k, v in slots.items() if k != 'homeroom'},
            }

        class_schedules = t153.get(iso, {}).get('classes', {})
        period_count = t153.get(iso, {}).get('period_count', 6 if day_type=='full-day' else 4)

        days.append({
            'date': iso,
            'label': label,
            'weekday': weekday,
            'type': day_type,
            'periodCount': period_count,
            'activities': t154['activities'].get(iso, ''),
            'morningDuty': t154['morningDuties'].get(iso),
            'duties': t154['dutyRosters'].get(iso, {}),
            'teacherSchedules': teacher_schedules,
            'classSchedules': class_schedules,
        })

    data = {
        'meta': {
            'schoolName': '佛教志蓮小學',
            'year': '2025-2026',
            'version': '15/5版',
            'generatedFromDocx': True,
        },
        'classes': CLASSES,
        'teachers': teachers,
        'bellSchedules': t154['bellSchedules'],
        'days': days,
    }

    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\nWrote {OUT} ({OUT.stat().st_size:,} bytes)")
    print(f"Days: {len(days)}  Teachers: {len(teachers)}")


if __name__ == '__main__':
    build()
