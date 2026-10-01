import { useEffect, useState } from "react";

type LookupResult = {
  ok: boolean; type: "ip" | "mac"; target: string; name: string;
  organization?: string | null; isp?: string | null; asn?: number | string | null;
  domain?: string | null; location?: string | null; country?: string | null;
  country_code?: string | null; region?: string | null; city?: string | null;
  continent?: string | null; latitude?: number | null; longitude?: number | null;
  timezone?: string | null; is_eu?: boolean | null; ip_version?: string | null;
  scope?: string | null; oui?: string | null; assignment?: string | null;
  message: string; source?: string | null;
};

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "");

function Field({ label, value }: { label: string; value?: string | number | boolean | null }) {
  if (value === undefined || value === null || value === "") return null;
  return <div className="row"><span>{label}</span><strong>{String(value)}</strong></div>;
}

function App() {
  const [ready, setReady] = useState(false);
  const [target, setTarget] = useState("");
  const [result, setResult] = useState<LookupResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const webApp = window.Telegram?.WebApp;

  useEffect(() => {
    webApp?.ready(); webApp?.expand();
    webApp?.setHeaderColor("#07111f"); webApp?.setBackgroundColor("#07111f");
    if (!API_BASE || !webApp?.initData) { setError("افتح التطبيق من Telegram لإجراء البحث."); return; }
    fetch(API_BASE + "/api/v1/session", {
      method: "POST",
      headers: {"Content-Type": "application/json", "X-Telegram-Init-Data": webApp.initData},
      body: JSON.stringify({init_data: webApp.initData}),
    }).then(async (r) => {
      if (!r.ok) {
        const payload = await r.json().catch(() => ({}));
        throw new Error(payload.detail ?? "تعذر التحقق من جلسة Telegram.");
      }
      setReady(true);
    }).catch((err) => setError(err instanceof Error ? err.message : "تعذر التحقق من جلسة Telegram."));
  }, [webApp]);

  async function search() {
    const value = target.trim();
    if (!value || !API_BASE || !webApp?.initData) return;
    setBusy(true); setError(""); setResult(null); setCopied(false);
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

  async function copyResult() {
    if (!result) return;
    const lines = [
      "ALIALI Network Lookup",
      `Target: ${result.target}`,
      `Type: ${result.type.toUpperCase()}`,
      `Name: ${result.name}`,
      result.organization && `Organization: ${result.organization}`,
      result.isp && `ISP: ${result.isp}`,
      result.asn && `ASN: ${result.asn}`,
      result.domain && `Domain: ${result.domain}`,
      result.location && `Location: ${result.location}`,
      result.timezone && `Timezone: ${result.timezone}`,
      result.latitude !== null && result.latitude !== undefined && result.longitude !== null && result.longitude !== undefined
        ? `Coordinates: ${result.latitude}, ${result.longitude}` : "",
      result.oui && `OUI: ${result.oui}`,
      result.assignment && `Assignment: ${result.assignment}`,
      `Source: ${result.source ?? "N/A"}`,
    ].filter(Boolean).join("\n");
    try {
      await navigator.clipboard.writeText(lines);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setError("تعذر نسخ النتيجة.");
    }
  }

  return (
    <main className="app">
      <section className="panel">
        <div className="brand">ALIALI · NETWORK INTELLIGENCE</div>
        <h1>بحث الشبكة</h1>
        <p className="subtitle">أدخل IP أو MAC للحصول على هوية الشبكة والمعلومات العامة المتاحة على الإنترنت.</p>
        <label className="label" htmlFor="target">عنوان IP أو MAC</label>
        <input id="target" dir="ltr" autoCapitalize="characters" autoComplete="off" spellCheck={false}
          placeholder="8.8.8.8 أو AA:BB:CC:DD:EE:FF" value={target}
          onChange={(event) => { setTarget(event.target.value); setError(""); }}
          onKeyDown={(event) => { if (event.key === "Enter") void search(); }}
          disabled={!ready || busy} />
        <button type="button" onClick={() => void search()} disabled={!ready || !target.trim() || busy}>
          {busy ? "جارٍ تحليل البيانات…" : "🔎 بحث"}
        </button>
        {error && <div className="error">{error}</div>}
        {result && (
          <section className="result">
            <div className="result-head">
              <span className="result-type">{result.type === "ip" ? "PUBLIC IP" : "MAC / OUI"}</span>
              <span className="status">● بيانات متاحة</span>
            </div>
            <h2>{result.name}</h2>
            <p className="target">{result.target}</p>

            <div className="section-title">الهوية</div>
            <div className="grid">
              <Field label="النوع" value={result.type === "ip" ? result.ip_version : "MAC"} />
              <Field label="النطاق" value={result.scope} />
              <Field label="الجهة" value={result.organization} />
              <Field label="مزود الشبكة" value={result.isp} />
              <Field label="ASN" value={result.asn} />
              <Field label="النطاق المرتبط" value={result.domain} />
            </div>

            {result.type === "ip" && (
              <>
                <div className="section-title">الموقع التقريبي</div>
                <div className="grid">
                  <Field label="الدولة" value={result.country} />
                  <Field label="المنطقة" value={result.region} />
                  <Field label="المدينة" value={result.city} />
                  <Field label="القارة" value={result.continent} />
                  <Field label="المنطقة الزمنية" value={result.timezone} />
                  <Field label="الاتحاد الأوروبي" value={result.is_eu === null || result.is_eu === undefined ? null : result.is_eu ? "نعم" : "لا"} />
                  <Field label="الإحداثيات" value={result.latitude !== null && result.latitude !== undefined && result.longitude !== null && result.longitude !== undefined ? `${result.latitude}, ${result.longitude}` : null} />
                </div>
              </>
            )}

            {result.type === "mac" && (
              <>
                <div className="section-title">هوية العنوان</div>
                <div className="grid">
                  <Field label="OUI" value={result.oui} />
                  <Field label="نوع التخصيص" value={result.assignment} />
                </div>
              </>
            )}

            <p className="message">{result.message}</p>
            <div className="result-footer">
              <span>المصدر: {result.source ?? "غير محدد"}</span>
              <button className="copy" type="button" onClick={() => void copyResult()}>{copied ? "✓ تم النسخ" : "نسخ النتيجة"}</button>
            </div>
          </section>
        )}
        <p className="hint">بيانات تعريفية عامة فقط؛ لا يوجد فحص منافذ أو مسح للأجهزة أو كشف لمعلومات خاصة.</p>
      </section>
    </main>
  );
}

export default App;
