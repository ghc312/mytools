#!/bin/bash
# 一键安装 Git hooks
# 用法：bash scripts/install-hooks.sh

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOK="$ROOT/.git/hooks/pre-commit"
SRC="$ROOT/scripts/pre-commit"

if [ ! -d "$ROOT/.git/hooks" ]; then
    echo "❌ 当前目录不是 git 仓库"
    exit 1
fi

cp "$SRC" "$HOOK"
chmod +x "$HOOK"

echo "✅ pre-commit hook 已安装"
echo "  以后每次 git commit 时会自动运行 scripts/update-readme.py"
echo ""
echo "   手动移除：rm $HOOK"
