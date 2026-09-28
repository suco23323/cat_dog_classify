"""M4 predict 模块单元测试(stub 模型,不加载真实权重、不依赖 GPU)。"""
from typing import Any, Dict

import predict as predict_module
import pytest
import torch
from config import MSG_RECOGNIZE_FAILED
from predict import format_result, predict_tensor
from torch import nn


class StubModel(nn.Module):
    """返回固定 logits 的 stub 模型,替代真实 ResNet。"""

    def __init__(self, logits: torch.Tensor) -> None:
        super().__init__()
        self.logits = logits

    def forward(self, tensor: torch.Tensor) -> torch.Tensor:  # noqa: D102
        return self.logits


class BrokenModel(nn.Module):
    """forward 抛异常的 stub 模型,用于异常兜底测试。"""

    def forward(self, tensor: torch.Tensor) -> torch.Tensor:  # noqa: D102
        raise ValueError("boom")


def test_predict_tensor_returns_softmax_probabilities() -> None:
    model = StubModel(torch.tensor([[2.0, -2.0]]))
    probs = predict_tensor(torch.randn(1, 3, 224, 224), model)
    assert probs.shape == (1, 2)
    assert abs(float(probs.sum()) - 1.0) < 1e-5
    assert float(probs[0, 0]) > float(probs[0, 1])


def test_predict_tensor_uses_default_model_via_monkeypatch(monkeypatch: pytest.MonkeyPatch) -> None:
    model = StubModel(torch.tensor([[-1.0, 1.0]]))
    monkeypatch.setattr(predict_module, "get_model", lambda: model)
    probs = predict_tensor(torch.randn(1, 3, 224, 224))
    assert float(probs[0, 1]) > float(probs[0, 0])


def test_predict_tensor_exception_wraps_chinese_message() -> None:
    with pytest.raises(RuntimeError) as excinfo:
        predict_tensor(torch.randn(1, 3, 224, 224), BrokenModel())
    assert str(excinfo.value) == MSG_RECOGNIZE_FAILED


def test_format_result_cat_mapping_and_fields() -> None:
    result: Dict[str, Any] = format_result(torch.tensor([[0.924, 0.076]]))
    assert result["predict"] == "cat"
    assert result["predict_label"] == "猫"
    assert result["confidence"] == 0.924
    assert result["probs"] == {"cat": 0.924, "dog": 0.076}


def test_format_result_dog_mapping() -> None:
    result: Dict[str, Any] = format_result(torch.tensor([[0.2, 0.8]]))
    assert result["predict"] == "dog"
    assert result["predict_label"] == "狗"
    assert result["confidence"] == 0.8


def test_format_result_rounds_to_four_decimals() -> None:
    result: Dict[str, Any] = format_result(torch.tensor([[0.87654, 0.12346]]))
    assert result["confidence"] == 0.8765
    assert result["probs"] == {"cat": 0.8765, "dog": 0.1235}


def test_format_result_accepts_1d_tensor() -> None:
    result: Dict[str, Any] = format_result(torch.tensor([0.1, 0.9]))
    assert result["predict"] == "dog"
    assert result["confidence"] == 0.9


def test_format_result_tie_prefers_cat() -> None:
    result: Dict[str, Any] = format_result(torch.tensor([[0.5, 0.5]]))
    assert result["predict"] == "cat"
    assert result["predict_label"] == "猫"
