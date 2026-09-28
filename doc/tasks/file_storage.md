# 任务清单:M6 文件与 CSV 读写(file_storage)

> 模块:M6 file_storage ｜ 来源:`doc/high-level-design.md` §3.2(M6)、§5.2、§5.4、§7.3 ｜ 最终落点:`backend/file_storage.py`(新建)
> 设计依据:经用户确认以 high-level-design.md 为准(detailed-design.md 不单独编写),§10 待办项已融入各任务实现要点。
> 约定:本模块是唯一写 `uploads/` 与 `result/` 的模块;CSV 编码 `utf-8-sig`;删除文件采用"忽略不存在"策略。

- [ ] 1. 实现上传副本保存 save_upload()
  - 描述:`save_upload(file_bytes, original_name) -> str`:命名 `原文件名_YYYYmmdd_HHMMSS.扩展名`(原名与扩展名分别取自 `Path(original_name).stem/suffix`),写入 `uploads/` 并返回文件名。
  - 涉及文件:`backend/file_storage.py`(新建)。
  - 前置依赖:M1 目录常量与 `ensure_dirs()`。
  - 验收/自测:同名文件连续两次保存不覆盖;返回文件名符合命名规则;文件可重新读取且内容一致。
- [ ] 2. 实现文件删除 delete_file()
  - 描述:`delete_file(stored_path)`:删除 `uploads/` 下对应文件;文件不存在时静默忽略不报错(设计 §5.4 联动删除使用)。
  - 涉及文件:`backend/file_storage.py`。
  - 前置依赖:任务 1。
  - 验收/自测:删除真实文件成功;对不存在的文件名调用不抛异常。
- [ ] 3. 实现批量结果 CSV 写入 write_batch_csv()
  - 描述:`write_batch_csv(results, created_at) -> str`:生成 `result/batch_result_YYYYmmdd_HHMMSS.csv`,列 `文件名/预测类别/置信度/备注`(M1 常量),编码 `utf-8-sig`;失败行预测类别/置信度填"-"、备注写原因;返回文件名。
  - 涉及文件:`backend/file_storage.py`。
  - 前置依赖:M1 列名常量与目录。
  - 验收/自测:写入含成功与失败行的样例数据,Excel 打开无乱码,列名与失败行备注与设计 §5.2 一致。
- [ ] 4. 实现历史导出 CSV 写入 write_history_csv()
  - 描述:`write_history_csv(records, created_at) -> str`:生成 `result/history_YYYYmmdd_HHMMSS.csv`,列 `编号/文件名/预测类别/置信度/识别时间`,编码 `utf-8-sig`;返回文件名。
  - 涉及文件:`backend/file_storage.py`。
  - 前置依赖:M1 列名常量与目录。
  - 验收/自测:写入样例记录后 Excel 打开无乱码,列名与设计 §5.2 一致。

## 本模块完成判定
4 项全部勾选;上传副本唯一命名、删除忽略不存在、两类 CSV 命名与编码符合设计。
