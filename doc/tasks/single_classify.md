# 任务清单:F4 单张识别视图(single_classify)

> 模块:F4 SingleClassify.vue ｜ 来源:`doc/high-level-design.md` §3.3(F4)、§4.2(1) ｜ 最终落点:`frontend/src/views/SingleClassify.vue`(新建)
> 设计依据:经用户确认以 high-level-design.md 为准(detailed-design.md 不单独编写),§10 待办项已融入各任务实现要点。
> 约定:组件内部状态即可,不引入 Pinia;结果区为"类别 + 置信度 + 猫/狗概率对比进度条"。

- [ ] 1. 实现上传与预览区
  - 描述:`el-upload`(drag、`auto-upload=false`、accept 图片类型)+ 已选图片 `el-image` 预览;只保留最近一次选择的单个文件。
  - 涉及文件:`frontend/src/views/SingleClassify.vue`(新建)。
  - 前置依赖:F3、F7。
  - 验收/自测:选择图片后出现预览;再次选择替换旧图。
- [ ] 2. 实现前端校验
  - 描述:点击识别时先校验:未选图 → 提示"请先上传图片";格式/大小不符 → 对应中文提示(F7 工具),均不发请求。
  - 涉及文件:`frontend/src/views/SingleClassify.vue`。
  - 前置依赖:任务 1;F7。
  - 验收/自测:TC-04 未上传即识别提示正确;选择 txt 被拦截。
- [ ] 3. 实现识别调用与加载态
  - 描述:"开始识别"按钮调用 F3 `classify(file)`,期间按钮 loading 且防重复点击;失败由 F3 统一提示。
  - 涉及文件:`frontend/src/views/SingleClassify.vue`。
  - 前置依赖:任务 2;F3。
  - 验收/自测:识别期间按钮禁用;返回后恢复。
- [ ] 4. 实现结果区渲染
  - 描述:展示 `predict_label` 大字、置信度百分比;两条 `el-progress` 分别渲染"猫/狗"概率(高者用 success 颜色突出,低者用 info);连续识别时结果更新且互不干扰。
  - 涉及文件:`frontend/src/views/SingleClassify.vue`。
  - 前置依赖:任务 3;F7 `format_percent`。
  - 验收/自测:猫图/狗图各一次,进度条比例与后端 `probs` 一致且高概率侧突出(TC-01/02);连续 5 次识别结果互不干扰(TC-05)。

## 本模块完成判定
4 项全部勾选;TC-01～TC-05 前端行为全部符合预期。
