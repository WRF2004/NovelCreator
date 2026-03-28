# NovelCreator

本项目是一个本地运行的小说训练与创作工作台，包含：

- `txt -> 数据集 -> LoRA 微调` 的训练流水线
- 独立的本地模型生成模块（不依赖训练）
- 书籍/章节管理、章节生成、章节编辑保存
- 本地持久化（重启后继续）
- 训练任务中断/恢复控制

## 目录结构

```text
NovelCreator/
├─ backend/                 # FastAPI
│  ├─ app/
│  │  ├─ api/               # training / generation / books
│  │  ├─ services/          # 业务服务
│  │  ├─ tasks/             # 后台任务
│  │  └─ main.py
│  ├─ scripts/train_lora.py # QLoRA 训练脚本
│  ├─ storage/              # 本地持久化
│  └─ requirements.txt
├─ frontend/                # Next.js
└─ docs/
   └─ IMPLEMENTATION.md
```

## 环境要求

- Python 3.9+
- Node.js 18+
- 推荐显卡：RTX 4090 24G

## 启动步骤

### 1. 启动后端

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

后端地址：`http://localhost:8000`

### 2. 启动前端

```powershell
cd frontend
npm install
npm run dev
```

前端地址：`http://localhost:3000`

可选：新建 `frontend/.env.local`：

```env
NEXT_PUBLIC_API_BASE=http://localhost:8000/api
```

## 功能说明

### 训练模块

- 输入作者 `txt` 文件夹、基础模型路径、数据集输出目录、模型输出目录
- 后台自动完成：
  1. 构建 `train.jsonl`
  2. 执行 LoRA 微调
  3. 保存模型并注册记录
- 支持外部 API（OpenAI 兼容）参与数据集指令构造

### 训练中断/恢复

- 中断接口：`POST /api/training/jobs/{job_id}/interrupt`
- 恢复接口：`POST /api/training/jobs/{job_id}/resume`
- 恢复逻辑：
  - 优先复用已生成数据集
  - 若存在 checkpoint，自动从 checkpoint 继续训练

### 生成模块（独立）

- 只要有本地模型路径即可生成
- 输入大纲和可选记忆文本
- 可选用外部 API 先扩展章节描述，再交给本地模型生成

### 书籍与章节模块

- 新建书籍、编辑书名和默认模型路径
- 新建章节、输入章节描述、生成章节正文
- 章节正文可手动编辑并保存
- 每章正文保存到本地文件

## 持久化位置

- 数据库：`backend/storage/app.db`
- 章节文件：`backend/storage/books/book_{id}/`
- 数据集：用户设置输出目录下的 `train.jsonl`
- 模型：用户设置输出目录下的 LoRA 目录

