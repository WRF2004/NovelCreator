import type { Metadata } from "next";

import Nav from "@/components/Nav";

import "./globals.css";

export const metadata: Metadata = {
  title: "Novel Creator",
  description: "本地小说微调与章节生成工作台"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <div className="app-wrap">
          <Nav />
          <main className="main-wrap">{children}</main>
        </div>
      </body>
    </html>
  );
}

