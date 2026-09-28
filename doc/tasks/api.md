# 任务清单:M8 API 路由层(api)

> 模块:M8 api ｜ 来源:`doc/high-level-design.md` §3.2(M8)、§4.3、§4.4、§6、§7.4 ｜ 最终落点:`backend/main.py`(新建)
> 设计依据:经用户确认以 high-level-design.md 为准(detailed-design.md 不单独编写),§10 待办项已融入各任务实现要点。
> 约定:只做路由、协议转换与统一错误响应,业务全部在 M7;失败统一返回 `{"detail": 中文提示}`;接口用普通 `def`(FastAPI 线程池执行阻塞推理)。

- [ ] 1. 创建应用骨架与静态挂载
  - 描述:创建 `app = FastAPI(title="猫狗分类识别后端")`;启动时调用 M1 `ensure_dirs()`;挂载 `StaticFiles`:`/uploads` → `UPLOAD_DIR`、`/result` → `RESULT_DIR`。
  - 涉及文件:`backend/main.py`(新建)。
  - 前置依赖:M1。
  - 验收/自测:应用可被 uvicorn 启动;`uploads/`、`result/` 目录自动创建;向目录放测试文件后可经静态地址访问。
- [ ] 2. 启动加载模型与健康检查
  - 描述:`@app.on_event('startup')` 调用 `get_model()`(日志出现"模型加载完成"一次);新增 `GET /api/health` 返回 `{"status": "ok"}`。
  - 涉及文件:`backend/main.py`。
  - 前置依赖:M2。
  - 验收/自测:启动日志含"模型加载完成";`GET /api/health` 返回 200(TC-12/13 依赖)。
- [ ] 3. 实现 POST /api/classify
  - 描述:`file: UploadFile` 读取字节后调用 M7 `classify_single`;成功返回 M9 `ClassifyResponse`;校验失败映射 400、意外异常映射 500,`detail` 均为中文。
  - 涉及文件:`backend/main.py`。
  - 前置依赖:M7、M9。
  - 验收/自测:TestClient/curl 上传猫图,响应结构与设计 §4.4 一致;上传 txt 返回 400 中文提示(TC-01/02/03 后端部分)。
- [ ] 4. 实现 POST /api/batch
  - 描述:`files: List[UploadFile]` 调 M7 `submit_batch`,返回 M9 `BatchSubmitResponse`(`job_id, total`);超上限返回 400 中文提示。
  - 涉及文件:`backend/main.py`。
  - 前置依赖:M7、M9。
  - 验收/自测:提交 3 张返回 `job_id/total=3`;501 张返回 400(TC-06 后端部分)。
- [ ] 5. 实现 GET /api/batch/status/{job_id}
  - 描述:调 M7 `get_job_status`;`None` 时返回 404 `MSG_JOB_NOT_FOUND`;否则返回 M9 `JobStatusResponse`。
  - 涉及文件:`backend/main.py`。
  - 前置依赖:M7、M9。
  - 验收/自测:任务推进中/完成后字段与设计 §4.4 一致;不存在的 job_id 返回 404 中文提示(TC-15/17 后端部分)。
- [ ] 6. 实现 GET /api/history
  - 描述:`page: int = 1`、`page_size: int = 10` 调 M5 `query_page`,返回 M9 `HistoryPageResponse`。
  - 涉及文件:`backend/main.py`。
  - 前置依赖:M5、M9。
  - 验收/自测:分页参数生效,倒序返回,`image_url` 可访问(TC-09 后端部分)。
- [ ] 7. 实现 DELETE /api/history/{id} 与 DELETE /api/history
  - 描述:删除单条:取 `stored_path` → M6 `delete_file` → M5 `delete_record`,不存在返回 404 中文;清空:M5 `clear_all` → 逐个 M6 `delete_file`,返回 `{"ok": true, "deleted": n}`。
  - 涉及文件:`backend/main.py`。
  - 前置依赖:M5、M6。
  - 验收/自测:删除后数据库记录与 `uploads/` 图片文件同步消失(设计 §5.4 联动);重复删除返回 404(TC-10 后端部分)。
- [ ] 8. 实现 GET /api/history/export
  - 描述:调 M7 `export_history`,返回 `FileResponse`(文件在 `result/`,media_type `text/csv`,filename 为 `history_*.csv`);空历史返回 400 中文提示。
  - 涉及文件:`backend/main.py`。
  - 前置依赖:M7。
  - 验收/自测:下载的 CSV 可被 Excel 打开无乱码;空历史返回中文提示(TC-11 后端部分)。

## 本模块完成判定
8 项全部勾选;`/docs` 可见全部接口;接口行为与设计 §4.3/§4.4 一致,错误均为中文 `detail`。
