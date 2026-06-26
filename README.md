# mytools

一天一个小刚需，每个工具解决一个实际问题。

## 工具列表

<!-- TOOLS_START -->
| 工具 | 说明 | 类型 |
|------|------|------|
| [豆包消息批量清理工具](./doubao-message-cleaner/) | 一键清空豆包网页版（doubao.com）主对话中的所有消息，无需手动逐条删除。 | 浏览器脚本 |
| [FileShare — 本地文件分享](./file-share/) | 在任意目录启动 HTTP 服务器，自动检测局域网 IP，终端显示二维码。 | Python |
<!-- TOOLS_END -->

## 目录结构

<!-- TREE_START -->
```
mytools/
├── README.md
├── doubao-message-cleaner/
└── file-share/
```
<!-- TREE_END -->

> 工具列表和目录结构由 `python scripts/update-readme.py` 自动生成，无需手动维护。

## 使用方式

每个工具子目录下都有独立的 `README.md` 说明文档，包含完整的使用教程。

| 工具类型 | 使用方式 |
|----------|----------|
| 浏览器脚本 | 打开网页 → F12 → Console → 粘贴运行 |
| Python 工具 | `python xxx.py` 或按子目录 README 操作 |
