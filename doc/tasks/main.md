# 任务清单:F1 前端入口与工程配置(main)

> 模块:F1 main.js ｜ 来源:`doc/high-level-design.md` §3.3(F1)、§7.1、§7.4 ｜ 最终落点:`frontend/vite.config.js`、`frontend/index.html`、`frontend/src/main.js`
> 设计依据:经用户确认以 high-level-design.md 为准(detailed-design.md 不单独编写),§10 待办项已融入各任务实现要点。
> 约定:前端脚手架创建见 S1 任务 3;本模块负责入口与工程配置,不实现业务界面。

- [ ] 1. 配置 vite.config.js(端口 5173 与 /api 代理)
  - 描述:`server.port = 5173`;`server.proxy = { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true } }`;静态资源(`/uploads`、`/result`)经同一代理规则转发或按设计 §7.4 约定处理。
  - 涉及文件:`frontend/vite.config.js`。
  - 前置依赖:S1 任务 3(脚手架)。
  - 验收/自测:`npm run dev` 起在 5173;浏览器 fetch `/api/health` 能返回 200(需后端已启动)。
- [ ] 2. 设置 index.html
  - 描述:`<html lang="zh-CN">`、`<title>猫狗分类识别</title>`。
  - 涉及文件:`frontend/index.html`。
  - 前置依赖:S1 任务 3。
  - 验收/自测:页面标题显示"猫狗分类识别",无乱码。
- [ ] 3. 实现 main.js 应用入口
  - 描述:`createApp(App).use(ElementPlus).mount('#app')`;引入 element-plus 及样式,配置中文 locale。
  - 涉及文件:`frontend/src/main.js`。
  - 前置依赖:S1 任务 3;F2 至少存在占位 `App.vue`。
  - 验收/自测:页面打开无控制台报错;Element Plus 组件可正常渲染。

## 本模块完成判定
3 项全部勾选;前端工程可在 5173 启动并代理到后端。
