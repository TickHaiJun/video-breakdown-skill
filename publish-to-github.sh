#!/usr/bin/env bash

set -Eeuo pipefail

REPO_URL="https://github.com/TickHaiJun/video-breakdown-skill.git"
COMMIT_MESSAGE="${1:-first commit}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR"

if ! command -v git >/dev/null 2>&1; then
  echo "错误：未找到 git，请先安装 Git。" >&2
  exit 1
fi

if ! git --version >/dev/null 2>&1; then
  echo "错误：Git 当前无法运行。" >&2
  echo "如果 macOS 提示尚未同意 Xcode 许可，请先执行：" >&2
  echo "  sudo xcodebuild -license" >&2
  exit 1
fi

if [[ ! -d .git ]]; then
  echo "正在初始化 Git 仓库……"
  git init
fi

if ! git config user.name >/dev/null || ! git config user.email >/dev/null; then
  echo "错误：尚未配置 Git 提交身份，请先执行：" >&2
  echo '  git config --global user.name "你的 GitHub 用户名"' >&2
  echo '  git config --global user.email "你的 GitHub 邮箱"' >&2
  exit 1
fi

echo "正在暂存项目文件……"
git add -A

if git diff --cached --quiet; then
  echo "没有需要提交的新变更，跳过 git commit。"
else
  echo "正在创建提交：$COMMIT_MESSAGE"
  git commit -m "$COMMIT_MESSAGE"
fi

git branch -M main

if git remote get-url origin >/dev/null 2>&1; then
  CURRENT_ORIGIN="$(git remote get-url origin)"
  if [[ "$CURRENT_ORIGIN" != "$REPO_URL" ]]; then
    echo "正在将 origin 更新为：$REPO_URL"
    git remote set-url origin "$REPO_URL"
  fi
else
  echo "正在添加远程仓库：$REPO_URL"
  git remote add origin "$REPO_URL"
fi

echo "正在推送到 GitHub……"
git push -u origin main

echo "发布完成：$REPO_URL"
