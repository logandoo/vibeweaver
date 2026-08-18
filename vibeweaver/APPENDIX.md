> This file contains executable code snippets for [SKILL.md](SKILL.md). Copy and use directly in projects.
> 
> **Stack note**: §A1, §A2, §A4 are universal (apply to any project). §A3 is FastAPI-specific. §A5 is an example template — adapt to your project's actual config. §A6 is for the default FastAPI+React+Vite stack — adapt to your project's build tooling.

# Vibeweaver — Appendix: Executable Code Library

---

## §A1. Playwright Media Capture Test — Video + Audio + Screenshot (Universal)

Captures the page operation flow as **video** (Playwright `record_video`),
**in-page audio** (Web Audio capture script injected via `add_init_script`),
plus a **terminal screenshot**. Which evidence gets captured AND graded is
decided by the mm-sensor probe mode (SKILL.md §A4.1 Step 0): `[video+audio]`
→ all three · `[video]` → video + screenshot · `[image]` → screenshot only
(original loop).

Save as `tests/flow_capture_test.py`:

```python
import json
import logging
import os
import shutil
import struct
import subprocess
import sys
import wave
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib
from playwright.sync_api import sync_playwright

# Read server config from config.toml
with open("config.toml", "rb") as f:
    cfg = tomllib.load(f)
srv = cfg.get("server", {})
HOST = srv.get("host", "127.0.0.1")
PORT = srv.get("port", 8000)
BASE_URL = f"http://{HOST}:{PORT}"

FLOW_NAME = "login_flow"   # stable per-flow name → tests/login_flow.webm / _audio.wav / _final.png
os.makedirs("tests", exist_ok=True)
logging.basicConfig(
    filename="tests/test_log.log", level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# mm-sensor skill dir — from available_skills <location>; "" = no mm-sensor (screenshot-only)
MM_SENSOR_DIR = ""

def probe_modes() -> dict:
    """Probe mm-sensor model media capabilities (SKILL.md A4.1 Step 0)."""
    if not MM_SENSOR_DIR:
        return {"video": False, "audio": False, "image": True}
    r = subprocess.run(
        [sys.executable, f"{MM_SENSOR_DIR}/vision.py", "--probe"],
        capture_output=True, text=True, timeout=60,
    )
    if r.returncode != 0:
        logging.error(f"probe failed: {r.stderr.strip()}")
        return {"video": False, "audio": False, "image": True}
    caps = json.loads(r.stdout).get("media_capabilities") or []
    return {m: (m in caps) for m in ("video", "audio", "image")}

# In-page Web Audio capture — inject BEFORE page load. Patches the
# AudioContext constructor so EVERY page-created context gets its own
# same-context ScriptProcessorNode tap (cross-context connect is invalid,
# which is why a pre-made shared context cannot work); also routes
# <audio>/<video> elements through their page context.
# __vibeweaverAudioDump() returns raw PCM per channel.
AUDIO_CAPTURE_JS = r"""
(() => {
  if (window.__vibeweaverAudioDump) return;
  const OrigAC = window.AudioContext || window.webkitAudioContext;
  if (!OrigAC) { window.__vibeweaverAudioDump = () => null; return; }
  const ch = [[], []];
  let sampleRate = 44100;
  const taps = new WeakMap();
  const makeTap = (ctx) => {
    const sp = ctx.createScriptProcessor(4096, 2, 2);
    sp.onaudioprocess = (e) => {
      const ib = e.inputBuffer;
      const l = ib.getChannelData(0);
      const r = ib.numberOfChannels > 1 ? ib.getChannelData(1) : l;
      ch[0].push(new Float32Array(l)); ch[1].push(new Float32Array(r));
    };
    sp.connect(ctx.destination);
    sampleRate = ctx.sampleRate;
    return sp;
  };
  window.AudioContext = function (...args) {
    const ctx = new OrigAC(...args);
    taps.set(ctx, makeTap(ctx));
    return ctx;
  };
  window.AudioContext.prototype = OrigAC.prototype;
  if (window.webkitAudioContext) window.webkitAudioContext = window.AudioContext;
  const origConnect = AudioNode.prototype.connect;
  AudioNode.prototype.connect = function (target) {
    const ret = origConnect.apply(this, arguments);
    try {
      const t = taps.get(this.context);
      if (t && this !== t && target !== t) origConnect.call(this, t);
    } catch (e) {}
    return ret;
  };
  const origPlay = HTMLMediaElement.prototype.play;
  HTMLMediaElement.prototype.play = function () {
    try {
      if (!this.__vibeweaverRouted) {
        this.__vibeweaverRouted = true;
        const ctx = new window.AudioContext();
        ctx.createMediaElementSource(this).connect(taps.get(ctx));
      }
    } catch (e) {}
    return origPlay.apply(this, arguments);
  };
  window.__vibeweaverAudioDump = () => {
    const flat = (arr) => {
      let n = 0; arr.forEach((a) => { n += a.length; });
      const out = new Float32Array(n); let o = 0;
      arr.forEach((a) => { out.set(a, o); o += a.length; });
      return Array.from(out);
    };
    return { sampleRate, channels: [flat(ch[0]), flat(ch[1])] };
  };
})();
"""

def dump_audio(page, path):
    """Assemble captured PCM into a WAV. Returns path, or None if no audio produced."""
    data = page.evaluate("window.__vibeweaverAudioDump()")
    if not data or not data["channels"] or not data["channels"][0]:
        logging.info("Audio: none produced during flow (no AudioContext or silence)")
        return None
    channels = data["channels"]
    with wave.open(path, "wb") as w:
        w.setnchannels(len(channels))
        w.setsampwidth(2)
        w.setframerate(data["sampleRate"])
        frames = bytearray()
        for i in range(len(channels[0])):
            for ch in channels:
                s = max(-1.0, min(1.0, ch[i]))
                frames += struct.pack("<h", int(s * 32767))
        w.writeframes(bytes(frames))
    logging.info(f"Audio: {path} ({len(frames)} bytes PCM)")
    return path

def run_flow(page):
    """The flow under test — the WHOLE sequence is recorded to video."""
    page.goto(f"{BASE_URL}/static")
    page.get_by_label("Username").fill("alice")        # example actions — replace
    page.get_by_label("Password").fill("secret")
    page.get_by_role("button", name="Sign In").click()
    page.wait_for_load_state("networkidle")

def main():
    modes = probe_modes()
    logging.info(f"Capture mode: video={modes['video']} audio={modes['audio']} image={modes['image']}")
    video_path = audio_path = None
    raw_video = None
    with sync_playwright() as p:
        browser = p.chromium.launch(
            args=["--autoplay-policy=no-user-gesture-required"],  # AudioContext works headless
        )
        ctx_kwargs = dict(viewport={"width": 1280, "height": 720})
        if modes["video"]:
            ctx_kwargs.update(record_video_dir="tests/videos",
                              record_video_size={"width": 1280, "height": 720})
        context = browser.new_context(**ctx_kwargs)
        page = context.new_page()
        if modes["audio"]:
            page.add_init_script(AUDIO_CAPTURE_JS)
        run_flow(page)
        screenshot_path = f"tests/{FLOW_NAME}_final.png"
        page.screenshot(path=screenshot_path, full_page=True)
        logging.info(f"Screenshot: {screenshot_path}")
        if modes["video"] and page.video:
            raw_video = page.video.path()   # path BEFORE context.close()
        if modes["audio"]:
            page.wait_for_timeout(600)   # settle: let pending audio callbacks fire before dump
            audio_path = dump_audio(page, f"tests/{FLOW_NAME}_audio.wav")
        context.close()                     # finalizes the video file
        if raw_video:
            video_path = f"tests/{FLOW_NAME}.webm"
            shutil.copy(raw_video, video_path)
            logging.info(f"Video (raw webm): {video_path}")
            # Transcode webm → mp4 for grading: Playwright emits VP8/webm, but
            # several OpenAI-compatible gateways (e.g. MiMo) accept mp4 only.
            # Without this, mm-sensor's lazy frame-sampling fallback still works
            # but loses motion/audio information.
            mp4_path = f"tests/{FLOW_NAME}.mp4"
            r = subprocess.run(
                ["ffmpeg", "-y", "-i", video_path, "-c:v", "libx264",
                 "-pix_fmt", "yuv420p", "-preset", "fast",
                 "-movflags", "+faststart", mp4_path],
                capture_output=True, timeout=300,
            )
            if r.returncode == 0:
                logging.info(f"Video (grading mp4): {mp4_path}")
            else:
                mp4_path = video_path   # grade the webm; mm-sensor fallback applies
                logging.warning(f"ffmpeg transcode failed, grading webm: {r.stderr.decode()[-200:]}")
            video_path = mp4_path
    print(json.dumps({"video": video_path, "audio": audio_path, "screenshot": screenshot_path}))
    return 0 if os.path.exists(screenshot_path) else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        logging.error(f"Test failed: {e}")
        print(f"✗ Test failed: {e}", file=sys.stderr)
        sys.exit(1)
```

**Grading (per probe mode — SKILL.md §A4.1 Step 3, all `--detail high`):**

```bash
# [video+audio] — one mixed-media call (grading mp4) + terminal screenshot
python3 {SKILL_DIR}/vision.py --detail high tests/login_flow.mp4 tests/login_flow_audio.wav
python3 {SKILL_DIR}/vision.py --detail high tests/login_flow_final.png

# [video]
python3 {SKILL_DIR}/vision.py --detail high tests/login_flow.mp4 tests/login_flow_final.png

# [image] — original screenshot loop
python3 {SKILL_DIR}/vision.py --detail high tests/login_flow_final.png
```

**Execution:**
```bash
python tests/flow_capture_test.py
```

**Verification:**
- [ ] `tests/login_flow.webm` exists and > 0 bytes (video mode)
- [ ] `tests/login_flow_audio.wav` exists and > 0 bytes, OR log shows `Audio: none produced` (audio mode; silence is not a failure unless a criterion requires sound)
- [ ] `tests/login_flow_final.png` exists and > 0 bytes (ALL modes)
- [ ] `tests/test_log.log` contains `Capture mode:` / `Video:` / `Audio:` / `Screenshot:`
- [ ] Graded through `vision.py --detail high` when mm-sensor is loaded; evidence filenames cited in `tests/verification_log.md` — assert_artifacts.py group 11 machine-checks the files exist

**Capture notes:**
- Video (Playwright `recordVideo`) has **no audio track** — page audio is
  graded via the separate wav. Grade both in one `vision.py` call (mm-sensor
  accepts mixed media inputs).
- Playwright emits **VP8/webm**; several OpenAI-compatible gateways (e.g.
  MiMo) accept **mp4 only** → the template transcodes webm → mp4 (ffmpeg)
  for grading and keeps the raw webm. If ffmpeg is missing or transcoding
  fails, grade the webm directly — mm-sensor's lazy fallback degrades it to
  frame-sampling (usable but loses motion/audio; output marked
  `fallback: video-to-image`).
- In-page audio capture covers Web Audio API + `<audio>`/`<video>` element
  output, NOT OS-level sounds (notifications, other apps). For system-wide
  audio, use an OS loopback (macOS: BlackHole virtual device +
  `ffmpeg -f avfoundation -i "none:BlackHole 2ch" out.wav`) and grade that
  file instead.
- 1280×720 webm ≈ 1–3 MB/min — well under mm-sensor's 50MB base64 cap.

---

## §A2. Backend API Test — httpx (Universal)

Save as `tests/api_test.py`:

```python
import tomllib
import httpx
import logging
import sys

# Read config
with open("config.toml", "rb") as f:
    cfg = tomllib.load(f)

srv = cfg.get("server", {})
BASE_URL = f"http://{srv.get('host', '127.0.0.1')}:{srv.get('port', 8000)}"

logging.basicConfig(
    filename="tests/api_test.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def test_endpoint(endpoint, method="GET", payload=None):
    url = f"{BASE_URL}{endpoint}"
    try:
        if method.upper() == "GET":
            response = httpx.get(url)
        elif method.upper() == "POST":
            response = httpx.post(url, json=payload)
        elif method.upper() == "PUT":
            response = httpx.put(url, json=payload)
        elif method.upper() == "DELETE":
            response = httpx.delete(url)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        logging.info(f"Endpoint: {method} {endpoint}")
        logging.info(f"Input: {payload}")
        logging.info(f"Status: {response.status_code}")
        logging.info(f"Output: {response.text[:500]}")
        
        return response.status_code, response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
    except Exception as e:
        logging.error(f"Test failed for {method} {endpoint}: {e}")
        raise

if __name__ == "__main__":
    # Example usage - modify endpoints as needed
    try:
        status, data = test_endpoint("/api/health", "GET")
        print(f"✓ API test passed: status={status}")
    except Exception as e:
        print(f"✗ API test failed: {e}", file=sys.stderr)
        sys.exit(1)
```

---

## §A3. FastAPI Fallback Route — History Routing (FastAPI Only)

Add to `backend/app/main.py`:

```python
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Fallback route for History routing
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    return FileResponse("static/index.html")
```

---

## §A4. WebSocket Test — websockets (Universal)

Save as `tests/ws_test.py`:

```python
import tomllib
import asyncio
import json
import websockets
import logging

with open("config.toml", "rb") as f:
    cfg = tomllib.load(f)

srv = cfg.get("server", {})
WS_URL = f"ws://{srv.get('host', '127.0.0.1')}:{srv.get('port', 8000)}/ws"

logging.basicConfig(
    filename="tests/ws_test.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

async def test_websocket():
    async with websockets.connect(WS_URL) as websocket:
        # Send test message
        test_msg = {"type": "ping"}
        await websocket.send(json.dumps(test_msg))
        logging.info(f"Sent: {test_msg}")
        
        # Receive response
        response = await websocket.recv()
        logging.info(f"Received: {response}")
        
        return response

if __name__ == "__main__":
    try:
        result = asyncio.run(test_websocket())
        print(f"✓ WebSocket test passed: {result}")
    except Exception as e:
        logging.error(f"WebSocket test failed: {e}")
        print(f"✗ WebSocket test failed: {e}", file=sys.stderr)
        sys.exit(1)
```

---

## §A5. config.toml Full Template (Example — Adapt to Your Project)

> **WARNING**: This is an example template for new FastAPI+PostgreSQL projects. All values below (including password `8i9o0p-[=]` and database name `psy`) are EXAMPLES only. **For existing projects, read and preserve the project's actual config values.** For non-PostgreSQL databases, adapt the `[database]` section accordingly.

```toml
[server]
host = "127.0.0.1"
port = 8000

[database]
host = "127.0.0.1"
port = 5432
username = "postgres"
password = "8i9o0p-[=]"
database = "psy"

[llm]
url = "https://api.example.com/v1"
api_key = ""
model_name = "gpt-4"
top_p = 0.9
top_k = 50
temperature = 0.7

[llm.self_define]
repetition_penalty = 1.1
presence_penalty = 0.6
frequency_penalty = 0.5
max_tokens = 4096
```

---

## §A6. Script Templates (Default: FastAPI + React + Vite — Adapt for Other Stacks)

### Linux/macOS: `script/linux/project_build.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "[BUILD] Building frontend..."
cd "$PROJECT_DIR/frontend"
npm install
npm run build
cd "$PROJECT_DIR"

echo "[BUILD] Mounting to backend/static..."
rm -rf "$PROJECT_DIR/backend/static"
mkdir -p "$PROJECT_DIR/backend/static"
cp -r "$PROJECT_DIR/frontend/dist/"* "$PROJECT_DIR/backend/static/"

echo "[BUILD] Done. Files in backend/static:"
ls -la "$PROJECT_DIR/backend/static/"
```

### Windows: `script/windows/project_build.bat`

```batch
@echo off
echo [BUILD] Building frontend...
cd frontend
call npm install
call npm run build
cd ..

echo [BUILD] Mounting to backend/static...
if exist backend\static rmdir /s /q backend\static
mkdir backend\static
xcopy /e /i frontend\dist\* backend\static\

echo [BUILD] Done.
dir backend\static\
```

### Linux/macOS: `script/linux/start.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "[START] Starting FastAPI server..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_DIR/backend"

source ../.venv/bin/activate

# Read host/port from config.toml
HOST=$(python -c "import tomllib;cfg=tomllib.load(open('../config.toml','rb'));print(cfg.get('server',{}).get('host','127.0.0.1'))")
PORT=$(python -c "import tomllib;cfg=tomllib.load(open('../config.toml','rb'));print(cfg.get('server',{}).get('port',8000))")

fastapi run app/main.py --host "$HOST" --port "$PORT" &
echo $! > .pid
echo "[START] Server started. PID: $(cat .pid)"
```

### Linux/macOS: `script/linux/stop.sh`

> ⚠ HOST-SAFETY: never replace this with `pkill -f "uvicorn app.main"` —
> pattern-kill hits unrelated services on shared hosts. Always kill the PID
> recorded in `.pid` by start.sh.

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ -f "$PROJECT_DIR/backend/.pid" ]; then
    PID=$(cat "$PROJECT_DIR/backend/.pid")
    echo "[STOP] Stopping server (PID: $PID)..."
    kill "$PID" || true
    rm "$PROJECT_DIR/backend/.pid"
    echo "[STOP] Server stopped."
else
    echo "[STOP] No PID file found."
fi
```

### Linux/macOS: `script/linux/restart.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "[RESTART] Restarting server..."
bash "$(dirname "$0")/stop.sh"
sleep 2
bash "$(dirname "$0")/start.sh"
echo "[RESTART] Done."
```

---

## §A7. Large-Task Implementation Plan Template

Save as `docs/PLAN.md` (see [SKILL.md C3](SKILL.md#c3-large-task-implementation-plan-conditional)). Write it assuming the executor has zero project context; every step carries actual content, never placeholders.

````markdown
# <Feature Name> Implementation Plan

**Goal:** <one sentence — what this builds>
**Architecture:** <2-3 sentences about the approach>
**Tech Stack:** <key technologies>

## Global Constraints

<Project-wide requirements — version floors, naming rules, config keys, exact values copied
verbatim from the design docs. Every task implicitly includes this section.>

## Consistency Hub (broadcast — write once, read many)

| Entity | Canonical spelling / value / type | Source of truth |
|---|---|---|
| <e.g. `SESSION_TTL`> | `<1800 s>` | `<DATABASE_DESIGN.html §sessions>` |
| <e.g. `SessionStore.get`> | `<get(token: str) -> Session \| None>` | `<Task 1>` |

<One row per shared name / config key / value / signature / style anchor reused by
≥2 tasks or ≥2 files. A rename or redefinition changes the hub row FIRST, then the old
spelling is grepped to zero hits across the tree (that grep output is completion evidence).
Re-reading the hub at every task boundary is what keeps a long deliverable consistent.>

### Task 1: <Component Name>

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/test_file.py`

**Interfaces:**
- Consumes: <exact signatures from earlier tasks, e.g. `load_config(path: str) -> dict`>
- Produces: <exact names/types later tasks rely on, e.g. `class SessionStore` with `get(token: str) -> Session | None`>

- [ ] **Step 1: Write the failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: Run test — verify it FAILS for the expected reason**

Run: `pytest tests/exact/path/test_file.py::test_specific_behavior -v`
Expected: FAIL — "function not defined"

- [ ] **Step 3: Minimal implementation**

```python
def function(input):
    return expected
```

- [ ] **Step 4: Run test — verify it PASSES** (and the rest of the suite stays green)

- [ ] **Step 5: Commit**

```bash
git add tests/exact/path/test_file.py exact/path/to/file.py
git commit -m "feat: add <specific behavior>"
```

### Task 2: <Next Component>

<repeat the block — NEVER write "similar to Task 1"; steps may be read out of order>
````

**Self-review before executing** (fix inline): requirement coverage · placeholder scan · type consistency across tasks.

---

## §A8. G-DED Artifact Assertion Script — `tests/assert_artifacts.py`

> Universal. Required by [SKILL.md §A4.4.1](SKILL.md#a441-g-ded-executable-artifact-assertions--non-negotiable).
> Byte-checks the artifacts behind every `[Verification Gate]` / `[Memory Gate]`
> claim. Run from the project root BEFORE emitting the `[Verification Gate]`
> line: `python3 tests/assert_artifacts.py` → exit 0 = claims backed by files;
> exit 1 = false claims listed — fix the artifacts, re-run.
> Flags: `--existing` (Modify-Existing task → skip new-project §A5 design-doc
> + git checks) · `--backend-only` (no UI → skip `PAGE_DESIGN.html` and
> `script/linux/project_build.sh`).
> The 13 assertion groups mirror SKILL.md §A4.4.1's minimum-check table.

**The canonical script is `scripts/assert_artifacts.py` in this skill's
directory** — copy it, do NOT retype it (self-written variants omit check
groups; observed in real runs):

```bash
cp <skill-dir>/scripts/assert_artifacts.py tests/assert_artifacts.py
```

- **Groups 1-11** — evidence/structure byte checks: iteration entries,
  acceptance cap-stall line, cited media exist >0 bytes, memory index,
  script executability, git commit count, design docs, README/deps,
  baseline verdict (COV-9), workflow traces, video/audio evidence.
- **Group 12 — FAIL diagnosis clause** — every `- iter N FAIL:` log line
  carries `diagnosis:` (A4.1 Step 4: a retry without its diagnosis is the
  same attempt again).
- **Group 13 — claim without coverage** — a claim word (verified /
  confirmed / validated / tested / proven, plus 已验证 / 已确认 / 已测试 /
  验证通过…) requires a coverage scope on the same line (all / each /
  n≤N / `criterion #N` / `tests/…` path / 覆盖 / 用例 / 边界…). Structured
  lines (iter entries, baseline verdict, COV skips) and fenced code blocks
  (pasted RED output) are exempt. The claim/scope lint is modeled on
  J-Space Cognition Suite's `ship` check (idea level; see repo
  README → Attribution).

Self-verify the copy with the 13 markers listed in SKILL.md §A4.4.1; an
incomplete variant is re-copied, never patched by hand.
