# SKILL: unifi-protect-sensors Release & Operations Workflow

## Repository
- **GitHub**: `git@github.com:disruptivepatternmaterial/unifi-protect-sensors.git`
- **Local path (build host)**: `~/Documents/GitHub/unifi-protect`
- **Build host**: `ntableman@192.168.10.223` (SSH key: `~/.ssh/id_ed25519_particle`)
- **HA host**: `192.168.70.30:8123` (Docker container, not directly SSH-able)
- **HA config volume**: `/Volumes/home-BowmanMtn/docker/ha/config` (SMB mount — **read-only from Mac**, ENOLCK on writes — use HACS to deploy, never cp)

## Auth

### Git / SSH
`git push` works via SSH key already configured on the build host. No action needed.

### GitHub API (gh CLI + releases)
`GITHUB_TOKEN` is set permanently in `~/.zprofile` on the build host. `gh` is at `/opt/homebrew/bin/gh`. In new shells it is auto-available. To use from this agent via SSH:

```bash
ssh -i ~/.ssh/id_ed25519_particle -o IdentitiesOnly=yes -o StrictHostKeyChecking=no ntableman@192.168.10.223 "
  export PATH=/opt/homebrew/bin:\$PATH
  export GITHUB_TOKEN=\$(grep GITHUB_TOKEN ~/.zprofile | cut -d= -f2 | tr -d \"'\")
  gh release create vX.Y.Z --title '...' --notes '...'
"
```

Or use the GitHub REST API directly with curl (no path issues):
```bash
curl -s -X POST \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.github.com/repos/disruptivepatternmaterial/unifi-protect-sensors/releases" \
  -d '{"tag_name":"vX.Y.Z","name":"vX.Y.Z — title","body":"notes","draft":false,"prerelease":false}'
```

The token is stored in `~/.zprofile`. To retrieve it for API calls from this agent:
```bash
ssh ntableman@192.168.10.223 "grep GITHUB_TOKEN ~/.zprofile | cut -d= -f2 | tr -d \"'\""
```

### HA API
Token (long-lived): `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIyMzMyZGY5Y2MzODA0YjJkYjk2Zjc2ZDJlZmNjMjgyNiIsImlhdCI6MTc3ODk0Mzk2NSwiZXhwIjoyMDk0MzAzOTY1fQ.HEPqycmEKmZOCLIwc9Da33ml06I2wp6PmyWgltDE6h0`
Base URL: `http://192.168.70.30:8123`

## MANDATORY: Before Every Release

**UPDATE THESE FILES EVERY TIME — NO EXCEPTIONS:**

1. `README.md` — verify all device tables, docs on update mechanism/polling, requirements, and test instructions match the current code exactly.
2. `docs/ENTITIES.md` — verify all entity keys, API field paths (`airQuality.*` vs `stats.*`), device model names, and notes match the current `sensor.py` / `binary_sensor.py` SENSOR_DESCRIPTIONS.
3. `docs/CHANGELOG.md` — add a section for the new version with complete change notes.
4. `custom_components/unifi_protect_sensors/manifest.json` — bump `version`.

Do **not** `git commit` until all four files are updated and accurate. A release with stale docs is worse than no docs.

## Release Checklist (run in order, all via SSH or curl)

```
1. Edit code, run tests: .venv_test/bin/pytest tests/ -q --no-header
2. Bump version in manifest.json
3. Update docs/CHANGELOG.md
4. git add -A && git commit -m "..." && git tag vX.Y.Z
5. git push origin main && git push origin vX.Y.Z
6. Create GitHub release (curl to API — see above)
7. Wait ~2 min for HACS to see it, then install + restart HA
```

## Deploying to HA via HACS

HACS tracks **GitHub releases** (not tags). After publishing a release:

```bash
HA_TOKEN="<token>"
HA="http://192.168.70.30:8123"

# Check what HACS sees
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA/api/states/update.unifi_protect_sensors_update" | \
  python3 -c "import json,sys; d=json.load(sys.stdin); a=d['attributes']; print('installed:',a.get('installed_version'),'latest:',a.get('latest_version'))"

# Install the update (once HACS shows the new version as latest)
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  "$HA/api/services/update/install" \
  -d '{"entity_id":"update.unifi_protect_sensors_update","version":"X.Y.Z"}'

# Wait 30s for HACS to write files, then restart HA
sleep 30
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  "$HA/api/services/homeassistant/restart" -d '{}'
```

HACS usually picks up new releases within 2-10 minutes. If it hasn't after 10 min, the user can force it in HACS UI: **⋮ → Redownload → type version**.

## Auto-watcher Pattern (run on build host, survives SSH exit)

```bash
ssh ntableman@192.168.10.223 "
nohup bash -c '
  for i in \$(seq 1 60); do
    sleep 120
    LATEST=\$(curl -s -H \"Authorization: Bearer \$HA_TOKEN\" \
      \"http://192.168.70.30:8123/api/states/update.unifi_protect_sensors_update\" | \
      python3 -c \"import json,sys; print(json.load(sys.stdin)[\\\"attributes\\\"].get(\\\"latest_version\\\"))\")
    [ \"\$LATEST\" = \"vX.Y.Z\" ] && curl -s -X POST ... install && sleep 30 && curl -s -X POST ... restart && exit 0
  done
' > /tmp/hacs_watch.log 2>&1 &
echo PID \$!
"
```

## HA WebSocket API (for entity operations)

Direct entity registry manipulation requires WebSocket (not REST). Use Python from this agent's sandbox or via SSH:

```python
import asyncio, json
import websockets  # pip3 install websockets

TOKEN = "<ha_token>"

async def ws_call(payload):
    async with websockets.connect("ws://192.168.70.30:8123/api/websocket", max_size=10*1024*1024) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": TOKEN}))
        await ws.recv()
        await ws.send(json.dumps(payload))
        return json.loads(await ws.recv())

# Delete stale entity
asyncio.run(ws_call({"id": 1, "type": "config/entity_registry/remove", "entity_id": "sensor.foo"}))

# List entities for a platform
result = asyncio.run(ws_call({"id": 1, "type": "config/entity_registry/list"}))
protect = [e for e in result["result"] if e.get("platform") == "unifi_protect_sensors"]
```

## Key Lessons Learned

### HA Coordinator / WebSocket
- **Never use `async_set_updated_data` for WebSocket updates** — it resets the coordinator's scheduled refresh timer. Use `deep_merge(self.data[device_id], delta)` + `self.async_update_listeners()` instead.
- **Bootstrap interval should be 30s** even with WebSocket — this guarantees `last_updated` stays fresh in HA for stable-room sensors that produce no WS deltas.
- Protect's `/integration/v1/sensors` endpoint has **no `type` field and no `airQuality` data**. Always use `/proxy/protect/api/bootstrap` for the full payload.
- Protect WebSocket URL: `wss://{host}/proxy/protect/ws/updates?lastUpdateId={id}` — requires `TOKEN` cookie auth.

### HACS / GitHub
- HACS tracks **releases**, not tags. A `git tag` alone is not enough.
- `gh auth login --with-token` requires `read:org` scope. Use `GITHUB_TOKEN` env var instead — `gh` picks it up automatically.
- The HA config SMB share is **read-only from the Mac** (ENOLCK). Never attempt `cp` or file writes to `/Volumes/home-BowmanMtn/`. HACS writes files from the HA container side.

### Testing
```bash
cd ~/Documents/GitHub/unifi-protect
.venv_test/bin/pytest tests/ -q --no-header
```
Tests use HA stubs (no live HA needed). Always run before committing.
