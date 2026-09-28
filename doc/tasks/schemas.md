# 任务清单:M9 响应模型(schemas)

> 模块:M9 schemas ｜ 来源:`doc/high-level-design.md` §3.2(M9)、§4.3、§4.4 ｜ 最终落点:`backend/schemas.py`(新建)
> 设计依据:经用户确认以 high-level-design.md 为准(detailed-design.md 不单独编写),§10 待办项已融入各任务实现要点。
> 约定:仅定义 Pydantic 模型,不包含任何业务逻辑;字段必须与设计 §4.3/§4.4 及 proposal §6 示例一致。

- [ ] 1. 定义 ClassifyResponse
  - 描述:`ClassifyResponse(BaseModel)` 字段:`id: int`、`filename: str`、`predict: str`、`predict_label: str`、`confidence: float`、`probs: dict`、`image_url: str`、`created_at: str`。
  - 涉及文件:`backend/schemas.py`(新建)。
  - 前置依赖:无。
  - 验收/自测:用设计 §4.4 示例 JSON 构造实例并序列化,字段名与类型完全一致。
- [ ] 2. 定义 BatchSubmitResponse
  - 描述:`BatchSubmitResponse(BaseModel)` 字段:`job_id: str`、`total: int`。
  - 涉及文件:`backend/schemas.py`。
  - 前置依赖:无。
  - 验收/自测:构造 `{"job_id": "...", "total": 100}` 序列化一致。
- [ ] 3. 定义 JobStatusResponse
  - 描述:`JobStatusResponse(BaseModel)` 字段:`job_id: str`、`status: str`、`total: int`、`done: int`、`percent: float`、`current_filename: Optional[str]`、`summary: Optional[dict]`、`results: Optional[list]`、`csv_url: Optional[str]`、`error: Optional[str]`。
  - 涉及文件:`backend/schemas.py`。
  - 前置依赖:无。
  - 验收/自测:running/succeeded/failed 三种示例均可构造且序列化与设计 §4.4 一致(可选字段在非终态时为 `null`)。
- [ ] 4. 定义 HistoryItem 与 HistoryPageResponse
  - 描述:`HistoryItem` 字段:`id, filename, predict_label, confidence, probs, image_url, created_at`;`HistoryPageResponse` 字段:`total: int`、`page: int`、`page_size: int`、`items: List[HistoryItem]`。
  - 涉及文件:`backend/schemas.py`。
  - 前置依赖:无。
  - 验收/自测:用 proposal §6 历史响应示例构造并序列化,字段一致。

## 本模块完成判定
4 项全部勾选;四个模型与设计 §4.3/§4.4 示例一一对应,供 M8 直接作为 `response_model` 使用。
