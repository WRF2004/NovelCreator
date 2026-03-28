import Link from "next/link";

export default function HomePage() {
  return (
    <>
      <section className="panel">
        <h2>小说创作工作台</h2>
        <p className="desc">
          使用作者作品训练本地模型，并在书籍章节页面完成“章节描述 → 生成正文 → 自动保存编辑”的完整创作流程。
        </p>
        <div className="row wrap">
          <Link href="/train">
            <button>进入训练模块</button>
          </Link>
          <Link href="/books">
            <button className="secondary">进入书籍创作</button>
          </Link>
        </div>
      </section>

      <section className="grid-2">
        <div className="panel">
          <h3>章节内生成</h3>
          <p className="desc">
            生成能力仅在书籍章节中使用。系统会结合已写章节记忆和当前章节描述，生成提示词后调用本地模型写正文。
          </p>
        </div>
        <div className="panel">
          <h3>自动保存</h3>
          <p className="desc">
            在章节正文页面，标题、描述和正文编辑会自动保存到本地数据库与章节文件，切章后可继续阅读与修改。
          </p>
        </div>
      </section>
    </>
  );
}
