# 任务清单:M1 配置常量(config)

> 模块:M1 config ｜ 来源:`doc/high-level-design.md` §3.2(M1)、§2、§5、§6 ｜ 最终落点:`backend/config.py`(新建)
> 设计依据:经用户确认以 high-level-design.md 为准(detailed-design.md 不单独编写),§10 待办项已融入各任务实现要点。
> 约定:只实现"配置常量与只读小工具",不涉及任何推理与 IO 业务;供 M2–M8 引用;不改动 `model.py`、训练/测试脚本与权重。

- [ ] 1. 定义路径与目录常量,并提供目录创建函数
  - 描述:定义 `BACKEND_DIR = Path(__file__).parent`、`PROJECT_ROOT = BACKEND_DIR.parent`、`WEIGHTS_PATH = PROJECT_ROOT / 'best_model_opt20.pth'`、`UPLOAD_DIR = BACKEND_DIR / 'uploads'`、`RESULT_DIR = BACKEND_DIR / 'result'`、`DB_PATH = BACKEND_DIR / 'app.db'`;提供 `ensure_dirs()` 自动创建 `uploads/` 与 `result/`(供 M8 启动时调用)。
  - 涉及文件:`backend/config.py`(新建)。
  - 前置依赖:无。
  - 验收/自测:在 `backend/` 目录执行 python 导入并调用 `ensure_dirs()`,两个目录被创建且路径指向正确;`WEIGHTS_PATH` 指向工程根目录真实权重文件。
- [ ] 2. 定义设备与类别映射常量
  - 描述:定义 `get_device()` 返回 `torch.device('cuda' if torch.cuda.is_available() else 'cpu')`;定义类别映射 `CLASS_INDEX = {0: ('cat', '猫'), 1: ('dog', '狗')}`(索引 → (英文, 中文),与 ImageFolder 目录字母序一致)。
  - 涉及文件:`backend/config.py`。
  - 前置依赖:任务 1。
  - 验收/自测:打印 `CLASS_INDEX` 与设计 §1.3 一致;`get_device()` 返回值与 `torch.cuda.is_available()` 一致。
- [ ] 3. 定义预处理 transform 常量
  - 描述:定义 `PREPROCESS_TRANSFORM = transforms.Compose([Resize((224,224)), ToTensor(), Normalize(mean=[0.4861,0.453,0.4153], std=[0.2628,0.2555,0.2583])])`,参数必须与 `model_train.py` 完全一致。
  - 涉及文件:`backend/config.py`。
  - 前置依赖:任务 1。
  - 验收/自测:对 `data/test` 一张图片应用后 `tensor.shape == (3,224,224)` 且 dtype 为 float32(无 `data/` 时可用任意本地图片代替)。
- [ ] 4. 定义业务常量与批量上限
  - 描述:定义 `SUPPORTED_SUFFIXES = ('.jpg', '.jpeg', '.png', '.bmp')`、`MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024`、`MAX_BATCH_FILES = 500`、`PAGE_SIZE_DEFAULT = 10`、`JOB_RETENTION = 20`(任务保留数,实现要点:先按 20 实现)、`BATCH_COLUMNS = ['文件名','预测类别','置信度','备注']`、`HISTORY_COLUMNS = ['编号','文件名','预测类别','置信度','识别时间']`。
  - 涉及文件:`backend/config.py`。
  - 前置依赖:任务 1。
  - 验收/自测:各常量数值与设计 §2(约束 10)、§5.2、§5.3 一致;M7 校验逻辑可直接引用。
- [ ] 5. 集中定义全部中文提示文案常量
  - 描述:定义 `MSG_*` 常量:未上传图片、仅支持 jpg/jpeg/png/bmp 图片且单张不超过 10MB、单次最多识别 500 张图片、未找到或无法加载权重文件 best_model_opt20.pth、无法读取该图片,请上传 jpg/png/bmp 等图片文件、识别失败,请重试、任务不存在或已失效(后端可能已重启)、暂无历史记录可导出、结果 CSV 写入失败,请重试、端口被占用提示。文案与设计 §6 表格完全一致。
  - 涉及文件:`backend/config.py`。
  - 前置依赖:无。
  - 验收/自测:文案均为简体中文且与设计 §6 逐条对应;M2–M8 不再硬编码任何提示文案。

## 本模块完成判定
5 项全部勾选;常量集中在本文件,与需求/设计文档数值一致,`ensure_dirs()` 可用。
