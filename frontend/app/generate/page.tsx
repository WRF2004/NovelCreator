"use client";

import { useState } from "react";

import { generateStandalone } from "@/lib/api";

export default function GeneratePage() {
  const [modelPath, setModelPath] = useState("");
  const [outline, setOutline] = useState("");
  const [memory, setMemory] = useState("");
  const [targetWords, setTargetWords] = useState(2200);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState("");
  const [useApiContext, setUseApiContext] = useState(true);
  const [apiEnabled, setApiEnabled] = useState(false);
  const [apiBaseUrl, setApiBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [apiModel, setApiModel] = useState("");

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await generateStandalone({
        model_path: modelPath,
        outline,
        memory_text: memory || undefined,
        target_words: targetWords,
        use_api_context: useApiContext,
        api_bridge: {
          enabled: apiEnabled,
          base_url: apiBaseUrl || undefined,
          api_key: apiKey || undefined,
          model: apiModel || undefined
        }
      });
      setResult(res.generated_text);
    } catch (e) {
      setError(e instanceof Error ? e.message : "生成失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel">
      <h2>独立生成（无需训练模块）</h2>
      <p className="desc">只要本地有可用模型路径，即可根据大纲直接生成章节内容。</p>
      {error ? <p className="small" style={{ color: "var(--danger)" }}>{error}</p> : null}
      <form onSubmit={handleGenerate}>
        <div className="field">
          <label>本地模型路径</label>
          <input value={modelPath} onChange={(e) => setModelPath(e.target.value)} placeholder="E:\\NovelData\\models\\author_lora_001" />
        </div>
        <div className="field">
          <label>章节大纲</label>
          <textarea value={outline} onChange={(e) => setOutline(e.target.value)} rows={6} />
        </div>
        <div className="field">
          <label>已生成内容（记忆，可选）</label>
          <textarea value={memory} onChange={(e) => setMemory(e.target.value)} rows={6} />
        </div>
        <div className="row wrap">
          <div className="field" style={{ minWidth: 170 }}>
            <label>目标字数</label>
            <input type="number" value={targetWords} onChange={(e) => setTargetWords(Number(e.target.value))} />
          </div>
          <div className="row">
            <input
              style={{ width: 18, height: 18 }}
              type="checkbox"
              checked={useApiContext}
              onChange={(e) => setUseApiContext(e.target.checked)}
            />
            <span>允许 API 扩展章节描述</span>
          </div>
          <div className="row">
            <input
              style={{ width: 18, height: 18 }}
              type="checkbox"
              checked={apiEnabled}
              onChange={(e) => setApiEnabled(e.target.checked)}
            />
            <span>启用外部 API</span>
          </div>
        </div>

        {apiEnabled ? (
          <div className="grid-2">
            <div className="field">
              <label>API Base URL</label>
              <input value={apiBaseUrl} onChange={(e) => setApiBaseUrl(e.target.value)} placeholder="https://api.xxx.com/v1" />
            </div>
            <div className="field">
              <label>API Model</label>
              <input value={apiModel} onChange={(e) => setApiModel(e.target.value)} placeholder="gpt-4.1-mini" />
            </div>
            <div className="field" style={{ gridColumn: "1 / -1" }}>
              <label>API Key</label>
              <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} />
            </div>
          </div>
        ) : null}

        <div className="row">
          <button type="submit" disabled={loading}>{loading ? "生成中..." : "生成章节"}</button>
        </div>
      </form>

      <div className="field" style={{ marginTop: 12 }}>
        <label>生成结果</label>
        <textarea value={result} onChange={(e) => setResult(e.target.value)} rows={18} />
      </div>
    </section>
  );
}

