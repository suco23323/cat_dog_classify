"""pytest 全局配置:路径注入与通用 fixture。

后端模块以顶层模块名互导入(如 `from config import WEIGHTS_PATH`),
`model.py` 位于工程根目录;本文件把 backend/ 与工程根加入 sys.path。
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"

for _p in (str(BACKEND_DIR), str(PROJECT_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
