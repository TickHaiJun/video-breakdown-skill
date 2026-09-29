<p align="center">
  <img src="assets/cover.png" alt="Video Breakdown Skill：视频拆解与复刻，从一条视频到可执行的创作方案" width="100%" />
</p>

<h1 align="center">视频爆款拆解与复刻</h1>

<p align="center">
  <strong>拆解开头钩子与叙事节奏，把参考视频变成分镜脚本、AI 提示词和可分享的报告。</strong>
</p>

<p align="center">
  <a href="#环境准备"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&amp;logo=python&amp;logoColor=white" alt="Python 3.10+" /></a>
  <a href="#环境准备"><img src="https://img.shields.io/badge/FFmpeg-required-007808?style=flat-square&amp;logo=ffmpeg&amp;logoColor=white" alt="需要 FFmpeg 与 ffprobe" /></a>
  <a href="#配置模型"><img src="https://img.shields.io/badge/Model-Volcengine%20Ark-1677FF?style=flat-square" alt="模型接口：火山方舟 Ark" /></a>
  <a href="#解析报告"><img src="https://img.shields.io/badge/Report-Standalone%20HTML-14B8A6?style=flat-square&amp;logo=html5&amp;logoColor=white" alt="自包含 HTML 报告" /></a>
  <a href="#license"><img src="https://img.shields.io/badge/License-MIT-D4A45F?style=flat-square" alt="许可证：MIT" /></a>
</p>

<p align="center">
  <a href="#解析报告">解析报告</a> ·
  <a href="#核心能力">核心能力</a> ·
  <a href="#快速上手">快速上手</a> ·
  <a href="#命令行使用">命令行使用</a> ·
  <a href="#常见问题">常见问题</a>
</p>

---

`video-breakdown-skill` 是面向短视频运营、编导与内容创作者的 Agent Skill。提供一条视频，即可围绕「为什么吸引人、如何组织内容、怎样拍出自己的版本」完成拆解，交付 **逐段分镜脚本、面向 Seedance 的生成提示词、自包含 HTML 报告**。

支持 `mp4` / `mov` / `mkv` / `m4v` 等常见视频格式；可在豆包工作中由 Agent 执行，也可以通过 Python 脚本分步运行。

## 解析报告

报告将素材信息、拆解结论与创作方案放在同一页，支持深浅主题切换、节奏图表和提示词复制。封面与图表资源内嵌，生成后可直接在浏览器中打开，无需外部 CDN。

**[查看完整报告截图](assets/doubaoSkill.jpg)** · **[查看示例 HTML 文件](examples/sample_report/report.html)** · **[查看示例分析 JSON](examples/sample_analysis_result.json)**

> 在 GitHub 中，HTML 链接展示的是文件内容；下载后用浏览器打开即可查看报告页面。

<details>
  <summary><strong>展开解析报告长图预览</strong></summary>
  <p align="center">
    <a href="assets/doubaoSkill.jpg">
      <img src="assets/doubaoSkill.jpg" alt="视频解析报告长图：视频信息、爆款拆解、镜头节奏、字幕与声音、复刻脚本、Seedance 提示词及 Token 统计" width="800" />
    </a>
  </p>
</details>

| 报告模块 | 你能看到什么 |
| --- | --- |
| 视频基本信息 | 封面、时长、分辨率、帧率、编码与音频信息 |
| 爆款拆解 | 开头钩子、前 3 秒呈现、叙事结构与分段时间线 |
| 镜头节奏 | 估计镜头数、时长分布、节奏强度曲线、转场与运镜 |
| 字幕与声音 | 字幕样式、配乐风格、语速与音效分析 |
| 复刻脚本 | 时间轴、画面、字幕、旁白、声音与运镜组成的分镜表 |
| AI 生成提示词 | 面向 Seedance 的整体提示词、负向提示词与分镜提示词 |
| Token 统计 | 本次输入 / 输出 Token、发送帧数；预留历史版本对比区域 |

## 核心能力

<p align="center">
  <img src="assets/analysis-dimensions.png" alt="视频拆解概念插画：将视频展开为开头钩子、叙事结构、剪辑节奏与字幕声音四个维度" width="860" />
</p>

### 看懂一条视频的四个维度

| 维度 | 关注的问题 | 分析内容 |
| --- | --- | --- |
| **开头钩子** | 前 3 秒为什么能留住人？ | 悬念、冲突、利益点、情绪、好奇、身份认同 |
| **叙事结构** | 内容如何展开与收尾？ | 总分总、递进、反转、痛点与解决方案、并列展示 |
| **镜头节奏** | 哪里快、哪里慢，怎样衔接？ | 镜头时长、节奏曲线、转场类型、运镜方式 |
| **字幕与声音** | 文字和声音怎样配合画面？ | 字幕样式与位置、动效、BGM、语速、音效 |

### 把分析变成创作材料

<p align="center">
  <img src="assets/creation-workbench.png" alt="复刻创作概念插画：将拆解结果整理为分镜、脚本和 AI 画面提示词" width="860" />
</p>

- **用于拍摄**：按时间段整理画面、台词、字幕、声音和运镜，形成可执行的分镜表。
- **用于 AI 创作**：整理主体、动作、场景、光线与色调，输出可复制的 Seedance 提示词。
- **用于复盘与协作**：交付 HTML 报告与结构化 JSON，方便阅读、分享和后续处理。

<sub>封面与以上两张配图为 AI 生成的概念插画，<a href="assets/image-prompts.md">查看生成提示词</a>；解析报告预览使用仓库中的 <code>assets/doubaoSkill.jpg</code>。</sub>

## 快速上手

### 在豆包工作中使用

将整个技能文件夹放入豆包工作环境的自定义技能目录，保留以下结构：

```text
workspace/.user_skills/video-breakdown-skill/
├── SKILL.md
├── scripts/
└── templates/
```

上传视频后，可以直接这样说：

> 帮我拆解这个视频，分析前 3 秒的钩子和镜头节奏，生成复刻分镜、Seedance 提示词和 HTML 报告。

Agent 会按照 [SKILL.md](SKILL.md) 完成预处理、音频转录、结构化分析和报告生成。执行环境需具备下文列出的 Python、FFmpeg 与模型访问配置；若环境已提供这些配置，即可直接运行。





## 安装 Skill

> 请将下面的仓库地址替换为本项目实际的 GitHub 地址。

### Codex

安装到个人 Skill 目录：

```bash
mkdir -p ~/.agents/skills

git clone https://github.com/TickHaiJun//video-breakdown-skill.git \
  ~/.agents/skills/video-breakdown-skill
```

仅在当前项目中使用：

```bash
mkdir -p .agents/skills

git clone https://github.com/TickHaiJun//video-breakdown-skill.git \
  .agents/skills/video-breakdown-skill
```

安装完成后，重新启动 Codex 或创建新会话，然后输入：

```text
使用 video-breakdown-skill 拆解这个视频，生成复刻脚本和 HTML 报告。
```



## 命令行使用

### 环境准备

下载仓库并解压，进入包含 `SKILL.md` 的项目根目录。

| 依赖 | 说明 |
| --- | --- |
| **Python 3.10+** | 脚本使用 `str \| None` 类型注解，需要 Python 3.10 或更新版本 |
| **FFmpeg / ffprobe** | 安装后加入 `PATH`，用于探测视频、按 1 fps 抽帧和提取音频 |
| **火山方舟 API Key** | 在线分析需要；浏览示例或显式使用离线模板时不需要 |

核心流程仅使用 **Python 标准库**，无需安装第三方 Python 包，也不依赖 OpenCV。`requirements.txt` 仅记录依赖说明与可选方案。

```bash
# 检查运行环境
python3 --version
ffmpeg -version
ffprobe -version

# macOS：如未安装 FFmpeg，可使用 Homebrew
brew install ffmpeg
```

### 配置模型

在 [火山方舟控制台](https://console.volcengine.com/ark) 获取 API Key，并确保账号有目标模型的调用权限。以下配置用于 macOS / Linux shell：

```bash
export ARK_API_KEY="<你的方舟 API Key>"

# 可选：覆盖脚本默认的接口地址和模型
export ARK_BASE_URL="https://ark.cn-beijing.volces.com/api/v3"
export ARK_MODEL="doubao-seed-2-1-pro-260915"
```

当前脚本默认模型为 `doubao-seed-2-1-pro-260915`（项目中称为 `Seed-2.1-pro-0915`）。也可通过 `--model` 传入账号可用、兼容脚本请求格式的模型 ID 或推理接入点 ID（`ep-…`）；命令行参数优先于 `ARK_MODEL`。

### 执行拆解

在项目根目录按顺序运行：

```bash
# 1. 读取元数据、按 1 fps 抽帧、提取音频
python3 scripts/preprocess.py "/path/to/video.mp4"

# 2. 有语音时，由 Agent 或其他转录工具生成文本，
#    保存为 breakdown_output/transcript.txt；无语音时可跳过。

# 3. 基于元数据、采样关键帧和可用的转录文本进行分析
python3 scripts/analyze.py

# 4. 生成报告，用浏览器打开 breakdown_output/report.html
python3 scripts/build_report.py
```

处理流程：**视频 → 元数据 / 关键帧 / 音频 → 转录文本 → 结构化分析 → HTML 报告**。

`analyze.py` 默认均匀采样最多 **12 张关键帧**，不会直接将视频或 `audio.mp3` 发送给模型。未提供转录文本时，仅根据画面与元数据分析；声音相关结论需结合实际素材核对。

### 常用参数

```bash
# 指定参考平台和发送帧数（max-frames 请使用不小于 2 的整数）
python3 scripts/analyze.py --platform 小红书 --max-frames 16

# 使用单独准备的转录文本
python3 scripts/analyze.py --transcript "/path/to/transcript.txt"

# 覆盖模型，或调整思考模式与输出上限
python3 scripts/analyze.py --model "<可用的模型或接入点 ID>"
python3 scripts/analyze.py --thinking enabled --max-tokens 32768

# 已完成预处理时，无需 API Key 即可验证离线报告流程
python3 scripts/analyze.py --offline
python3 scripts/build_report.py
```

**离线模式生成的是占位模板，不是真实分析结果。** 它仍需要预处理产生的元数据和关键帧，适合检查输出结构与报告样式。

处理不同视频时，为每条视频使用独立目录，并在三个步骤中传入相同的 `--workdir`：

```bash
python3 scripts/preprocess.py "/path/to/video.mp4" --workdir breakdown_output/demo
python3 scripts/analyze.py --workdir breakdown_output/demo
python3 scripts/build_report.py --workdir breakdown_output/demo
```

完整参数可通过各脚本的 `--help` 查看。

## 输出文件

```text
breakdown_output/
├── meta.json               # 视频元数据
├── frames/                 # 按 1 fps 抽取的 JPG 帧
├── audio.mp3               # 有音频时生成：16 kHz 单声道
├── no_audio.flag           # 无音频流时生成的标记
├── transcript.txt          # 由 Agent 或用户提供的转录文本（可选）
├── analysis_result.json    # 结构化分析、复刻脚本、提示词与 Token 统计
└── report.html             # 可独立打开的 HTML 报告
```

## 目录结构

```text
video-breakdown-skill/
├── README.md
├── SKILL.md                       # Agent 的触发条件与执行指令
├── assets/
│   ├── cover.png                  # 项目封面
│   ├── analysis-dimensions.png    # 拆解维度插画
│   ├── creation-workbench.png     # 复刻创作插画
│   ├── doubaoSkill.jpg            # 解析报告截图
│   └── image-prompts.md           # 配图生成提示词
├── scripts/
│   ├── preprocess.py             # 视频预处理
│   ├── analyze.py                # 模型分析与 JSON 输出
│   └── build_report.py           # HTML 报告生成
├── templates/
│   └── report_template.html      # 报告模板
├── examples/
│   ├── sample_analysis_result.json
│   └── sample_report/
│       ├── analysis_result.json
│       └── report.html
└── requirements.txt              # 依赖说明
```



## 输出报告

<p align="center">
  <img src="assets/doubaoSkill.jpg" alt="skill" width="860" />
</p>



## 常见问题

**没有 API Key 能使用吗？**  
可以浏览已有示例，也可以先预处理视频，再用 `--offline` 生成占位模板。对新素材进行真实分析需要配置 API Key。

**会自动转录音频吗？**  
Skill 将转录步骤交给 Agent；Python 脚本只负责提取音频和读取转录文本。手动运行时，需自行准备 `transcript.txt` 或通过 `--transcript` 指定文件。

**能直接生成复刻视频吗？**  
当前交付分镜脚本与 Seedance 提示词，需在相应的视频生成工具中继续创作。

**长视频怎样处理？**  
预处理会按每秒一帧生成图片，长视频建议先截取目标片段。`--max-frames` 只限制发送给模型的帧数，不会减少本地抽帧量。采样分析中的镜头数与时长分布属于估计值。

**模型报错或输出被截断怎么办？**  
先检查 API Key、模型权限及 `ARK_BASE_URL`；出现输出截断时可调高 `--max-tokens`。若模型输出无法解析，脚本会将原文写入工作目录的 `raw_model_output.txt`，便于排查。



## 联系我

<p align="center">
  <img src="https://img2024.cnblogs.com/blog/1654515/202602/1654515-20260224140842561-1851540179.jpg" alt="skill" width="400" />
</p>

