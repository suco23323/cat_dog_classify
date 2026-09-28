# 任务清单:S1 环境准备与一键启动(startup)

> 模块:S1 启动.bat ｜ 来源:`doc/high-level-design.md` §3.3(S1)、§4.2(4)、§7.2 ｜ 最终落点:`启动.bat`、`backend/requirements.txt`
> 设计依据:经用户确认以 high-level-design.md 为准(detailed-design.md 不单独编写),§10 待办项已融入各任务实现要点。
> 约定:任务 1–3 为环境准备(必须最先执行),任务 4–5 为启动脚本与验证(必须最后执行);联调验收清单见 `doc/tasks/progress.md`。

- [x] 1. 安装后端依赖并编写 requirements.txt
  - 描述:`conda activate pytorch_paoge` 后 `pip install fastapi uvicorn python-multipart`;编写 `backend/requirements.txt` 记录 `fastapi`、`uvicorn`、`python-multipart`。
  - 涉及文件:`backend/requirements.txt`(新建);conda 环境 `pytorch_paoge`。
  - 前置依赖:无。
  - 验收/自测:`pip list` 含三包且可 import;`requirements.txt` 内容与安装一致。
- [x] 2. 安装并验证 Node.js
  - 描述:检查 `node -v`、`npm -v`;未安装时用 `winget install OpenJS.NodeJS.LTS`(或官网下载 LTS 安装包)安装,新开终端后验证版本。
  - 涉及文件:系统环境(非工程文件)。
  - 前置依赖:无。
  - 验收/自测:新终端中 `node -v`、`npm -v` 均输出版本号。
- [x] 3. 创建前端工程脚手架并安装依赖
  - 描述:在工程根执行 `npm create vite@latest frontend -- --template vue`;在 `frontend/` 执行 `npm install` 并 `npm install axios element-plus`。(实现要点:若脚手架创建后即可开始 F1/F2 开发,本任务只负责工程可用。)
  - 涉及文件:`frontend/`(新建工程)。
  - 前置依赖:任务 2。
  - 验收/自测:`frontend/` 下 `npm run dev` 可启动默认页面。
- [x] 4. 编写一键启动脚本 启动.bat
  - 描述:双击后先后:`start` 新窗口执行 `cd backend && conda activate pytorch_paoge && uvicorn main:app --port 8000`;`start` 新窗口执行 `cd frontend && npm run dev`;随后 `start http://localhost:5173` 打开浏览器。
  - 涉及文件:`启动.bat`(新建,工程根目录)。
  - 前置依赖:任务 1、3;M8、F1 完成。
  - 验收/自测:双击后两个命令窗口启动,浏览器自动打开 5173。
- [x] 5. 启动与关闭验证
  - 描述:后端日志出现"模型加载完成"且 `GET /api/health` 返回 ok;前端页面正常加载;端口被占用时窗口可见中文提示(实现要点:脚本或后端启动日志提示);关闭两个命令窗口即停止服务。
  - 涉及文件:`启动.bat`。
  - 前置依赖:任务 4;全部模块完成。
  - 验收/自测:TC-12 一键启动通过;重复双击时端口占用提示可见。

## 本模块完成判定
5 项全部勾选;环境准备(任务 1–3)最先完成、启动验证(任务 4–5)最后完成,一键启动流程与设计 §4.2(4)一致。
