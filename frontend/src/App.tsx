import { useEffect, useState } from "react";

type LookupResult = {
  ok: boolean; type: "ip" | "mac"; target: string; name: string;
  organization?: string | null; isp?: string | null; asn?: number | string | null;
  location?: string | null; domain?: string | null; message: string;
};

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "");

function App() {
  const [ready, setReady] = useState(false);
  const [target, setTarget] = useState("");
  const [result, setResult] = useState<LookupResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const webApp = window.Telegram?.WebApp;

  useEffect(() => {
    webApp?.ready(); webApp?.expand();
    webApp?.setHeaderColor("#07111f"); webApp?.setBackgroundColor("#07111f");
    if (!API_BASE || !webApp?.initData) { setError("افتح التطبيق من Telegram لإجراء البحث."); return; }
    fetch(API_BASE + "/api/v1/session", {
      method: "POST",
      headers: {"Content-Type": "application/json", "X-Telegram-Init-Data": webApp.initData},
      body: JSON.stringify({init_data: webApp.initData}),
    }).then((r) => { if (!r.ok) throw new Error(); setReady(true); })
      .catch(() => setError("تعذر التحقق من جلسة Telegram."));
  }, [webApp]);

  async function search() {
    const value = target.trim();
    if (!value || !API_BASE || !webApp?.initData) return;
    setBusy(true); setError(""); setResult(null);
    try {
      const response = await fetch(API_BASE + "/api/v1/lookup", {
        method: "POST",
        headers: {"Content-Type": "application/json", "X-Telegram-Init-Data": webApp.initData},
        body: JSON.stringify({init_data: webApp.initData, target: value}),
      });
      const payload = await response.json() as LookupResult & {detail?: string};
      if (!response.ok) throw new Error(payload.detail ?? "تعذر تنفيذ البحث.");
      setResult(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر تنفيذ البحث.");
    } finally { setBusy(false); }
  }

  return (
    <main className="app">
      <section className="panel">
        <div className="brand">ALIALI</div>
        <h1>بحث الشبكة</h1>
        <p className="subtitle">أدخل عنوان IP أو MAC واضغط بحث لمعرفة الشبكة أو الشركة المصنّعة المتاحة على الإنترنت.</p>
        <label className="label" htmlFor="target">عنوان IP أو MAC</label>
        <input id="target" dir="ltr" autoCapitalize="characters" autoComplete="off" spellCheck={false}
          placeholder="8.8.8.8 أو AA:BB:CC:DD:EE:FF" value={target}
          onChange={(event) => { setTarget(event.target.value); setError(""); }}
          onKeyDown={(event) => { if (event.key === "Enter") void search(); }}
          disabled={!ready || busy} />
        <button type="button" onClick={() => void search()} disabled={!ready || !target.trim() || busy}>
          {busy ? "جارٍ البحث…" : "🔎 بحث"}
        </button>
        {error && <div className="error">{error}</div>}
        {result && (
          <section className="result">
            <span className="result-type">{result.type === "ip" ? "IP" : "MAC"}</span>
            <h2>{result.name}</h2>
            <p className="target">{result.target}</p>
            {result.organization && <div className="row"><span>الجهة</span><strong>{result.organization}</strong></div>}
            {result.isp && <div className="row"><span>مزود الشبكة</span><strong>{result.isp}</strong></div>}
            {result.asn && <div className="row"><span>ASN</span><strong>{result.asn}</strong></div>}
            {result.location && <div className="row"><span>الموقع التقريبي</span><strong>{result.location}</strong></div>}
            {result.domain && <div className="row"><span>النطاق</span><strong>{result.domain}</strong></div>}
            <p className="message">{result.message}</p>
          </section>
        )}
        <p className="hint">البحث تعريفي فقط؛ لا يوجد فحص منافذ أو مسح للأجهزة.</p>
      </section>
    </main>
  );
}
export default App;
