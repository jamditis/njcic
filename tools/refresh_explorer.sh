#!/usr/bin/env bash
# refresh_explorer.sh — pull Airtable, rebuild data.json, verify, deploy.
#
# Safe to run by hand or from a systemd timer. Exits non-zero on any
# failure so systemd/cron will mark the run as failed.
#
# No UI changes, no git pushes, no external traffic beyond:
#   - Airtable API (read-only, via the airtable-pat-dnr PAT)
#   - Writing local files
#   - sudo cp to /srv/pages/njcic/explorer/ (same deploy pattern used manually)

set -euo pipefail

LOG=/var/log/njcic-explorer-refresh.log
TS="$(date +%Y%m%d-%H%M%S)"
REPO=/home/jamditis/projects/njcic
DATA_DIR=/home/jamditis/projects/njcic-grantees-map/data
LIVE_DIR=/srv/pages/njcic/explorer
BUILD_OUT="$REPO/explorer/data.json"
LIVE_OUT="$LIVE_DIR/data.json"

# Optional Telegram alert on failure.
# Enable by setting NJCIC_REFRESH_NOTIFY=1 (e.g. in the systemd unit's
# Environment= line). Default: off — systemd still records the failure
# via exit code; no messages are sent.
ERROR_REPORTER=/home/jamditis/projects/houseofjawn-bot/scheduler/error_reporter.py

log()  { printf '[%s] %s\n' "$(date -Iseconds)" "$*" | sudo tee -a "$LOG" >/dev/null; printf '[%s] %s\n' "$(date -Iseconds)" "$*"; }
fail() {
  log "FAIL: $*"
  if [ "${NJCIC_REFRESH_NOTIFY:-}" = "1" ] && [ -x "$ERROR_REPORTER" ]; then
    "$ERROR_REPORTER" \
      --source "njcic-explorer-refresh" \
      --message "$*" \
      --retry-command "bash /home/jamditis/projects/njcic/tools/refresh_explorer.sh" \
      || log "WARN: error_reporter invocation failed (continuing)"
  fi
  exit 1
}

log "==== refresh start ($TS) ===="

# 1. Pull Airtable → CSV
if ! python3 "$REPO/tools/airtable_to_csv.py"; then
  fail "airtable_to_csv.py failed"
fi

# 2. Run build_data.py against the fresh CSV
if ! NJCIC_GRANTEES_MAP_DATA="$DATA_DIR" python3 "$REPO/explorer/build_data.py"; then
  fail "build_data.py failed"
fi

# 3. Verification gate
python3 - "$BUILD_OUT" "$LIVE_OUT" <<'PY' || fail "verification failed"
import json, sys
NEW = json.load(open(sys.argv[1]))
LIVE = json.load(open(sys.argv[2]))
errors = []

s = NEW['summary']
if s['totalGrantees'] < 80:
    errors.append(f"totalGrantees looks low: {s['totalGrantees']}")
if s['totalAwarded'] < 10_000_000:
    errors.append(f"totalAwarded looks low: {s['totalAwarded']}")
if s['activeGrantees'] < 70:
    errors.append(f"activeGrantees looks low: {s['activeGrantees']}")

# No more than a 25% swing in totals from what's currently live (excess
# would imply an Airtable mass-delete or API pagination bug)
live_s = LIVE['summary']
for k in ('totalGrantees', 'totalGrants', 'activeGrantees', 'totalAwarded'):
    old, new = live_s.get(k, 0), s.get(k, 0)
    if old and abs(new - old) / old > 0.25:
        errors.append(f"{k} swung {new - old:+} ({(new-old)/old:+.1%}) vs live — refusing to deploy")

# Areas facet must always be populated (catches an empty/broken build)
if not NEW['facets'].get('areas'):
    errors.append("areas facet is empty")
if not NEW['facets'].get('focusAreas'):
    errors.append("focusAreas facet is empty")

# New schema fields (Phase 4): legislativeDistricts + projects aggregates
# exist on every grantee, and the LD facet is populated.
if not NEW['facets'].get('legislativeDistricts'):
    errors.append("legislativeDistricts facet is empty")
missing_new = [g['name'] for g in NEW['grantees']
               if 'projects' not in g or 'legislativeDistricts' not in g]
if missing_new:
    errors.append(f"{len(missing_new)} grantees missing projects/legislativeDistricts keys; first: {missing_new[:3]}")

if errors:
    for e in errors:
        print(f"VERIFY ERROR: {e}")
    sys.exit(1)
print("verification: ok")
PY

# 4. Deploy (backup-then-copy; keep last 7 backups)
sudo cp "$LIVE_OUT" "$LIVE_OUT.bak-$TS"
sudo cp "$BUILD_OUT" "$LIVE_OUT"
sudo chmod 644 "$LIVE_OUT"

# Backup rotation — keep 7 most recent
sudo bash -c "ls -1t $LIVE_DIR/data.json.bak-* 2>/dev/null | tail -n +8 | xargs -r rm -f"

GRANTEE_COUNT="$(python3 -c "import json; print(json.load(open('$LIVE_OUT'))['summary']['totalGrantees'])")"
log "deployed data.json (grantees=$GRANTEE_COUNT)"
log "==== refresh done ===="
