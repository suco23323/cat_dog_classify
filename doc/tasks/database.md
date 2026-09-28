# 任务清单:M5 数据库访问(database)

> 模块:M5 database ｜ 来源:`doc/high-level-design.md` §3.2(M5)、§5.1、§5.4 ｜ 最终落点:`backend/database.py`(新建)
> 设计依据:经用户确认以 high-level-design.md 为准(detailed-design.md 不单独编写),§10 待办项已融入各任务实现要点。
> 约定:使用 Python 标准库 `sqlite3`,不引入 ORM;本模块是唯一访问 SQLite 的模块;删除记录时需返回 `stored_path` 供 M6 删除图片文件(设计 §5.4 联动)。

- [ ] 1. 实现连接管理 get_connection()
  - 描述:`get_connection()` 返回 `sqlite3.connect(DB_PATH)`(实现要点:先按"每次调用新建连接"实现,简单可靠;`row_factory = sqlite3.Row` 便于字典化)。
  - 涉及文件:`backend/database.py`(新建)。
  - 前置依赖:M1 路径常量。
  - 验收/自测:可执行 SQL 并提交;连接能正常关闭。
- [ ] 2. 实现建表 init_db()
  - 描述:建表 `classify_history(id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT, stored_path TEXT, predict TEXT, prob_cat REAL, prob_dog REAL, confidence REAL, created_at TEXT)`;在 `created_at` 上建索引;`CREATE TABLE IF NOT EXISTS` 保证幂等。
  - 涉及文件:`backend/database.py`。
  - 前置依赖:任务 1。
  - 验收/自测:首次与重复调用均成功;`PRAGMA table_info` 字段与设计 §5.1 完全一致;索引存在。
- [ ] 3. 实现插入 insert_record()
  - 描述:`insert_record(filename, stored_path, predict, prob_cat, prob_dog, confidence, created_at) -> int`,返回新记录 id。
  - 涉及文件:`backend/database.py`。
  - 前置依赖:任务 2。
  - 验收/自测:连续插入多条,id 自增且数据回读一致。
- [ ] 4. 实现分页查询 query_page()
  - 描述:`query_page(page, page_size) -> (total, items)`:按 `created_at DESC, id DESC` 倒序,返回总数与当前页记录列表(每条含 `image_url` 所需文件名,实现要点:由 `stored_path` 拼出 `/uploads/<filename>`)。
  - 涉及文件:`backend/database.py`。
  - 前置依赖:任务 2、3。
  - 验收/自测:插入 25 条后查 `page=2, page_size=10` 得 10 条且倒序、`total=25`;`page=3` 得 5 条。
- [ ] 5. 实现删除单条 delete_record()
  - 描述:`delete_record(record_id) -> Optional[str]`:删除指定记录并返回其 `stored_path`;记录不存在返回 `None`(供 M8 判 404)。
  - 涉及文件:`backend/database.py`。
  - 前置依赖:任务 2、3。
  - 验收/自测:删除后记录消失且返回正确路径;重复删除返回 `None`。
- [ ] 6. 实现清空 clear_all()
  - 描述:`clear_all() -> list[str]`:取出全部 `stored_path` 后清空表,返回路径列表(供 M6 批量删除图片文件)。
  - 涉及文件:`backend/database.py`。
  - 前置依赖:任务 2、3。
  - 验收/自测:清空后 `COUNT(*) == 0`,返回的路径列表条数与清空前一致。
- [ ] 7. 实现全量查询 query_all()
  - 描述:`query_all() -> list`:按时间倒序返回全部记录(供历史导出 CSV)。
  - 涉及文件:`backend/database.py`。
  - 前置依赖:任务 2、3。
  - 验收/自测:返回条数与插入数一致、顺序为倒序。

## 本模块完成判定
7 项全部勾选;表结构与设计 §5.1 一致,增删查行为正确,删除/清空均能返回 `stored_path` 支撑设计 §5.4 文件联动删除。
