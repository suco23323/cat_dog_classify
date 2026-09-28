"""M2 模型加载模块:构建 ResNet、加载权重、单例常驻与全局推理锁。

职责(见 `doc/high-level-design.md` §3.2/§4.1/§4.2):
- 复用工程根目录 `model.py` 的 `ResNet`/`residual`(只读,不改动);
- 模型在首次调用 `get_model()` 时加载一次并常驻内存,供 M4/M8 使用;
- 提供全局推理锁 `INFERENCE_LOCK`,供 M4 在推理入口串行化单张/批量并发请求(设计 §2 约束 7);
- 权重加载失败抛出含 M1 中文文案 `MSG_WEIGHTS_MISSING` 的 `RuntimeError`(设计 §6)。

注意:`model.py` 位于工程根目录,导入前把工程根加入 `sys.path`(E402 为有意为之)。
"""
import logging
import sys
import threading
from pathlib import Path
from typing import Optional

import config
import torch

# ---- 把工程根目录加入 sys.path,以便 `from model import residual, ResNet` ----
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from model import ResNet, residual  # noqa: E402

logger = logging.getLogger(__name__)

# ---- 全局推理锁:单张/批量并发请求在推理入口串行执行(设计 §2 约束 7)----
INFERENCE_LOCK = threading.Lock()

# ---- 模块级单例:模型首次加载后常驻内存,只加载一次 ----
_model: Optional[torch.nn.Module] = None


def build_model() -> ResNet:
    """构建模型结构 `ResNet(residual)`,不加载权重。"""
    return ResNet(residual)


def load_model(weights_path: Optional[Path] = None, device: Optional[torch.device] = None) -> ResNet:
    """加载权重到设备并返回就绪模型(已 `eval()` 且位于目标设备)。

    - `weights_path` 缺省时使用 M1 的 `WEIGHTS_PATH`;
    - `device` 缺省时使用 M1 的 `get_device()`(有 CUDA 用 GPU,否则自动回退 CPU);
    - 权重文件不存在、无法读取或 state_dict 键不匹配时,抛出含中文文案的 `RuntimeError`。
    """
    weights_path = config.WEIGHTS_PATH if weights_path is None else weights_path
    device = config.get_device() if device is None else device

    model = build_model()
    try:
        state_dict = torch.load(weights_path, map_location=device)
        model.load_state_dict(state_dict)
    except Exception as exc:
        raise RuntimeError(config.MSG_WEIGHTS_MISSING) from exc

    model.eval()
    model.to(device)
    return model


def get_model() -> torch.nn.Module:
    """返回常驻内存的模型实例:仅第一次调用真正加载权重,之后复用单例。"""
    global _model
    model = _model
    if model is None:
        model = load_model()
        _model = model
        logger.info("模型加载完成")
    return model
