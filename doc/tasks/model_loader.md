# 任务清单:M2 模型加载(model_loader)

> 模块:M2 model_loader ｜ 来源:`doc/high-level-design.md` §3.2(M2)、§4.1、§4.2 ｜ 最终落点:`backend/model_loader.py`(新建)
> 设计依据:经用户确认以 high-level-design.md 为准(detailed-design.md 不单独编写),§10 待办项已融入各任务实现要点。
> 约定:复用根目录 `model.py`(只读,不改动)与权重 `best_model_opt20.pth`(只读);模型启动时加载一次并常驻内存;提供全局推理锁供 M4 使用。

- [ ] 1. 实现建模型函数 build_model()
  - 描述:`from model import residual, ResNet`(经 `sys.path` 加入工程根目录);`build_model()` 返回 `ResNet(residual)` 实例(此时不加载权重)。
  - 涉及文件:`backend/model_loader.py`(新建);引用根目录 `model.py`(只读)。
  - 前置依赖:环境准备(见 S1 任务 1)。
  - 验收/自测:`model = build_model()`;在 `torch.no_grad()` 下对 `torch.randn(1,3,224,224)` 前向,输出 shape 为 `(1,2)`。
- [ ] 2. 实现加载权重函数 load_model()
  - 描述:`load_model(weights_path=None, device=None)`:默认使用 `WEIGHTS_PATH`;`model.load_state_dict(torch.load(weights_path, map_location=device))`;`model.eval()`;`model.to(device)`;返回就绪模型。
  - 涉及文件:`backend/model_loader.py`。
  - 前置依赖:任务 1;M1 设备常量。
  - 验收/自测:加载真实权重成功,无 missing/unexpected keys 报错;`model.training == False`;对 `data/test` 一张图可得 `(1,2)` 输出。
- [ ] 3. 加载失败的中文错误处理
  - 描述:权重文件不存在、无法读取或 state_dict 键不匹配时,抛出含 `MSG_WEIGHTS` 中文文案的 `RuntimeError`。
  - 涉及文件:`backend/model_loader.py`。
  - 前置依赖:任务 2;M1 文案常量。
  - 验收/自测:用不存在的路径(如 `./no_such.pth`)调用得到上述中文错误;**不得删除或改名真实权重文件**。
- [ ] 4. 单例常驻与启动加载一次
  - 描述:模块级 `_model = None` 与 `get_model()` 惰性加载(仅第一次真正加载),供 M4/M8 使用;加载成功打印日志"模型加载完成"。
  - 涉及文件:`backend/model_loader.py`。
  - 前置依赖:任务 2、3。
  - 验收/自测:连续两次 `get_model()` 返回同一实例;日志中"模型加载完成"只出现一次。
- [ ] 5. 提供全局推理锁
  - 描述:定义 `INFERENCE_LOCK = threading.Lock()`,供 M4 在推理时使用,保证单张/批量并发请求串行执行。
  - 涉及文件:`backend/model_loader.py`。
  - 前置依赖:无。
  - 验收/自测:`with INFERENCE_LOCK:` 在单线程下可正常进入退出;连续多次加锁释放无异常。

## 本模块完成判定
5 项全部勾选;模型加载路径与设计 §4 一致,加载失败给出中文提示,启动只加载一次,推理锁可用。
