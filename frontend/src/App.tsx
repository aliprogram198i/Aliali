import { useEffect, useMemo, useState } from "react";

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
  module_summary: {
    total_enabled: number;
    categories: string[];
  };
  modules: DashboardModule[];
};

type NetworkResult = {
  ok: boolean;
  message: string;
  hostname?: string | null;
  reachable?: boolean;
  target?: { type: string; value: string };
  port?: number;
};

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "");

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [networkOpen, setNetworkOpen] = useState(false);
  const [selectedModule, setSelectedModule] = useState<DashboardModule | null>(null);
  const [ip, setIp] = useState("");
  const [mac, setMac] = useState("");
  const [port, setPort] = useState("443");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<NetworkResult | null>(null);

  const webApp = window.Telegram?.WebApp;

  useEffect(() => {
    webApp?.ready();
    webApp?.expand();
    webApp?.setHeaderColor("#0b1220");
    webApp?.setBackgroundColor("#07101f");

    if (!API_BASE || !webApp?.initData) {
      setError("بيئة Mini App غير مكتملة. يلزم فتح التطبيق من Telegram وربط API.");
      return;
    }

    const headers = {
      "Content-Type": "application/json",
      "X-Telegram-Init-Data": webApp.initData,
    };
    const body = JSON.stringify({ init_data: webApp.initData });

    fetch(API_BASE + "/api/v1/session", { method: "POST", headers, body })
      .then(async (response) => {
        if (!response.ok) throw new Error("session_failed");
        return (await response.json()) as Session;
      })
      .then(async (authenticatedSession) => {
        setSession(authenticatedSession);
        const dashboardResponse = await fetch(API_BASE + "/api/v1/dashboard", {
          method: "POST",
          headers,
          body,
        });
        if (!dashboardResponse.ok) throw new Error("dashboard_failed");
        setDashboard((await dashboardResponse.json()) as Dashboard);
      })
      .catch(() => setError("تعذر تحميل جلسة Telegram أو لوحة العمليات."));
  }, [webApp]);

  const networkModules = useMemo(
    () => dashboard?.modules.filter((module) => module.category === "network") ?? [],
    [dashboard],
  );

  const otherModules = useMemo(
    () => dashboard?.modules.filter((module) => module.category !== "network") ?? [],
    [dashboard],
  );

  function openNetwork() {
    setNetworkOpen(true);
    setSelectedModule(networkModules[0] ?? null);
    setResult(null);
    setError(null);
  }

  function closeNetwork() {
    setNetworkOpen(false);
    setSelectedModule(null);
    setResult(null);
  }

  async function runNetworkOperation(operation: "validate" | "reverse_dns" | "connectivity") {
    if (!API_BASE || !webApp?.initData || !selectedModule) return;

    setBusy(true);
    setResult(null);
    setError(null);

    const response = await fetch(API_BASE + "/api/v1/network/operate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Telegram-Init-Data": webApp.initData,
      },
      body: JSON.stringify({
        init_data: webApp.initData,
        module_key: selectedModule.key,
        operation,
        ip: ip.trim() || null,
        mac: mac.trim() || null,
        port: operation === "connectivity" ? Number(port) : null,
      }),
    });

    const payload = (await response.json()) as NetworkResult & { detail?: string };
    if (!response.ok) {
      setError(payload.detail ?? "تعذر تنفيذ العملية.");
      setBusy(false);
      return;
    }

    setResult(payload);
    setBusy(false);
  }

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
          <div>
            <strong>الوضع التشغيلي</strong>
            <p>Authorization-first · Evidence-aware</p>
          </div>
        </article>
        <article className="card">
          <strong>الأصول</strong>
          <span className="metric">{dashboard?.metrics.assets ?? "—"}</span>
          <small>بيانات حقيقية فقط</small>
        </article>
        <article className="card">
          <strong>التغييرات</strong>
          <span className="metric">{dashboard?.metrics.changes ?? "—"}</span>
          <small>بانتظار مصدر بيانات</small>
        </article>
        <article className="card">
          <strong>الأدلة</strong>
          <span className="metric">{dashboard?.metrics.evidence ?? "—"}</span>
          <small>لا أرقام وهمية</small>
        </article>
      </section>

      <section className="section-head">
        <div>
          <h2>الوحدات</h2>
          <p>الوحدات المسجلة تأتي من Backend، والتنفيذ الحساس يبقى في الخادم.</p>
        </div>
      </section>

      {dashboard && (
        <section className="card">
          <strong>ملخص الوحدات</strong>
          <span className="metric">{dashboard.module_summary.total_enabled}</span>
          <small>{dashboard.module_summary.categories.join(" · ")}</small>
        </section>
      )}

      <section className="module-list">
        {networkModules.length > 0 && (
          <button className="module module-feature" type="button" onClick={openNetwork}>
            <span className="module-icon">🌐</span>
            <span>
              <strong>إدارة الشبكات</strong>
              <small>{networkModules.length} وحدات شبكية — IP و MAC واختبارات الهدف</small>
            </span>
            <span className="arrow">‹</span>
          </button>
        )}

        {otherModules.map((module) => (
          <button className="module" key={module.key} type="button">
            <span className="module-icon">{module.category === "facebook" ? "📘" : "🧩"}</span>
            <span>
              <strong>{module.title}</strong>
              <small>{module.description}</small>
            </span>
            <span className="arrow">‹</span>
          </button>
        ))}
      </section>

      {networkOpen && (
        <section className="workspace" aria-label="إدارة الشبكات">
          <div className="workspace-head">
            <div>
              <span className="eyebrow">NETWORK MANAGEMENT</span>
              <h2>إدارة الشبكات</h2>
              <p>أدخل هدفًا مصرحًا لك بإدارته ثم اختر العملية المطلوبة.</p>
            </div>
            <button className="close-button" type="button" onClick={closeNetwork}>إغلاق</button>
          </div>

          <div className="network-tools">
            {networkModules.map((module) => (
              <button
                className={"tool-button " + (selectedModule?.key === module.key ? "selected" : "")}
                key={module.key}
                type="button"
                onClick={() => {
                  setSelectedModule(module);
                  setResult(null);
                  setError(null);
                }}
              >
                {module.title}
              </button>
            ))}
          </div>

          {selectedModule && (
            <div className="tool-panel">
              <strong>{selectedModule.title}</strong>
              <p>{selectedModule.description}</p>

              <div className="field-grid">
                <label>
                  عنوان IP
                  <input
                    inputMode="decimal"
                    placeholder="مثال: 192.168.1.10"
                    value={ip}
                    onChange={(event) => setIp(event.target.value)}
                    disabled={busy}
                  />
                </label>
                <label>
                  عنوان MAC
                  <input
                    placeholder="مثال: AA:BB:CC:DD:EE:FF"
                    value={mac}
                    onChange={(event) => setMac(event.target.value)}
                    disabled={busy}
                  />
                </label>
                <label>
                  المنفذ <span>(لاختبار الاتصال)</span>
                  <input
                    inputMode="numeric"
                    placeholder="443"
                    value={port}
                    onChange={(event) => setPort(event.target.value)}
                    disabled={busy}
                  />
                </label>
              </div>

              <div className="action-list">
                <button type="button" onClick={() => runNetworkOperation("validate")} disabled={busy}>
                  {busy ? "جارٍ التنفيذ…" : "تحقق من الهدف"}
                </button>
                <button
                  type="button"
                  onClick={() => runNetworkOperation("reverse_dns")}
                  disabled={busy || !ip.trim()}
                >
                  تعريف الجهاز عبر IP
                </button>
                <button
                  type="button"
                  onClick={() => runNetworkOperation("connectivity")}
                  disabled={busy || !ip.trim() || !port.trim()}
                >
                  اختبار الاتصال بالمنفذ
                </button>
              </div>

              {result && (
                <div className="result-card">
                  <strong>نتيجة العملية</strong>
                  <p>{result.message}</p>
                  {result.target && <small>الهدف: {result.target.value} ({result.target.type.toUpperCase()})</small>}
                  {result.hostname && <small>اسم المضيف: {result.hostname}</small>}
                  {typeof result.reachable === "boolean" && (
                    <small>الحالة: {result.reachable ? "متاح" : "غير متاح ضمن مهلة الاختبار"}</small>
                  )}
                </div>
              )}
            </div>
          )}
        </section>
      )}

      <footer>
        {session?.user?.first_name ? "مرحبًا " + session.user.first_name : "Aliali"}
        {" · لا تنفيذ حساس دون تفويض صريح."}
      </footer>
    </main>
  );
}

export default App;
