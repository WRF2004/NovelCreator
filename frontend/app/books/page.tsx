"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { createBook, listBooks, type Book } from "@/lib/api";

export default function BooksPage() {
  const [books, setBooks] = useState<Book[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [modelPath, setModelPath] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function refresh() {
    try {
      const data = await listBooks();
      setBooks(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载书籍失败");
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await createBook({
        title,
        description: description || undefined,
        model_path: modelPath || undefined
      });
      setTitle("");
      setDescription("");
      setModelPath("");
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "创建失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <section className="panel">
        <h2>书籍管理</h2>
        <p className="desc">新建书籍后可进入分章节创作页面，每章可输入描述并调用模型生成，再手动编辑保存。</p>
        {error ? <p className="small" style={{ color: "var(--danger)" }}>{error}</p> : null}
        <form onSubmit={handleCreate}>
          <div className="grid-2">
            <div className="field">
              <label>书名</label>
              <input value={title} onChange={(e) => setTitle(e.target.value)} />
            </div>
            <div className="field">
              <label>默认模型路径（可选）</label>
              <input value={modelPath} onChange={(e) => setModelPath(e.target.value)} placeholder="E:\\NovelData\\models\\xxx" />
            </div>
            <div className="field" style={{ gridColumn: "1 / -1" }}>
              <label>简介（可选）</label>
              <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
            </div>
          </div>
          <button type="submit" disabled={loading}>{loading ? "创建中..." : "新建书籍"}</button>
        </form>
      </section>

      <section className="panel">
        <h3>已有书籍</h3>
        <div className="card-list">
          {books.map((book) => (
            <Link key={book.id} href={`/books/${book.id}`} className="card">
              <div className="row wrap" style={{ justifyContent: "space-between" }}>
                <strong>{book.title}</strong>
                <span className="small">ID: {book.id}</span>
              </div>
              {book.description ? <p className="small">{book.description}</p> : null}
              {book.model_path ? <p className="small mono">{book.model_path}</p> : null}
            </Link>
          ))}
          {books.length === 0 ? <p className="small">暂无书籍，先创建一本</p> : null}
        </div>
      </section>
    </>
  );
}

