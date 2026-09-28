# 任务清单:F3 接口封装(api_client)

> 模块:F3 api/index.js ｜ 来源:`doc/high-level-design.md` §3.3(F3)、§4.3、§6 ｜ 最终落点:`frontend/src/api/index.js`(新建)
> 设计依据:经用户确认以 high-level-design.md 为准(detailed-design.md 不单独编写),§10 待办项已融入各任务实现要点。
> 约定:所有后端请求必须经本模块;统一错误提示使用 Element Plus 的 `ElMessage`;视图组件不得自行拼请求。

- [ ] 1. 创建 axios 实例
  - 描述:`axios.create({ baseURL: '/api', timeout: 120000 })`(批量任务轮询与单张识别均适用)。
  - 涉及文件:`frontend/src/api/index.js`(新建)。
  - 前置依赖:F1(vite 代理)。
  - 验收/自测:实例可发起 `/api/health` 请求并经代理到达后端。
- [ ] 2. 封装全部接口函数
  - 描述:实现 `classify(file)`(FormData + `file`)、`submitBatch(files)`(FormData + `files[]`)、`getJobStatus(jobId)`、`getHistory(page, pageSize)`、`deleteHistory(id)`、`clearHistory()`、`exportHistory()`(responseType blob)、`health()`;返回 Promise。
  - 涉及文件:`frontend/src/api/index.js`。
  - 前置依赖:任务 1;M8 接口约定。
  - 验收/自测:后端联调下每个函数返回预期数据;`exportHistory` 拿到 blob。
- [ ] 3. 实现统一错误拦截
  - 描述:响应拦截器:有响应且非 2xx → 取 `response.data.detail` 弹 `ElMessage.error`;无响应(网络错误/后端未启动)→ 弹"后端服务未启动,请先运行启动.bat";统一 reject 供调用方终止流程。
  - 涉及文件:`frontend/src/api/index.js`。
  - 前置依赖:任务 1。
  - 验收/自测:后端关闭时调用任意接口出现中文提示(TC-13);后端返回 400/404 时显示后端 detail 文案。
- [ ] 4. 实现 CSV 下载封装
  - 描述:`downloadCsv(blob, filename)`:创建临时 URL,`<a download>` 触发下载后释放;供 F5/F6 复用。
  - 涉及文件:`frontend/src/api/index.js`。
  - 前置依赖:任务 2。
  - 验收/自测:点击下载得到可打开的 CSV 文件。

## 本模块完成判定
4 项全部勾选;全部接口调用与错误提示收敛于本模块,视图组件不再出现 axios/ElMessage 的错误逻辑。
