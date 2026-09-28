# 任务清单:M4 推理预测(predict)

> 模块:M4 predict ｜ 来源:`doc/high-level-design.md` §3.2(M4)、§4.2、§4.4 ｜ 最终落点:`backend/predict.py`(新建)
> 设计依据:经用户确认以 high-level-design.md 为准(detailed-design.md 不单独编写),§10 待办项已融入各任务实现要点。
> 约定:只做推理与结果格式化,不涉及文件读写与数据库;推理经全局推理锁串行化。

- [ ] 1. 实现推理 predict_tensor()
  - 描述:`predict_tensor(tensor)`:在 `with INFERENCE_LOCK:` 与 `torch.no_grad():` 下前向得到 2 类 logits,`softmax(logits, dim=1)` 转为概率。
  - 涉及文件:`backend/predict.py`(新建)。
  - 前置依赖:M2 推理锁与模型、M3 预处理。
  - 验收/自测:输入 `(1,3,224,224)` tensor,输出 shape `(1,2)` 且两值之和约等于 1、均在 0~1。
- [ ] 2. 实现结果格式化 format_result()
  - 描述:`format_result(probs)`:返回 dict:`probs={'cat': round(p0,4), 'dog': round(p1,4)}`、取 argmax 得 `predict`('cat'/'dog')与 `predict_label`('猫'/'狗',经 M1 映射)、`confidence=round(max,4)`。字段与 M9 `ClassifyResponse` 一致。
  - 涉及文件:`backend/predict.py`。
  - 前置依赖:任务 1;M1 类别映射。
  - 验收/自测:对 `data/test` 猫图/狗图各一次:猫图 `predict=='cat'`、`predict_label=='猫'` 且 `confidence>0.5`;字段名与设计 §4.4 JSON 完全一致。
- [ ] 3. 推理异常兜底
  - 描述:捕获推理过程中的异常,抛出含 `MSG_FAIL`("识别失败,请重试")中文文案的 `RuntimeError`,由 M7 统一处理。
  - 涉及文件:`backend/predict.py`。
  - 前置依赖:任务 1;M1 文案常量。
  - 验收/自测:临时构造异常场景(如传入错误形状)触发中文文案,程序不崩溃。

## 本模块完成判定
3 项全部勾选;推理输出与格式化结果符合设计 §4.4 示例结构。
