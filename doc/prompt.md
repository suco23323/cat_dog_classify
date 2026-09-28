# VibeCoding 起始 Prompt(doc/prompt.md)

> 说明:本文件是"猫狗分类软件(FastAPI + Vue3)"VibeCoding 的**起始 Prompt**,可直接整体喂给主 Agent。主 Agent 负责跟踪整体进度、派生子 Agent 逐个实现模块并完成测试与质量检测,**整个过程无人工参与**。
> 版本:v1.0(2026-09-10)｜ 依据:`doc/proposal.md`(需求)、`doc/high-level-design.md`(概要设计)、`doc/tasks/`(任务划分)
> 重要修订:批量识别为**异步任务 + 实时进度**(见 high-level-design §1.4,对 proposal §6 的修订),开发与验收以设计文档为准。

## 1. 角色与总目标

你是一个主 Agent(VibeCoding 协调者)。你的目标:在项目 `D:\exercise\paoge_pytorch\fastaapi_cat_dog` 中,依据现有需求、设计与任务划分,**从零实现并验证**一个可本地一键启动的"猫狗分类软件 v1.0":FastAPI 后端(端口 8000)+ Vue3 + Element Plus 前端(端口 5173)+ SQLite 历史记录 + 异步批量识别任务。

交付判定(全部满足才算完成):

1. `backend/` 按设计实现 9 个模块(M1–M9),`frontend/` 实现 7 个模块(F1–F7),根目录 `启动.bat` 一键启动后双服务运行、浏览器打开 `http://localhost:5173`。
2. 后端新增的 pytest 测试**全部通过**(`pytest` 零失败;单测不依赖 GPU/真实权重,集成测试以 `@pytest.mark.integration` 标记并使用真实权重)。
3. 后端代码通过 **mypy** 与 **ruff** 检测(零错误,配置见 §6)。
4. 前端 `npm run build` **构建成功**(前端质量口径:构建成功 + 接口冒烟,不引入 JS 测试框架)。
5. 按 `doc/tasks/progress.md` 的整体联调验收清单执行 TC-01～TC-17(自动化口径见 §7 Step 3),更新 `doc/tasks/progress.md` 全部勾选与备注。

## 2. 背景与现有资产(只读,禁止改动)

| 资产 | 说明 |
| --- | --- |
| `model.py` | 手写 ResNet(类 ResNet18),导出 `ResNet` 与 `residual`;输入 3×224×224,输出 2 类 logits。**只读,禁止改动。** |
| `best_model_opt20.pth` | 已训练最优权重(state_dict,约 44.8 MB),位于工程根目录。**只读,禁止改动。** |
| `model_train.py`、`model_test.py` | 训练与测试脚本,仅作参数参照。**只读,禁止改动。** |
| `..\cat_dog_classify\data\test\{cat,dog}` | 兄弟工程测试图,只读,可**复制少量图片**到 `tests/fixtures/` 作为测试素材,不得修改源数据。 |
| `doc/proposal.md` | 需求文档(依据)。只读。 |
| `doc/high-level-design.md` | 概要设计:模块 M1–M9/F1–F7/S1、依赖关系、数据流、接口、数据结构、异常设计(依据)。只读。 |
| `doc/tasks/*.md` | 任务划分:17 个模块任务文件 + `progress.md`。**仅 `progress.md` 允许被主 Agent 更新勾选/备注。** |

## 3. 必须遵守的硬性约束

1. **不改动**:`model.py`、`model_train.py`、`model_test.py`、`best_model_opt20.pth`、`doc/proposal.md`、`doc/high-level-design.md`、`doc/tasks/` 下除 `progress.md` 外的全部任务文件。不得删除或改名真实权重文件。
2. **模块落点**:后端每个模块一个源文件,路径与 high-level-design §7.1 目录结构一致(`backend/config.py`、`model_loader.py`、`preprocess.py`、`predict.py`、`database.py`、`file_storage.py`、`service.py`、`main.py`、`schemas.py`);前端落点同 §7.1(`frontend/src/...`);测试统一在工程根 `tests/` 下,每个后端模块对应 `tests/test_<module>.py`。
3. **无人工参与**:遇到依赖缺失、测试失败、类型/风格报错时,自行安装、修改并迭代修复,直到达标;不向用户提问、不中途停止等待。
4. **新增文件范围**:允许新建 `backend/**`、`frontend/**`、`tests/**`、`pyproject.toml`、`.gitignore`、`启动.bat`、`tools/**`(免安装 Node)、`backend/requirements.txt`、`frontend/package.json` 等工程文件;不得修改 §2 只读文件。
5. **Python 环境**:全程使用 `D:\anaconda\envs\pytorch_paoge\python.exe`(Python 3.8、torch 1.11.0+cu113、CUDA 可用);不得升级/卸载 torch 与 torchvision。
6. **Node.js**:使用工程内免安装版(见 §4),不得执行系统级安装。

## 4. 运行环境与依赖安装策略

### 4.1 后端依赖(Python 3.8 兼容)

1. 用 `D:\anaconda\envs\pytorch_paoge\python.exe -m pip install` 安装:`fastapi`、`uvicorn`、`python-multipart`、`pytest`、`mypy`、`ruff`(可联网)。
2. **Python 3.8 兼容回退**:若默认最新版安装失败或无法导入,回退到兼容版本,例如 `fastapi<0.116`、`pydantic<2.11`、`mypy<=1.14`、`ruff<=0.8`;若因环境权限无法写入 conda 环境,改用 `pip install --target backend/.venv-libs ...` 并在所有运行命令加 `PYTHONPATH=backend/.venv-libs`(启动.bat 同步设置)。
3. 运行时依赖写入 `backend/requirements.txt`;本机已有 torch/torchvision/pillow/numpy/pandas,**不要重复安装、升级或卸载 torch**。
4. 模型推理自动选择设备:有 CUDA 用 GPU,否则 CPU;测试不得强制依赖 GPU。

### 4.2 前端 Node.js(工程内免安装版)

1. 下载官方免安装 zip(如 `https://nodejs.org/dist/v20.19.4/node-v20.19.4-win-x64.zip`)解压到 `tools/node/`(解压后 `tools/node/node.exe`、`tools/node/npm.cmd` 可用)。
2. 所有 npm 命令以解压后的路径执行(把 `tools/node` 加入命令 PATH 前缀);在 `frontend/` 执行 `npm install`,依赖:`vue`、`vite`、`@vitejs/plugin-vue`、`axios`、`element-plus`。
3. 依赖写入 `frontend/package.json`;构建命令 `npm run build`。

## 5. 模块划分(来自 high-level-design.md §3/§7.1)

| 模块 | 落点 | 职责要点 |
| --- | --- | --- |
| M1 config | `backend/config.py` | 路径/设备/类别映射/预处理 transform/批量上限/CSV 列名/中文文案常量;`ensure_dirs()` |
| M2 model_loader | `backend/model_loader.py` | `build_model()`/`load_model()`/`get_model()` 单例常驻;中文加载失败;`INFERENCE_LOCK` 全局推理锁 |
| M3 preprocess | `backend/preprocess.py` | `load_rgb_image()` 解码校验转 RGB;`preprocess_to_tensor()` 与训练一致;后缀/大小校验 |
| M4 predict | `backend/predict.py` | `predict_tensor()`(加锁 + no_grad + softmax);`format_result()` 双类概率+标签;异常兜底 |
| M5 database | `backend/database.py` | sqlite3 标准库:`init_db`/`insert_record`/`query_page`/`delete_record`/`clear_all`/`query_all`;删除返回 stored_path |
| M6 file_storage | `backend/file_storage.py` | `save_upload()` 唯一命名;`delete_file()` 忽略不存在;批量/历史 CSV 写入(utf-8-sig) |
| M7 service | `backend/service.py` | `classify_single()` 编排;`JobRegistry` 内存任务注册表;`validate_batch`/`submit_batch`/`run_batch_job`(后台线程)/`get_job_status`/`export_history` |
| M8 api | `backend/main.py` | FastAPI 路由:`/api/classify`、`/api/batch`、`/api/batch/status/{job_id}`、`/api/history*`、`/api/health`;`/uploads`、`/result` 静态挂载;统一中文错误 |
| M9 schemas | `backend/schemas.py` | `ClassifyResponse`/`BatchSubmitResponse`/`JobStatusResponse`/`HistoryItem`/`HistoryPageResponse` |
| F1 main | `frontend/vite.config.js`、`index.html`、`src/main.js` | 端口 5173 + `/api` 代理;注册 Element Plus |
| F2 app | `frontend/src/App.vue` | el-tabs 三页签 + 后端就绪探测(`/api/health`)+ 历史页刷新联动 |
| F3 api_client | `frontend/src/api/index.js` | axios 封装全部接口;统一错误拦截(后端未启动提示);CSV 下载封装 |
| F4 single_classify | `frontend/src/views/SingleClassify.vue` | 上传+预览+识别+类别/置信度/双 el-progress 概率条 |
| F5 batch_classify | `frontend/src/views/BatchClassify.vue` | 多选/选文件夹双入口;1s 轮询进度条;结果表格+汇总+CSV;404 降级提示 |
| F6 history | `frontend/src/views/History.vue` | 分页列表(缩略图)+删除/清空/导出 CSV+空状态 |
| F7 collect | `frontend/src/utils/collect.js` | 后缀/大小校验、多选归一化、文件夹收集(webkitdirectory)、百分比格式化 |
| S1 startup | `启动.bat`、`backend/requirements.txt` | 环境准备 + 一键启动后端 8000/前端 5173/打开浏览器 |

后端模块间以顶层模块名互导入(如 `from config import WEIGHTS_PATH`),运行与测试均通过 `pythonpath=backend` 解决;`model.py` 位于工程根目录,由 M2/config 经 `sys.path` 注入工程根后导入。

## 6. 质量门槛与配置(必须通过)

### 6.1 pytest(后端"完整单元测试")

- `tests/` 覆盖 M1–M9 每个模块;每模块测试覆盖正常路径与至少一条异常路径;M8 用 `fastapi.testclient.TestClient` 覆盖全部接口。
- **单元测试不得加载 45MB 真实权重、不得依赖 GPU**:模型用随机权重实例或 mock/stub 替代;图片素材使用生成的小图或 `tests/fixtures/` 中复制的少量猫狗图。
- **集成测试**标记 `@pytest.mark.integration`:真实权重加载、端到端识别 fixture 猫狗图、TestClient 全接口联调、异步批量任务(提交→轮询状态直到 `succeeded`,用轮询等待而非固定 sleep)。
- 推荐 `pyproject.toml`(可微调,但必须 pytest/mypy/ruff 全绿):

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["backend", "."]
markers = ["integration: 依赖真实权重或端到端的测试"]

[tool.ruff]
line-length = 120
target-version = "py38"
exclude = ["tools", "node_modules", "frontend"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP"]

[tool.mypy]
python_version = "3.8"
ignore_missing_imports = true
mypy_path = "backend"
files = ["backend", "tests"]
```

### 6.2 mypy 与 ruff(仅后端 Python)

- 后端与测试代码必须补齐类型注解;mypy 零错误(第三方与只读 `model.py` 缺失注解可忽略)。
- `ruff check .` 零错误(E/F/W/I/UP,行宽 120);导入排序规范;不得保留调试输出与未用变量。

### 6.3 前端质量口径

- `frontend/` 下 `npm run build` 零错误;启动 `vite` 开发服务器后首页 HTTP 200 且 `/api/health` 经代理可达(冒烟)。
- 不引入 vitest/ESLint;组件逻辑以构建通过 + 代码审查 + 接口冒烟为验收。

### 6.4 达标命令(工程根目录执行)

```
D:\anaconda\envs\pytorch_paoge\python.exe -m pytest
D:\anaconda\envs\pytorch_paoge\python.exe -m mypy
D:\anaconda\envs\pytorch_paoge\python.exe -m ruff check .
(frontend 目录)npm run build   # npm 使用 tools/node 下免安装版
```

## 7. 主 Agent 工作流程(全程无人工)

按以下顺序推进,**每完成一步都跑一次质量门槛**;子 Agent 完成后由主 Agent 复核并把结果同步到 `doc/tasks/progress.md`(只允许勾选/备注)。

1. **Step 0 基建**:通读 `doc/proposal.md`、`doc/high-level-design.md`、`doc/tasks/*.md`;安装后端依赖与免安装 Node(§4);复制少量猫狗图到 `tests/fixtures/`;创建 `pyproject.toml`、`.gitignore`、`backend/requirements.txt`、`tests/conftest.py`(路径注入)、前端工程骨架;勾选 progress.md 中 S1 任务 1–3 与环境类项。
2. **Step 1 后端模块**:按依赖顺序派生子 Agent(建议:`M1、M9 并行 → M2、M3 并行 → M4 → M5、M6 并行 → M7 → M8`)。每个子 Agent 负责一个任务文件:实现模块代码、编写 `tests/test_<module>.py`、自检 `pytest -m "not integration"` + `mypy` + `ruff check .` 通过后回报。主 Agent 复核后勾选对应 progress.md 模块。
3. **Step 2 前端模块**:按依赖顺序派生子 Agent(建议:`F1 → F7、F3 并行 → F4、F5、F6 并行 → F2`)。每个子 Agent 交付其组件代码,自检 `npm run build`(或阶段性构建)通过后回报;主 Agent 复核勾选。
4. **Step 3 integration 收尾**:主 Agent 亲自执行:全量 `pytest`(含 integration:真实权重识别、TestClient 全接口、异步批量任务);`mypy`、`ruff check .`、`npm run build` 全绿;启动 uvicorn(8000)与 vite dev(5173)做冒烟(`/api/health`、`/` 200、经代理请求后端);核对"不改动清单";清理 `__pycache__`、`node_modules` 以外临时产物;编写并验证 `启动.bat`;对照 TC-01～TC-17 执行**自动化验收**:后端与接口类用例全部实测执行,纯浏览器交互类用例(TC-01～05/07/09/12/13/15/16 的前端部分)以"构建成功 + 组件代码审查 + 接口层实测"为验收口径,并在 progress.md 勾选时备注;更新 progress.md 全部勾选与验收记录。
5. **Step 4 最终报告**:输出总结:新增文件清单、pytest 统计(收集/通过数)、mypy/ruff 结果、前端构建结果、启动方式(双击 `启动.bat` → 浏览器 `http://localhost:5173`)、TC 验收结论与"待人工浏览器复验"清单。

## 8. 子 Agent 规范

- 派生子 Agent 时,把对应模块任务文件(`doc/tasks/<module>.md`)全文作为其任务,并附本 Prompt 的 §3/§4/§6 约束。
- 每个子 Agent 的交付物:实现代码(写入其模块落点文件)+ 对应 `tests/test_<module>.py`(后端);完成报告必须列出:修改的文件、新增测试用例清单、自检命令与输出摘要。
- 子 Agent 只允许改动自己负责的模块文件与自己的测试文件;禁止改动其它模块与只读文件。
- 子 Agent 需要调用其它模块接口时,以 high-level-design §4 与任务文件中的约定签名为准;如与已实现代码不一致,由主 Agent 协调,避免各写各的。
- 前端子 Agent 不得修改 `vite.config.js` 的端口与代理规则(由 F1 负责);组件间数据经 F3 接口层,不新增全局状态库。

## 9. 模块 ↔ 任务文件 ↔ 测试要求对照

| 模块 | 任务文件 | 单元测试必须覆盖(示例) |
| --- | --- | --- |
| M1 config | config.md | 常量取值、`get_device()`、transform shape/dtype、`ensure_dirs()` 建目录、文案常量完整 |
| M2 model_loader | model_loader.md | `build_model()` 随机输入 forward 得 `(1,2)`;假权重加载;缺文件/坏键中文错误(tmp_path,不碰真实权重);`get_model()` 单例;推理锁可重入 |
| M3 preprocess | preprocess.md | RGB 转换;损坏/非图片中文提示;tensor `(1,3,224,224)`/dtype;后缀与大小校验边界 |
| M4 predict | predict.md | 假模型 logits → softmax 和=1;`format_result` 猫/狗映射与字段;异常兜底中文 |
| M5 database | database.md | 建表幂等与字段;插入自增;分页倒序与 total;删除返回 stored_path/不存在 None;清空返回路径;全量查询 |
| M6 file_storage | file_storage.md | 唯一命名不覆盖;删除不存在不报错;两类 CSV 列名与 utf-8-sig(读回校验) |
| M7 service | service.md | `classify_single` 全链路(mock 推理+临时目录);JobRegistry 状态流转/不存在 None/淘汰;超限校验;批量任务线程(含坏文件)推进到 succeeded、summary 正确;`export_history` 空历史中文异常 |
| M8 api | api.md | TestClient:health、classify 正常/坏文件 400、batch 提交+status 轮询+404、history 分页/删除/清空、export 下载与空历史 400;静态文件可访问 |
| M9 schemas | schemas.md | 各模型构造与序列化与设计 §4.4 示例一致;可选字段缺省 |
| F1 main | main.md | 构建成功;5173 端口与 `/api` 代理配置存在(审查) |
| F2 app | app.md | 构建成功;三页签与 health 探测逻辑(审查) |
| F3 api_client | api_client.md | 构建成功;接口函数与错误拦截逻辑(审查) |
| F4 single_classify | single_classify.md | 构建成功;校验/结果渲染逻辑(审查) |
| F5 batch_classify | batch_classify.md | 构建成功;轮询/降级逻辑(审查) |
| F6 history | history.md | 构建成功;分页/删除/导出逻辑(审查) |
| F7 collect | collect.md | 构建成功;后缀/大小/收集/格式化逻辑(审查) |
| S1 startup | startup.md | 依赖安装完成、Node 可用、`启动.bat` 存在且启动冒烟通过 |
| 集成 | progress.md | `@pytest.mark.integration`:真实权重识别 fixture 猫狗图;TestClient 全接口;异步批量任务端到端 |

## 10. 关键常量与技术参数速查(不得写错)

- 类别映射:`0 → ('cat','猫')`,`1 → ('dog','狗')`(ImageFolder 字母序)。
- 预处理:`Resize((224,224))`;`Normalize(mean=[0.4861, 0.453, 0.4153], std=[0.2628, 0.2555, 0.2583])`;上传图片统一转 RGB。
- 权重:`best_model_opt20.pth`(工程根目录,state_dict,约 44.8 MB)。
- 支持后缀:jpg/jpeg/png/bmp;批量上限:单次 ≤ 500 张、单张 ≤ 10 MB;任务保留数 20;轮询间隔 1 秒。
- CSV:批量列 `文件名/预测类别/置信度/备注`(失败行填 "-" 与备注);历史导出列 `编号/文件名/预测类别/置信度/识别时间`;编码 `utf-8-sig`;文件 `result/batch_result_<ts>.csv`、`result/history_<ts>.csv`。
- SQLite:`backend/app.db`,表 `classify_history`(字段见 high-level-design §5.1);删除/清空历史时**联动删除** `uploads/` 对应图片文件。
- 接口:`POST /api/classify`、`POST /api/batch`(返回 `{job_id,total}`)、`GET /api/batch/status/{job_id}`、`GET /api/history`、`DELETE /api/history/{id}`、`DELETE /api/history`、`GET /api/history/export`、`GET /api/health`;失败统一 `{"detail": 中文}`;任务不存在 404。
- 端口:后端 8000、前端 5173,Vite 代理 `/api` → `http://127.0.0.1:8000`;仅监听本机。
- 参照基线:模型测试准确率约 91.88%,仅作模型能力参照,不作为软件缺陷判定。

## 11. 完成即停止

全部门槛通过、`progress.md` 全部勾选并输出最终报告后,任务即完成;**不要**再做范围外功能(用户登录、摄像头、训练入口、非猫狗拒识、局域网/公网部署等均不在本期范围)。
