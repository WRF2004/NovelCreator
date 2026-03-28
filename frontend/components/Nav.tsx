"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "总览" },
  { href: "/train", label: "训练模型" },
  { href: "/generate", label: "独立生成" },
  { href: "/books", label: "书籍管理" }
];

export default function Nav() {
  const pathname = usePathname();
  return (
    <header className="top-nav">
      <div className="top-nav-title">Novel Creator Studio</div>
      <nav className="top-nav-links">
        {links.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={pathname === item.href ? "active" : ""}
          >
            {item.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}

