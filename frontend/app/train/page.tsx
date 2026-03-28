"use client";

import { useEffect, useMemo, useState } from "react";

import {
  interruptTrainingJob,
  listDatasets,
  listModels,
  listTrainingJobs,
  resumeTrainingJob,
  startTraining,
  type DatasetRecord,
  type LocalModelRecord,
  type TrainingJob
} from "@/lib/api";

type FormState = {
  source_folder: string;
  base_model_path: string;
  dataset_output_dir: string;
  model_output_dir: string;
  dataset_name: string;
  model_name: string;
  max_samples_per_book: number;
  chunk_min_chars: number;
  chunk_max_chars: number;
  epochs: number;
  batch_size: number;
  grad_accumulation_steps: number;
  learning_rate: number;
  lora_r: number;
  lora_alpha: number;
  lora_dropout: number;
  max_seq_length: number;
  api_bridge_enabled: boolean;
  api_base_url: string;
  api_key: string;
  api_model: string;
};

const initialForm: FormState = {
  source_folder: "",
  base_model_path: "",
  dataset_output_dir: "",
  model_output_dir: "",
  dataset_name: "",
  model_name: "",
  max_samples_per_book: 120,
  chunk_min_chars: 600,
  chunk_max_chars: 1600,
  epochs: 1,
  batch_size: 1,
  grad_accumulation_steps: 8,
  learning_rate: 0.0002,
  lora_r: 16,
  lora_alpha: 32,
  lora_dropout: 0.05,
  max_seq_length: 1024,
  api_bridge_enabled: false,
  api_base_url: "",
  api_key: "",
  api_model: ""
};

const RUNNING_STATUSES = new Set(["queued", "preparing_dataset", "resuming", "training", "interrupting"]);
const RESUMABLE_STATUSES = new Set(["interrupted", "failed"]);

export default function TrainPage() {
  const [form, setForm] = useState<FormState>(initialForm);
  const [jobs, setJobs] = useState<TrainingJob[]>([]);
  const [datasets, setDatasets] = useState<DatasetRecord[]>([]);
  const [models, setModels] = useState<LocalModelRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionJobId, setActionJobId] = useState<number | null>(null);
  const [error, setError] = useState<string>("");

  const activeJob = useMemo(() => jobs.find((j) => RUNNING_STATUSES.has(j.status)), [jobs]);

  async function refreshAll() {
    try {
      const [jobsRes, dsRes, modelRes] = await Promise.all([listTrainingJobs(), listDatasets(), listModels()]);
      setJobs(jobsRes);
      setDatasets(dsRes);
      setModels(modelRes);
    } catch (e) {
      setError(e instanceof Error ? e.message : "刷新失败");
    }
  }

  useEffect(() => {
    refreshAll();
    const timer = setInterval(refreshAll, 5000);
    return () => clearInterval(timer);
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await startTraining({
        source_folder: form.source_folder,
        base_model_path: form.base_model_path,
        dataset_output_dir: form.dataset_output_dir,
        model_output_dir: form.model_output_dir,
        dataset_name: form.dataset_name || undefined,
        model_name: form.model_name || undefined,
        max_samples_per_book: Number(form.max_samples_per_book),
        chunk_min_chars: Number(form.chunk_min_chars),
        chunk_max_chars: Number(form.chunk_max_chars),
        epochs: Number(form.epochs),
        batch_size: Number(form.batch_size),
        grad_accumulation_steps: Number(form.grad_accumulation_steps),
        learning_rate: Number(form.learning_rate),
        lora_r: Number(form.lora_r),
        lora_alpha: Number(form.lora_alpha),
        lora_dropout: Number(form.lora_dropout),
        max_seq_length: Number(form.max_seq_length),
        api_bridge: {
          enabled: form.api_bridge_enabled,
          base_url: form.api_base_url || undefined,
          api_key: form.api_key || undefined,
          model: form.api_model || undefined
        }
      });
      await refreshAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : "训练任务提交失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleInterrupt(jobId: number) {
    setError("");
    setActionJobId(jobId);
    try {
      await interruptTrainingJob(jobId);
      await refreshAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : "中断失败");
    } finally {
      setActionJobId(null);
    }
  }

  async function handleResume(jobId: number) {
    setError("");
    setActionJobId(jobId);
    try {
      await resumeTrainingJob(jobId);
      await refreshAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : "恢复失败");
    } finally {
      setActionJobId(null);
    }
  }

  return (
    <>
      <section className="panel">
        <h2>模型训练</h2>
        <p className="desc">输入作者 txt 文件夹、基础模型路径和输出目录，后台自动执行数据集构建与 LoRA 训练。</p>
        {error ? <p className="small" style={{ color: "var(--danger)" }}>{error}</p> : null}
        <form onSubmit={handleSubmit}>
          <div className="grid-2">
            <div className="field">
              <label>作者 txt 文件夹</label>
              <input value={form.source_folder} onChange={(e) => setForm({ ...form, source_folder: e.target.value })} placeholder="E:\\AuthorBooks" />
            </div>
            <div className="field">
              <label>基础模型路径</label>
              <input value={form.base_model_path} onChange={(e) => setForm({ ...form, base_model_path: e.target.value })} placeholder="E:\\Models\\Qwen" />
            </div>
            <div className="field">
              <label>数据集输出目录</label>
              <input value={form.dataset_output_dir} onChange={(e) => setForm({ ...form, dataset_output_dir: e.target.value })} placeholder="E:\\NovelData\\datasets" />
            </div>
            <div className="field">
              <label>训练模型输出目录</label>
              <input value={form.model_output_dir} onChange={(e) => setForm({ ...form, model_output_dir: e.target.value })} placeholder="E:\\NovelData\\models" />
            </div>
            <div className="field">
              <label>数据集名称（可选）</label>
              <input value={form.dataset_name} onChange={(e) => setForm({ ...form, dataset_name: e.target.value })} />
            </div>
            <div className="field">
              <label>模型名称（可选）</label>
              <input value={form.model_name} onChange={(e) => setForm({ ...form, model_name: e.target.value })} />
            </div>
          </div>

          <div className="grid-2">
            <div className="field">
              <label>每本书最大样本数</label>
              <input type="number" value={form.max_samples_per_book} onChange={(e) => setForm({ ...form, max_samples_per_book: Number(e.target.value) })} />
            </div>
            <div className="field">
              <label>chunk 最小字符</label>
              <input type="number" value={form.chunk_min_chars} onChange={(e) => setForm({ ...form, chunk_min_chars: Number(e.target.value) })} />
            </div>
            <div className="field">
              <label>chunk 最大字符</label>
              <input type="number" value={form.chunk_max_chars} onChange={(e) => setForm({ ...form, chunk_max_chars: Number(e.target.value) })} />
            </div>
            <div className="field">
              <label>epochs</label>
              <input type="number" value={form.epochs} onChange={(e) => setForm({ ...form, epochs: Number(e.target.value) })} />
            </div>
            <div className="field">
              <label>batch size</label>
              <input type="number" value={form.batch_size} onChange={(e) => setForm({ ...form, batch_size: Number(e.target.value) })} />
            </div>
            <div className="field">
              <label>grad accumulation</label>
              <input type="number" value={form.grad_accumulation_steps} onChange={(e) => setForm({ ...form, grad_accumulation_steps: Number(e.target.value) })} />
            </div>
            <div className="field">
              <label>learning rate</label>
              <input type="number" step="0.00001" value={form.learning_rate} onChange={(e) => setForm({ ...form, learning_rate: Number(e.target.value) })} />
            </div>
            <div className="field">
              <label>LoRA r</label>
              <input type="number" value={form.lora_r} onChange={(e) => setForm({ ...form, lora_r: Number(e.target.value) })} />
            </div>
            <div className="field">
              <label>LoRA alpha</label>
              <input type="number" value={form.lora_alpha} onChange={(e) => setForm({ ...form, lora_alpha: Number(e.target.value) })} />
            </div>
            <div className="field">
              <label>LoRA dropout</label>
              <input type="number" step="0.01" value={form.lora_dropout} onChange={(e) => setForm({ ...form, lora_dropout: Number(e.target.value) })} />
            </div>
            <div className="field">
              <label>max seq length</label>
              <input type="number" value={form.max_seq_length} onChange={(e) => setForm({ ...form, max_seq_length: Number(e.target.value) })} />
            </div>
          </div>

          <div className="panel" style={{ marginTop: 12 }}>
            <div className="row">
              <input
                style={{ width: 18, height: 18 }}
                type="checkbox"
                checked={form.api_bridge_enabled}
                onChange={(e) => setForm({ ...form, api_bridge_enabled: e.target.checked })}
              />
              <span>启用外部 API（用于数据集指令构造）</span>
            </div>
            {form.api_bridge_enabled ? (
              <div className="grid-2" style={{ marginTop: 8 }}>
                <div className="field">
                  <label>API Base URL（OpenAI 兼容）</label>
                  <input value={form.api_base_url} onChange={(e) => setForm({ ...form, api_base_url: e.target.value })} placeholder="https://api.xxx.com/v1" />
                </div>
                <div className="field">
                  <label>API Model</label>
                  <input value={form.api_model} onChange={(e) => setForm({ ...form, api_model: e.target.value })} placeholder="gpt-4.1-mini" />
                </div>
                <div className="field" style={{ gridColumn: "1 / -1" }}>
                  <label>API Key</label>
                  <input value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} type="password" />
                </div>
              </div>
            ) : null}
          </div>

          <div className="row" style={{ marginTop: 12 }}>
            <button type="submit" disabled={loading || Boolean(activeJob)}>
              {loading ? "提交中..." : activeJob ? "当前有任务运行中" : "开始训练"}
            </button>
            <button type="button" className="secondary" onClick={refreshAll}>
              刷新状态
            </button>
          </div>
        </form>
      </section>

      <section className="grid-2">
        <div className="panel">
          <h3>训练任务</h3>
          <div className="card-list">
            {jobs.map((job) => (
              <div className="card" key={job.id}>
                <div className="row wrap" style={{ justifyContent: "space-between" }}>
                  <strong>任务 #{job.id}</strong>
                  <span className={`status-pill status-${job.status}`}>{job.status}</span>
                </div>
                <p className="small">进度：{(job.progress * 100).toFixed(1)}%</p>
                <p className="small mono">{job.source_folder}</p>
                <div className="row wrap">
                  {RUNNING_STATUSES.has(job.status) ? (
                    <button
                      type="button"
                      className="warn"
                      disabled={actionJobId === job.id}
                      onClick={() => handleInterrupt(job.id)}
                    >
                      {actionJobId === job.id ? "处理中..." : "中断任务"}
                    </button>
                  ) : null}
                  {RESUMABLE_STATUSES.has(job.status) ? (
                    <button
                      type="button"
                      className="secondary"
                      disabled={actionJobId === job.id || Boolean(activeJob)}
                      onClick={() => handleResume(job.id)}
                    >
                      {actionJobId === job.id ? "处理中..." : "恢复任务"}
                    </button>
                  ) : null}
                </div>
                {job.error_message ? <p className="small" style={{ color: "var(--danger)" }}>{job.error_message}</p> : null}
                <details>
                  <summary className="small">日志</summary>
                  <pre className="small mono" style={{ whiteSpace: "pre-wrap" }}>{job.logs || "暂无日志"}</pre>
                </details>
              </div>
            ))}
            {jobs.length === 0 ? <p className="small">暂无训练任务</p> : null}
          </div>
        </div>

        <div className="panel">
          <h3>已保存数据集</h3>
          <div className="card-list">
            {datasets.map((item) => (
              <div className="card" key={item.id}>
                <strong>{item.name}</strong>
                <p className="small">样本：{item.samples}</p>
                <p className="small mono">{item.path}</p>
              </div>
            ))}
            {datasets.length === 0 ? <p className="small">暂无数据集</p> : null}
          </div>

          <h3 style={{ marginTop: 14 }}>已注册模型</h3>
          <div className="card-list">
            {models.map((item) => (
              <div className="card" key={item.id}>
                <strong>{item.name}</strong>
                <p className="small mono">{item.path}</p>
                {item.base_model_path ? <p className="small mono">base: {item.base_model_path}</p> : null}
              </div>
            ))}
            {models.length === 0 ? <p className="small">暂无模型记录</p> : null}
          </div>
        </div>
      </section>
    </>
  );
}

