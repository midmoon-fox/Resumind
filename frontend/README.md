# 简立得前端

Vue 3 + TypeScript + Vite。主要业务页面已改为调用后端接口：资料和 JD、智能追问、简历生成编辑、版本、后端导出、面试准备、海外岗位推荐。

已接入真实 JWT 注册登录及退出；按用户选择将 Token 保存到 localStorage，刷新和重新打开浏览器后恢复登录，过期后重新登录。真实服务已验证简历保存及 HTML/Word/PDF 导出；真实 JD 分析与 AI 生成后自动进入编辑页也已通过；OCR、面试等其余模型链路及外部岗位源仍需单独验收。

```powershell
pnpm dev
pnpm typecheck
pnpm test
pnpm build
```

开发地址 `http://127.0.0.1:5173`，无需安装或信任本地证书。业务请求经 Vite 代理至本机 HTTPS 后端；前端不读取后端证书文件。模型密钥只允许保存在后端。

对接说明、原始源码备份及浏览器验证记录位于相邻目录 `../frontend-support`，详见其中的 `前端业务接口对接说明.md`。
