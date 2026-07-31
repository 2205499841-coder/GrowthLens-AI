import { UploadPanel } from "@/components/upload-panel";

export default function HomePage() {
  return (
    <main className="page-shell">
      <section className="hero">
        <div className="hero-copy-block">
          <p className="eyebrow">GrowthLens AI · 第一阶段</p>
          <h1>从写真业务 Excel 到增长 Dashboard</h1>
          <p className="hero-copy">
            上传标准数据模板，完成数据解析、清洗、指标计算和漏斗分析。
          </p>
        </div>
        <UploadPanel />
      </section>
    </main>
  );
}
