"""M9 响应模型(Pydantic v2)。

字段与序列化结果以 `doc/high-level-design.md` §4.3/§4.4 与
`doc/proposal.md` §6 的示例 JSON 为准,供 M8 直接作为 `response_model` 使用。
本模块仅定义 Pydantic 模型,不包含任何业务逻辑。
"""
from typing import List, Optional

from pydantic import BaseModel


class ClassifyResponse(BaseModel):
    """单张识别响应(`POST /api/classify`),对应 proposal §6 示例。"""

    id: int
    filename: str
    predict: str
    predict_label: str
    confidence: float
    probs: dict
    image_url: str
    created_at: str


class BatchSubmitResponse(BaseModel):
    """批量识别提交响应(`POST /api/batch`),对应设计 §4.3。"""

    job_id: str
    total: int


class JobStatusResponse(BaseModel):
    """批量任务状态响应(`GET /api/batch/status/{job_id}`),对应设计 §4.4。

    可选字段在非终态(running/queued)时为 `null`;succeeded 时携带
    `summary`/`results`/`csv_url`,failed 时携带 `error`。
    """

    job_id: str
    status: str
    total: int
    done: int
    percent: float
    current_filename: Optional[str] = None
    summary: Optional[dict] = None
    results: Optional[list] = None
    csv_url: Optional[str] = None
    error: Optional[str] = None


class HistoryItem(BaseModel):
    """历史记录单条(proposal §6 历史响应 `items` 元素)。"""

    id: int
    filename: str
    predict_label: str
    confidence: float
    probs: dict
    image_url: str
    created_at: str


class HistoryPageResponse(BaseModel):
    """历史分页响应(`GET /api/history`),对应 proposal §6 示例。"""

    total: int
    page: int
    page_size: int
    items: List[HistoryItem]
