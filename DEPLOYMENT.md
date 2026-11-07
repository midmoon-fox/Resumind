# GitHub Pages 与本机后端

前端网站：https://midmoon-fox.github.io/Resumind/

前端静态文件发布在 `gh-pages` 分支，`main` 保留源码。Pages 使用 Hash 路由，刷新子页面不会 404。

构建时在 `frontend` 目录设置：

```powershell
$env:VITE_BASE_PATH='/Resumind/'
$env:VITE_PAGES_DEPLOY='true'
$env:VITE_API_BASE_URL='https://你的后端公网域名'
npm run build
```

`VITE_API_BASE_URL` 是公开接口域名，不是密钥。未配置时，页面会明确提示后端未连接。

后端环境变量设置：

```text
CORS_ALLOWED_ORIGINS=https://midmoon-fox.github.io
```

跨域允许 Authorization、Content-Type 和 Idempotency-Key；继续使用 JWT，关闭 Cookie 凭据。API、预览和受保护的文件下载都经同一个后端入口。

本机仍需运行 Web、Worker、Supervisor、MySQL 和 Redis。公网隧道必须持续运行；临时域名改变后需要重新构建并发布前端。不要将 `.env.local`、证书私钥、数据库或用户文件提交到仓库。
