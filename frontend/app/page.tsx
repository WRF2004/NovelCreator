import Link from "next/link";

export default function HomePage() {
  return (
    <>
      <section className="panel">
        <h2>小说模型工作台</h2>
        <p className="desc">
          用作者 txt 作品自动构建数据集并进行 LoRA 微调，支持分章节生成、章节编辑、章节本地保存和重启后继续创作。
        </p>
        <div className="row wrap">
          <Link href="/train">
            <button>进入训练模块</button>
          </Link>
          <Link href="/generate">
            <button className="secondary">进入独立生成模块</button>
          </Link>
          <Link href="/books">
            <button className="secondary">进入书籍章节管理</button>
          </Link>
        </div>
      </section>
      <section className="grid-2">
        <div className="panel">
          <h3>模块独立</h3>
          <p className="desc">
            训练和生成功能解耦。即使不训练，只要本地已有模型，也可直接在生成模块与书籍模块写作。
          </p>
        </div>
        <div className="panel">
          <h3>持久化</h3>
          <p className="desc">
            书籍、章节、数据集、模型注册信息写入本地 SQLite 和文件系统，项目重启后自动恢复展示。
          </p>
        </div>
      </section>
    </>
  );
}

