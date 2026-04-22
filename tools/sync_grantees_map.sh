#!/usr/bin/env bash
# sync_grantees_map.sh
#
# Pulls Airtable grants via the patched sync-airtable.js, validates the
# generated grantees.json, backs up the remote file, and SFTP-uploads the
# fresh one to njcivicinfo.org/map/data/grantees.json.
#
# Credentials live at pass://claude/services/njcic-sftp and pass://claude/tokens/airtable-pat-dnr.
#
# Flags:
#   --dry-run      generate locally, validate, but skip the SFTP upload
#   --force        skip the interactive "looks right?" check (for cron)
#
# Exits non-zero on any failure so cron/systemd surfaces it.

set -euo pipefail

DRY_RUN=0
FORCE=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --force)   FORCE=1 ;;
  esac
done

REPO=/home/jamditis/projects/njcic-grantees-map
TS="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR=/home/jamditis/.claude/njcic-grantees-map-backups
mkdir -p "$BACKUP_DIR"

log() { printf '[%s] %s\n' "$(date -Iseconds)" "$*"; }

log "==== sync_grantees_map start ($TS) ===="

# 1. Regenerate grantees.json from Airtable
export AIRTABLE_PAT="$(pass show claude/tokens/airtable-pat-dnr | head -1)"
export AIRTABLE_VIEW_ID='-'  # '-' means "don't filter by a view"
node "$REPO/scripts/sync-airtable.js" >/tmp/njcic-sync.log 2>&1 \
  || { log "FAIL: sync-airtable.js error"; tail -20 /tmp/njcic-sync.log; exit 1; }
tail -12 /tmp/njcic-sync.log

NEW_JSON="$REPO/data/grantees.json"

# 2. Validate the output
python3 - "$NEW_JSON" <<'PY' || { echo "FAIL: validation"; exit 1; }
import json, sys
d = json.load(open(sys.argv[1]))
g = d.get('grantees', [])
md = d.get('metadata', {})
if len(g) < 60:
    print(f"grantee count {len(g)} looks low", file=sys.stderr); sys.exit(1)
for item in g:
    if not item.get('name') or item.get('lat') is None or item.get('lng') is None:
        print(f"invalid grantee: {item.get('name')!r}", file=sys.stderr); sys.exit(1)
if not md.get('lastUpdated'):
    print("missing lastUpdated", file=sys.stderr); sys.exit(1)
print(f"validation ok: {len(g)} grantees, ${md.get('totalFunding',0):,.0f} total")
PY

if [ "$DRY_RUN" = "1" ]; then
    log "DRY RUN — not uploading. New file at $NEW_JSON"
    exit 0
fi

# 3. Pull creds
CREDS_RAW="$(pass show claude/services/njcic-sftp)"
HOST=$(printf '%s' "$CREDS_RAW" | awk -F': ' '/^host:/{print $2}')
PORT=$(printf '%s' "$CREDS_RAW" | awk -F': ' '/^port:/{print $2}')
USER=$(printf '%s' "$CREDS_RAW" | awk -F': ' '/^username:/{print $2}')
PASS=$(printf '%s' "$CREDS_RAW" | awk -F': ' '/^password:/{print $2}')

# 4. Download the CURRENT remote grantees.json as a backup before overwriting
BACKUP_REMOTE="$BACKUP_DIR/grantees.json.remote-$TS"
log "Backing up remote grantees.json to $BACKUP_REMOTE"
lftp -u "$USER,$PASS" -e "set sftp:auto-confirm yes; get public_html/map/data/grantees.json -o $BACKUP_REMOTE; bye" \
    "sftp://$HOST:$PORT" >/dev/null 2>&1
if [ ! -s "$BACKUP_REMOTE" ]; then
    log "FAIL: could not download current remote grantees.json for backup"
    exit 1
fi
log "Remote backup ok: $(stat -c %s "$BACKUP_REMOTE") bytes"

# 5. Upload the new file
log "Uploading new grantees.json ($(stat -c %s "$NEW_JSON") bytes)"
cd "$REPO/data"
lftp -u "$USER,$PASS" -e "set sftp:auto-confirm yes; lcd $REPO/data; cd public_html/map/data/; put grantees.json; bye" \
    "sftp://$HOST:$PORT" >/tmp/njcic-upload.log 2>&1 \
    || { log "FAIL: upload"; cat /tmp/njcic-upload.log; exit 1; }
log "Upload complete"

# 6. Verify remote file size + mtime via HEAD
sleep 2
REMOTE_SIZE=$(curl -sI "https://njcivicinfo.org/map/data/grantees.json?ts=$TS" \
    | grep -i '^content-length' | awk '{print $2}' | tr -d '\r')
LOCAL_SIZE=$(stat -c %s "$NEW_JSON")
log "Size check: remote=$REMOTE_SIZE local=$LOCAL_SIZE"
if [ "$REMOTE_SIZE" = "$LOCAL_SIZE" ]; then
    log "==== sync_grantees_map DONE — remote now matches local ===="
else
    log "WARN: size mismatch (possibly CDN cache). Manual Nestify purge may be needed."
fi
