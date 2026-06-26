# mytools

个人工具集合，每个工具都配有详细的中文使用说明。

## 工具列表

| 工具 | 说明 | 适用平台 |
|------|------|----------|
| [doubao-message-cleaner](./doubao-message-cleaner/) | 豆包网页版消息批量清理 | 桌面浏览器 |

## 目录结构

```
mytools/
├── README.md                         # 本文件
├── .gitignore
├── doubao-message-cleaner/           # 豆包消息批量清理
│   ├── README.md                     # 使用说明
│   └── delete-doubao-console.js      # 主脚本
└── ...                               # 更多工具待添加
```

## 使用约定

- 所有工具都是**浏览器控制台脚本**，打开 F12 → Console → 粘贴运行即可
- 每个工具的 `README.md` 都包含完整的使用说明、原理和 FAQ
- 无需安装任何依赖，纯 JavaScript
