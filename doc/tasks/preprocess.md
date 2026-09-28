# 任务清单:M3 图像预处理(preprocess)

> 模块:M3 preprocess ｜ 来源:`doc/high-level-design.md` §3.2(M3)、§4.2、§6 ｜ 最终落点:`backend/preprocess.py`(新建)
> 设计依据:经用户确认以 high-level-design.md 为准(detailed-design.md 不单独编写),§10 待办项已融入各任务实现要点。
> 约定:预处理参数必须与 `model_train.py` 完全一致;上传图片统一转 RGB;校验失败返回中文提示供 M7 使用。

- [ ] 1. 实现图片打开与解码校验 load_rgb_image()
  - 描述:`load_rgb_image(file_bytes)`:用 PIL 打开并校验可解码,统一转 RGB;失败抛出含 `MSG_BAD_IMAGE` 中文文案的 `ValueError`。
  - 涉及文件:`backend/preprocess.py`(新建)。
  - 前置依赖:M1 文案常量。
  - 验收/自测:jpg/png/bmp 可正常打开且 mode 为 RGB(含 RGBA 图转 RGB 后仍可识别);txt 或损坏文件触发中文错误。
- [ ] 2. 实现预处理与升维 preprocess_to_tensor()
  - 描述:`preprocess_to_tensor(img)`:`PREPROCESS_TRANSFORM(img)` 后 `unsqueeze(0)`,返回 `(1,3,224,224)` 的 float32 tensor。
  - 涉及文件:`backend/preprocess.py`。
  - 前置依赖:M1 transform 常量。
  - 验收/自测:对 `data/test` 一张图(或任意本地图片)得到 shape `(1,3,224,224)`、dtype float32。
- [ ] 3. 实现文件合法性校验辅助函数
  - 描述:`is_supported_suffix(filename) -> bool` 与 `is_within_size_limit(size_bytes) -> bool`(阈值取 M1 常量),供 M7 单张/批量校验使用。
  - 涉及文件:`backend/preprocess.py`。
  - 前置依赖:M1 业务常量。
  - 验收/自测:`.jpg/.jpeg/.png/.bmp` 大小写均通过,`.txt/.gif` 拒绝;`10MB` 边界值行为正确(≤ 通过,> 拒绝)。

## 本模块完成判定
3 项全部勾选;预处理链路输出与训练脚本一致,校验失败给出中文提示。
