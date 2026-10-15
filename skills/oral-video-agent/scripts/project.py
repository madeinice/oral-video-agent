"""Local project, timing and editable Remotion generation. Standard library only."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalized(text):
    return "".join(c.lower() for c in text if c.isalnum())


def anchor(words, phrase, occurrence=None):
    needle = normalized(phrase)
    if not needle:
        raise ValueError("Anchor phrase is empty")
    stream, boundaries = "", []
    previous = -1.0
    for word in words:
        start, end = float(word["start"]), float(word["end"])
        if not math.isfinite(start + end) or start < previous or start < 0 or end <= start:
            raise ValueError("Invalid or unordered word timestamps")
        previous = start
        token = normalized(word["text"])
        stream += token
        boundaries.extend([(start, end)] * len(token))
    matches = [m.start() for m in re.finditer("(?=" + re.escape(needle) + ")", stream)]
    if not matches:
        raise ValueError("Phrase not found: correct transcript by listening before placing the effect")
    if occurrence is None and len(matches) != 1:
        raise ValueError(f"Phrase occurs {len(matches)} times; specify --occurrence (1 based)")
    n = occurrence or 1
    if n < 1 or n > len(matches):
        raise ValueError("Occurrence is out of range")
    pos = matches[n - 1]
    return {"phrase": phrase, "occurrence": n, "start": boundaries[pos][0],
            "end": boundaries[pos + len(needle) - 1][1], "precision": "input-token-boundaries"}


def frame(value, fps):
    return int(math.floor(float(value) * fps + 0.5))


def span(item, duration, fps):
    a, b = float(item["start"]), float(item["end"])
    if not math.isfinite(a + b) or a < 0 or b <= a or b > duration + 0.000001:
        raise ValueError(f"Invalid time interval: {item.get('id', item)}")
    if frame(b, fps) <= frame(a, fps):
        raise ValueError("Interval is shorter than one output frame")
    return a, b


def media_path(project, src):
    if not isinstance(src, str) or not src or ":" in src or "\\" in src:
        raise ValueError("Media src must be a relative public/ path with forward slashes")
    public = (Path(project) / "outputs" / "editor" / "public").resolve()
    target = (public / src).resolve()
    if not target.is_relative_to(public) or not target.is_file():
        raise ValueError(f"Missing or escaping public asset: {src}")
    return target


def validate(data, project=None, production=False):
    m = data["meta"]
    fps, duration = m["fps"], m["duration"]
    if not isinstance(fps, int) or isinstance(fps, bool) or not 1 <= fps <= 120:
        raise ValueError("fps must be an integer from 1 to 120")
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Invalid duration")
    for key in ("width", "height"):
        if not isinstance(m[key], int) or m[key] < 2 or m[key] % 2:
            raise ValueError("H.264 canvas dimensions must be positive even integers")
    previous, text_parts = 0.0, []
    scenes = data.get("scenes", [])
    if not scenes:
        raise ValueError("At least one scene is required")
    for scene in scenes:
        a, b = span(scene, duration, fps)
        if abs(a - previous) > 0.001:
            raise ValueError("Scenes must be ordered, continuous and non-overlapping")
        if not isinstance(scene.get("needs_host"), bool) or not scene.get("text"):
            raise ValueError("Each scene needs text and a boolean needs_host")
        previous = b
        text_parts.append(scene["text"])
    if abs(previous - duration) > 0.001:
        raise ValueError("Scenes must cover the complete audio duration")
    if normalized("".join(text_parts)) != normalized(data.get("script", "")):
        raise ValueError("Scene texts do not cover the approved script exactly")
    ids = set()
    kinds = {"video", "image", "audio", "text", "portrait", "steps"}
    for layer in data.get("layers", []):
        span(layer, duration, fps)
        if not layer.get("id") or layer["id"] in ids:
            raise ValueError("Layer IDs must be nonempty and unique")
        ids.add(layer["id"])
        if layer["kind"] not in kinds:
            raise ValueError("Unsupported layer kind")
        if layer["kind"] in {"video", "image", "audio", "portrait"}:
            if not layer.get("src"):
                raise ValueError("Media layer is missing src")
            if project:
                media_path(project, layer["src"])
        if layer["kind"] == "steps":
            items = layer.get("items", [])
            if not items:
                raise ValueError("Step line needs timed items")
            for item in items:
                if not item.get("text") or not layer["start"] <= item["at"] < layer["end"]:
                    raise ValueError("Step item needs text and an absolute time inside the layer")
        if float(layer.get("source_start", 0)) < 0:
            raise ValueError("Negative media trim")
        if not 0 <= float(layer.get("volume", 1)) <= 1:
            raise ValueError("Volume must be between zero and one")
        if layer["kind"] == "text" and not layer.get("text"):
            raise ValueError("Empty text layer")
    last_caption_end = 0.0
    for cap in data.get("captions", []):
        a, b = span(cap, duration, fps)
        if a < last_caption_end - 0.001 or not cap.get("text"):
            raise ValueError("Captions must be ordered and non-overlapping")
        last_caption_end = b
    if data.get("demo", False) or not production:
        return  # Deliberately has no paid voice/avatar assets.
    voice = [l for l in data.get("layers", []) if l.get("role") == "narration" and l["kind"] == "audio"]
    if not voice:
        raise ValueError("Production timeline needs a narration audio track")
    voice_end=0.0
    for layer in sorted(voice,key=lambda x:x["start"]):
        if layer["start"]>voice_end+0.001 or layer["start"]<voice_end-0.001:
            raise ValueError("Narration tracks must cover the timeline once, without gaps or doubled voice")
        voice_end=layer["end"]
    if abs(voice_end-duration)>0.001:
        raise ValueError("Narration does not cover the full timeline; include intended silence in the audio")
    for scene in scenes:
        if not scene["needs_host"]:
            continue
        intervals = sorted((l["start"], l["end"]) for l in data["layers"]
                           if l.get("role") == "host" and l["kind"] == "video")
        covered = scene["start"]
        for a, b in intervals:
            if a <= covered + 0.001 and b > covered:
                covered = b
        if covered < scene["end"] - 0.001:
            raise ValueError(f"Host footage does not cover scene {scene['id']}")


def host_plan(data):
    validate(data)
    groups = []
    for scene in data["scenes"]:
        if not scene["needs_host"]:
            continue
        if groups and abs(groups[-1]["end"] - scene["start"]) < 0.001:
            groups[-1]["end"] = scene["end"]
            groups[-1]["scene_ids"].append(scene["id"])
        else:
            groups.append({"start": scene["start"], "end": scene["end"], "scene_ids": [scene["id"]]})
    return {"groups": groups, "host_seconds": round(sum(g["end"] - g["start"] for g in groups), 3),
            "audio_seconds": data["meta"]["duration"], "note": "Plan only; no API call performed"}


def init_project(dest, profile=None):
    dest = Path(dest).resolve()
    if dest.exists():
        raise ValueError("Destination already exists; refusing to overwrite an existing project")
    if dest.is_relative_to(SKILL):
        raise ValueError("Keep production projects outside the distributable Skill")
    config=read(profile) if profile else read(SKILL / "assets" / "examples" / "profile.example.json")
    def check_config(value):
        if isinstance(value,dict):
            for key,value in value.items():
                if key.lower().replace('_','').replace('-','') in {'apikey','authorization','secret','password'}:
                    raise ValueError("Profile must not contain credentials; use environment variables")
                check_config(value)
        elif isinstance(value,list):
            for item in value: check_config(item)
    check_config(config)
    dest.mkdir(parents=True)
    for folder in ("inputs", "work", "outputs"):
        (dest / folder).mkdir()
    shutil.copytree(SKILL / "assets" / "remotion-template", dest / "outputs" / "editor")
    shutil.copyfile(SKILL / "assets" / "examples" / "timeline.demo.json", dest / "timeline.json")
    write(dest / "profile.local.json",config)
    if config.get("runtime"):
        write(dest / "outputs" / "editor" / "runtime.local.json",config["runtime"])
    shutil.copyfile(SKILL / "assets" / "examples" / "sources.example.json", dest / "sources.json")
    shutil.copyfile(SKILL / "scripts" / "studio.ps1", dest / "outputs" / "editor" / "Studio.ps1")
    compile_project(dest)
    return {"project": str(dest), "editor": str(dest / "outputs" / "editor"), "demo": True}


def srt_time(seconds):
    value = int(math.floor(seconds * 1000 + 0.5))
    hours, value = divmod(value, 3600000)
    minutes, value = divmod(value, 60000)
    seconds, millis = divmod(value, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"


def compile_project(root, overwrite=False):
    root = Path(root).resolve()
    data = read(root / "timeline.json")
    validate(data, root, production=True)
    editor = root / "outputs" / "editor"
    generated, metadata = editor / "src" / "Generated.tsx", editor / "src" / "meta.json"
    state_path = root / "work" / "build-state.json"
    old = read(state_path) if state_path.exists() else {}
    for target in (generated, metadata):
        if target.exists() and digest(target) != old.get(target.name) and not overwrite:
            raise ValueError(f"Manual edit detected in {target.name}; merge changes before recompiling")
    m, j = data["meta"], lambda v: json.dumps(v, ensure_ascii=False, separators=(",", ":"))
    fps = m["fps"]
    code = ["// Generated from timeline.json. Studio edits are protected by build-state.json.",
            "import React from 'react';", "import {Sequence, Interactive, staticFile, Audio} from 'remotion';",
            "import {Enter, Media, Portrait, StepLine} from './Layers';",
            "export const Generated: React.FC = () => <>" ]
    for l in data.get("layers", []):
        a, b = frame(l["start"], fps), frame(l["end"], fps)
        code.append(f'<Sequence name={{{j(l["id"])}}} from={{{a}}} durationInFrames={{{b-a}}}>')
        kind = l["kind"]
        rect = l.get("rect", [0, 0, m["width"], m["height"]])
        if kind in {"video", "image"}:
            code.append(f'<Media src={{{j(l["src"])}}} image={{{str(kind=="image").lower()}}} '
                        f'rect={{{j(rect)}}} trim={{{frame(l.get("source_start",0),fps)}}} '
                        f'initialRect={{{j(l.get("from_rect",rect))}}} moveFrames={{{max(1,frame(l.get("move_seconds",0.32),fps))}}} '
                        f'fit={{{j(l.get("fit","cover"))}}} transparent={{{str(l.get("transparent",False)).lower()}}} />')
        elif kind == "audio":
            code.append(f'<Audio src={{staticFile({j(l["src"])})}} trimBefore={{{frame(l.get("source_start",0),fps)}}} volume={{{l.get("volume",1)}}} />')
        elif kind == "portrait":
            code.append(f'<Portrait src={{{j(l["src"])}}} rect={{{j(rect)}}} frames={{{b-a}}} side={{{j(l.get("side","left"))}}} />')
        elif kind == "steps":
            items = [{"text": x["text"], "at": frame(x["at"], fps)-a} for x in l["items"]]
            code.append(f'<StepLine items={{{j(items)}}} rect={{{j(rect)}}} />')
        else:
            style = {"position":"absolute", "left":rect[0], "top":rect[1], "width":rect[2],
                     "height":rect[3], "margin":0,"fontSize":l.get("font_size",84),
                     "fontWeight":900,"lineHeight":1.2,"color":l.get("color","#FFFFFF"),
                     "textAlign":l.get("align","center"),"translate":"0px 0px","scale":1,"whiteSpace":"pre-line"}
            code.append(f'<Enter frames={{{b-a}}}><Interactive.P style={{{j(style)}}}>{{{j(l["text"])}}}</Interactive.P></Enter>')
        code.append('</Sequence>')
    for cap in data.get("captions", []):
        a, b = frame(cap["start"], fps), frame(cap["end"], fps)
        style = {"position":"absolute","left":"6%","right":"6%","bottom":"9%","margin":0,
                 "textAlign":"center","fontSize":m.get("subtitle_size",48),"fontWeight":700,
                 "color":"#FFFFFF","textShadow":"0 2px 5px #000, 0 0 12px #000","lineHeight":1.35}
        code.append(f'<Sequence name="中文字幕" from={{{a}}} durationInFrames={{{b-a}}}><Interactive.P style={{{j(style)}}}>{{{j(cap["text"])}}}</Interactive.P></Sequence>')
    code.append('</>;\n')
    generated.write_text("\n".join(code), encoding="utf-8")
    write(metadata, {**m, "durationInFrames": frame(m["duration"],fps), "demo":data.get("demo",False)})
    subtitle = "\n\n".join(f'{i}\n{srt_time(c["start"])} --> {srt_time(c["end"])}\n{c["text"]}'
                            for i,c in enumerate(data.get("captions",[]),1))
    (root / "outputs" / "captions.srt").write_text(subtitle + "\n",encoding="utf-8")
    write(state_path, {p.name:digest(p) for p in (generated, metadata)})
    return {"editor":str(editor),"frames":frame(m["duration"],fps),"demo":data.get("demo",False)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="command",required=True)
    s=sub.add_parser("init"); s.add_argument("--project",required=True); s.add_argument("--profile")
    s=sub.add_parser("compile"); s.add_argument("--project",required=True); s.add_argument("--overwrite-edits",action="store_true")
    for cmd in ("validate","plan-host"):
        s=sub.add_parser(cmd); s.add_argument("--timeline",required=True)
    s=sub.add_parser("anchor"); s.add_argument("--words",required=True); s.add_argument("--phrase",required=True); s.add_argument("--occurrence",type=int)
    a=p.parse_args()
    if a.command=="init": result=init_project(a.project,a.profile)
    elif a.command=="compile": result=compile_project(a.project,a.overwrite_edits)
    elif a.command=="anchor": result=anchor(read(a.words),a.phrase,a.occurrence)
    elif a.command=="plan-host": result=host_plan(read(a.timeline))
    else: validate(read(a.timeline)); result={"valid":True}
    print(json.dumps(result,ensure_ascii=False))


if __name__=="__main__":
    try: main()
    except (ValueError,KeyError,OSError,TypeError) as e:
        raise SystemExit(f"Project error: {e}")
