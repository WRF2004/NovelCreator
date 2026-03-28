"use client";

import { useEffect, useMemo, useRef, useState } from "react";
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

type SaveState = "idle" | "pending" | "saving" | "saved" | "error";

export default function BookDetailPage() {
  const params = useParams<{ id: string }>();
  const bookId = Number(params.id);

  const [book, setBook] = useState<Book | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [newChapterTitle, setNewChapterTitle] = useState("新章节");
  const [newChapterDesc, setNewChapterDesc] = useState("");
  const [savingBook, setSavingBook] = useState(false);
  const [savingNow, setSavingNow] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [lastSavedAt, setLastSavedAt] = useState<string>("");

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
  const [chapterPrompts, setChapterPrompts] = useState<Record<number, string>>({});

  const selectedChapter = useMemo(
    () => chapters.find((c) => c.id === selectedId) || null,
    [chapters, selectedId]
  );

  const chaptersRef = useRef<Chapter[]>([]);
  const selectedIdRef = useRef<number | null>(null);
  const autoSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    chaptersRef.current = chapters;
  }, [chapters]);

  useEffect(() => {
    selectedIdRef.current = selectedId;
  }, [selectedId]);

  useEffect(() => {
    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
    };
  }, []);

  function chapterPayload(chapter: Chapter) {
    return {
      title: chapter.title,
      description: chapter.description || "",
      content: chapter.content || "",
      order_index: chapter.order_index,
      status: chapter.status
    };
  }

  function markSaved() {
    setSaveState("saved");
    setLastSavedAt(new Date().toLocaleTimeString());
  }

  async function persistChapter(chapterId: number, silent = false) {
    const chapter = chaptersRef.current.find((c) => c.id === chapterId);
    if (!chapter) return;
    if (!silent) {
      setSavingNow(true);
    }
    setSaveState("saving");
    try {
      const updated = await updateChapter(chapterId, chapterPayload(chapter));
      setChapters((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
      markSaved();
    } catch (e) {
      setSaveState("error");
      setError(e instanceof Error ? e.message : "章节保存失败");
    } finally {
      if (!silent) {
        setSavingNow(false);
      }
    }
  }

  function scheduleAutoSave(chapterId: number) {
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }
    setSaveState("pending");
    autoSaveTimerRef.current = setTimeout(() => {
      void persistChapter(chapterId, true);
      autoSaveTimerRef.current = null;
    }, 1200);
  }

  async function flushAutoSave() {
    const currentId = selectedIdRef.current;
    if (!currentId) return;
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
      autoSaveTimerRef.current = null;
      await persistChapter(currentId, true);
    }
  }

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

      if (chapterRes.length === 0) {
        setSelectedId(null);
      } else if (!selectedId || !chapterRes.some((c) => c.id === selectedId)) {
        setSelectedId(chapterRes[0].id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    }
  }

  useEffect(() => {
    void refreshAll();
  }, [bookId]);

  async function handleSaveBook() {
    if (!book) return;
    setSavingBook(true);
    setError("");
    try {
      const updated = await updateBook(book.id, {
        title: bookTitleInput,
        description: bookDescriptionInput,
        model_path: bookModelPathInput
      });
      setBook(updated);
      setRuntimeModelPath(updated.model_path || runtimeModelPath);
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存书籍失败");
    } finally {
      setSavingBook(false);
    }
  }

  async function handleCreateChapter() {
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
      setSaveState("idle");
    } catch (e) {
      setError(e instanceof Error ? e.message : "新建章节失败");
    }
  }

  async function handleSelectChapter(chapterId: number) {
    await flushAutoSave();
    setSelectedId(chapterId);
    setSaveState("idle");
    setError("");
  }

  function patchSelectedChapter(patch: Partial<Chapter>, autoSave = true) {
    if (!selectedChapter) return;
    const targetId = selectedChapter.id;
    setChapters((prev) => prev.map((c) => (c.id === targetId ? { ...c, ...patch } : c)));
    if (autoSave) {
      scheduleAutoSave(targetId);
    }
  }

  async function handleSaveNow() {
    if (!selectedChapter) return;
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
      autoSaveTimerRef.current = null;
    }
    await persistChapter(selectedChapter.id);
  }

  async function handleGenerateChapter() {
    if (!selectedChapter) return;
    if (!selectedChapter.description || !selectedChapter.description.trim()) {
      setError("请先填写当前章节描述，再生成正文。");
      return;
    }
    await flushAutoSave();
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

      setChapterPrompts((prev) => ({ ...prev, [selectedChapter.id]: response.prompt }));
      setChapters((prev) =>
        prev.map((c) =>
          c.id === selectedChapter.id
            ? {
                ...c,
                content: response.generated_text,
                status: "generated"
              }
            : c
        )
      );
      markSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : "章节生成失败");
    } finally {
      setGenerating(false);
    }
  }

  function saveStatusText() {
    if (saveState === "pending") return "待自动保存";
    if (saveState === "saving") return "自动保存中...";
    if (saveState === "saved") return lastSavedAt ? `已自动保存 ${lastSavedAt}` : "已自动保存";
    if (saveState === "error") return "自动保存失败";
    return "编辑后将自动保存";
  }

  return (
    <>
      <section className="panel">
        <h2>书籍内容页面</h2>
        <p className="desc">目录在左侧，章节正文在中间。编辑章节名、描述和正文后会自动保存。</p>
        {error ? (
          <p className="small" style={{ color: "var(--danger)" }}>
            {error}
          </p>
        ) : null}
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
          <button onClick={handleSaveBook} disabled={savingBook}>
            {savingBook ? "保存中..." : "保存书籍信息"}
          </button>
          <button className="secondary" onClick={() => void refreshAll()}>
            刷新
          </button>
        </div>
      </section>

      <section className="chapter-layout">
        <aside className="panel">
          <h3>章节目录</h3>
          <div className="field">
            <label>新章节名</label>
            <input value={newChapterTitle} onChange={(e) => setNewChapterTitle(e.target.value)} />
          </div>
          <div className="field">
            <label>新章节描述</label>
            <textarea value={newChapterDesc} onChange={(e) => setNewChapterDesc(e.target.value)} rows={3} />
          </div>
          <button onClick={() => void handleCreateChapter()}>新建章节</button>

          <div className="chapter-list" style={{ marginTop: 12 }}>
            {chapters.map((chapter) => (
              <div
                key={chapter.id}
                className={`chapter-item ${chapter.id === selectedId ? "active" : ""}`}
                onClick={() => void handleSelectChapter(chapter.id)}
              >
                <strong>
                  {chapter.order_index}. {chapter.title}
                </strong>
                <p className="small">
                  字数：{chapter.word_count} | 状态：{chapter.status}
                </p>
              </div>
            ))}
            {chapters.length === 0 ? <p className="small">暂无章节</p> : null}
          </div>
        </aside>

        <section className="panel reader-main">
          {!selectedChapter ? (
            <p className="small">请选择章节开始创作</p>
          ) : (
            <>
              <div className="reader-title-row">
                <h3>章节正文</h3>
                <span className={`autosave-pill autosave-${saveState}`}>{saveStatusText()}</span>
              </div>

              <div className="grid-2">
                <div className="field">
                  <label>章节名称（可修改）</label>
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
                    rows={5}
                    value={selectedChapter.description || ""}
                    onChange={(e) => patchSelectedChapter({ description: e.target.value })}
                  />
                </div>
              </div>

              <div className="panel">
                <h3>章节生成</h3>
                <p className="desc">后台会用“已写章节记忆 + 当前描述”生成提示词，再调用本地模型生成本章正文。</p>
                <div className="grid-2">
                  <div className="field">
                    <label>运行模型路径（为空则用书籍默认模型）</label>
                    <input value={runtimeModelPath} onChange={(e) => setRuntimeModelPath(e.target.value)} />
                  </div>
                  <div className="field">
                    <label>目标字数（建议 2000~3000）</label>
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
                    <span>启用 API 优化章节描述</span>
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
                <div className="row wrap">
                  <button onClick={() => void handleGenerateChapter()} disabled={generating}>
                    {generating ? "生成中..." : "生成当前章节"}
                  </button>
                  <button className="secondary" onClick={() => void handleSaveNow()} disabled={savingNow}>
                    {savingNow ? "保存中..." : "立即保存"}
                  </button>
                </div>

                {chapterPrompts[selectedChapter.id] ? (
                  <details>
                    <summary className="small">查看本章生成提示词</summary>
                    <pre className="small mono" style={{ whiteSpace: "pre-wrap" }}>
                      {chapterPrompts[selectedChapter.id]}
                    </pre>
                  </details>
                ) : null}
              </div>

              <div className="field">
                <label>章节正文（阅读/编辑）</label>
                <textarea
                  className="reader-textarea"
                  rows={28}
                  value={selectedChapter.content || ""}
                  onChange={(e) => patchSelectedChapter({ content: e.target.value })}
                />
              </div>

              <p className="small mono">章节文件：{selectedChapter.file_path || "保存后生成"}</p>
            </>
          )}
        </section>
      </section>
    </>
  );
}

