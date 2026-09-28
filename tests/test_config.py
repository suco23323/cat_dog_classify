"""M1 config 模块单元测试。

覆盖 `doc/tasks/config.md` 全部"验收/自测"点:
- 任务 1:路径/目录常量指向正确,`ensure_dirs()` 创建目录且幂等;
- 任务 2:`get_device()` 与 `torch.cuda.is_available()` 一致,`CLASS_INDEX` 与设计 §1.3 一致;
- 任务 3:`PREPROCESS_TRANSFORM` 输出 shape/dtype,参数与 `model_train.py` 完全一致;
- 任务 4:业务常量与批量上限数值与设计 §2/§5 一致;
- 任务 5:全部中文提示文案与设计 §6 异常设计表逐条一致且齐全。

约定:单测不加载真实权重、不依赖 GPU;目录类测试用 `tmp_path`/`monkeypatch`
隔离,不污染真实的 `backend/uploads` 与 `backend/result` 目录。
"""
from pathlib import Path
from typing import Dict

import config
import pytest
import torch
from PIL import Image
from torchvision import transforms

FIXTURES_DIR: Path = Path(__file__).resolve().parent / "fixtures"

EXPECTED_MESSAGES: Dict[str, str] = {
    "MSG_NO_IMAGE": "请先上传图片",
    "MSG_INVALID_FORMAT_SIZE": "仅支持 jpg/jpeg/png/bmp 图片,单张不超过 10MB",
    "MSG_BATCH_TOO_MANY": "单次最多识别 500 张图片",
    "MSG_BACKEND_NOT_READY": "后端服务未启动,请先运行启动.bat",
    "MSG_WEIGHTS_MISSING": "未找到或无法加载权重文件 best_model_opt20.pth",
    "MSG_IMAGE_UNREADABLE": "无法读取该图片,请上传 jpg/png/bmp 等图片文件",
    "MSG_RECOGNIZE_FAILED": "识别失败,请重试",
    "MSG_JOB_NOT_FOUND": "任务不存在或已失效(后端可能已重启)",
    "MSG_HISTORY_EMPTY_EXPORT": "暂无历史记录可导出",
    "MSG_CSV_WRITE_FAILED": "结果 CSV 写入失败,请重试",
    "MSG_PORT_OCCUPIED": "端口 8000/5173 已被占用",
}


def _has_cjk(text: str) -> bool:
    """判断文案是否包含简体中文常用汉字。"""
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


# ---- 任务 1:路径与目录常量 + ensure_dirs() ----
def test_path_constants_point_correctly() -> None:
    """BACKEND_DIR/PROJECT_ROOT/WEIGHTS_PATH/UPLOAD_DIR/RESULT_DIR/DB_PATH 指向正确。"""
    assert config.BACKEND_DIR == config.PROJECT_ROOT / "backend"
    assert config.UPLOAD_DIR == config.BACKEND_DIR / "uploads"
    assert config.RESULT_DIR == config.BACKEND_DIR / "result"
    assert config.DB_PATH == config.BACKEND_DIR / "app.db"
    assert config.WEIGHTS_PATH == config.PROJECT_ROOT / "best_model_opt20.pth"
    # 仅校验真实权重文件存在,不加载权重
    assert config.WEIGHTS_PATH.is_file()


def test_ensure_dirs_creates_upload_and_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ensure_dirs() 创建 uploads/ 与 result/,指向正确且幂等(用 tmp_path 隔离)。"""
    fake_upload = tmp_path / "uploads"
    fake_result = tmp_path / "result"
    monkeypatch.setattr(config, "UPLOAD_DIR", fake_upload)
    monkeypatch.setattr(config, "RESULT_DIR", fake_result)

    config.ensure_dirs()
    assert fake_upload.is_dir()
    assert fake_result.is_dir()

    # 幂等:目录已存在时再次调用不报错
    config.ensure_dirs()
    assert fake_upload.is_dir()
    assert fake_result.is_dir()


# ---- 任务 2:设备与类别映射 ----
def test_get_device_matches_cuda_availability(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_device() 返回 torch.device 且与 torch.cuda.is_available() 一致。"""
    device = config.get_device()
    assert isinstance(device, torch.device)
    assert device == torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # 无 CUDA 时自动回退 CPU(monkeypatch 模拟,不依赖真实 GPU)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert config.get_device() == torch.device("cpu")

    # 有 CUDA 时返回 GPU
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    assert config.get_device() == torch.device("cuda")


def test_class_index_matches_design() -> None:
    """CLASS_INDEX 与 ImageFolder 目录字母序一致:0→(cat,猫)、1→(dog,狗)。"""
    assert config.CLASS_INDEX == {0: ("cat", "猫"), 1: ("dog", "狗")}
    assert sorted(config.CLASS_INDEX) == [0, 1]
    for index, (english, chinese) in config.CLASS_INDEX.items():
        assert isinstance(index, int)
        assert isinstance(english, str) and english in {"cat", "dog"}
        assert isinstance(chinese, str) and _has_cjk(chinese)


# ---- 任务 3:预处理 transform ----
def test_preprocess_transform_output_shape_and_dtype() -> None:
    """对本地图片应用 PREPROCESS_TRANSFORM 后输出 (3,224,224) 的 float32 tensor。"""
    image_path = FIXTURES_DIR / "cat_1.jpg"
    assert image_path.is_file()

    with Image.open(image_path) as img:
        tensor = config.PREPROCESS_TRANSFORM(img)

    assert tuple(tensor.shape) == (3, 224, 224)
    assert tensor.dtype == torch.float32


def test_preprocess_transform_params_match_model_train() -> None:
    """Resize/ToTensor/Normalize 参数与 model_train.py 完全一致。"""
    assert len(config.PREPROCESS_TRANSFORM.transforms) == 3
    resize, to_tensor, normalize = config.PREPROCESS_TRANSFORM.transforms

    assert isinstance(resize, transforms.Resize)
    assert tuple(resize.size) == (224, 224)
    assert isinstance(to_tensor, transforms.ToTensor)
    assert isinstance(normalize, transforms.Normalize)
    assert list(normalize.mean) == [0.4861, 0.453, 0.4153]
    assert list(normalize.std) == [0.2628, 0.2555, 0.2583]


# ---- 任务 4:业务常量与批量上限 ----
def test_business_constants_match_design() -> None:
    """业务常量数值与设计 §2(约束 10)、§5.2、§5.3 一致。"""
    assert config.SUPPORTED_SUFFIXES == (".jpg", ".jpeg", ".png", ".bmp")
    assert config.MAX_FILE_SIZE_BYTES == 10 * 1024 * 1024
    assert config.MAX_BATCH_FILES == 500
    assert config.PAGE_SIZE_DEFAULT == 10
    assert config.JOB_RETENTION == 20
    assert config.BATCH_COLUMNS == ["文件名", "预测类别", "置信度", "备注"]
    assert config.HISTORY_COLUMNS == ["编号", "文件名", "预测类别", "置信度", "识别时间"]


# ---- 任务 5:中文提示文案常量 ----
def test_message_constants_match_design_section_6() -> None:
    """全部 MSG_* 文案与设计 §6 异常设计表逐条一致、非空、为简体中文。"""
    for name, text in EXPECTED_MESSAGES.items():
        value = getattr(config, name)
        assert isinstance(value, str)
        assert value == text
        assert _has_cjk(value)

    # 文案常量齐全:config 中 MSG_* 名称集合与设计 §6 逐条对应,无缺漏
    msg_names = {
        name for name, value in vars(config).items() if name.startswith("MSG_") and isinstance(value, str)
    }
    assert msg_names == set(EXPECTED_MESSAGES)
