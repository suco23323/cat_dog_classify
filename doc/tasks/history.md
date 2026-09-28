# 任务清单:F6 历史记录视图(history)

> 模块:F6 History.vue ｜ 来源:`doc/high-level-design.md` §3.3(F6)、§4.2(3)、§5.4 ｜ 最终落点:`frontend/src/views/History.vue`(新建)
> 设计依据:经用户确认以 high-level-design.md 为准(detailed-design.md 不单独编写),§10 待办项已融入各任务实现要点。
> 约定:删除历史会连带删除后端 `uploads/` 图片文件(设计 §5.4),前端只需调用接口;缩略图直接用原图缩放显示。

- [ ] 1. 实现分页列表
  - 描述:`el-table` 列:缩略图(`el-image` 加载 `image_url`,原图 + 固定小尺寸)、文件名、预测类别、置信度(百分比)、识别时间;`el-pagination` 默认每页 10 条,联动刷新。
  - 涉及文件:`frontend/src/views/History.vue`(新建)。
  - 前置依赖:F3。
  - 验收/自测:记录倒序展示、分页正确、缩略图可显示(TC-09)。
- [ ] 2. 实现删除单条
  - 描述:`el-popconfirm` 二次确认后调 F3 `deleteHistory(id)`,成功后刷新当前页(删空当前页时回退上一页)。
  - 涉及文件:`frontend/src/views/History.vue`。
  - 前置依赖:任务 1。
  - 验收/自测:删除后该条消失且后端 `uploads/` 文件同步删除(TC-10)。
- [ ] 3. 实现清空全部
  - 描述:`el-popconfirm` 确认后调 F3 `clearHistory()`,成功后列表为空。
  - 涉及文件:`frontend/src/views/History.vue`。
  - 前置依赖:任务 1。
  - 验收/自测:清空后列表与数据库均为空,`uploads/` 文件同步删除(TC-10)。
- [ ] 4. 实现导出 CSV
  - 描述:"导出历史"按钮调 F3 `exportHistory()` 并 `downloadCsv` 下载;空历史时显示后端返回的中文提示。
  - 涉及文件:`frontend/src/views/History.vue`。
  - 前置依赖:任务 1;F3。
  - 验收/自测:下载的 CSV 可打开且无乱码(TC-11)。
- [ ] 5. 实现空状态与页签刷新
  - 描述:无数据时显示 `el-empty`;每次进入本页签(或由 F2 通知)重新加载第一页。
  - 涉及文件:`frontend/src/views/History.vue`。
  - 前置依赖:任务 1。
  - 验收/自测:识别新图片后切到历史页签能看到最新记录。

## 本模块完成判定
5 项全部勾选;TC-09/10/11 前端行为全部符合预期。
