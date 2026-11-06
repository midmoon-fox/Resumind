# Resumind · 简立得

AI 简历求职助手，包含简历资料整理、岗位 JD 分析、智能追问、简历生成与编辑、模板预览与导出、面试准备等业务。

## 目录

```text
frontend/             Vue 3 + TypeScript + Vite 前端
backend/
  app/                FastAPI 接口、JWT 认证、AI 与任务处理
  resume_b/           简历文档、模板渲染、导出与面试资料
  assets/             HTML/CSS 和 Word 模板资产
  alembic/            数据库迁移
  scripts/            Web、Worker、Supervisor 启动脚本
```

## 前端

需要 Node.js 22.12+ 和 pnpm（版本见 `frontend/package.json`）。

```powershell
cd frontend
pnpm install --frozen-lockfile
pnpm dev
```

访问 `http://127.0.0.1:5173`。开发请求默认代理到 `https://localhost:8443`，配置在 `frontend/vite.config.ts`。

```powershell
pnpm test
pnpm build
```

## 后端

需要 Python 3.13、MySQL、Redis；PDF 导出需要 Playwright Chromium 和中文字体。

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
```

启动前通过环境变量配置 `DATABASE_URL`、`APP_SECRET`（至少 32 位随机密钥）、`REDIS_URL`、`APP_ORIGIN`、`DOWNLOAD_BASE` 和 `OBJECT_ROOT`。模型设置参考 `.env.example`，模型密钥只放在后端私有 `.env.local` 或部署环境中。

数据库初始化：

```powershell
python -m alembic upgrade head
```

开发 Web 启动示例（请自行准备本机 HTTPS 证书，路径替换为实际文件）：

```powershell
python -m uvicorn app.web:app --host 127.0.0.1 --port 8443 --ssl-certfile <证书路径> --ssl-keyfile <私钥路径>
```

另外打开终端，在后端目录、同一虚拟环境及相同环境变量配置下，分别启动任务执行和任务调度：

```powershell
python -m scripts.run_worker
python -m scripts.run_supervisor
```

以上两条命令需要分别保持运行。不要把证书私钥、数据库密码、模型密钥提交到仓库。

## 源码范围

此仓库保留前端与整合版后端源码和模板资产，排除了依赖目录、构建输出、缓存、私有配置和运行数据。原有账号、简历记录和上传文件需要继续连接原数据库及对象存储，或单独迁移。
