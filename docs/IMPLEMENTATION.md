# 实现说明

## 架构

- 后端：FastAPI + SQLAlchemy + SQLite
- 前端：Next.js App Router + TypeScript
- 存储：数据库 + 本地文件系统

模块拆分：

- 训练模块（数据集生成 + LoRA 微调）
- 生成模块（独立生成）
- 书籍章节模块（分章写作与编辑）

## 后端实现

### API

- `app/api/training.py`
  - 启动训练
  - 查询任务
  - 中断训练
  - 恢复训练
- `app/api/generation.py`
  - 章节生成
  - 独立生成
- `app/api/books.py`
  - 书籍/章节 CRUD

### 训练任务控制

文件：`app/tasks/training_tasks.py`

- 使用后台线程执行训练流水线
- 运行态维护：
  - 当前线程
  - 当前训练子进程
  - 中断标记
  - 任务参数缓存
- 中断逻辑：
  - 设置中断标记
  - 终止训练子进程
  - 任务状态改为 `interrupted`
- 恢复逻辑：
  - 读取缓存/持久化参数
  - 优先复用已生成数据集
  - 若存在 checkpoint，则从 checkpoint 恢复训练

### 数据库扩展

`training_jobs` 新增字段：

- `params_json`：训练参数快照（恢复使用）
- `dataset_path`：已生成数据集路径
- `model_run_dir`：当前任务输出模型目录

应用启动时执行轻量迁移（`app/db/migrations.py`）。

## 训练脚本

文件：`backend/scripts/train_lora.py`

新增参数：

- `--resume-from-checkpoint`

行为：

- 传入 checkpoint 时，调用 `Trainer.train(resume_from_checkpoint=...)`
- 未传入时，执行普通训练

## 前端实现

页面：`frontend/app/train/page.tsx`

- 每个训练任务卡片增加按钮：
  - 运行中：`中断任务`
  - 已中断/失败：`恢复任务`
- 前端调用：
  - `POST /api/training/jobs/{id}/interrupt`
  - `POST /api/training/jobs/{id}/resume`
- 与原有任务轮询逻辑共用，实时看到状态变化与日志。

## 持久化与重启

- 训练参数和关键路径写入数据库，便于恢复
- 重启后可查看历史任务
- 若要恢复任务，需要该任务有可用参数与模型目录

