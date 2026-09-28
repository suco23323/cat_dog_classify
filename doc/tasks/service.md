# 任务清单:M7 业务编排(service)

> 模块:M7 service ｜ 来源:`doc/high-level-design.md` §3.2(M7)、§4.2、§4.4、§5.3、§1.4 ｜ 最终落点:`backend/service.py`(新建)
> 设计依据:经用户确认以 high-level-design.md 为准(detailed-design.md 不单独编写),§10 待办项已融入各任务实现要点。
> 约定:业务编排的唯一模块;批量任务为异步后台线程 + 内存 JobRegistry(状态仅内存、不支持取消,见设计 §1.4);每张结果实时写入历史。

- [ ] 1. 实现单张识别编排 classify_single()
  - 描述:`classify_single(file_bytes, filename) -> dict`:后缀/大小校验(失败抛中文异常)→ M3 预处理 → M4 推理 → M6 保存上传副本 → M5 插入历史 → 返回 dict(`id, filename, predict, predict_label, confidence, probs, image_url='/uploads/<stored>', created_at`),字段与 M9 `ClassifyResponse` 一致。
  - 涉及文件:`backend/service.py`(新建)。
  - 前置依赖:M3、M4、M5、M6、M1。
  - 验收/自测:`data/test` 猫图/狗图各一次,返回字段完整、历史新增两条、`uploads/` 出现两个文件;txt 文件触发中文异常且不落库。
- [ ] 2. 实现内存任务注册表 JobRegistry
  - 描述:`JobRegistry` 类:`create_job(total) -> job_id`(uuid4)、`update_progress(job_id, done, current_filename)`、`complete_job(job_id, summary, results, csv_filename)`、`fail_job(job_id, error)`、`get_job(job_id) -> dict | None`;内部 `dict` + `threading.Lock` 保护;创建任务时按 `created_at` 淘汰超过 `JOB_RETENTION`(20)个的最旧任务。
  - 涉及文件:`backend/service.py`。
  - 前置依赖:M1 常量。
  - 验收/自测:状态流转 `queued → running → succeeded/failed` 正确;`get_job` 不存在返回 `None`;连续创建 21 个任务后最旧的 1 个被清理。
- [ ] 3. 实现批量校验 validate_batch()
  - 描述:`validate_batch(files)`:总数超过 `MAX_BATCH_FILES` 抛出 `MSG_BATCH_LIMIT` 中文异常;返回通过数量校验的文件列表(单张坏文件不在此拦截,由任务线程逐张失败写备注)。
  - 涉及文件:`backend/service.py`。
  - 前置依赖:M1 上限常量。
  - 验收/自测:501 个文件触发中文异常;500 个通过。
- [ ] 4. 实现批量任务执行 run_batch_job()
  - 描述:`run_batch_job(job_id, files)`:在后台线程(daemon)逐张调用 `classify_single`,每张结束 `done+1` 并更新 `current_filename`;单张失败捕获后计入失败并写备注,不中断;全部结束后统计 `summary(total/success/failed/cat_count/dog_count)`、调用 M6 `write_batch_csv`,最后 `complete_job`。
  - 涉及文件:`backend/service.py`。
  - 前置依赖:任务 1、2、3;M6。
  - 验收/自测:3 张(含 1 个 txt)提交后任务最终 `status=='succeeded'`,`summary` 为 `{total:3, success:2, failed:1, ...}`;CSV 生成;坏文件进备注;成功的 2 张已写入历史。
- [ ] 5. 实现批量提交入口 submit_batch()
  - 描述:`submit_batch(files) -> (job_id, total)`:先 `validate_batch`,再 `create_job` 并启动任务线程,立即返回。
  - 涉及文件:`backend/service.py`。
  - 前置依赖:任务 2、3、4。
  - 验收/自测:调用后立即返回 `job_id`;任务在后台推进,不阻塞调用方。
- [ ] 6. 实现任务状态查询 get_job_status()
  - 描述:`get_job_status(job_id) -> dict | None`:返回状态字典,含 `status/total/done/percent(round(done/total*100,1))/current_filename`;终态时附加 `summary/results/csv_url`(成功)或 `error`(失败);不存在返回 `None`(供 M8 转 404)。
  - 涉及文件:`backend/service.py`。
  - 前置依赖:任务 2、4。
  - 验收/自测:running/succeeded/failed 三种状态字段与设计 §4.4 示例一致;不存在的 job_id 返回 `None`。
- [ ] 7. 实现历史导出编排 export_history()
  - 描述:`export_history() -> str`:M5 全量查询;空历史抛出 `MSG_NO_HISTORY` 中文异常;否则调用 M6 `write_history_csv` 并返回 CSV 文件名。
  - 涉及文件:`backend/service.py`。
  - 前置依赖:任务 1;M5、M6。
  - 验收/自测:有记录时生成文件且内容正确;空表时抛出中文提示。

## 本模块完成判定
7 项全部勾选;单张全链路正确落库,批量异步状态机与进度符合设计 §4.4,任务仅内存保存(重启失效为预期行为,见设计 §1.4)。
