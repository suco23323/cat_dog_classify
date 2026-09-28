"""tests/test_preprocess.py —— M3 图像预处理模块单元测试。

覆盖 `doc/tasks/preprocess.md` 全部"验收/自测"点:
- 任务 1:`load_rgb_image()` 对 jpg/png/bmp 正常打开且 mode 为 RGB(RGBA/P/L 转 RGB
  后颜色内容不变);非图片、损坏、空字节与 txt 文件均抛出含中文文案的 `ValueError`;
- 任务 2:`preprocess_to_tensor()` 输出 `(1, 3, 224, 224)` 的 float32 tensor,
  数值与 `config.PREPROCESS_TRANSFORM`(与 `model_train.py` 一致)逐元素相同;
- 任务 3:`is_supported_suffix()` 大小写不敏感、按 M1 `SUPPORTED_SUFFIXES` 判定;
  `is_within_size_limit()` 在 10MB 边界 ≤ 通过、> 拒绝。

约定:单测不加载真实权重、不依赖 GPU;png/bmp 与 RGBA/P/L 小图用 PIL 现场生成,
非图片用 `bytes(b"not an image")` 与 `tmp_path` 临时 txt 文件,不污染真实目录。
"""
import io
import re
from pathlib import Path

import config
import pytest
import torch
from PIL import Image
from preprocess import is_supported_suffix, is_within_size_limit, load_rgb_image, preprocess_to_tensor

FIXTURES_DIR: Path = Path(__file__).resolve().parent / "fixtures"

JPEG_FIXTURES = ["cat_1.jpg", "cat_2.jpg", "dog_1.jpg", "dog_2.jpg"]


def _encode(img: Image.Image, img_format: str) -> bytes:
    """把 PIL 图片编码为指定格式的字节流。"""
    buffer = io.BytesIO()
    img.save(buffer, format=img_format)
    return buffer.getvalue()


def _image_bytes(img_format: str, mode: str) -> bytes:
    """用 PIL 现场生成一张 mode 模式的 32x24 小图并编码为 img_format 字节流。"""
    color = (200, 30, 60, 128) if mode == "RGBA" else (200, 30, 60)
    return _encode(Image.new(mode, (32, 24), color), img_format)


# ---- 任务 1:图片打开与解码校验 load_rgb_image() ----
@pytest.mark.parametrize("fixture_name", JPEG_FIXTURES)
def test_load_rgb_image_jpeg_fixtures_return_rgb(fixture_name: str) -> None:
    """jpg 图片正常打开且 mode 为 RGB(四张测试图全过)。"""
    img = load_rgb_image((FIXTURES_DIR / fixture_name).read_bytes())
    assert img.mode == "RGB"
    assert img.size[0] > 0 and img.size[1] > 0


@pytest.mark.parametrize("img_format", ["PNG", "BMP"])
def test_load_rgb_image_png_and_bmp_return_rgb(img_format: str) -> None:
    """png/bmp 字节流正常打开且 mode 为 RGB。"""
    img = load_rgb_image(_image_bytes(img_format, "RGB"))
    assert img.mode == "RGB"
    assert img.size == (32, 24)


def test_load_rgb_image_rgba_converts_to_rgb_keeping_colors() -> None:
    """RGBA 图转 RGB 后丢弃 alpha 通道,颜色内容不变(仍可识别)。"""
    img = load_rgb_image(_image_bytes("PNG", "RGBA"))
    assert img.mode == "RGB"
    assert img.size == (32, 24)
    assert img.getpixel((0, 0)) == (200, 30, 60)


def test_load_rgb_image_grayscale_converts_to_rgb() -> None:
    """灰度 L 模式图统一转 RGB,灰度值映射到三个通道。"""
    img = load_rgb_image(_encode(Image.new("L", (16, 16), 128), "PNG"))
    assert img.mode == "RGB"
    assert img.getpixel((0, 0)) == (128, 128, 128)


def test_load_rgb_image_palette_converts_to_rgb() -> None:
    """调色板 P 模式图统一转 RGB,颜色不变(自定义调色板保证颜色精确)。"""
    palette = Image.new("P", (16, 16))
    palette.putpalette([200, 30, 60] + [0, 0, 0] * 255)
    img = load_rgb_image(_encode(palette, "PNG"))
    assert img.mode == "RGB"
    assert img.getpixel((0, 0)) == (200, 30, 60)


def test_load_rgb_image_error_message_is_exact_chinese_constant() -> None:
    """异常文案与 config.MSG_IMAGE_UNREADABLE 完全一致(供 M7 直接返回前端)。"""
    with pytest.raises(ValueError) as exc_info:
        load_rgb_image(b"not an image")
    assert str(exc_info.value) == config.MSG_IMAGE_UNREADABLE


@pytest.mark.parametrize(
    "bad_bytes",
    [b"", b"not an image", b"\x00\x01\x02\x03", b"PK\x03\x04 not-a-zip"],
    ids=["empty", "text", "binary", "fake-zip"],
)
def test_load_rgb_image_invalid_bytes_raise_chinese_error(bad_bytes: bytes) -> None:
    """非图片/损坏/空字节抛出含 MSG_IMAGE_UNREADABLE 中文文案的 ValueError。"""
    with pytest.raises(ValueError, match=re.escape(config.MSG_IMAGE_UNREADABLE)):
        load_rgb_image(bad_bytes)


def test_load_rgb_image_text_file_raises_chinese_error(tmp_path: Path) -> None:
    """txt 文件内容触发中文错误提示(tmp_path 临时文件)。"""
    txt = tmp_path / "fake.txt"
    txt.write_text("这是一个文本文件,不是图片。", encoding="utf-8")
    with pytest.raises(ValueError, match=re.escape(config.MSG_IMAGE_UNREADABLE)):
        load_rgb_image(txt.read_bytes())


def test_load_rgb_image_truncated_jpeg_raises_chinese_error() -> None:
    """损坏(截断)的 jpg 数据触发中文错误提示。"""
    data = (FIXTURES_DIR / "cat_1.jpg").read_bytes()
    with pytest.raises(ValueError, match=re.escape(config.MSG_IMAGE_UNREADABLE)):
        load_rgb_image(data[: len(data) // 2])


# ---- 任务 2:预处理与升维 preprocess_to_tensor() ----
@pytest.mark.parametrize("fixture_name", JPEG_FIXTURES)
def test_preprocess_to_tensor_shape_and_dtype(fixture_name: str) -> None:
    """本地图片经预处理后得到 (1,3,224,224) 的 float32 tensor。"""
    img = load_rgb_image((FIXTURES_DIR / fixture_name).read_bytes())
    tensor = preprocess_to_tensor(img)
    assert tuple(tensor.shape) == (1, 3, 224, 224)
    assert tensor.dtype == torch.float32


def test_preprocess_to_tensor_values_match_config_transform() -> None:
    """预处理链路数值与 config.PREPROCESS_TRANSFORM(同 model_train.py)逐元素一致。"""
    img = load_rgb_image((FIXTURES_DIR / "cat_2.jpg").read_bytes())
    expected = config.PREPROCESS_TRANSFORM(img)
    actual = preprocess_to_tensor(img).squeeze(0)
    assert tuple(actual.shape) == (3, 224, 224)
    assert torch.equal(actual, expected)


def test_preprocess_pipeline_accepts_converted_rgba_image() -> None:
    """load_rgb_image → preprocess_to_tensor 完整链路对 RGBA 生成图同样可用。"""
    img = load_rgb_image(_image_bytes("PNG", "RGBA"))
    tensor = preprocess_to_tensor(img)
    assert tuple(tensor.shape) == (1, 3, 224, 224)
    assert tensor.dtype == torch.float32


# ---- 任务 3:文件合法性校验辅助函数 ----
@pytest.mark.parametrize(
    "filename",
    ["a.jpg", "a.JPG", "b.jpeg", "B.JPEG", "c.png", "c.PnG", "d.bmp", "D.BMP", "cat_1.JpG", "x.y.z.PNG"],
)
def test_is_supported_suffix_accepts_supported_case_insensitive(filename: str) -> None:
    """.jpg/.jpeg/.png/.bmp 大小写均通过。"""
    assert is_supported_suffix(filename) is True


@pytest.mark.parametrize(
    "filename",
    ["a.txt", "a.gif", "a.GIF", "a.webp", "a", "no_suffix", "a.jpg.txt"],
    ids=["txt", "gif", "GIF", "webp", "no-dot", "no-suffix", "double-suffix"],
)
def test_is_supported_suffix_rejects_unsupported(filename: str) -> None:
    """.txt/.gif 等非支持格式或无后缀文件名被拒绝。"""
    assert is_supported_suffix(filename) is False


def test_is_supported_suffix_matches_config_list() -> None:
    """与 M1 SUPPORTED_SUFFIXES 一致:配置内后缀(大小写)通过。"""
    for suffix in config.SUPPORTED_SUFFIXES:
        assert is_supported_suffix("image" + suffix) is True
        assert is_supported_suffix("IMAGE" + suffix.upper()) is True


def test_is_within_size_limit_boundary_values() -> None:
    """10MB 边界行为正确:≤ 通过,> 拒绝。"""
    limit = config.MAX_FILE_SIZE_BYTES
    assert limit == 10 * 1024 * 1024
    assert is_within_size_limit(0) is True
    assert is_within_size_limit(1) is True
    assert is_within_size_limit(limit - 1) is True
    assert is_within_size_limit(limit) is True
    assert is_within_size_limit(limit + 1) is False
