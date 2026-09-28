"""M2 model_loader 模块单元测试。

覆盖 `doc/tasks/model_loader.md` 全部"验收/自测"点:
- 任务 1:`build_model()` 返回 `ResNet(residual)`(不加载权重),随机输入前向输出 (1,2);
- 任务 2:`load_model()` 用 `tmp_path` 假权重加载成功、`eval()`、无键报错、参数一致、前向 (1,2);
- 任务 3:权重缺失/损坏/键不匹配时抛出含 `MSG_WEIGHTS_MISSING` 中文文案的 `RuntimeError`;
- 任务 4:`get_model()` 单例:两次调用同一实例、只加载一次、"模型加载完成"日志只出现一次;
- 任务 5:`INFERENCE_LOCK` 可正常加锁/释放,连续多次无异常。

约定:不加载 45MB 真实权重、不依赖 GPU(设备显式用 CPU,或 monkeypatch 强制 CPU);
假权重由 `build_model().state_dict()` 保存到 `tmp_path`;单例测试用 monkeypatch 替换
`_model`/`load_model`,绝不触发真实权重加载;前向测试仅 2 例(CPU 较慢)。
"""
import logging
from pathlib import Path
from typing import Iterator

import config
import model_loader
import pytest
import torch

FAKE_WEIGHTS_NAME = "fake_weights.pth"


@pytest.fixture(autouse=True)
def _reset_model_singleton() -> Iterator[None]:
    """每个用例前后重置模块级单例,防止用例间互相污染或误触真实权重加载。"""
    original = model_loader._model
    model_loader._model = None
    yield
    model_loader._model = original


def _save_fake_weights(tmp_path: Path) -> Path:
    """构建一次模型并把其 state_dict 保存为假权重文件(不加载真实权重)。"""
    reference = model_loader.build_model()
    weights_path = tmp_path / FAKE_WEIGHTS_NAME
    torch.save(reference.state_dict(), weights_path)
    return weights_path


# ---- 任务 1:build_model() ----
def test_build_model_returns_resnet_forward_shape() -> None:
    """build_model() 返回模型实例;no_grad 下对 (1,3,224,224) 前向输出 (1,2)。"""
    model = model_loader.build_model()
    assert isinstance(model, torch.nn.Module)

    with torch.no_grad():
        output = model(torch.randn(1, 3, 224, 224))
    assert tuple(output.shape) == (1, 2)


# ---- 任务 2:load_model() ----
def test_load_model_with_fake_weights(tmp_path: Path) -> None:
    """假权重加载成功:无 missing/unexpected keys 报错、eval 模式、参数一致、前向 (1,2)。"""
    reference = model_loader.build_model()
    weights_path = tmp_path / FAKE_WEIGHTS_NAME
    torch.save(reference.state_dict(), weights_path)

    model = model_loader.load_model(weights_path=weights_path, device=torch.device("cpu"))

    assert isinstance(model, torch.nn.Module)
    assert model.training is False
    # 全部参数与缓冲均位于 CPU(不依赖 GPU)
    for param in model.parameters():
        assert param.device == torch.device("cpu")
    for buffer in model.buffers():
        assert buffer.device == torch.device("cpu")
    # state_dict 键完全一致且数值逐一相等(strict 模式加载成功即无键报错)
    loaded_state = model.state_dict()
    saved_state = reference.state_dict()
    assert loaded_state.keys() == saved_state.keys()
    for key in saved_state:
        assert torch.equal(loaded_state[key], saved_state[key])

    with torch.no_grad():
        output = model(torch.randn(1, 3, 224, 224))
    assert tuple(output.shape) == (1, 2)


def test_load_model_default_device_from_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """device 缺省时取自 config.get_device();monkeypatch 强制 CPU,不依赖 GPU。"""
    weights_path = _save_fake_weights(tmp_path)
    monkeypatch.setattr(config, "get_device", lambda: torch.device("cpu"))

    model = model_loader.load_model(weights_path=weights_path)

    assert model.training is False
    assert all(param.device == torch.device("cpu") for param in model.parameters())


# ---- 任务 3:加载失败的中文错误处理 ----
def test_load_model_missing_weights_raises_chinese_runtime_error(tmp_path: Path) -> None:
    """权重文件不存在:抛出含 MSG_WEIGHTS_MISSING 中文文案的 RuntimeError。"""
    missing = tmp_path / "no_such_weights.pth"
    with pytest.raises(RuntimeError) as exc_info:
        model_loader.load_model(weights_path=missing, device=torch.device("cpu"))
    assert str(exc_info.value) == config.MSG_WEIGHTS_MISSING


def test_load_model_corrupt_weights_raises_chinese_runtime_error(tmp_path: Path) -> None:
    """权重文件无法读取(损坏):抛出含 MSG_WEIGHTS_MISSING 中文文案的 RuntimeError。"""
    corrupt = tmp_path / "corrupt_weights.pth"
    corrupt.write_bytes(b"this is not a torch checkpoint")
    with pytest.raises(RuntimeError) as exc_info:
        model_loader.load_model(weights_path=corrupt, device=torch.device("cpu"))
    assert str(exc_info.value) == config.MSG_WEIGHTS_MISSING


def test_load_model_state_dict_mismatch_raises_chinese_runtime_error(tmp_path: Path) -> None:
    """state_dict 键不匹配:抛出含 MSG_WEIGHTS_MISSING 中文文案的 RuntimeError。"""
    wrong_keys = tmp_path / "wrong_keys_weights.pth"
    torch.save({"unexpected_key": torch.zeros(1)}, wrong_keys)
    with pytest.raises(RuntimeError) as exc_info:
        model_loader.load_model(weights_path=wrong_keys, device=torch.device("cpu"))
    assert str(exc_info.value) == config.MSG_WEIGHTS_MISSING


# ---- 任务 4:单例常驻与启动加载一次 ----
def test_get_model_returns_same_instance_and_loads_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """连续两次 get_model() 返回同一实例,底层 load_model 只调用一次。"""
    calls = 0
    fake_model = object()

    def fake_load_model() -> object:
        nonlocal calls
        calls += 1
        return fake_model

    monkeypatch.setattr(model_loader, "_model", None)
    monkeypatch.setattr(model_loader, "load_model", fake_load_model)

    first = model_loader.get_model()
    second = model_loader.get_model()
    assert first is fake_model
    assert second is fake_model
    assert first is second
    assert calls == 1


def test_get_model_uses_preset_instance_without_reload(monkeypatch: pytest.MonkeyPatch) -> None:
    """_model 已有实例时直接返回,不触发 load_model。"""
    fake_model = object()

    def load_should_not_be_called() -> torch.nn.Module:
        raise AssertionError("get_model() 不应在单例已存在时再次加载权重")

    monkeypatch.setattr(model_loader, "_model", fake_model)
    monkeypatch.setattr(model_loader, "load_model", load_should_not_be_called)

    assert model_loader.get_model() is fake_model


def test_get_model_logs_completion_once(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """加载成功打印"模型加载完成"日志,连续两次调用只出现一次。"""
    monkeypatch.setattr(model_loader, "_model", None)
    monkeypatch.setattr(model_loader, "load_model", lambda: object())

    with caplog.at_level(logging.INFO):
        model_loader.get_model()
        model_loader.get_model()

    assert caplog.text.count("模型加载完成") == 1


# ---- 任务 5:全局推理锁 ----
def test_inference_lock_with_statement_and_repeated_acquire() -> None:
    """INFERENCE_LOCK 支持 with 进入/退出,连续多次加锁释放无异常且不残留锁。"""
    lock = model_loader.INFERENCE_LOCK
    for _ in range(10):
        with lock:
            assert lock.locked()
    for _ in range(10):
        lock.acquire()
        assert lock.locked()
        lock.release()
    assert not lock.locked()
