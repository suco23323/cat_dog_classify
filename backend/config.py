"""M1 配置模块:路径、设备、类别映射、预处理、批量上限与中文提示文案等常量。

本模块只提供配置常量与只读小工具(目录创建、设备选择),不涉及任何推理与 IO 业务;
供 M2–M8 统一引用,避免各处硬编码。类别映射与预处理参数同 `model_train.py`,
中文提示文案与 `doc/high-level-design.md` §6 异常设计表一致。
"""
from pathlib import Path
from typing import Dict, List, Tuple

import torch
from torchvision import transforms

# ---- 路径与目录常量 ----
BACKEND_DIR: Path = Path(__file__).resolve().parent
PROJECT_ROOT: Path = BACKEND_DIR.parent
WEIGHTS_PATH: Path = PROJECT_ROOT / "best_model_opt20.pth"
UPLOAD_DIR: Path = BACKEND_DIR / "uploads"
RESULT_DIR: Path = BACKEND_DIR / "result"
DB_PATH: Path = BACKEND_DIR / "app.db"


def ensure_dirs() -> None:
    """创建 `uploads/` 与 `result/` 目录(供 M8 启动时调用)。"""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)


def get_device() -> torch.device:
    """返回推理设备:有 CUDA 用 GPU,否则自动回退 CPU(设计 §2 约束 6)。"""
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ---- 类别映射与预处理(与 model_train.py 完全一致) ----
# ImageFolder 目录字母序:cat 在前(索引 0 → 猫)、dog 在后(索引 1 → 狗)
CLASS_INDEX: Dict[int, Tuple[str, str]] = {0: ("cat", "猫"), 1: ("dog", "狗")}

PREPROCESS_TRANSFORM: transforms.Compose = transforms.Compose(
    [
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.4861, 0.453, 0.4153], std=[0.2628, 0.2555, 0.2583]),
    ]
)

# ---- 业务常量与批量上限 ----
SUPPORTED_SUFFIXES: Tuple[str, ...] = (".jpg", ".jpeg", ".png", ".bmp")
MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024
MAX_BATCH_FILES: int = 500
PAGE_SIZE_DEFAULT: int = 10
JOB_RETENTION: int = 20
BATCH_COLUMNS: List[str] = ["文件名", "预测类别", "置信度", "备注"]
HISTORY_COLUMNS: List[str] = ["编号", "文件名", "预测类别", "置信度", "识别时间"]

# ---- 中文提示文案(doc/high-level-design.md §6 异常设计表) ----
MSG_NO_IMAGE: str = "请先上传图片"
MSG_INVALID_FORMAT_SIZE: str = "仅支持 jpg/jpeg/png/bmp 图片,单张不超过 10MB"
MSG_BATCH_TOO_MANY: str = "单次最多识别 500 张图片"
MSG_BACKEND_NOT_READY: str = "后端服务未启动,请先运行启动.bat"
MSG_WEIGHTS_MISSING: str = "未找到或无法加载权重文件 best_model_opt20.pth"
MSG_IMAGE_UNREADABLE: str = "无法读取该图片,请上传 jpg/png/bmp 等图片文件"
MSG_RECOGNIZE_FAILED: str = "识别失败,请重试"
MSG_JOB_NOT_FOUND: str = "任务不存在或已失效(后端可能已重启)"
MSG_HISTORY_EMPTY_EXPORT: str = "暂无历史记录可导出"
MSG_CSV_WRITE_FAILED: str = "结果 CSV 写入失败,请重试"
MSG_PORT_OCCUPIED: str = "端口 8000/5173 已被占用"
