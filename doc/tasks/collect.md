# 任务清单:F7 前端工具函数(collect)

> 模块:F7 utils/collect.js ｜ 来源:`doc/high-level-design.md` §3.3(F7)、§4.2(2)、§6 ｜ 最终落点:`frontend/src/utils/collect.js`(新建)
> 设计依据:经用户确认以 high-level-design.md 为准(detailed-design.md 不单独编写),§10 待办项已融入各任务实现要点。
> 约定:纯工具函数,不涉及组件与请求;文件夹收集依赖 Chromium 内核(Edge/Chrome),不支持时提示降级为多选文件。

- [ ] 1. 实现后缀校验 is_supported()
  - 描述:`is_supported(filename) -> boolean`:小写化后判断扩展名属于 `.jpg/.jpeg/.png/.bmp`。
  - 涉及文件:`frontend/src/utils/collect.js`(新建)。
  - 前置依赖:无。
  - 验收/自测:大小写混合的 `A.JPG`、`b.Png` 均返回 true;`.txt/.gif` 返回 false。
- [ ] 2. 实现大小校验 check_size()
  - 描述:`check_size(file) -> boolean`:文件大小 ≤ 10MB(与后端 M1 常量一致)。
  - 涉及文件:`frontend/src/utils/collect.js`。
  - 前置依赖:无。
  - 验收/自测:10MB 边界内通过、超出拒绝。
- [ ] 3. 实现多选文件归一化 collect_files()
  - 描述:`collect_files(fileList) -> File[]`:从 FileList 中过滤出支持的图片文件,返回数组(不支持的项由调用方提示)。
  - 涉及文件:`frontend/src/utils/collect.js`。
  - 前置依赖:任务 1。
  - 验收/自测:混入 txt 的 FileList 只返回图片文件。
- [ ] 4. 实现文件夹收集 collect_folder_files()
  - 描述:`collect_folder_files(inputElement) -> File[]`:读取 `webkitdirectory` 输入的所有文件(`webkitRelativePath` 已含递归结果,实现要点:直接遍历 `input.files` 过滤即可),仅保留支持的图片;浏览器不支持时返回空数组并提示"当前浏览器不支持选择文件夹,请使用多选文件"。
  - 涉及文件:`frontend/src/utils/collect.js`。
  - 前置依赖:任务 1、3。
  - 验收/自测:Edge 中选择含子文件夹的目录,返回全部图片;Firefox 中返回空并给出提示(TC-07)。
- [ ] 5. 实现百分比格式化 format_percent()
  - 描述:`format_percent(p) -> string`:0~1 概率转百分比并保留 1 位小数,如 `0.924 → '92.4%'`。
  - 涉及文件:`frontend/src/utils/collect.js`。
  - 前置依赖:无。
  - 验收/自测:`format_percent(0.924) === '92.4%'`、`format_percent(0.5) === '50.0%'`。

## 本模块完成判定
5 项全部勾选;F4/F5 的校验与收集逻辑全部复用本模块。
