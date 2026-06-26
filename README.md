# mytools

一天一个小刚需，每个工具解决一个实际问题。

## 工具列表

<!-- TOOLS_START -->
| 工具 | 说明 | 类型 |
|------|------|------|
| [豆包消息批量清理工具](./doubao-message-cleaner/) | 全自动批量删除**：自动滚动加载历史消息，分批调用豆包官方删除接口 | 浏览器脚本 |
| [FileShare — 本地文件分享](./file-share/) | 在任意目录启动 HTTP 服务器，自动检测局域网 IP，终端显示二维码。手机扫码即可浏览、下载文件，免去微信传文件的压缩和大小限制。 | Python |
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
