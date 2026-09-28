"""M4 推理预测模块:前向推理(加全局推理锁)与结果格式化。

只做推理与结果格式化,不涉及文件读写与数据库;推理异常统一转为中文 `RuntimeError`。
"""
from typing import Any, Dict, Optional

import torch
from config import CLASS_INDEX, MSG_RECOGNIZE_FAILED
from model_loader import INFERENCE_LOCK, get_model
from torch import nn


def predict_tensor(tensor: torch.Tensor, model: Optional[nn.Module] = None) -> torch.Tensor:
    """在全局推理锁与 `no_grad` 下前向推理,返回 softmax 后概率 tensor。

    `model` 缺省时使用 M2 单例模型(便于测试注入 stub);任何推理异常统一
    转为含 `MSG_RECOGNIZE_FAILED` 中文文案的 `RuntimeError`(设计 §4.4/§6)。
    """
    try:
        target = model if model is not None else get_model()
        params = list(target.parameters())
        device = params[0].device if params else tensor.device
        tensor = tensor.to(device)
        with INFERENCE_LOCK:
            with torch.no_grad():
                logits = target(tensor)
        return torch.softmax(logits, dim=1)
    except Exception as exc:
        raise RuntimeError(MSG_RECOGNIZE_FAILED) from exc


def format_result(probs: torch.Tensor) -> Dict[str, Any]:
    """把 `(1, 2)` 概率 tensor 格式化为结果 dict(字段与 M9 契约一致)。

    返回 `predict`('cat'/'dog')、`predict_label`('猫'/'狗')、`confidence`(最大类概率,
    保留 4 位)、`probs`({'cat': ..., 'dog': ...});概率相同时按类别序取猫。
    """
    if probs.dim() == 2:
        values = probs[0].tolist()
    else:
        values = probs.tolist()
    prob_cat = round(float(values[0]), 4)
    prob_dog = round(float(values[1]), 4)
    index = 0 if prob_cat >= prob_dog else 1
    predict, predict_label = CLASS_INDEX[index]
    return {
        "predict": predict,
        "predict_label": predict_label,
        "confidence": round(max(prob_cat, prob_dog), 4),
        "probs": {"cat": prob_cat, "dog": prob_dog},
    }
