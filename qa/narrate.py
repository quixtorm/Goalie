"""English narration for the Goalie demo video (QA tooling only).

Audio comes from the Speko connector (text-to-speech only) or, as a fallback, from edge-tts.
The voice is ONE setting: "voice" in qa/narration.json.

  speko/<provider:model>/<voice-id>   Speko voice. Speko is called through its MCP connector,
                                      which saves each result as JSON; import it with:
                                        python qa/narrate.py import <scene-id> <saved-result.json>
  edge/<voice-name>                   edge-tts voice (free, no key); generated here by `build`.

Commands
  python qa/narrate.py import <scene> <result.json> [--sample <name>]   decode a saved Speko result
  python qa/narrate.py build                                            fill missing scenes, measure durations
  python qa/narrate.py edge-sample <voice> <text>                       write qa/audio/samples/edge_<voice>.mp3

Outputs: qa/audio/en/<scene>.mp3, qa/audio/en/sources.json (which engine made each scene, and fallbacks),
qa/audio/durations.json. No API key, token or signed URL is ever written to these files.
"""
from __future__ import annotations

import asyncio
import base64
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CFG = ROOT / "narration.json"
AUDIO = ROOT / "audio"
EN = AUDIO / "en"
SAMPLES = AUDIO / "samples"
SOURCES = EN / "sources.json"
DURATIONS = AUDIO / "durations.json"
sys.stdout.reconfigure(encoding="utf-8")


def ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def duration(path: Path) -> float:
    """Seconds, via ffprobe when installed, else parsed from ffmpeg's header output."""
    probe = shutil.which("ffprobe")
    if probe:
        out = subprocess.run([probe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                             capture_output=True, text=True).stdout.strip()
        return round(float(out), 3)
    err = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
    return round(int(h) * 3600 + int(m) * 60 + float(s), 3)


def to_mp3(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", str(src), "-ac", "1", "-ar", "24000",
                    "-c:a", "libmp3lame", "-q:a", "3", str(dst)], check=True)


def cfg() -> dict:
    return json.loads(CFG.read_text(encoding="utf-8"))


def sources() -> dict:
    return json.loads(SOURCES.read_text(encoding="utf-8")) if SOURCES.exists() else {}


def save_sources(d: dict) -> None:
    EN.mkdir(parents=True, exist_ok=True)
    SOURCES.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------- Speko (results saved by the MCP connector) ----------
def import_speko(scene: str, result: Path, sample: str | None = None) -> None:
    data = json.loads(result.read_text(encoding="utf-8"))
    if "audio_base64" not in data:
        raise SystemExit(f"no audio in {result.name}: {data.get('error') or data.get('code') or 'unknown error'}")
    ext = ".wav" if "wav" in data.get("content_type", "") else ".mp3"
    tmp = AUDIO / f"_tmp_{scene}{ext}"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(base64.b64decode(data["audio_base64"]))
    if sample:  # voice samples are kept in the format Speko returned
        SAMPLES.mkdir(parents=True, exist_ok=True)
        shutil.move(tmp, SAMPLES / f"{sample}{ext}")
        print(f"sample {sample}{ext}: {data.get('provider')}/{data.get('model')}, {data.get('duration_seconds')} s")
        return
    to_mp3(tmp, EN / f"{scene}.mp3")
    tmp.unlink()
    src = sources()
    src[scene] = {"engine": "speko", "voice": cfg()["voice"], "provider": data.get("provider"),
                  "model": data.get("model"), "fallback": False}
    save_sources(src)
    print(f"{scene}.mp3 <- Speko {data.get('provider')}/{data.get('model')}")


# ---------- edge-tts ----------
def edge_tts(voice: str, text: str, out: Path, tries: int = 6) -> None:
    """edge-tts sometimes answers 'No audio was received' for a good request; retry with backoff."""
    import edge_tts
    out.parent.mkdir(parents=True, exist_ok=True)
    last = None
    for i in range(tries):
        try:
            asyncio.run(edge_tts.Communicate(text, voice).save(str(out)))
            if out.exists() and out.stat().st_size > 1000:
                return
        except Exception as e:  # noqa: BLE001
            last = e
        time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"edge-tts failed after {tries} tries: {last}")


def build() -> int:
    c = cfg()
    engine, _, rest = c["voice"].partition("/")
    src = sources()
    for sc in c["scenes"]:
        mp3 = EN / f"{sc['id']}.mp3"
        have = src.get(sc["id"], {})
        if mp3.exists() and have.get("voice") == c["voice"] and not have.get("fallback"):
            continue  # made with the selected voice
        if engine == "edge":
            edge_tts(rest, sc["text_en"], mp3)
            src[sc["id"]] = {"engine": "edge-tts", "voice": c["voice"], "fallback": False}
        else:
            # selected voice is Speko but this scene has no Speko audio (call failed or not imported yet)
            fb = c["fallback_voice"].partition("/")[2]
            edge_tts(fb, sc["text_en"], mp3)
            src[sc["id"]] = {"engine": "edge-tts", "voice": c["fallback_voice"], "fallback": True,
                             "reason": "no Speko audio for this scene"}
        print(f"{sc['id']}.mp3 <- {src[sc['id']]['engine']} ({src[sc['id']]['voice']})")
    save_sources(src)
    durs = {sc["id"]: duration(EN / f"{sc['id']}.mp3") for sc in c["scenes"]}
    DURATIONS.write_text(json.dumps(durs, indent=2) + "\n", encoding="utf-8")
    print("durations:", durs, "total", round(sum(durs.values()), 1), "s")
    return 0


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "import":
        sample = sys.argv[sys.argv.index("--sample") + 1] if "--sample" in sys.argv else None
        import_speko(sys.argv[2], Path(sys.argv[3]), sample)
        return 0
    if cmd == "edge-sample":
        voice, text = sys.argv[2], sys.argv[3]
        out = SAMPLES / f"edge_{voice}.mp3"
        edge_tts(voice, text, out)
        print(out, duration(out), "s")
        return 0
    if cmd == "build":
        return build()
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
