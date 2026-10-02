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

type SocialEvidenceLedgerEntry = {
  provider_id: string;
  status: string;
  verification?: string | null;
  source?: string | null;
  checked_at?: string | null;
  evidence?: unknown;
  method?: string | null;
  note?: string | null;
};

type SocialApp = {
  id: string;
  name: string;
  status: string;
  verification?: string | null;
  note?: string | null;
  source?: string | null;
  checked_at?: string | null;
  evidence?: unknown;
  method?: string | null;
};

type LocationProfile = {
  status?: "available" | "unknown" | null;
  precision?: "PHONE_AREA" | "PHONE_REGION" | "UNKNOWN" | null;
  country?: string | null;
  region_code?: string | null;
  geographic_area?: string | null;
  timezones?: string[];
  source?: string | null;
  checked_at?: string | null;
  note?: string | null;
  coordinates?: null;
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

type Intelligence = {
  executive_summary?: { headline?: string; validity?: string; identity?: string; live_location?: string; evidence_coverage?: number };
  coverage?: { percent?: number; confirmed?: number; supported?: number; unknown?: number; method?: string };
  confidence?: { overall?: "low" | "medium" | "high"; identity?: string; reason?: string };
  source_registry?: Array<{ id?: string; name?: string; type?: string; status?: string; retrieved_at?: string | null; metadata_version?: string }>;
  consistency_checks?: Array<{ id?: string; label?: string; status?: string; details?: string }>;
  known?: string[];
  unknown?: string[];
  timeline?: Array<{ event?: string; label?: string; at?: string }>;
  ai_analysis?: { status?: string; provider?: string | null; model?: string | null; message?: string };
  generated_at?: string;
};

type LookupResult = {
  ok: boolean;
  type: "phone";
  target: string;
  analysis_id?: string | null;
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
  location_profile?: LocationProfile | null;
  social_apps?: SocialApp[] | null;
  social_evidence_ledger?: SocialEvidenceLedgerEntry[] | null;
  message: string;
  source?: string | null;
  evidence?: Evidence | null;
  executive_summary?: Intelligence["executive_summary"];
  coverage?: Intelligence["coverage"];
  confidence?: Intelligence["confidence"];
  source_registry?: Intelligence["source_registry"];
  consistency_checks?: Intelligence["consistency_checks"];
  known?: string[];
  unknown?: string[];
  timeline?: Intelligence["timeline"];
  ai_analysis?: Intelligence["ai_analysis"];
  generated_at?: string | null;
};

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "");

const confidenceLabel: Record<string, string> = {
  high: "مرتفع",
  medium: "متوسط",
  low: "منخفض",
};

const confidenceWeight: Record<string, number> = { high: 3, medium: 2, low: 1 };

function evidencePriority(item: EvidenceItem) {
  return confidenceWeight[item.confidence] ?? 0;
}

function socialPriority(app: SocialApp) {
  const weights: Record<string, number> = {
    verified_present: 4,
    verified_absent: 3,
    privacy_blocked: 2,
    provider_unavailable: 1,
    not_checked: 0,
  };
  return weights[app.status] ?? 0;
}

function checkPriority(status?: string) {
  return status === "inconsistent" || status === "conflict" ? 3 : status === "insufficient" ? 2 : status === "consistent" ? 1 : 0;
}

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
  const [sessionToken, setSessionToken] = useState<string | null>(null);
  const [target, setTarget] = useState("");
  const [result, setResult] = useState<LookupResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);
  const [aiResult, setAiResult] = useState<{ status?: string; provider?: string | null; model?: string | null; message?: string; analysis?: { summary?: string; evidence_interpretation?: string; cautions?: string[]; next_steps?: string[]; claims?: Array<{ claim?: string; support?: string[]; confidence?: string }> }; verification?: { verified?: boolean; risk?: string; message?: string } } | null>(null);
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
      const session = await response.json() as { session_token?: string };
      if (!session.session_token) throw new Error("تعذر إنشاء جلسة Aliali.");
      setSessionToken(session.session_token);
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
    setAiResult(null);

    try {
      const response = await fetch(API_BASE + "/api/v1/lookup", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Aliali-Session": sessionToken ?? "", "X-Telegram-Init-Data": webApp.initData },
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

  async function runAiAnalysis() {
    if (!result?.analysis_id || !API_BASE || !webApp?.initData) {
      setError("أجرِ البحث أولًا للحصول على لقطة الأدلة.");
      return;
    }
    setAiBusy(true);
    setError("");
    try {
      const response = await fetch(API_BASE + "/api/v1/ai-analysis", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Aliali-Session": sessionToken ?? "", "X-Telegram-Init-Data": webApp.initData },
        body: JSON.stringify({ init_data: webApp.initData, analysis_id: result.analysis_id }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "تعذر تنفيذ التحليل الذكي.");
      setAiResult(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر تنفيذ التحليل الذكي.");
    } finally {
      setAiBusy(false);
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

            <div className="executive-card">
              <div className="executive-title">🧠 الملخص التنفيذي</div>
              <strong>{result.executive_summary?.headline ?? "تحليل قائم على الأدلة"}</strong>
              <div className="executive-grid">
                <span>صلاحية الرقم <b>{result.executive_summary?.validity === "confirmed" ? "مؤكدة" : "غير مؤكدة"}</b></span>
                <span>الهوية <b>{result.executive_summary?.identity === "high" ? "مرتفعة" : result.executive_summary?.identity === "medium" ? "مدعومة" : "غير مثبتة"}</b></span>
                <span>الموقع المباشر <b>{result.executive_summary?.live_location === "available" ? "متاح" : "غير متاح"}</b></span>
                <span>تغطية الأدلة <b>{result.executive_summary?.evidence_coverage ?? 0}%</b></span>
              </div>
            </div>

            <nav className="result-nav" aria-label="أقسام نتيجة التحليل">
              <a href="#overview">الخلاصة</a>
              <a href="#identity">الهوية</a>
              <a href="#social">التواصل</a>
              <a href="#facts">الرقم</a>
              <a href="#analysis">التحليل</a>
            </nav>

            <div id="overview" className="quick-summary">
              <div><span>الحالة</span><strong>{result.valid ? "صالحة" : "غير مؤكدة"}</strong></div>
              <div><span>الدولة</span><strong>{result.country_name ?? result.region_code ?? "—"}</strong></div>
              <div><span>النوع</span><strong>{result.line_type ?? "—"}</strong></div>
              <div><span>الأدلة</span><strong>{result.evidence?.items?.length ?? 0}</strong></div>
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

            <div className="result-actions">
              <button type="button" className="secondary-action" onClick={() => { setResult(null); setAiResult(null); setError(""); window.scrollTo({ top: 0, behavior: "smooth" }); }}>
                ↻ بحث جديد
              </button>
              <button type="button" className="secondary-action" onClick={() => navigator.clipboard.writeText(result.international ?? result.target)}>
                ⧉ نسخ الرقم
              </button>
            </div>

            <div id="identity" className="section-title">👤 هوية صاحب الرقم</div>
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

            <div id="social" className="section-title">📱 تطبيقات التواصل</div>
            <div className="grid">
              {[...(result.social_apps ?? [])].sort((a, b) => socialPriority(b) - socialPriority(a)).map((app) => (
                <article className="row" key={app.id}>
                  <strong>{app.name}</strong>
                  <span>{app.status === "verified_present" ? "ارتباط مؤكد" : app.status === "verified_absent" ? "ارتباط غير مثبت من المصدر" : app.status === "privacy_blocked" ? "الحماية بالخصوصية تمنع التحقق" : app.status === "provider_unavailable" ? "لا يوجد مزود تحقق مصرح متاح" : "لم يتم التحقق"}</span>
                  <small>{app.note}</small>
                  {app.source && <small>المصدر: {app.source}</small>}
                  {app.checked_at && <small>آخر تحقق: {new Date(app.checked_at).toLocaleString("ar")}</small>}
                </article>
              ))}
            </div>
            <div className="identity-note"><span>🛡️</span><div><strong>حالة التحقق</strong><p>ظهور المنصة في القائمة لا يعني وجود حساب. لا تُعرض نتيجة ارتباط إلا بدليل من مزود مصرح أو ارتباط عام موثق، وتُفصل حالات عدم التحقق عن النفي.</p></div></div>

            <div className="section-title">🌍 الموقع الجغرافي المستنتج من بيانات الرقم</div>
            <div className="location-evidence">
              <div className="location-evidence-head">
                <div>
                  <strong>{result.location_profile?.geographic_area ?? result.location_profile?.country ?? "غير متوفر"}</strong>
                  <span>
                    {result.location_profile?.precision === "PHONE_AREA"
                      ? "دقة: منطقة جغرافية مرتبطة بالرقم"
                      : result.location_profile?.precision === "PHONE_REGION"
                        ? "دقة: منطقة ترقيم"
                        : "دقة: غير معروفة"}
                  </span>
                </div>
                <span className="location-status">{result.location_profile?.precision ?? "UNKNOWN"}</span>
              </div>
              <div className="grid">
                <Field label="الدولة" value={result.location_profile?.country ?? result.country_name ?? result.region_code} />
                <Field label="رمز المنطقة" value={result.location_profile?.region_code ?? result.region_code} ltr />
                <Field label="المنطقة المرتبطة بالرقم" value={result.location_profile?.geographic_area ?? result.location} />
                <Field label="المناطق الزمنية" value={(result.location_profile?.timezones ?? result.timezones ?? []).join(", ")} ltr />
              </div>
              <div className="location-explanation">{result.location_profile?.note ?? "لا توجد إشارة جغرافية كافية."}</div>
              <div className="location-source">المصدر: {result.location_profile?.source ?? result.source ?? "—"} · تحقق: {result.location_profile?.checked_at ? new Date(result.location_profile.checked_at).toLocaleString("ar") : "—"}</div>
            </div>

            <div id="facts" className="section-title">📱 خصائص الرقم</div>
            <div className="grid">
              <Field label="نوع الخط" value={result.line_type} />
              <Field label="الصيغة الدولية" value={result.international} ltr />
              <Field label="E.164" value={result.e164} ltr />
              <Field label="الصيغة المحلية" value={result.national} ltr />
              <Field label="شركة الاتصالات" value={result.carrier} />
            </div>

            <details className="advanced-panel">
              <summary>
                <span><b>🔐 الأدلة والتفاصيل المتقدمة</b><small>المصادر، الاتساق، وسجل التحقق</small></span>
                <strong>عرض التفاصيل</strong>
              </summary>
              <div id="evidence" className="section-title">🔐 الأدلة التي بُنيت عليها النتيجة</div>
              <div className="evidence-list">
                {[...(result.evidence?.items ?? [])].sort((a, b) => evidencePriority(b) - evidencePriority(a) || a.field.localeCompare(b.field)).map((item) => (
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

              <div className="section-title">🧾 سجل أدلة التحقق الاجتماعي</div>
              <div className="evidence-list">
                {(result.social_evidence_ledger ?? []).map((entry) => (
                  <article className="evidence-item" key={entry.provider_id}>
                    <div>
                      <strong>{entry.provider_id}</strong>
                      <span>{entry.method ?? "—"} · {entry.note ?? "—"}</span>
                    </div>
                    <div className="evidence-value">
                      <b>{entry.verification === "verified" ? "موثق" : "غير موثق"}</b>
                      <em>{entry.source ?? "لا يوجد مصدر"}</em>
                    </div>
                  </article>
                ))}
              </div>

              <div className="section-title">🧩 مصفوفة الأدلة والتحقق</div>
              <div className="source-card">
                <div className="source-row"><span>الأدلة المؤكدة</span><strong>{result.coverage?.confirmed ?? 0}</strong></div>
                <div className="source-row"><span>الأدلة المدعومة</span><strong>{result.coverage?.supported ?? 0}</strong></div>
                <div className="source-row"><span>المعلومات غير المعروفة</span><strong>{result.coverage?.unknown ?? 0}</strong></div>
                <div className="source-row"><span>طريقة التقييم</span><strong>{result.coverage?.method ?? "—"}</strong></div>
              </div>

              <div className="section-title">⚖️ فحص الاتساق والتعارضات</div>
              <div className="evidence-list">
                {[...(result.consistency_checks ?? [])].sort((a, b) => checkPriority(b.status) - checkPriority(a.status)).map((check) => (
                  <article className="evidence-item" key={check.id}>
                    <div><strong>{check.label}</strong><span>{check.details}</span></div>
                    <div className="evidence-value"><b>{check.status}</b></div>
                  </article>
                ))}
              </div>

              <div className="section-title">🗂️ سجل المصادر</div>
              <div className="evidence-list">
                {[...(result.source_registry ?? [])].sort((a, b) => (a.status === "available" ? 1 : 0) - (b.status === "available" ? 1 : 0)).reverse().map((source) => (
                  <article className="evidence-item" key={source.id}>
                    <div><strong>{source.name}</strong><span>{source.type} · {source.status}</span></div>
                    <div className="evidence-value"><b>{source.retrieved_at ? new Date(source.retrieved_at).toLocaleString("ar") : "—"}</b></div>
                  </article>
                ))}
              </div>


            </details>

            <div id="analysis" className="section-title">🤖 طبقة التحليل الذكي</div>
            <div className="identity-note">
              <span>🧠</span>
              <div>
                <strong>تحليل AI اختياري قائم على الأدلة</strong>
                <p>{aiResult?.message ?? result.ai_analysis?.message}</p>
                <button className="copy" type="button" onClick={() => void runAiAnalysis()} disabled={aiBusy}>
                  {aiBusy ? "جارٍ التحليل الذكي…" : "تشغيل التحليل الذكي"}
                </button>
              </div>
            </div>
            {aiResult?.analysis ? (
              <div className="source-card">
                <div className="source-row"><span>الملخص</span><strong>{aiResult.analysis.summary}</strong></div>
                <div className="source-row"><span>قراءة الأدلة</span><strong>{aiResult.analysis.evidence_interpretation}</strong></div>
                <div className="source-row"><span>التحذيرات</span><strong>{(aiResult.analysis.cautions ?? []).join(" · ")}</strong></div>
                <div className="source-row"><span>الخطوات التالية</span><strong>{(aiResult.analysis.next_steps ?? []).join(" · ")}</strong></div>
                <div className="source-row"><span>التحقق</span><strong>{aiResult.verification?.verified ? "✓ اجتاز التحقق" : "✕ مرفوض"}</strong></div>
                <div className="source-row"><span>مخاطر التحليل</span><strong>{aiResult.verification?.risk ?? "—"}</strong></div>
                <div className="source-row"><span>المزود / النموذج</span><strong>{aiResult.provider ?? "محرك حتمي"} / {aiResult.model ?? "—"}</strong></div>
              </div>
            ) : null}

            {aiResult?.analysis?.claims?.length ? (
              <>
                <div className="section-title">🔗 خريطة الدليل ← الاستنتاج</div>
                <div className="evidence-list">
                  {aiResult.analysis.claims.map((claim, index) => (
                    <article className="evidence-item" key={claim.claim ?? index}>
                      <div>
                        <strong>{claim.claim ?? "استنتاج غير مسمى"}</strong>
                        <span>الأدلة الداعمة: {(claim.support ?? []).join(", ") || "لا يوجد"}</span>
                      </div>
                      <div className="evidence-value">
                        <b>{claim.confidence ?? "unknown"}</b>
                        <em>{(claim.support ?? []).length ? "مدعوم" : "غير مدعوم"}</em>
                      </div>
                    </article>
                  ))}
                </div>
              </>
            ) : null}

            <div className="section-title">📌 ما نعرفه وما لا نعرفه</div>
            <div className="known-unknown">
              <div><strong>نعرف</strong><ul>{(result.known ?? []).map((item) => <li key={item}>{item}</li>)}</ul></div>
              <div><strong>لا نعرف</strong><ul>{(result.unknown ?? []).map((item) => <li key={item}>{item}</li>)}</ul></div>
            </div>

            <div className="section-title">🕒 الخط الزمني</div>
            <div className="timeline">
              {(result.timeline ?? []).map((event) => (
                <div className="timeline-item" key={event.event}>
                  <span>{event.at ? new Date(event.at).toLocaleTimeString("ar") : "—"}</span>
                  <strong>{event.label}</strong>
                </div>
              ))}
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
