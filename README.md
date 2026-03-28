# NovelCreator

本项目是本地小说训练与创作工作台，核心流程为：

- 作者 `txt` 作品 -> 数据集 -> LoRA 微调
- 在“书籍 -> 章节”页面内输入章节描述并生成正文
- 章节正文可阅读、编辑，并自动保存

## 启动

## 后端

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

后端地址：`http://localhost:8000`

## 前端

```powershell
cd frontend
npm install
npm run dev
```

前端地址：`http://localhost:3000`

可选：`frontend/.env.local`

```env
NEXT_PUBLIC_API_BASE=http://localhost:8000/api
```

## 功能

- 训练模块：路径配置、数据集构建、LoRA 训练、任务日志、任务中断/恢复
- 书籍模块：新建书籍、章节目录管理、章节生成、章节阅读编辑
- 自动保存：章节名、章节描述、正文内容编辑后自动落盘

## 生成规则（章节内）

在书籍的章节页中生成正文时，后端会：

1. 读取当前书已写章节内容作为记忆
2. 将“记忆 + 当前章节描述”发送到外部 API（可选）完善提示词
3. 把提示词输入本地训练模型生成章节正文
4. 回写到该章节并保存

## 任务中断/恢复接口

- 中断：`POST /api/training/jobs/{job_id}/interrupt`
- 恢复：`POST /api/training/jobs/{job_id}/resume`

## 持久化

- 数据库：`backend/storage/app.db`
- 章节文件：`backend/storage/books/book_{id}/`
- 数据集：用户指定输出目录
- 模型：用户指定输出目录

