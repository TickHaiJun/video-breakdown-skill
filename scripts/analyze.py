#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze.py —— 视频爆款要素拆解脚本

功能：
  1. 读取 preprocess.py 生成的 meta.json、frames/ 关键帧、audio.mp3
     （音频转录由 Agent 本身完成，Agent 可将转录文本通过 --transcript 传入；
      本脚本负责整理 Prompt 与素材）
  2. 构造结构化多模态 Prompt，调用大模型（默认 Seed-2.1-pro-0915，
     Model ID doubao-seed-2-1-pro-260915）进行拆解
  3. 使用 json_schema 严格模式，输出结构化 JSON：analysis_result.json，
     并统计本次 Token 消耗

拆解维度：
  开头钩子 / 叙事结构 / 镜头节奏 / 字幕与声音 / 复刻脚本 / AI 生成提示词

调用方式（OpenAI 兼容接口，默认火山方舟 Ark）：
  - ARK_API_KEY（或 VOLC_API_KEY）环境变量提供密钥
  - ARK_BASE_URL 可覆盖接口地址，默认 https://ark.cn-beijing.volces.com/api/v3
  - --model 可覆盖模型名；--thinking 控制深度思考，默认 disabled 以提速
  - --offline 为显式离线模板模式（无密钥时跑通流程用，结果会明确标注）

用法：
  python3 scripts/analyze.py [--workdir breakdown_output]
      [--transcript <转录文本文件>] [--platform 抖音]
      [--thinking disabled|enabled|auto] [--offline]
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------- 日志


def log(msg: str) -> None:
    print(f"[analyze] {msg}", flush=True)


def err(msg: str) -> None:
    print(f"[analyze][ERROR] {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------- 素材读取


def load_meta(workdir: Path) -> dict:
    meta_path = workdir / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(
            f"未找到 meta.json：{meta_path}，请先运行 preprocess.py。"
        )
    return json.loads(meta_path.read_text(encoding="utf-8"))


def sample_frames(workdir: Path, max_frames: int) -> list:
    """均匀抽取至多 max_frames 张关键帧，返回 [(文件名, 路径)]。"""
    frames = sorted((workdir / "frames").glob("frame_*.jpg"))
    if not frames:
        raise FileNotFoundError(
            f"frames/ 目录下没有关键帧：{workdir / 'frames'}，请先运行 preprocess.py。"
        )
    if len(frames) <= max_frames:
        return [(f.name, f) for f in frames]
    # 均匀取样，始终保留首帧
    indexes = sorted(
        {round(i * (len(frames) - 1) / (max_frames - 1)) for i in range(max_frames)}
    )
    return [(frames[i].name, frames[i]) for i in indexes]


def load_transcript(workdir: Path, transcript_arg: str | None) -> str:
    """读取 Agent 完成的音频转录文本。"""
    candidates = []
    if transcript_arg:
        candidates.append(Path(transcript_arg).expanduser())
    candidates.append(workdir / "transcript.txt")
    for path in candidates:
        if path.exists():
            text = path.read_text(encoding="utf-8").strip()
            if text:
                log(f"已读取音频转录文本：{path}（{len(text)} 字符）")
                return text
    log("未提供音频转录文本，将仅基于画面与元数据进行拆解。")
    return ""


# ---------------------------------------------------------------- Prompt


SYSTEM_PROMPT = (
    "你是一名资深短视频爆款拆解与复刻编导，擅长拆解竖屏短视频的开头钩子、叙事结构、"
    "镜头节奏、字幕与声音设计，并能产出可直接用于拍摄或 AI 视频生成的复刻脚本与提示词。\n"
    "请严格依据用户提供的视频关键帧、元数据与音频转录文本进行分析，不得臆造画面中不存在的信息；"
    "信息不足的字段请如实描述为“未明确呈现”。\n"
    "合规要求：输出中不得使用极限词（如“最、第一、绝对”等）、导流词（如“私我、加V”等），"
    "不得拉踩其他产品或竞品。"
)


def build_user_prompt(meta: dict, transcript: str, frame_names: list, platform: str) -> str:
    """组装结构化分析指令（json_schema 已约束字段，这里聚焦分析要求）。"""
    frame_list = "\n".join(f"  - {name}" for name in frame_names)
    transcript_block = transcript if transcript else "（未提供转录文本）"
    return f"""请拆解以下短视频。

【视频元数据】
- 文件名：{meta.get('file_name')}
- 时长：{meta.get('duration_seconds')} 秒
- 分辨率：{meta.get('resolution')}（{meta.get('orientation')}）
- 帧率：{meta.get('fps')} fps
- 视频编码：{meta.get('video_codec')}
- 发布平台（供参考，可修正）：{platform}

【随附关键帧（按时间顺序，每帧约对应 1 秒）】
{frame_list}

【音频转录文本】
{transcript_block}

【分析要求】
1. 开头钩子：从 悬念/冲突/利益点/情绪/好奇/身份认同 中选取类型，并说明前 3 秒呈现与留存原因；
2. 叙事结构：从 总分总/递进/反转/痛点-解决方案/并列展示 中选取，并划分叙事段落；
3. 镜头节奏：估计镜头数量、平均时长、时长分布、转场、运镜，并给出覆盖全片的节奏强度曲线（1-10 分）；
4. 字幕与声音：描述字幕样式、BGM、语速、音效；
5. 复刻脚本：逐段分镜表，时间轴与画面、字幕、旁白、声音、运镜具体可执行；
6. AI 提示词：面向 Seedance，画面描述含主体、动作、场景、光线、色调；
7. 信息不足请写“未明确呈现”，避免极限词、导流词与拉踩表述。"""


# ---------------------------------------------------------------- 输出 JSON Schema


def build_output_schema() -> dict:
    """构造严格模式的输出 JSON Schema（所有对象 additionalProperties=false）。"""
    seg_item = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "start": {"type": "number"},
            "end": {"type": "number"},
            "purpose": {"type": "string"},
            "description": {"type": "string"},
        },
        "required": ["name", "start", "end", "purpose", "description"],
        "additionalProperties": False,
    }
    curve_item = {
        "type": "object",
        "properties": {
            "time": {"type": "string"},
            "intensity": {"type": "integer"},
        },
        "required": ["time", "intensity"],
        "additionalProperties": False,
    }
    storyboard_item = {
        "type": "object",
        "properties": {
            "no": {"type": "integer"},
            "start": {"type": "string"},
            "end": {"type": "string"},
            "visual": {"type": "string"},
            "subtitle": {"type": "string"},
            "voiceover": {"type": "string"},
            "sound": {"type": "string"},
            "camera": {"type": "string"},
        },
        "required": ["no", "start", "end", "visual", "subtitle",
                     "voiceover", "sound", "camera"],
        "additionalProperties": False,
    }
    shot_prompt_item = {
        "type": "object",
        "properties": {
            "no": {"type": "integer"},
            "start": {"type": "string"},
            "end": {"type": "string"},
            "prompt": {"type": "string"},
        },
        "required": ["no", "start", "end", "prompt"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "platform": {"type": "string"},
            "topic": {"type": "string"},
            "summary": {"type": "string"},
            "hook": {
                "type": "object",
                "properties": {
                    "types": {"type": "array", "items": {"type": "string"}},
                    "opening_3s": {"type": "string"},
                    "description": {"type": "string"},
                    "why_works": {"type": "string"},
                },
                "required": ["types", "opening_3s", "description", "why_works"],
                "additionalProperties": False,
            },
            "narrative": {
                "type": "object",
                "properties": {
                    "structure": {"type": "string"},
                    "description": {"type": "string"},
                    "segments": {"type": "array", "items": seg_item},
                },
                "required": ["structure", "description", "segments"],
                "additionalProperties": False,
            },
            "pacing": {
                "type": "object",
                "properties": {
                    "shot_count": {"type": "integer"},
                    "avg_shot_duration": {"type": "number"},
                    "duration_distribution": {
                        "type": "object",
                        "properties": {
                            "0-1s": {"type": "integer"},
                            "1-2s": {"type": "integer"},
                            "2-4s": {"type": "integer"},
                            "4s+": {"type": "integer"},
                        },
                        "required": ["0-1s", "1-2s", "2-4s", "4s+"],
                        "additionalProperties": False,
                    },
                    "transitions": {"type": "array", "items": {"type": "string"}},
                    "camera_movements": {"type": "array", "items": {"type": "string"}},
                    "rhythm_curve": {"type": "array", "items": curve_item},
                },
                "required": ["shot_count", "avg_shot_duration",
                             "duration_distribution", "transitions",
                             "camera_movements", "rhythm_curve"],
                "additionalProperties": False,
            },
            "subtitle_sound": {
                "type": "object",
                "properties": {
                    "subtitle_style": {
                        "type": "object",
                        "properties": {
                            "font": {"type": "string"},
                            "color": {"type": "string"},
                            "position": {"type": "string"},
                            "animation": {"type": "string"},
                            "size": {"type": "string"},
                        },
                        "required": ["font", "color", "position",
                                     "animation", "size"],
                        "additionalProperties": False,
                    },
                    "subtitle_description": {"type": "string"},
                    "bgm_style": {"type": "string"},
                    "speech_rate": {"type": "string"},
                    "speech_rate_chars_per_sec": {"type": "number"},
                    "sound_effects": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["subtitle_style", "subtitle_description",
                             "bgm_style", "speech_rate",
                             "speech_rate_chars_per_sec", "sound_effects"],
                "additionalProperties": False,
            },
            "replication_script": {
                "type": "object",
                "properties": {
                    "overview": {"type": "string"},
                    "target_duration": {"type": "number"},
                    "storyboard": {"type": "array", "items": storyboard_item},
                },
                "required": ["overview", "target_duration", "storyboard"],
                "additionalProperties": False,
            },
            "ai_prompts": {
                "type": "object",
                "properties": {
                    "master_prompt": {"type": "string"},
                    "negative_prompt": {"type": "string"},
                    "shots": {"type": "array", "items": shot_prompt_item},
                },
                "required": ["master_prompt", "negative_prompt", "shots"],
                "additionalProperties": False,
            },
            "compliance_notes": {"type": "string"},
        },
        "required": ["platform", "topic", "summary", "hook", "narrative",
                     "pacing", "subtitle_sound", "replication_script",
                     "ai_prompts", "compliance_notes"],
        "additionalProperties": False,
    }


# ---------------------------------------------------------------- 模型调用


def call_chat_model(
    base_url: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    frames: list,
    response_format: dict,
    thinking: str,
    max_tokens: int = 16384,
    timeout: int = 300,
) -> dict:
    """通过 OpenAI 兼容 /chat/completions 接口调用多模态模型，返回原始响应 JSON。"""
    content = [{"type": "text", "text": user_prompt}]
    for _, frame_path in frames:
        b64 = base64.b64encode(frame_path.read_bytes()).decode("utf-8")
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            }
        )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
        "temperature": 0.6,
        "max_tokens": max_tokens,
        "response_format": response_format,
        "thinking": {"type": thinking},
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    log(f"调用模型 {model}（发送 {len(frames)} 帧，thinking={thinking}，"
        f"max_tokens={max_tokens}，请求体 {len(body) // 1024} KB）...")
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"模型接口返回 HTTP {exc.code}：{detail[:800]}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"模型接口请求失败（网络/地址问题）：{exc.reason}") from exc
    log(f"模型响应完成，耗时 {time.time() - started:.1f}s")
    return json.loads(raw)


# ---------------------------------------------------------------- JSON 解析


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) >= 2 else text
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def repair_json(text: str) -> dict:
    """针对“截断/缺少闭合括号”的确定性修复：补全未闭合字符串与括号。

    仅在严格模式输出仍不完整时作为兜底；修复后仍无法解析则抛出异常。
    """
    text = _strip_fences(text)
    start = text.find("{")
    if start == -1:
        raise json.JSONDecodeError("未找到 JSON 起始花括号", text, 0)
    text = text[start:]

    stack = []
    in_str = False
    esc = False
    for c in text:
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c in "{[":
            stack.append(c)
        elif c in "}]":
            if stack:
                stack.pop()

    repaired = text
    if in_str:
        repaired += '"'  # 截断在字符串内部，先闭合引号
    repaired += "".join("}" if c == "{" else "]" for c in reversed(stack))
    return json.loads(repaired)


def extract_json_object(text: str) -> dict:
    """从模型输出中稳健提取 JSON 对象（兼容代码块包裹与轻微截断）。"""
    text = _strip_fences(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return repair_json(text)


# ---------------------------------------------------------------- 离线模板


def build_offline_template(meta: dict, platform: str) -> dict:
    """无密钥时生成结构完整的离线模板，所有待分析字段明确标注。"""
    duration = meta.get("duration_seconds", 0)
    seg_len = max(1, round(duration / 4))
    segments = []
    for i in range(4):
        start = i * seg_len
        end = min(duration, (i + 1) * seg_len)
        segments.append(
            {
                "name": ["开场", "展开", "递进", "收尾"][i],
                "start": start,
                "end": end,
                "purpose": "（离线模板，待模型分析填充）",
                "description": "（离线模板，待模型分析填充）",
            }
        )
    points = max(8, int(duration // 4))
    curve = [
        {"time": time.strftime("%M:%S", time.gmtime(i * duration / max(points - 1, 1))),
         "intensity": 5}
        for i in range(points)
    ]
    return {
        "platform": platform,
        "topic": "（离线模板，待模型分析填充）",
        "summary": "（离线模板，待模型分析填充）",
        "hook": {
            "types": ["悬念"],
            "opening_3s": "（离线模板，待模型分析填充）",
            "description": "（离线模板，待模型分析填充）",
            "why_works": "（离线模板，待模型分析填充）",
        },
        "narrative": {
            "structure": "递进",
            "description": "（离线模板，待模型分析填充）",
            "segments": segments,
        },
        "pacing": {
            "shot_count": 0,
            "avg_shot_duration": 0,
            "duration_distribution": {"0-1s": 0, "1-2s": 0, "2-4s": 0, "4s+": 0},
            "transitions": ["硬切"],
            "camera_movements": ["固定"],
            "rhythm_curve": curve,
        },
        "subtitle_sound": {
            "subtitle_style": {"font": "", "color": "", "position": "", "animation": "", "size": ""},
            "subtitle_description": "（离线模板，待模型分析填充）",
            "bgm_style": "（离线模板，待模型分析填充）",
            "speech_rate": "（离线模板，待模型分析填充）",
            "speech_rate_chars_per_sec": 0,
            "sound_effects": [],
        },
        "replication_script": {
            "overview": "（离线模板，待模型分析填充）",
            "target_duration": round(duration),
            "storyboard": [
                {
                    "no": i + 1,
                    "start": time.strftime("%M:%S", time.gmtime(s["start"])),
                    "end": time.strftime("%M:%S", time.gmtime(s["end"])),
                    "visual": "（离线模板，待模型分析填充）",
                    "subtitle": "",
                    "voiceover": "",
                    "sound": "",
                    "camera": "",
                }
                for i, s in enumerate(segments)
            ],
        },
        "ai_prompts": {
            "master_prompt": "（离线模板，待模型分析填充）",
            "negative_prompt": "",
            "shots": [
                {
                    "no": i + 1,
                    "start": time.strftime("%M:%S", time.gmtime(s["start"])),
                    "end": time.strftime("%M:%S", time.gmtime(s["end"])),
                    "prompt": "（离线模板，待模型分析填充）",
                }
                for i, s in enumerate(segments)
            ],
        },
        "compliance_notes": "复刻内容需遵守平台规范，避免极限词、导流词与拉踩表述。",
    }


# ---------------------------------------------------------------- 主流程


def main() -> int:
    parser = argparse.ArgumentParser(description="视频爆款要素拆解，输出结构化 JSON")
    parser.add_argument("--workdir", default=None, help="预处理产物目录，默认 ./breakdown_output")
    parser.add_argument("--transcript", default=None, help="Agent 完成的音频转录文本文件路径")
    parser.add_argument("--platform", default="抖音", help="视频发布平台，默认 抖音")
    parser.add_argument("--model", default=os.environ.get("ARK_MODEL", "doubao-seed-2-1-pro-260915"),
                        help="模型 Model ID，默认 Seed-2.1-pro-0915（doubao-seed-2-1-pro-260915）")
    parser.add_argument("--max-frames", type=int, default=12, help="发送给模型的最大关键帧数")
    parser.add_argument("--thinking", choices=["disabled", "enabled", "auto"],
                        default="disabled", help="深度思考开关，默认 disabled 以提速")
    parser.add_argument("--max-tokens", type=int, default=16384,
                        help="输出 Token 上限，默认 16384，避免结果被截断")
    parser.add_argument("--offline", action="store_true",
                        help="显式离线模板模式：不调用模型，生成结构完整的模板结果")
    args = parser.parse_args()

    workdir = (
        Path(args.workdir).expanduser()
        if args.workdir
        else Path.cwd() / "breakdown_output"
    )
    result_path = workdir / "analysis_result.json"
    raw_path = workdir / "raw_model_output.txt"

    try:
        # 1. 读取素材
        meta = load_meta(workdir)
        frames = sample_frames(workdir, args.max_frames)
        transcript = load_transcript(workdir, args.transcript)
        log(f"素材就绪：{len(frames)} 张关键帧将参与分析。")

        if args.offline:
            # 2a. 显式离线模板模式
            log("当前为 --offline 离线模板模式，不会调用模型。")
            analysis = build_offline_template(meta, args.platform)
            token_usage = {
                "model": args.model,
                "mode": "offline-template",
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "frames_sent": len(frames),
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "note": "离线模板模式，未实际调用模型；配置 ARK_API_KEY 后去掉 --offline 即可在线分析。",
            }
        else:
            # 2b. 在线调用
            api_key = os.environ.get("ARK_API_KEY") or os.environ.get("VOLC_API_KEY")
            base_url = os.environ.get("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
            if not api_key:
                raise RuntimeError(
                    "未检测到 ARK_API_KEY 环境变量。请配置模型 API Key；"
                    "若仅需跑通流程，可显式加 --offline 生成离线模板。"
                )

            user_prompt = build_user_prompt(
                meta, transcript, [name for name, _ in frames], args.platform
            )
            schema = build_output_schema()

            # 优先：json_schema 严格模式；若模型不支持（HTTP 4xx），
            # 退化为 json_object 模式重试。
            try:
                response = call_chat_model(
                    base_url, api_key, args.model, SYSTEM_PROMPT, user_prompt,
                    frames,
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "video_breakdown",
                            "strict": True,
                            "schema": schema,
                        },
                    },
                    thinking=args.thinking,
                    max_tokens=args.max_tokens,
                )
            except RuntimeError as exc:
                if "HTTP 4" in str(exc):
                    log("json_schema 模式可能不被支持，退化为 json_object 模式重试。")
                    response = call_chat_model(
                        base_url, api_key, args.model, SYSTEM_PROMPT, user_prompt,
                        frames,
                        response_format={"type": "json_object"},
                        thinking=args.thinking,
                        max_tokens=args.max_tokens,
                    )
                else:
                    raise

            choices = response.get("choices", [])
            if not choices:
                raise RuntimeError(f"模型响应中没有 choices 字段：{json.dumps(response)[:500]}")
            finish_reason = choices[0].get("finish_reason", "")
            if finish_reason == "length":
                raise RuntimeError(
                    "模型输出因达到 max_tokens 上限被截断。请增大 --max-tokens"
                    "（例如 --max-tokens 32768）后重试。"
                )
            content = choices[0].get("message", {}).get("content", "")

            # 解析失败时把原始输出落盘，便于排查，不静默失败
            try:
                analysis = extract_json_object(content)
            except json.JSONDecodeError as exc:
                raw_path.write_text(content, encoding="utf-8")
                raise RuntimeError(
                    f"模型输出无法解析为 JSON：{exc}；原始输出已保存到 {raw_path}"
                ) from exc

            usage = response.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
            token_usage = {
                "model": args.model,
                "mode": "online",
                "thinking": args.thinking,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "frames_sent": len(frames),
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
            log(f"Token 消耗：输入 {prompt_tokens} / 输出 {completion_tokens} / 合计 {total_tokens}")

        # 3. 组装并落盘
        result = {
            "meta": meta,
            "platform": analysis.get("platform", args.platform),
            "topic": analysis.get("topic", ""),
            "summary": analysis.get("summary", ""),
            "hook": analysis.get("hook", {}),
            "narrative": analysis.get("narrative", {}),
            "pacing": analysis.get("pacing", {}),
            "subtitle_sound": analysis.get("subtitle_sound", {}),
            "replication_script": analysis.get("replication_script", {}),
            "ai_prompts": analysis.get("ai_prompts", {}),
            "compliance_notes": analysis.get("compliance_notes", ""),
            "token_usage": token_usage,
        }
        result_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        log(f"结构化拆解结果已保存：{result_path}")
        return 0

    except (FileNotFoundError, RuntimeError, json.JSONDecodeError) as exc:
        err(str(exc))
        return 1
    except Exception as exc:  # noqa: BLE001
        err(f"未预期的错误：{type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
