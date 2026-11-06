# 前端服务层

业务页面使用 `client.ts`、`tasks.ts` 调用真实接口。`mapping.ts` 转换正文、富文本和资料，`schema.ts` 根据后端 2.0.0 OpenAPI 生成。

JWT 统一通过 Bearer 请求头发送，Token 和 expiresAt 按用户选择保存在 localStorage；不保存密码。不再使用 Cookie 或 CSRF。接口、上传、预览、头像、下载均共用认证请求函数。

完整范围、实际验证与限制见工作区 `前端/frontend-support/前端业务接口对接说明.md`。
