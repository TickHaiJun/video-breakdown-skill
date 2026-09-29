#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preprocess.py —— 视频预处理脚本

功能：
  1. 使用 ffprobe 获取视频元数据（时长、分辨率、帧率、编码等），保存为 meta.json
  2. 使用 ffmpeg 按 1fps 抽帧，保存到 frames/ 目录（jpg 格式）
  3. 使用 ffmpeg 提取音频，保存为 audio.mp3

约束：
  - 仅依赖 Python 3 标准库 + 系统 ffmpeg/ffprobe，不使用 opencv
  - 视频路径通过命令行参数传入，禁止硬编码
  - 路径不存在 / 非视频文件 / ffmpeg 执行失败时，明确报错并以非零码退出

用法：
  python3 scripts/preprocess.py "<视频路径>" [--workdir <输出目录>]
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------- 日志工具


def log(msg: str) -> None:
    """打印带时间阶段的进度日志，便于 Agent 监控。"""
    print(f"[preprocess] {msg}", flush=True)


def err(msg: str) -> None:
    print(f"[preprocess][ERROR] {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------- 通用执行


def require_binary(name: str) -> str:
    """确认 ffmpeg / ffprobe 可执行文件存在。"""
    binary = shutil.which(name)
    if not binary:
        raise RuntimeError(
            f"未找到 `{name}` 可执行文件，请先安装 ffmpeg（本项目基于 ffmpeg 8.x 验证）"
            "并确认其已加入 PATH。"
        )
    return binary


def run_cmd(cmd: list, stage: str) -> subprocess.CompletedProcess:
    """执行子进程命令；失败时抛出带阶段信息和 stderr 的明确错误。"""
    log(f"{stage}，执行命令：{' '.join(str(c) for c in cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()
        tail_msg = "\n".join(tail[-15:]) if tail else "(无 stderr 输出)"
        raise RuntimeError(f"{stage}失败（returncode={proc.returncode}）：\n{tail_msg}")
    return proc


# ---------------------------------------------------------------- 输入校验


def validate_video(video_path: Path, ffprobe_bin: str) -> dict:
    """校验文件存在且为可被 ffprobe 解析的视频，返回 ffprobe 原始 JSON。"""
    if not video_path.exists():
        raise FileNotFoundError(f"视频路径不存在：{video_path}")
    if not video_path.is_file():
        raise RuntimeError(f"给定路径不是文件：{video_path}")

    proc = run_cmd(
        [
            ffprobe_bin,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(video_path),
        ],
        stage="探测视频信息",
    )
    try:
        probe = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"ffprobe 输出无法解析为 JSON：{exc}") from exc

    streams = probe.get("streams", [])
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    if not video_streams:
        raise RuntimeError(
            f"文件中未检测到视频流，可能不是有效的视频文件：{video_path}"
        )
    return probe


# ---------------------------------------------------------------- 帧率换算


def parse_frame_rate(rate: str) -> float:
    """将 ffprobe 的 '30/1'、'30000/1001' 形式换算为每秒帧数。"""
    try:
        if not rate or rate == "0/0":
            return 0.0
        num, den = rate.split("/")
        den_f = float(den)
        if den_f == 0:
            return 0.0
        return round(float(num) / den_f, 3)
    except (ValueError, ZeroDivisionError):
        return 0.0


# ---------------------------------------------------------------- 元数据


def build_meta(video_path: Path, probe: dict) -> dict:
    """从 ffprobe 结果中提取结构化元数据。"""
    vstream = next(s for s in probe["streams"] if s.get("codec_type") == "video")
    astream = next((s for s in probe["streams"] if s.get("codec_type") == "audio"), None)
    fmt = probe.get("format", {})

    duration = 0.0
    if fmt.get("duration") is not None:
        duration = float(fmt["duration"])
    elif vstream.get("duration") is not None:
        duration = float(vstream["duration"])

    width = int(vstream.get("width") or 0)
    height = int(vstream.get("height") or 0)
    fps = parse_frame_rate(vstream.get("r_frame_rate", "0/0"))
    avg_fps = parse_frame_rate(vstream.get("avg_frame_rate", "0/0"))

    orientation = "竖屏"
    if width and height:
        if width > height:
            orientation = "横屏"
        elif width == height:
            orientation = "方形"

    meta = {
        "file_name": video_path.name,
        "file_path": str(video_path.resolve()),
        "file_size_bytes": video_path.stat().st_size,
        "duration_seconds": round(duration, 3),
        "width": width,
        "height": height,
        "resolution": f"{width}x{height}" if width and height else "unknown",
        "orientation": orientation,
        "fps": fps,
        "avg_fps": avg_fps,
        "video_codec": vstream.get("codec_name", "unknown"),
        "pixel_format": vstream.get("pix_fmt", "unknown"),
        "bit_rate": int(fmt["bit_rate"]) if fmt.get("bit_rate") else None,
        "format_name": fmt.get("format_name", "unknown"),
        "has_audio": astream is not None,
        "audio_codec": astream.get("codec_name") if astream else None,
        "audio_sample_rate": int(astream["sample_rate"]) if astream and astream.get("sample_rate") else None,
        "audio_channels": astream.get("channels") if astream else None,
    }
    return meta


# ---------------------------------------------------------------- 主流程


def main() -> int:
    parser = argparse.ArgumentParser(description="视频预处理：元数据 / 抽帧 / 音频提取")
    parser.add_argument("video_path", help="用户上传视频的本地路径（必填）")
    parser.add_argument(
        "--workdir",
        default=None,
        help="产物输出目录，默认为当前工作目录下的 breakdown_output/",
    )
    args = parser.parse_args()

    video_path = Path(args.video_path).expanduser()
    workdir = (
        Path(args.workdir).expanduser()
        if args.workdir
        else Path.cwd() / "breakdown_output"
    )
    frames_dir = workdir / "frames"

    try:
        ffprobe_bin = require_binary("ffprobe")
        ffmpeg_bin = require_binary("ffmpeg")

        # 1. 校验 + 探测
        log(f"开始处理视频：{video_path}")
        probe = validate_video(video_path, ffprobe_bin)
        meta = build_meta(video_path, probe)

        workdir.mkdir(parents=True, exist_ok=True)
        frames_dir.mkdir(parents=True, exist_ok=True)

        # 2. 元数据落盘
        meta_path = workdir / "meta.json"
        meta_path.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        log(
            f"元数据已保存：{meta_path}（时长 {meta['duration_seconds']}s，"
            f"{meta['resolution']}，{meta['fps']}fps，编码 {meta['video_codec']}）"
        )

        # 长视频提示（不阻断，1fps 抽帧可能产生大量图片）
        if meta["duration_seconds"] > 300:
            log(
                f"提示：视频时长 {meta['duration_seconds']}s，1fps 抽帧将产生约 "
                f"{int(meta['duration_seconds'])} 张图片，耗时与磁盘占用会相应增加。"
            )

        # 3. 按 1fps 抽帧
        #    -q:v 2 控制 jpg 质量；-vsync vfr 配合 fps 滤镜避免重复帧
        frame_pattern = str(frames_dir / "frame_%04d.jpg")
        run_cmd(
            [
                ffmpeg_bin,
                "-y",
                "-i",
                str(video_path),
                "-vf",
                "fps=1",
                "-vsync",
                "vfr",
                "-q:v",
                "2",
                frame_pattern,
            ],
            stage="按 1fps 抽取关键帧",
        )
        frame_count = len(list(frames_dir.glob("frame_*.jpg")))
        if frame_count == 0:
            raise RuntimeError("抽帧完成但 frames/ 目录下没有图片，请检查视频是否损坏。")
        log(f"抽帧完成：共 {frame_count} 张，目录 {frames_dir}")

        # 4. 提取音频
        audio_path = workdir / "audio.mp3"
        if meta["has_audio"]:
            run_cmd(
                [
                    ffmpeg_bin,
                    "-y",
                    "-i",
                    str(video_path),
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-b:a",
                    "64k",
                    str(audio_path),
                ],
                stage="提取音频（16kHz 单声道 mp3，便于语音转录）",
            )
            log(f"音频已保存：{audio_path}")
        else:
            # 无音频流属于素材本身属性，给出明确提示并写入标记，不当作静默失败
            log("警告：该视频不含音频流，跳过音频提取并写入 no_audio 标记。")
            (workdir / "no_audio.flag").write_text(
                "source video has no audio stream\n", encoding="utf-8"
            )

        log("预处理全部完成。")
        return 0

    except (FileNotFoundError, RuntimeError) as exc:
        err(str(exc))
        return 1
    except Exception as exc:  # noqa: BLE001 - 兜底，确保任何异常都有明确报错
        err(f"未预期的错误：{type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
