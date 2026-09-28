# 任务清单:F5 批量识别视图(batch_classify)

> 模块:F5 BatchClassify.vue ｜ 来源:`doc/high-level-design.md` §3.3(F5)、§4.2(2)、§1.4 ｜ 最终落点:`frontend/src/views/BatchClassify.vue`(新建)
> 设计依据:经用户确认以 high-level-design.md 为准(detailed-design.md 不单独编写),§10 待办项已融入各任务实现要点。
> 约定:异步任务 + 实时进度条(每 1 秒轮询);任务状态仅内存,页面刷新后进度不可见为预期行为(设计 §1.4),需给出降级提示。

- [ ] 1. 实现双入口选择
  - 描述:①`el-upload multiple` 多选图片;②"选择文件夹"按钮触发隐藏的 `<input type="file" webkitdirectory>` 并复用 F7 `collect_folder_files` 收集;显示已选数量与文件列表;不支持的浏览器给出降级提示(仅多选可用)。
  - 涉及文件:`frontend/src/views/BatchClassify.vue`(新建)。
  - 前置依赖:F7。
  - 验收/自测:多选与文件夹两种方式均能收集图片;Firefox 下文件夹入口给出提示(TC-06/07 前端部分)。
- [ ] 2. 实现提交与结果获取
  - 描述:提交调用 F3 `submitBatch(files)` 得到 `{job_id, total}`;超上限/错误由 F3 统一提示;提交成功后开始轮询。
  - 涉及文件:`frontend/src/views/BatchClassify.vue`。
  - 前置依赖:任务 1;F3。
  - 验收/自测:提交 3 张后拿到 job_id 并进入轮询;501 张被提示。
- [ ] 3. 实现进度轮询与进度条
  - 描述:`setInterval` 每 1 秒调用 F3 `getJobStatus(jobId)`,`el-progress` 显示 `percent` 与"当前文件名";终态(成功/失败)即停止轮询;组件卸载(`onBeforeUnmount`)清理定时器;进行中禁止重复提交。
  - 涉及文件:`frontend/src/views/BatchClassify.vue`。
  - 前置依赖:任务 2;F3。
  - 验收/自测:进度条随 `done` 实时推进且显示当前文件名;离开页签后无残留请求(TC-15)。
- [ ] 4. 实现终态结果展示
  - 描述:`succeeded` → `el-table` 渲染 `results`(文件名/预测类别/置信度/备注)、汇总区(总数/成功/失败/猫/狗,取 `summary`)、CSV 下载按钮(取 `csv_url`,经 F3 下载封装或直接打开 `/result` 地址);`failed` → 展示 `error` 中文提示。
  - 涉及文件:`frontend/src/views/BatchClassify.vue`。
  - 前置依赖:任务 3;F3。
  - 验收/自测:含坏文件的批次,表格备注正确、汇总数字正确、CSV 可下载打开(TC-06/07/08)。
- [ ] 5. 实现降级处理
  - 描述:轮询遇到 404(任务不存在/已失效)时停止并提示"任务状态已失效,已完成图片结果可在历史记录查看";页面刷新后若本地无 job_id 同样给出该提示(TC-16/17)。
  - 涉及文件:`frontend/src/views/BatchClassify.vue`。
  - 前置依赖:任务 3。
  - 验收/自测:批量进行中刷新页面出现降级提示;后端重启后查询旧任务出现同一提示,不报未处理异常。

## 本模块完成判定
5 项全部勾选;TC-06/07/08 与设计补充用例 TC-15/16/17 前端行为全部符合预期。
