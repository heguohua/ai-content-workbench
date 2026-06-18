# AI Content Workbench

一个面向 AI 内容创作场景的全流程工作台项目，支持从选题输入、标题生成、大纲编辑、正文流式生成，到配图分析、图文合成与结果管理的完整闭环。

本仓库当前以 `frontend + python-backend` 作为本地开发主线，同时保留原始多实现结构，便于后续扩展与对比。

## 项目亮点

- AI 长链路创作流程：标题、大纲、正文、配图按阶段推进，支持用户在关键节点介入确认
- 实时交互体验：基于 SSE 推送流式内容与执行进度
- 多智能体协作：标题生成、结构规划、正文生成、配图分析、图片处理职责拆分
- 多配图策略：支持图库检索、图标、流程图、AI 生图、SVG 示意图等多种方式
- 商业化能力雏形：包含用户体系、配额、VIP 支付、执行日志、后台统计

## 仓库结构

```text
.
├── frontend/          # Vue 3 + TypeScript 前端
├── python-backend/    # FastAPI 后端（推荐本地开发）
├── src/               # Java Spring Boot 后端
├── go-backend/        # Go 后端实现
└── sql/               # 数据库初始化脚本
```

## 前端结构

前端位于 [frontend](./frontend)，技术栈为：

- Vue 3
- TypeScript
- Vite
- Pinia
- Vue Router
- Ant Design Vue
- Axios
- ECharts

核心目录：

```text
frontend/src/
├── api/               # API 调用层
├── components/        # 公共组件
├── pages/             # 页面
├── router/            # 路由配置
├── stores/            # 状态管理
├── utils/             # 工具函数
└── config/            # 环境配置
```

创作主页面：

- `frontend/src/pages/article/ArticleCreatePage.vue`

## Python 后端结构

Python 后端位于 [python-backend](./python-backend)，技术栈为：

- FastAPI
- SQLAlchemy / databases
- Redis
- OpenAI Compatible API
- Stripe

核心目录：

```text
python-backend/app/
├── routers/           # 路由层
├── services/          # 业务服务层
├── agent/             # 多智能体编排
├── schemas/           # Pydantic 模型
├── models/            # 数据模型
├── managers/          # SSE 等基础设施
├── constants/         # Prompt / 常量配置
└── utils/             # 工具函数
```

主入口：

- `python-backend/app/main.py`

## 核心业务流程

```text
1. 输入选题
2. 生成多个标题方案
3. 用户确认标题并补充要求
4. 生成文章大纲
5. 用户编辑或 AI 修改大纲
6. 流式生成正文
7. 分析配图需求并生成图片
8. 合成完整图文内容
```

## 本地开发

### 前置环境

- Node.js 18+
- Python 3.10+
- MySQL 8
- Redis 7

### 1. 启动前端

```bash
cd frontend
npm install
npm run dev
```

默认访问：

- [http://localhost:5173](http://localhost:5173)

### 2. 启动 Python 后端

```bash
cd python-backend
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8567
```

默认访问：

- 后端根路径：[http://localhost:8567](http://localhost:8567)
- 接口文档：[http://localhost:8567/docs](http://localhost:8567/docs)

### 3. Python 后端配置

Python 本地开发依赖：

- MySQL
- Redis
- `python-backend/.env`

如果你的本机 MySQL 不是 `13306`，可以临时指定：

```bash
cd python-backend
env DB_PORT=3306 .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8567
```

## 后续升级方向

本项目后续重点会往以下方向演进：

- 创作页工作台化
- 前端状态机与 SSE 事件流重构
- Prompt 配置化与版本化
- 后端异步任务可靠化
- AI 输出质量评估闭环
- 平台化扩展（多模板、多模型、多角色）

## 说明

当前仓库是基于原始项目进行的个人开发与整理版本：

- `origin` 指向当前个人仓库
- `upstream` 指向原始上游仓库

适合作为：

- AI 应用前端/全栈作品集项目
- 多智能体内容创作平台实验仓库
- Prompt、SSE、AI 工作台交互改造实践项目
