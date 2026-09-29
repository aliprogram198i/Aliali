import { useEffect, useState } from "react";

const modules = [
  ["🌐", "أمن الشبكة", "الأصول والهوية والخدمات والأدلة"],
  ["🔵", "Facebook", "تحليل المصادر العامة المصرح بها"],
  ["📱", "الهوية", "ذكاء المصادر العامة"],
  ["🚨", "القضايا", "إدارة التحقيقات والأدلة"],
  ["📊", "التقارير", "تقارير قابلة للتتبع"],
] as const;

type Session = {
  authenticated: boolean;
  user?: { first_name?: string; username?: string };
};

function App() {
  const [session, setSession] = useState<Session | null>(null);
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

    const endpoint = apiBase.replace(/\/$/, "") + "/api/v1/session";
    fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Telegram-Init-Data": webApp.initData
      },
      body: JSON.stringify({ init_data: webApp.initData })
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("session_failed");
        return (await response.json()) as Session;
      })
      .then(setSession)
      .catch(() => setError("تعذر التحقق من جلسة Telegram."));
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
        <article className="card"><strong>الأصول</strong><span className="metric">—</span><small>بانتظار البيانات</small></article>
        <article className="card"><strong>التغييرات</strong><span className="metric">—</span><small>بانتظار البيانات</small></article>
        <article className="card"><strong>الأدلة</strong><span className="metric">—</span><small>لا أرقام وهمية</small></article>
      </section>

      <section className="section-head">
        <div><h2>الوحدات</h2><p>الوحدات تُدار من الـ Backend ولا تحتوي الواجهة على منطق أمني حساس.</p></div>
      </section>
      <section className="module-list">
        {modules.map(([icon, title, description]) => (
          <button className="module" key={title} type="button">
            <span className="module-icon">{icon}</span>
            <span><strong>{title}</strong><small>{description}</small></span>
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
