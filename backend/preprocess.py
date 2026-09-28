"""M3 图像预处理模块:图片解码校验、训练一致预处理与文件合法性校验辅助函数。

供 M7(service)在单张/批量识别编排中调用:
- `load_rgb_image`:图片字节流 → RGB 模式 PIL 图片,解码失败抛出含中文文案的 `ValueError`;
- `preprocess_to_tensor`:RGB 图片 → `(1, 3, 224, 224)` float32 tensor,
  预处理参数经 `config.PREPROCESS_TRANSFORM` 与 `model_train.py` 完全一致;
- `is_supported_suffix` / `is_within_size_limit`:文件名后缀与文件大小校验,
  供 M7 单张/批量入口做后端权威校验(设计 §2 约束 10 双重校验)。

本模块不加载权重、不访问 GPU,可脱离模型单独单元测试。
"""
import io
from pathlib import Path

import torch
from config import MAX_FILE_SIZE_BYTES, MSG_IMAGE_UNREADABLE, PREPROCESS_TRANSFORM, SUPPORTED_SUFFIXES
from PIL import Image


def load_rgb_image(file_bytes: bytes) -> Image.Image:
    """用 PIL 打开并校验图片字节流,统一转换为 RGB 模式。

    参数:
        file_bytes: 上传图片文件的原始字节(如 `UploadFile` 的 `file.read()` 结果)。

    返回:
        已完整解码的 RGB 模式 PIL 图片(RGBA/P/L 等模式均已转为 RGB)。

    异常:
        ValueError: 字节流不是可解码图片(非图片、损坏或解码失败),
            异常文案即 `config.MSG_IMAGE_UNREADABLE` 中文提示,供 M7 直接返回给前端。
    """
    try:
        with Image.open(io.BytesIO(file_bytes)) as img:
            img.load()  # 强制完整解码:截断/损坏文件在此处抛错
            return img.convert("RGB")
    except Exception:
        # 上传字节流属不可信外部输入:任何打开/解码异常统一转为中文 ValueError,
        # 避免把 PIL 内部异常类型泄漏给上层(M7 只约定捕获 ValueError)。
        raise ValueError(MSG_IMAGE_UNREADABLE) from None


def preprocess_to_tensor(img: Image.Image) -> torch.Tensor:
    """对 RGB 图片执行与训练一致的预处理,并升维为单样本 batch。

    参数:
        img: `load_rgb_image()` 返回的 RGB 模式 PIL 图片。

    返回:
        形状 `(1, 3, 224, 224)`、dtype float32 的模型输入 tensor,
        数值与 `config.PREPROCESS_TRANSFORM`(与 `model_train.py` 完全一致)逐元素相同。
    """
    return PREPROCESS_TRANSFORM(img).unsqueeze(0)


def is_supported_suffix(filename: str) -> bool:
    """判断文件名后缀是否在 M1 支持列表内(不区分大小写)。"""
    return Path(filename).suffix.lower() in SUPPORTED_SUFFIXES


def is_within_size_limit(size_bytes: int) -> bool:
    """判断文件字节数是否不超过 `MAX_FILE_SIZE_BYTES`(≤ 通过,> 拒绝)。"""
    return size_bytes <= MAX_FILE_SIZE_BYTES
