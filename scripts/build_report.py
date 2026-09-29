#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_report.py —— HTML 报告生成脚本

功能：
  1. 读取 analyze.py 输出的 analysis_result.json
  2. 读取 templates/report_template.html
  3. 将封面帧（默认首帧）以 base64 内嵌到数据中，替换模板占位符
  4. 渲染生成自包含的 report.html（本地双击即可打开，不依赖外部 CDN）

用法：
  python3 scripts/build_report.py [--workdir breakdown_output]
      [--template templates/report_template.html] [--cover-frame <图片路径>]
"""

import argparse
import base64
import json
import sys
from pathlib import Path

PLACEHOLDER = "__ANALYSIS_DATA__"


def log(msg: str) -> None:
    print(f"[build_report] {msg}", flush=True)


def err(msg: str) -> None:
    print(f"[build_report][ERROR] {msg}", file=sys.stderr, flush=True)


def embed_cover(workdir: Path, cover_frame: str | None) -> str:
    """选择封面帧并转成 data URI；找不到时返回空字符串。"""
    if cover_frame:
        cover_path = Path(cover_frame).expanduser()
    else:
        frames = sorted((workdir / "frames").glob("frame_*.jpg"))
        if not frames:
            return ""
        # 首帧可能是黑屏，取第 2 帧（约第 1 秒）更稳妥，否则退回首帧
        cover_path = frames[1] if len(frames) > 1 else frames[0]

    if not cover_path.exists():
        log(f"警告：封面帧不存在：{cover_path}，报告将不显示封面。")
        return ""
    b64 = base64.b64encode(cover_path.read_bytes()).decode("utf-8")
    log(f"已内嵌封面帧：{cover_path.name}（{cover_path.stat().st_size // 1024} KB）")
    return f"data:image/jpeg;base64,{b64}"


def main() -> int:
    parser = argparse.ArgumentParser(description="根据结构化 JSON 生成 HTML 报告")
    parser.add_argument("--workdir", default=None, help="分析产物目录，默认 ./breakdown_output")
    parser.add_argument("--template", default=None, help="HTML 模板路径，默认使用 skill 内置模板")
    parser.add_argument("--cover-frame", default=None, help="指定封面帧图片路径，默认取第 2 帧")
    parser.add_argument("--output", default=None, help="报告输出路径，默认 <workdir>/report.html")
    args = parser.parse_args()

    workdir = (
        Path(args.workdir).expanduser()
        if args.workdir
        else Path.cwd() / "breakdown_output"
    )
    # 模板默认路径：本脚本位于 scripts/ 下，模板在 ../templates/
    script_dir = Path(__file__).resolve().parent
    template_path = (
        Path(args.template).expanduser()
        if args.template
        else script_dir.parent / "templates" / "report_template.html"
    )
    result_path = workdir / "analysis_result.json"
    output_path = (
        Path(args.output).expanduser()
        if args.output
        else workdir / "report.html"
    )

    try:
        # 1. 读取分析结果
        if not result_path.exists():
            raise FileNotFoundError(
                f"未找到 analysis_result.json：{result_path}，请先运行 analyze.py。"
            )
        data = json.loads(result_path.read_text(encoding="utf-8"))
        log(f"已读取分析结果：{result_path}")

        # 2. 读取模板
        if not template_path.exists():
            raise FileNotFoundError(f"未找到 HTML 模板：{template_path}")
        template = template_path.read_text(encoding="utf-8")
        if PLACEHOLDER not in template:
            raise RuntimeError(
                f"模板中缺少占位符 {PLACEHOLDER}，请检查模板：{template_path}"
            )

        # 3. 内嵌封面
        cover = embed_cover(workdir, args.cover_frame)
        data.setdefault("_assets", {})
        data["_assets"]["cover"] = cover

        # 4. 注入数据并输出
        # 使用 ensure_ascii=False 保留中文，再通过 json.dumps 保证是合法 JS 对象字面量
        data_js = json.dumps(data, ensure_ascii=False, indent=2)
        html = template.replace(PLACEHOLDER, data_js)
        output_path.write_text(html, encoding="utf-8")
        log(f"HTML 报告已生成：{output_path}（{output_path.stat().st_size // 1024} KB）")
        return 0

    except (FileNotFoundError, RuntimeError, json.JSONDecodeError) as exc:
        err(str(exc))
        return 1
    except Exception as exc:  # noqa: BLE001
        err(f"未预期的错误：{type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
