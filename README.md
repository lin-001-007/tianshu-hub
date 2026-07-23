# 天枢 HUD (Tianshu Hub)

<img width="1901" height="920" alt="image" src="https://github.com/user-attachments/assets/b7bfaf74-532f-43bc-bf95-a5195cc37de1" />

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

科幻风 Windows 桌面系统遥测大屏 · **16+ 性能指标** · 反应堆全息动画 · 实时日志 · 可选 AI 中文概括

> 仓库：[https://github.com/lin-001-007/tianshu-hub](https://github.com/lin-001-007/tianshu-hub)

## 功能

- **16+ 指标**：CPU/核心/频率/温度、内存/交换、磁盘读写、网络、进程/线程、GPU、电池、温度传感器等
- **多种可视化**：反应堆线框核心、波形图、雷达图、柱图、环形图、遥测指标矩阵
- **系统日志**：Windows 事件 + 遥测动态；可选 DashScope AI 将英文报错概括成中文
- **可拖拽布局**：面板宽度/高度自动保存到浏览器 localStorage
- **桌面模式**：Edge Kiosk 全屏，或配合 [Lively Wallpaper](https://github.com/rocksdanister/lively) 作动态壁纸，壁纸软件19.9元，一次买断永久免费
<img width="1918" height="1015" alt="image" src="https://github.com/user-attachments/assets/4fc8716b-a09f-4d12-a4ff-da9206115bc2" />

## 快速开始

### 1. 克隆仓库

```powershell
git clone https://github.com/lin-001-007/tianshu-hub.git
cd tianshu-hub
```

### 2. 安装依赖

```powershell
python -m pip install -r server/requirements.txt
cd web
npm install
cd ..
```

### 3. （可选）配置 AI 日志翻译

```powershell
Copy-Item server/.env.example server/.env
# 编辑 server/.env，填入 DASHSCOPE_API_KEY
```

### 4. 一键启动

```powershell
.\start-hud.ps1          # 普通窗口
.\start-hud.ps1 -Kiosk   # 全屏桌面模式
```

浏览器访问：<http://127.0.0.1:5199>

## 端口

| 服务 | 端口 |
|------|------|
| 指标 API + SSE | 8799 |
| HUD 前端 (Vite) | 5199 |

## 项目结构

```
tianshu-hub/
├── start-hud.ps1       # 一键启动
├── create-shortcut.ps1 # 创建桌面快捷方式
├── server/             # Python FastAPI 后端
│   ├── main.py
│   ├── metrics.py
│   ├── logs.py
│   └── log_summarizer.py
├── web/                # Vue 3 前端
│   └── src/
└── docs/               # 详细使用说明
```

## 文档

完整安装、界面说明、API、排错指南见 [docs/使用说明书.md](docs/使用说明书.md)。

## 技术栈

- **后端**：Python 3.9+ · FastAPI · psutil · uvicorn
- **前端**：Vue 3 · Vite 5 · Canvas 动画

## 开源协议

[MIT License](LICENSE)

## 说明

- 本工具仅在本机采集系统指标，**不会修改 Windows 壁纸文件**
- `server/.env` 含 API 密钥，已在 `.gitignore` 中排除，请勿提交到仓库
