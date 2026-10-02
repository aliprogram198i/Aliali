import { useEffect, useState } from "react";

type EvidenceItem = {
  field: string;
  value: unknown;
  source: string;
  confidence: "low" | "medium" | "high";
  kind: string;
  note?: string;
};

type Evidence = {
  source?: string | null;
  metadata_version?: string | null;
  scope?: string | null;
  items?: EvidenceItem[];
  limitations?: string[];
};

type Analysis = {
  status?: string | null;
  overall_confidence?: "low" | "medium" | "high" | null;
  evidence_count?: number | null;
};

type Identity = {
  status?: "verified" | "publicly_associated" | "not_established" | null;
  name?: string | null;
  source?: string | null;
  verified_at?: string | null;
  note?: string | null;
};

type CurrentLocation = {
  status?: "live" | "not_available" | null;
  latitude?: number | null;
  longitude?: number | null;
  accuracy_m?: number | null;
  updated_at?: string | null;
  source?: string | null;
  note?: string | null;
};

type LookupResult = {
  ok: boolean;
  type: "phone";
  target: string;
  international?: string | null;
  e164?: string | null;
  national?: string | null;
  country_code?: number | null;
  region_code?: string | null;
  country_name?: string | null;
  valid?: boolean | null;
  possible?: boolean | null;
  line_type?: string | null;
  carrier?: string | null;
  location?: string | null;
  timezones?: string[] | null;
  checked_at?: string | null;
  analysis?: Analysis | null;
  identity?: Identity | null;
  current_location?: CurrentLocation | null;
  message: string;
  source?: string | null;
  evidence?: Evidence | null;
};

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "");

const confidenceLabel: Record<string, string> = {
  high: "مرتفع",
  medium: "متوسط",
  low: "منخفض",
};

function Field({ label, value, ltr = false }: { label: string; value?: string | number | boolean | null; ltr?: boolean }) {
  if (value === undefined || value === null || value === "") return null;
  return (
    <div className="row">
      <span>{label}</span>
      <strong className={ltr ? "ltr" : ""}>{String(value)}</strong>
    </div>
  );
}

function StatusPill({ ok, label }: { ok: boolean; label: string }) {
  return <span className={ok ? "pill pill-ok" : "pill pill-muted"}>{ok ? "✓" : "—"} {label}</span>;
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
    webApp?.ready();
    webApp?.expand();
    webApp?.setHeaderColor("#07111f");
    webApp?.setBackgroundColor("#07111f");
    if (!API_BASE || !webApp?.initData) {
      setError("افتح التطبيق من Telegram لإجراء البحث.");
      return;
    }

    fetch(API_BASE + "/api/v1/session", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Telegram-Init-Data": webApp.initData },
      body: JSON.stringify({ init_data: webApp.initData }),
    }).then(async (response) => {
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail ?? "تعذر التحقق من جلسة Telegram.");
      }
      setReady(true);
    }).catch((err) => {
      setError(err instanceof Error ? err.message : "تعذر التحقق من جلسة Telegram.");
    });
  }, [webApp]);

  async function search() {
    const value = target.trim();
    if (!value || !API_BASE || !webApp?.initData) return;
    setBusy(true);
    setError("");
    setResult(null);
    setCopied(false);

    try {
      const response = await fetch(API_BASE + "/api/v1/lookup", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Telegram-Init-Data": webApp.initData },
        body: JSON.stringify({ init_data: webApp.initData, target: value }),
      });
      const payload = await response.json() as LookupResult & { detail?: string };
      if (!response.ok) throw new Error(payload.detail ?? "تعذر تنفيذ البحث.");
      setResult(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر تنفيذ البحث.");
    } finally {
      setBusy(false);
    }
  }

  async function copyResult() {
    if (!result) return;
    const lines = [
      "ALIALI · REVERSE INTELLIGENCE",
      `Number: ${result.international ?? result.target}`,
      `E.164: ${result.e164 ?? "—"}`,
      `Country: ${result.country_name ?? result.region_code ?? "—"} (+${result.country_code ?? "—"})`,
      `Type: ${result.line_type ?? "—"}`,
      `Valid: ${result.valid ? "Yes" : "No"}`,
      `Owner identity: ${result.identity?.name ?? "Not established"}`,
      `Current location: ${result.current_location?.status === "live" ? "Live" : "Not available"}`,
      result.carrier && `Carrier: ${result.carrier}`,
      result.location && `Geographic area: ${result.location}`,
      result.timezones?.length && `Timezones: ${result.timezones.join(", ")}`,
      `Confidence: ${confidenceLabel[result.analysis?.overall_confidence ?? "low"] ?? "منخفض"}`,
      `Source: ${result.evidence?.source ?? result.source ?? "—"}`,
      `Metadata: ${result.evidence?.metadata_version ?? "—"}`,
      `Checked: ${result.checked_at ?? "—"}`,
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
        <header className="hero">
          <div>
            <div className="brand">ALIALI · REVERSE INTELLIGENCE</div>
            <h1>تحليل رقم الهاتف</h1>
            <p className="subtitle">
              بحث عكسي قائم على بيانات الترقيم العامة، مع فصل واضح بين المعلومات المؤكدة
              والإشارات والقيود.
            </p>
          </div>
          <div className="secure-badge">🔐 Telegram session</div>
        </header>

        <div className="search-box">
          <label className="label" htmlFor="target">رقم الهاتف</label>
          <div className="input-wrap">
            <input
              id="target"
              dir="ltr"
              inputMode="tel"
              autoComplete="off"
              spellCheck={false}
              placeholder="+33 1 42 34 56 78"
              value={target}
              onChange={(event) => { setTarget(event.target.value); setError(""); }}
              onKeyDown={(event) => { if (event.key === "Enter") void search(); }}
              disabled={!ready || busy}
            />
            <span className="input-hint">E.164</span>
          </div>
          <button type="button" onClick={() => void search()} disabled={!ready || !target.trim() || busy}>
            {busy ? "جارٍ التحليل والتحقق…" : "🔎 تحليل الرقم"}
          </button>
          {!ready && !error && <div className="session-note">جاري التحقق من جلسة Telegram…</div>}
        </div>

        {error && <div className="error">{error}</div>}

        {result && (
          <section className="result" aria-live="polite">
            <div className="result-head">
              <div>
                <span className="result-type">PHONE INTELLIGENCE</span>
                <span className="result-time">{result.checked_at ? new Date(result.checked_at).toLocaleString("ar") : ""}</span>
              </div>
              <div className="confidence">
                <span>الثقة في بيانات الترقيم</span>
                <strong className={`confidence-${result.analysis?.overall_confidence ?? "low"}`}>
                  {confidenceLabel[result.analysis?.overall_confidence ?? "low"] ?? "منخفض"}
                </strong>
              </div>
            </div>

            <div className="number-card">
              <div className="number-label">الرقم المحلل</div>
              <h2 dir="ltr">{result.international ?? result.target}</h2>
              <div className="number-meta" dir="ltr">{result.e164 ?? result.target}</div>
              <div className="pills">
                <StatusPill ok={Boolean(result.valid)} label={result.valid ? "رقم صالح وفق metadata" : "غير صالح وفق metadata"} />
                <StatusPill ok={Boolean(result.possible)} label={result.possible ? "البنية ممكنة" : "البنية غير ممكنة"} />
              </div>
            </div>

            <div className="section-title">👤 هوية صاحب الرقم</div>
            <div className="identity-result">
              <div className="identity-main">
                <span className="identity-icon">👤</span>
                <div>
                  <strong>{result.identity?.name ?? "غير مثبتة"}</strong>
                  <span>{result.identity?.status === "verified" ? "هوية موثقة" : "لا توجد هوية موثقة ضمن هذا البحث"}</span>
                </div>
              </div>
              <div className="identity-meta">
                <Field label="المصدر" value={result.identity?.source} />
                <Field label="آخر تحقق" value={result.identity?.verified_at} ltr />
              </div>
              <p>{result.identity?.note ?? "لا توجد بيانات هوية موثوقة متاحة."}</p>
            </div>

            <div className="section-title">📍 الموقع الحالي للجهاز</div>
            <div className="live-location">
              <div className="live-location-head">
                <div>
                  <strong>{result.current_location?.status === "live" ? "موقع مباشر متاح" : "الموقع الحالي غير متاح"}</strong>
                  <span>{result.current_location?.note ?? "لا يمكن تحديد موقع الجهاز الحالي من رقم الهاتف وحده."}</span>
                </div>
                <span className={result.current_location?.status === "live" ? "location-status location-live" : "location-status"}>{result.current_location?.status === "live" ? "LIVE" : "UNAVAILABLE"}</span>
              </div>
              {result.current_location?.status === "live" ? (
                <div className="grid">
                  <Field label="خط العرض" value={result.current_location.latitude} ltr />
                  <Field label="خط الطول" value={result.current_location.longitude} ltr />
                  <Field label="الدقة" value={result.current_location.accuracy_m ? result.current_location.accuracy_m + " m" : null} ltr />
                  <Field label="آخر تحديث" value={result.current_location.updated_at} ltr />
                </div>
              ) : (
                <div className="location-explanation">لإظهار موقع حقيقي، يجب أن يصل إلى Aliali موقع GPS من جهاز أو خدمة مصرح لها بمشاركة الموقع. بيانات الدولة أو المنطقة أو شركة الاتصالات لا تُعرض كموقع حالي.</div>
              )}
            </div>

            <div className="section-title">🌍 الهوية الجغرافية للرقم</div>
            <div className="grid">
              <Field label="الدولة" value={result.country_name ?? result.region_code} />
              <Field label="رمز الاتصال" value={result.country_code ? `+${result.country_code}` : null} ltr />
              <Field label="المنطقة" value={result.region_code} ltr />
              <Field label="منطقة مرتبطة بالرقم" value={result.location} />
              <Field label="المناطق الزمنية المحتملة" value={result.timezones?.join(", ")} ltr />
            </div>

            <div className="section-title">📱 خصائص الرقم</div>
            <div className="grid">
              <Field label="نوع الخط" value={result.line_type} />
              <Field label="الصيغة الدولية" value={result.international} ltr />
              <Field label="E.164" value={result.e164} ltr />
              <Field label="الصيغة المحلية" value={result.national} ltr />
              <Field label="شركة الاتصالات" value={result.carrier} />
            </div>

            <div className="section-title">🔐 الأدلة التي بُنيت عليها النتيجة</div>
            <div className="evidence-list">
              {(result.evidence?.items ?? []).map((item) => (
                <article className="evidence-item" key={item.field}>
                  <div>
                    <strong>{item.field}</strong>
                    <span>{item.note ?? "بيانات ترقيم عامة"}</span>
                  </div>
                  <div className="evidence-value">
                    <b>{Array.isArray(item.value) ? item.value.join(", ") : String(item.value)}</b>
                    <em className={`confidence-${item.confidence}`}>{confidenceLabel[item.confidence]}</em>
                  </div>
                </article>
              ))}
            </div>

            <div className="source-card">
              <div className="source-row"><span>المصدر</span><strong>{result.evidence?.source ?? result.source}</strong></div>
              <div className="source-row"><span>إصدار metadata</span><strong>{result.evidence?.metadata_version}</strong></div>
              <div className="source-row"><span>نطاق البيانات</span><strong>{result.evidence?.scope}</strong></div>
              <div className="source-row"><span>عدد الأدلة</span><strong>{result.analysis?.evidence_count ?? result.evidence?.items?.length ?? 0}</strong></div>
            </div>

            {result.evidence?.limitations?.length ? (
              <div className="limitations">
                <div className="limitations-title">⚠️ حدود التحليل</div>
                <ul>
                  {result.evidence.limitations.map((item) => <li key={item}>{item}</li>)}
                </ul>
              </div>
            ) : null}

            <div className="identity-note">
              <span>🛡️</span>
              <div>
                <strong>فصل الهوية والموقع عن بيانات الرقم</strong>
                <p>اسم الشخص وموقع الجهاز الحالي لا يُملآن إلا من مصدر موثوق ومصرح به؛ لا يتم تخمينهما من metadata.</p>
              </div>
            </div>

            <p className="message">{result.message}</p>

            <div className="result-footer">
              <span>لا يتم تخزين رقم البحث في الواجهة.</span>
              <button className="copy" type="button" onClick={() => void copyResult()}>
                {copied ? "✓ تم نسخ التقرير" : "نسخ تقرير التحليل"}
              </button>
            </div>
          </section>
        )}

        <footer className="hint">
          Aliali يعرض ما يمكن إثباته من metadata العامة فقط؛ لا يتم تحويل الإشارات الجغرافية أو carrier إلى هوية شخصية.
        </footer>
      </section>
    </main>
  );
}

export default App;
