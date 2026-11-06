# JWT 认证迁移（2.0.0）

本次只修改后端与后端测试、文档。业务资源字段和权限模型沿用原实现；认证方式为不兼容变更，整合 API 的版本与 `X-Contract-Version` 更新为 `2.0.0`。

## 请求方式

无需 Cookie、Origin、X-CSRF-Token，也不再提供 `GET /api/auth/csrf`。

1. `POST /api/auth/registrations`：JSON 包含 email、password、username；password 为 5～128 位（允许纯数字，例如 12345）；携带 Idempotency-Key，成功为 201。
2. `POST /api/auth/sessions`：JSON 仅包含 email、password；携带新的 Idempotency-Key，成功为 201。
3. 登录响应的 data 包含 user、expiresAt、accessToken、tokenType（固定为 Bearer）。
4. 其他业务接口携带 `Authorization: Bearer <accessToken>`。写请求沿用 Idempotency-Key；退出和导出预检除外。
5. `DELETE /api/auth/session` 撤销当前 JWT，成功为 204。即使复制了旧 JWT，退出后也不能继续使用。

```http
Authorization: Bearer eyJ...
Idempotency-Key: a-new-uuid-per-operation
Content-Type: application/json
```

Apifox 可以关闭 Cookie 管理。注册、登录设置 Auth 为无需认证；其他接口选择 Bearer Token，填写登录响应 `data.accessToken`，或使用环境变量 `{{accessToken}}`。新的 OpenAPI 位于 `../backend-support/docs/api-testing/openapi.apifox.json`，导入后移除旧的全局 Cookie / CSRF 前置脚本。

## 生命周期与存储

- JWT 使用 PyJWT、固定 HS256、从 APP_SECRET 派生的独立签名密钥；校验签名、issuer、audience、token_type 和全部必需声明。
- 有效期沿用原登录会话的 7 天，以 expiresAt 为准；未添加刷新令牌接口，到期重新登录。
- 保留 sessions 表作为撤销与禁用校验，JWT 不是完全无状态。数据库不保存可直接使用的完整 JWT。
- 注册和登录仍有限流和幂等保护。匿名幂等作用域改为规范化邮箱的服务端 HMAC；登录重试也必须重新校验密码，不依赖匿名 Cookie。
- 同一登录意图重试返回同一个有效 JWT；已撤销或过期的意图返回 409 SESSION_REAUTH_REQUIRED，需更换请求编号重新登录。
- APP_SECRET 必须在各服务间一致。更换 APP_SECRET 或 APP_ORIGIN 会使现有 JWT 失效。
- 无需新建数据库表或执行结构迁移；保留原 sessions.csrf_hash 非空列以兼容已有数据库，写入占位值，认证不再读取它。旧 Cookie 与旧会话不会被接纳为 JWT。
- HTTPS 继续使用。令牌仅接受 Authorization 请求头，不从 Cookie 或 URL 查询参数读取。

## 对前端和业务的影响

前端没有在这个对话中修改。当前前端依赖 CSRF 引导和 Cookie，在另行适配前不能直接完成登录及受保护接口调用。

- 删除初始化、注册和登录前的 CSRF 引导。
- 保存登录返回的 accessToken，在统一 API 客户端附加 Authorization；退出成功或 401 后清除令牌。令牌存储方式由前端单独设计。
- 文件上传、任务轮询、简历预览、头像读取、导出下载也都需要 Bearer；签名下载 URL 本身不替代用户认证。
- 浏览器直接打开 URL、iframe src 或原生下载链接不能自行附加 Authorization。需要通过带头的 fetch 获取 HTML/Blob，再展示或下载。
- 仍应检查前端部署的 HTTPS、同源代理或精确 CORS 配置；移除 CSRF 并不自动开放跨域访问。

账户、工作区、材料、JD、经历、简历、版本和任务的归属校验保持原业务模型。原有业务数据无需转换。具体测试结果和未通过的历史测试见后端支持目录中的 JWT 验证报告。
