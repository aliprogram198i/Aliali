import { useEffect, useState } from "react";

type LookupResult = {
  ok: boolean;
  type: "phone" | "ip" | "mac";
  target: string;
  name?: string;
  international?: string | null;
  e164?: string | null;
  national?: string | null;
  country_code?: number | null;
  region_code?: string | null;
  valid?: boolean | null;
  possible?: boolean | null;
  line_type?: string | null;
  carrier?: string | null;
  location?: string | null;
  timezones?: string[] | null;
  organization?: string | null; isp?: string | null; asn?: number | string | null;
  domain?: string | null; country?: string | null; region?: string | null; city?: string | null;
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
      "ALIALI Reverse Lookup",
      `Target: ${result.target}`,
      `Type: ${result.type.toUpperCase()}`,
      result.international && `International: ${result.international}`,
      result.e164 && `E.164: ${result.e164}`,
      result.national && `National: ${result.national}`,
      result.country_code && `Country code: +${result.country_code}`,
      result.region_code && `Region: ${result.region_code}`,
      result.valid !== undefined && `Valid: ${result.valid ? "Yes" : "No"}`,
      result.possible !== undefined && `Possible: ${result.possible ? "Yes" : "No"}`,
      result.line_type && `Line type: ${result.line_type}`,
      result.carrier && `Carrier: ${result.carrier}`,
      result.location && `Location: ${result.location}`,
      result.timezones?.length && `Timezones: ${result.timezones.join(", ")}`,
      result.organization && `Organization: ${result.organization}`,
      result.isp && `ISP: ${result.isp}`,
      result.asn && `ASN: ${result.asn}`,
      result.domain && `Domain: ${result.domain}`,
      result.oui && `OUI: ${result.oui}`,
      result.assignment && `Assignment: ${result.assignment}`,
      `Source: ${result.source ?? "N/A"}`,
    ].filter(Boolean).join("\n");
    try {
      await navigator.clipboard.writeText(lines);
      setCopied(true); window.setTimeout(() => setCopied(false), 1800);
    } catch { setError("تعذر نسخ النتيجة."); }
  }

  const isPhone = result?.type === "phone";

  return (
    <main className="app">
      <section className="panel">
        <div className="brand">ALIALI · REVERSE INTELLIGENCE</div>
        <h1>البحث العكسي</h1>
        <p className="subtitle">أدخل رقم الهاتف بالصيغة الدولية للحصول على معلومات الترقيم العامة المتاحة.</p>
        <label className="label" htmlFor="target">رقم الهاتف</label>
        <input id="target" dir="ltr" inputMode="tel" autoComplete="off" spellCheck={false}
          placeholder="+33 1 42 34 56 78" value={target}
          onChange={(event) => { setTarget(event.target.value); setError(""); }}
          onKeyDown={(event) => { if (event.key === "Enter") void search(); }}
          disabled={!ready || busy} />
        <button type="button" onClick={() => void search()} disabled={!ready || !target.trim() || busy}>
          {busy ? "جارٍ البحث والتحقق…" : "🔎 بحث"}
        </button>
        {error && <div className="error">{error}</div>}
        {result && (
          <section className="result">
            <div className="result-head">
              <span className="result-type">{isPhone ? "PHONE" : result.type === "ip" ? "IP" : "MAC / OUI"}</span>
              <span className="status">● نتيجة موثقة من بيانات عامة</span>
            </div>
            <h2>{isPhone ? (result.international ?? result.target) : (result.name ?? "Network result")}</h2>
            <p className="target">{result.target}</p>

            {isPhone ? (
              <>
                <div className="section-title">الرقم</div>
                <div className="grid">
                  <Field label="الصيغة الدولية" value={result.international} />
                  <Field label="E.164" value={result.e164} />
                  <Field label="الصيغة المحلية" value={result.national} />
                  <Field label="رمز الدولة" value={result.country_code ? `+${result.country_code}` : null} />
                  <Field label="المنطقة" value={result.region_code} />
                  <Field label="صالح" value={result.valid ? "نعم" : "لا"} />
                  <Field label="قابل للاستخدام" value={result.possible ? "نعم" : "لا"} />
                  <Field label="نوع الخط" value={result.line_type} />
                </div>
                <div className="section-title">المعلومات العامة</div>
                <div className="grid">
                  <Field label="شركة الاتصالات" value={result.carrier} />
                  <Field label="الموقع التقريبي" value={result.location} />
                  <Field label="المناطق الزمنية" value={result.timezones?.join(", ")} />
                </div>
              </>
            ) : (
              <>
                <div className="section-title">الهوية</div>
                <div className="grid">
                  <Field label="النوع" value={result.type === "ip" ? result.ip_version : "MAC"} />
                  <Field label="النطاق" value={result.scope} />
                  <Field label="الجهة" value={result.organization} />
                  <Field label="مزود الشبكة" value={result.isp} />
                  <Field label="ASN" value={result.asn} />
                  <Field label="النطاق المرتبط" value={result.domain} />
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
        <p className="hint">لا يتم حفظ الرقم. لا يمكن استخراج اسم صاحب الرقم أو عنوانه أو حساباته الخاصة من الرقم وحده.</p>
      </section>
    </main>
  );
}

export default App;
