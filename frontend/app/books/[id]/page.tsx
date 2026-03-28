"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

import {
  createChapter,
  generateChapter,
  getBook,
  listChapters,
  updateBook,
  updateChapter,
  type Book,
  type Chapter
} from "@/lib/api";

export default function BookDetailPage() {
  const params = useParams<{ id: string }>();
  const bookId = Number(params.id);

  const [book, setBook] = useState<Book | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [newChapterTitle, setNewChapterTitle] = useState("新章节");
  const [newChapterDesc, setNewChapterDesc] = useState("");
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  const [bookTitleInput, setBookTitleInput] = useState("");
  const [bookDescriptionInput, setBookDescriptionInput] = useState("");
  const [bookModelPathInput, setBookModelPathInput] = useState("");

  const [apiEnabled, setApiEnabled] = useState(false);
  const [apiBaseUrl, setApiBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [apiModel, setApiModel] = useState("");
  const [targetWords, setTargetWords] = useState(2400);
  const [useApiContext, setUseApiContext] = useState(true);
  const [runtimeModelPath, setRuntimeModelPath] = useState("");

  const selectedChapter = useMemo(
    () => chapters.find((c) => c.id === selectedId) || null,
    [chapters, selectedId]
  );

  async function refreshAll() {
    if (!bookId) return;
    try {
      const [bookRes, chapterRes] = await Promise.all([getBook(bookId), listChapters(bookId)]);
      setBook(bookRes);
      setChapters(chapterRes);
      setBookTitleInput(bookRes.title || "");
      setBookDescriptionInput(bookRes.description || "");
      setBookModelPathInput(bookRes.model_path || "");
      setRuntimeModelPath(bookRes.model_path || "");
      if (!selectedId && chapterRes.length > 0) {
        setSelectedId(chapterRes[0].id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    }
  }

  useEffect(() => {
    refreshAll();
  }, [bookId]);

  async function handleSaveBook() {
    if (!book) return;
    setSaving(true);
    setError("");
    try {
      const updated = await updateBook(book.id, {
        title: bookTitleInput,
        description: bookDescriptionInput,
        model_path: bookModelPathInput
      });
      setBook(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存书籍失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleCreateChapter() {
    setSaving(true);
    setError("");
    try {
      const chapter = await createChapter(bookId, {
        title: newChapterTitle,
        description: newChapterDesc || undefined
      });
      setChapters((prev) => [...prev, chapter].sort((a, b) => a.order_index - b.order_index));
      setSelectedId(chapter.id);
      setNewChapterTitle("新章节");
      setNewChapterDesc("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "新建章节失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveChapter() {
    if (!selectedChapter) return;
    setSaving(true);
    setError("");
    try {
      const updated = await updateChapter(selectedChapter.id, {
        title: selectedChapter.title,
        description: selectedChapter.description || "",
        content: selectedChapter.content,
        order_index: selectedChapter.order_index,
        status: selectedChapter.status
      });
      setChapters((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存章节失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleGenerateChapter() {
    if (!selectedChapter) return;
    setGenerating(true);
    setError("");
    try {
      const response = await generateChapter({
        book_id: bookId,
        chapter_id: selectedChapter.id,
        model_path: runtimeModelPath || undefined,
        user_description: selectedChapter.description || "",
        target_words: targetWords,
        use_api_context: useApiContext,
        api_bridge: {
          enabled: apiEnabled,
          base_url: apiBaseUrl || undefined,
          api_key: apiKey || undefined,
          model: apiModel || undefined
        }
      });
      setChapters((prev) =>
        prev.map((c) => (c.id === selectedChapter.id ? { ...c, content: response.generated_text, status: "generated" } : c))
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "章节生成失败");
    } finally {
      setGenerating(false);
    }
  }

  function patchSelectedChapter(patch: Partial<Chapter>) {
    if (!selectedChapter) return;
    setChapters((prev) => prev.map((c) => (c.id === selectedChapter.id ? { ...c, ...patch } : c)));
  }

  return (
    <>
      <section className="panel">
        <h2>书籍详情</h2>
        {error ? <p className="small" style={{ color: "var(--danger)" }}>{error}</p> : null}
        <div className="grid-2">
          <div className="field">
            <label>书名</label>
            <input value={bookTitleInput} onChange={(e) => setBookTitleInput(e.target.value)} />
          </div>
          <div className="field">
            <label>默认模型路径</label>
            <input value={bookModelPathInput} onChange={(e) => setBookModelPathInput(e.target.value)} />
          </div>
          <div className="field" style={{ gridColumn: "1 / -1" }}>
            <label>简介</label>
            <textarea value={bookDescriptionInput} onChange={(e) => setBookDescriptionInput(e.target.value)} rows={3} />
          </div>
        </div>
        <div className="row">
          <button onClick={handleSaveBook} disabled={saving}>保存书籍信息</button>
          <button className="secondary" onClick={refreshAll}>刷新</button>
        </div>
      </section>

      <section className="chapter-layout">
        <aside className="panel">
          <h3>章节列表</h3>
          <div className="field">
            <label>新章节名</label>
            <input value={newChapterTitle} onChange={(e) => setNewChapterTitle(e.target.value)} />
          </div>
          <div className="field">
            <label>新章节描述</label>
            <textarea value={newChapterDesc} onChange={(e) => setNewChapterDesc(e.target.value)} rows={3} />
          </div>
          <button onClick={handleCreateChapter} disabled={saving}>新建章节</button>
          <div className="chapter-list" style={{ marginTop: 12 }}>
            {chapters.map((chapter) => (
              <div
                key={chapter.id}
                className={`chapter-item ${chapter.id === selectedId ? "active" : ""}`}
                onClick={() => setSelectedId(chapter.id)}
              >
                <strong>{chapter.order_index}. {chapter.title}</strong>
                <p className="small">字数：{chapter.word_count} | 状态：{chapter.status}</p>
              </div>
            ))}
            {chapters.length === 0 ? <p className="small">暂无章节</p> : null}
          </div>
        </aside>

        <section className="panel">
          {!selectedChapter ? (
            <p className="small">请选择章节进行编辑</p>
          ) : (
            <>
              <h3>章节编辑与生成</h3>
              <div className="grid-2">
                <div className="field">
                  <label>章节标题</label>
                  <input value={selectedChapter.title} onChange={(e) => patchSelectedChapter({ title: e.target.value })} />
                </div>
                <div className="field">
                  <label>章节序号</label>
                  <input
                    type="number"
                    value={selectedChapter.order_index}
                    onChange={(e) => patchSelectedChapter({ order_index: Number(e.target.value) })}
                  />
                </div>
                <div className="field" style={{ gridColumn: "1 / -1" }}>
                  <label>章节描述（生成输入）</label>
                  <textarea
                    rows={6}
                    value={selectedChapter.description || ""}
                    onChange={(e) => patchSelectedChapter({ description: e.target.value })}
                  />
                </div>
              </div>

              <div className="panel">
                <h3>生成参数</h3>
                <div className="grid-2">
                  <div className="field">
                    <label>运行模型路径（为空则用书籍默认模型）</label>
                    <input value={runtimeModelPath} onChange={(e) => setRuntimeModelPath(e.target.value)} />
                  </div>
                  <div className="field">
                    <label>目标字数</label>
                    <input type="number" value={targetWords} onChange={(e) => setTargetWords(Number(e.target.value))} />
                  </div>
                </div>
                <div className="row wrap">
                  <div className="row">
                    <input
                      style={{ width: 18, height: 18 }}
                      type="checkbox"
                      checked={useApiContext}
                      onChange={(e) => setUseApiContext(e.target.checked)}
                    />
                    <span>使用 API 扩展章节描述</span>
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
                      <input value={apiModel} onChange={(e) => setApiModel(e.target.value)} />
                    </div>
                    <div className="field" style={{ gridColumn: "1 / -1" }}>
                      <label>API Key</label>
                      <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} />
                    </div>
                  </div>
                ) : null}
                <div className="row">
                  <button onClick={handleGenerateChapter} disabled={generating}>
                    {generating ? "生成中..." : "生成当前章节"}
                  </button>
                  <button className="secondary" onClick={handleSaveChapter} disabled={saving}>保存章节</button>
                </div>
              </div>

              <div className="field">
                <label>章节正文（可编辑）</label>
                <textarea
                  rows={24}
                  value={selectedChapter.content || ""}
                  onChange={(e) => patchSelectedChapter({ content: e.target.value })}
                />
              </div>
              <p className="small mono">文件路径：{selectedChapter.file_path || "保存后生成"}</p>
            </>
          )}
        </section>
      </section>
    </>
  );
}

