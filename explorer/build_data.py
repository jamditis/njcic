"""Merge NJCIC grants data into a single clean JSON for the explorer UI.
Produces: grantees (deduped, org-aggregated) + grants (per-award rows).

Source data lives in the `grantees-map` submodule by default. Override with
env vars `NJCIC_GRANTEES_MAP_DATA` (source CSV dir) and `NJCIC_EXPLORER_OUT`
(output JSON path) if the data lives elsewhere on disk.
"""
import csv, json, os
from collections import defaultdict
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = Path(os.environ.get('NJCIC_GRANTEES_MAP_DATA', REPO_ROOT / 'grantees-map' / 'data'))
OUT = Path(os.environ.get('NJCIC_EXPLORER_OUT', REPO_ROOT / 'explorer' / 'data.json'))

# Load grid view (2021-2024 grants) — the historical dataset
grid_rows = []
with open(SRC / 'Grants-Grid view.csv', newline='', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        grid_rows.append({k.strip().rstrip(':'): (v or '').strip() for k, v in row.items()})

# Load 2025-2026 updated grants (with BIPOC flag)
new_rows = []
with open(SRC / '2025-2026-updated-grants.csv', newline='', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        new_rows.append({(k or '').strip(): (v or '').strip() for k, v in row.items()})

# Load pre-existing lat/lng + county data from grantees.json
with open(SRC / 'grantees.json') as f:
    gj = json.load(f)
geo_by_name = {g['name'].lower(): g for g in gj['grantees']}

FOCUS_TYPO_FIX = {
    'Journalism pipline': 'Journalism pipeline',
}

def norm_focus(f):
    return FOCUS_TYPO_FIX.get(f.strip(), f.strip())


def norm_amount(s):
    s = (s or '').replace('$', '').replace(',', '').strip()
    if not s: return 0
    try: return int(float(s))
    except ValueError: return 0

def split_years(raw):
    """Expand 'Year(s) granted' strings like '2021, 2022, 2023' or '2025-2026'
    into distinct year tokens (ranges preserved as single tokens)."""
    if not raw: return []
    out = []
    for tok in str(raw).split(','):
        tok = tok.strip()
        if tok:
            out.append(tok)
    return out

def area_from_county(county):
    if not county: return ''
    c = county.lower()
    if 'south jersey' in c: return 'South'
    if 'north jersey' in c: return 'North'
    if 'central jersey' in c: return 'Central'
    north = {'bergen', 'essex', 'hudson', 'morris', 'passaic', 'sussex', 'warren', 'union'}
    central = {'hunterdon', 'mercer', 'middlesex', 'monmouth', 'somerset'}
    south = {'atlantic', 'burlington', 'camden', 'cape may', 'cumberland', 'gloucester', 'ocean', 'salem'}
    for k in north:
        if k in c: return 'North'
    for k in central:
        if k in c: return 'Central'
    for k in south:
        if k in c: return 'South'
    return ''

# Build the canonical per-grant list
grants = []
for r in grid_rows:
    name = r.get('Grantee', '').strip()
    if not name: continue
    geo = geo_by_name.get(name.lower(), {})
    grants.append({
        'grantee': name,
        'amount': norm_amount(r.get('Total awarded', '')),
        'purpose': r.get('Grant purpose', ''),
        'website': r.get('Grantee website', ''),
        'year': r.get('Year(s) granted', ''),
        'focus': norm_focus(r.get('Focus area', '')),
        'serviceArea': r.get('Service area', ''),
        'area': area_from_county(r.get('Service area', '') or geo.get('county', '')),
        'cancelled': bool(r.get('Returned/Cancelled grant?', '').strip()),
        'bipocLed': None,
        'grantType': 'Historical',
        'category': norm_focus(r.get('Focus area', '')),
        'lat': geo.get('lat'),
        'lng': geo.get('lng'),
        'city': geo.get('city', ''),
    })

for r in new_rows:
    name = r.get('Organization Name', '').strip()
    if not name: continue
    geo = geo_by_name.get(name.lower(), {})
    bipoc_raw = (r.get('BIPOC Led Project', '') or '').strip().lower()
    bipoc = True if bipoc_raw.startswith('yes') else False if bipoc_raw.startswith('no') else None
    grants.append({
        'grantee': name,
        'amount': norm_amount(r.get('Grant Award', '')),
        'purpose': r.get('Proposed Project/ Project Progress', '') or r.get('Project Overview', ''),
        'website': geo.get('website', ''),
        'year': '2025-2026',
        'focus': norm_focus(r.get('Category', '')),
        'serviceArea': geo.get('county', ''),
        'area': area_from_county(geo.get('county', '')),
        'cancelled': r.get('Action', '').lower().startswith('deny') or r.get('Action', '').lower().startswith('decline'),
        'bipocLed': bipoc,
        'grantType': r.get('Grant Type', 'New Grant'),
        'category': norm_focus(r.get('Category', '')),
        'lat': geo.get('lat'),
        'lng': geo.get('lng'),
        'city': geo.get('city', ''),
    })

# Aggregate by grantee
by_grantee = defaultdict(lambda: {'grants': [], 'total': 0, 'years': set(),
                                   'focusAreas': set(), 'areas': set(),
                                   'bipocLed': None, 'website': '', 'city': '',
                                   'lat': None, 'lng': None, 'serviceArea': ''})
for g in grants:
    key = g['grantee']
    rec = by_grantee[key]
    rec['grants'].append(g)
    if not g['cancelled']:
        rec['total'] += g['amount']
    for y in split_years(g['year']):
        rec['years'].add(y)
    if g['focus']: rec['focusAreas'].add(g['focus'])
    if g['area']: rec['areas'].add(g['area'])
    if g['website'] and not rec['website']: rec['website'] = g['website']
    if g['city'] and not rec['city']: rec['city'] = g['city']
    if g['lat'] and not rec['lat']: rec['lat'] = g['lat']; rec['lng'] = g['lng']
    if g['serviceArea'] and not rec['serviceArea']: rec['serviceArea'] = g['serviceArea']
    if g['bipocLed'] is True: rec['bipocLed'] = True
    elif g['bipocLed'] is False and rec['bipocLed'] is None: rec['bipocLed'] = False

grantees = []
for name, rec in by_grantee.items():
    grantees.append({
        'name': name,
        'total': rec['total'],
        'grantCount': len(rec['grants']),
        'years': sorted(rec['years']),
        'focusAreas': sorted(rec['focusAreas']),
        'areas': sorted(rec['areas']),
        'serviceArea': rec['serviceArea'],
        'city': rec['city'],
        'bipocLed': rec['bipocLed'],
        'website': rec['website'],
        'lat': rec['lat'],
        'lng': rec['lng'],
        'grants': rec['grants'],
    })
grantees.sort(key=lambda x: x['total'], reverse=True)

# Build dropdown facet values
all_areas = sorted({a for g in grantees for a in g['areas'] if a})
all_focus = sorted({f for g in grantees for f in g['focusAreas'] if f})
all_years = sorted({y for g in grantees for y in g['years'] if y})

total_all = sum(g['total'] for g in grantees)
active_count = sum(1 for g in grantees if g['total'] > 0)

awarded_grants = sum(
    1 for g in grantees for gr in g['grants'] if not gr['cancelled']
)

payload = {
    'generatedAt': date.today().isoformat(),
    'summary': {
        'totalGrantees': len(grantees),
        'totalGrants': awarded_grants,
        'totalAwarded': total_all,
        'activeGrantees': active_count,
    },
    'facets': {'areas': all_areas, 'focusAreas': all_focus, 'years': all_years},
    'grantees': grantees,
}

OUT.write_text(json.dumps(payload, indent=2))
print(f"Wrote {OUT}")
print(f"grantees={len(grantees)}, grants={payload['summary']['totalGrants']}, total=${total_all:,}")
print(f"areas: {all_areas}")
print(f"focus areas ({len(all_focus)}): {all_focus[:5]}...")
