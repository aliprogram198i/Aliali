import { useEffect, useState } from "react";

type Session = {
  authenticated: boolean;
  user?: { first_name?: string; username?: string };
};

type DashboardModule = {
  key: string;
  title: string;
  description: string;
  category: string;
  enabled: boolean;
};

type Dashboard = {
  status: string;
  data_source: string;
  metrics: {
    assets: number | null;
    changes: number | null;
    evidence: number | null;
  };
  modules: DashboardModule[];
};

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const webApp = window.Telegram?.WebApp;
    webApp?.ready();
    webApp?.expand();
    webApp?.setHeaderColor("#0b1220");
    webApp?.setBackgroundColor("#07101f");

    const apiBase = import.meta.env.VITE_API_BASE_URL as string | undefined;
    if (!apiBase || !webApp?.initData) {
      setError("بيئة Mini App غير مكتملة. يلزم فتح التطبيق من Telegram وربط API.");
      return;
    }

    const endpoint = apiBase.replace(/\/$/, "");
    const headers = {
      "Content-Type": "application/json",
      "X-Telegram-Init-Data": webApp.initData
    };
    const body = JSON.stringify({ init_data: webApp.initData });

    fetch(endpoint + "/api/v1/session", {
      method: "POST",
      headers,
      body
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("session_failed");
        return (await response.json()) as Session;
      })
      .then(async (authenticatedSession) => {
        setSession(authenticatedSession);
        const dashboardResponse = await fetch(endpoint + "/api/v1/dashboard", {
          method: "POST",
          headers,
          body
        });
        if (!dashboardResponse.ok) throw new Error("dashboard_failed");
        setDashboard((await dashboardResponse.json()) as Dashboard);
      })
      .catch(() => setError("تعذر تحميل جلسة Telegram أو لوحة العمليات."));
  }, []);

  return (
    <main className="app-shell">
      <header className="hero">
        <div>
          <span className="eyebrow">ALIALI · CYBER OPERATIONS</span>
          <h1>مركز العمليات</h1>
          <p>منصة أمنية معيارية تعمل من داخل Telegram Mini App.</p>
        </div>
        <div className={"status " + (session?.authenticated ? "online" : "")}>
          {session?.authenticated ? "● موثّق" : "● انتظار التحقق"}
        </div>
      </header>

      {error && <section className="notice">{error}</section>}

      <section className="grid">
        <article className="card primary">
          <span className="card-icon">🛡️</span>
          <div><strong>الوضع التشغيلي</strong><p>Authorization-first · Evidence-aware</p></div>
        </article>
        <article className="card"><strong>الأصول</strong><span className="metric">{dashboard?.metrics.assets ?? "—"}</span><small>بيانات حقيقية فقط</small></article>
        <article className="card"><strong>التغييرات</strong><span className="metric">{dashboard?.metrics.changes ?? "—"}</span><small>بانتظار مصدر بيانات</small></article>
        <article className="card"><strong>الأدلة</strong><span className="metric">{dashboard?.metrics.evidence ?? "—"}</span><small>لا أرقام وهمية</small></article>
      </section>

      <section className="section-head">
        <div><h2>الوحدات</h2><p>الكتالوج يأتي من Backend، والواجهة لا تحتوي على منطق أمني حساس.</p></div>
      </section>
      <section className="module-list">
        {dashboard?.modules.map((module) => (
          <button className="module" key={module.key} type="button">
            <span className="module-icon">{module.category === "network" ? "🌐" : "🧩"}</span>
            <span><strong>{module.title}</strong><small>{module.description}</small></span>
            <span className="arrow">‹</span>
          </button>
        ))}
      </section>

      <footer>
        {session?.user?.first_name ? "مرحبًا " + session.user.first_name : "Aliali"}
        {" · لا تنفيذ حساس دون تفويض صريح."}
      </footer>
    </main>
  );
}

export default App;
