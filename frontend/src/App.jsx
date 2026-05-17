import { useState, useEffect, createContext, useContext, useCallback } from "react";

// ─────────────────────────────────────────────
// API client
// ─────────────────────────────────────────────
const API_BASE = process.env.REACT_APP_API_BASE || "/api/v1";

async function apiFetch(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

// ─────────────────────────────────────────────
// App Context
// ─────────────────────────────────────────────
const AppContext = createContext(null);
function useApp() { return useContext(AppContext); }

// ─────────────────────────────────────────────
// Icon components (SVG inline)
// ─────────────────────────────────────────────
const Icon = {
  Upload: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17,8 12,3 7,8"/><line x1="12" y1="3" x2="12" y2="15"/>
    </svg>
  ),
  Fire: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
      <path d="M12 2c0 6-8 8-8 14a8 8 0 0 0 16 0c0-5-4-9-4-14-1 2-1 4-3 5-1-1.5 0-3.5-1-5z"/>
    </svg>
  ),
  Calendar: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
    </svg>
  ),
  BookOpen: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
    </svg>
  ),
  AlertTriangle: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
  ),
  Grid: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
      <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
    </svg>
  ),
  Check: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" width="14" height="14">
      <polyline points="20,6 9,17 4,12"/>
    </svg>
  ),
  X: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" width="14" height="14">
      <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
    </svg>
  ),
  Zap: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
      <polygon points="13,2 3,14 12,14 11,22 21,10 12,10 13,2"/>
    </svg>
  ),
};

// ─────────────────────────────────────────────
// Workload Heatmap — clear calendar view
// ─────────────────────────────────────────────
function WorkloadHeatmap({ heatmapData }) {
  const today = new Date();
  const startDate = new Date(today);
  startDate.setMonth(startDate.getMonth() - 5);

  const weeks = [];
  const cursor = new Date(startDate);
  cursor.setDate(cursor.getDate() - cursor.getDay() + 1);

  for (let w = 0; w < 26; w++) {
    const week = [];
    for (let d = 0; d < 7; d++) {
      const dateStr = cursor.toISOString().split("T")[0];
      week.push({ date: dateStr, load: heatmapData[dateStr] || 0 });
      cursor.setDate(cursor.getDate() + 1);
    }
    weeks.push(week);
  }

  const getColor = (load) => {
    if (load === 0) return "#e2e8f0";
    if (load <= 2) return "#93c5fd";
    if (load <= 4) return "#60a5fa";
    if (load <= 6) return "#fbbf24";
    if (load <= 9) return "#f97316";
    return "#ef4444";
  };

  const dayLabels = ["M", "T", "W", "T", "F", "S", "S"];

  return (
    <div style={{ overflowX: "auto", padding: "4px 0" }}>
      <div style={{ display: "flex", gap: "3px", alignItems: "flex-start" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "3px", marginRight: "6px", paddingTop: "24px" }}>
          {dayLabels.map((d, i) => (
            <div key={i} style={{ width: "16px", height: "16px", fontSize: "11px", color: "#64748b", lineHeight: "16px", textAlign: "center", fontWeight: 600 }}>{d}</div>
          ))}
        </div>
        {weeks.map((week, wi) => {
          const monthLabel = new Date(week[0].date).toLocaleDateString("en-US", { month: "short" });
          const showMonth = wi === 0 || new Date(week[0].date).getDate() <= 7;
          return (
            <div key={wi} style={{ display: "flex", flexDirection: "column", gap: "3px" }}>
              <div style={{ height: "20px", fontSize: "11px", color: "#475569", fontWeight: 600 }}>
                {showMonth ? monthLabel : ""}
              </div>
              {week.map((cell, di) => (
                <div
                  key={di}
                  title={`${cell.date}: load ${cell.load}`}
                  style={{
                    width: "16px",
                    height: "16px",
                    borderRadius: "4px",
                    backgroundColor: getColor(cell.load),
                    cursor: cell.load > 0 ? "pointer" : "default",
                  }}
                />
              ))}
            </div>
          );
        })}
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "16px", flexWrap: "wrap" }}>
        <span style={{ fontSize: "12px", color: "#64748b", fontWeight: 500 }}>Workload:</span>
        {[0, 2, 4, 6, 9, 12].map(v => (
          <div key={v} style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <div style={{ width: "14px", height: "14px", borderRadius: "4px", backgroundColor: getColor(v) }} />
            <span style={{ fontSize: "11px", color: "#64748b" }}>{v === 0 ? "none" : v}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// Weekly Bar Chart — simple and readable
// ─────────────────────────────────────────────
function WeeklyBarChart({ weeklyWorkload, threshold = 7 }) {
  const weeks = Object.entries(weeklyWorkload || {}).slice(-12);
  if (!weeks.length) return <div style={{ color: "#64748b", fontSize: "14px", padding: "24px 0" }}>No workload data yet</div>;

  const maxLoad = Math.max(...weeks.map(([, v]) => v.total), threshold + 1);

  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: "8px", height: "140px", padding: "0 8px" }}>
      {weeks.map(([week, data]) => {
        const pct = (data.total / maxLoad) * 100;
        const isCritical = data.total >= 12;
        const isWarning = data.total >= threshold && !isCritical;
        const barColor = isCritical ? "#ef4444" : isWarning ? "#f59e0b" : "#3b82f6";
        const shortWeek = week.replace(/\d{4}-/, "");
        return (
          <div key={week} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: "6px", height: "100%" }}>
            <div style={{ flex: 1, width: "100%", display: "flex", alignItems: "flex-end" }}>
              <div
                title={`${week}: load ${data.total}`}
                style={{
                  width: "100%",
                  height: `${pct}%`,
                  minHeight: "6px",
                  backgroundColor: barColor,
                  borderRadius: "6px 6px 0 0",
                }}
              />
            </div>
            <div style={{ fontSize: "11px", color: "#475569", fontWeight: 600 }}>{shortWeek}</div>
          </div>
        );
      })}
    </div>
  );
}

// ─────────────────────────────────────────────
// Upload Panel
// ─────────────────────────────────────────────
function UploadPanel({ onUploaded }) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [formData, setFormData] = useState({ course_name: "", course_code: "", professor: "", semester: "" });

  const handleFile = async (file) => {
    if (!file) return;
    if (!formData.course_name.trim()) {
      setError("Please enter a course name before uploading.");
      return;
    }
    setUploading(true);
    setResult(null);
    setError(null);

    const fd = new FormData();
    fd.append("file", file);
    Object.entries(formData).forEach(([k, v]) => { if (v) fd.append(k, v); });

    try {
      const res = await fetch(`${API_BASE}/upload-syllabus/`, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Upload failed");
      setResult(data);
      onUploaded && onUploaded();
    } catch (e) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      {/* Form fields */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "16px" }}>
        {[
          ["course_name", "Course Name *", "e.g. Introduction to CS"],
          ["course_code", "Course Code", "e.g. CS101"],
          ["professor", "Professor", "e.g. Dr. Smith"],
          ["semester", "Semester", "e.g. Spring 2026"],
        ].map(([key, label, placeholder]) => (
          <div key={key}>
            <label style={{ display: "block", fontSize: "12px", color: "#475569", fontWeight: 600, marginBottom: "6px" }}>{label}</label>
            <input
              type="text"
              placeholder={placeholder}
              value={formData[key]}
              onChange={e => setFormData(prev => ({ ...prev, [key]: e.target.value }))}
              style={{
                width: "100%", padding: "10px 12px", borderRadius: "8px",
                background: "#fff", border: "1px solid #e2e8f0",
                color: "#1e293b", fontSize: "14px", outline: "none",
                boxSizing: "border-box",
              }}
            />
          </div>
        ))}
      </div>

      {/* Drop zone */}
      <div
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]); }}
        onClick={() => document.getElementById("syllabus-file-input").click()}
        style={{
          border: `2px dashed ${dragging ? "#2563eb" : "#cbd5e1"}`,
          borderRadius: "12px",
          padding: "32px 20px",
          textAlign: "center",
          cursor: "pointer",
          transition: "all 0.2s",
          background: dragging ? "#eff6ff" : "#f8fafc",
        }}
      >
        <input
          id="syllabus-file-input"
          type="file"
          accept=".pdf,.txt,.docx"
          style={{ display: "none" }}
          onChange={e => handleFile(e.target.files[0])}
        />
        <div style={{ marginBottom: "10px", opacity: 0.5 }}>
          <svg viewBox="0 0 48 48" fill="none" stroke="#3b82f6" strokeWidth="1.5" width="42" height="42" style={{ margin: "0 auto" }}>
            <path d="M24 4L24 32M14 14L24 4L34 14" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M8 36v4a4 4 0 004 4h24a4 4 0 004-4v-4" strokeLinecap="round"/>
          </svg>
        </div>
        {uploading ? (
          <div style={{ color: "#3b82f6", fontSize: "14px" }}>
            <span style={{ animation: "pulse 1s infinite" }}>⏳ Processing syllabus...</span>
          </div>
        ) : (
          <>
            <div style={{ color: "#1e293b", fontSize: "14px", fontWeight: 600 }}>Drop your syllabus here</div>
            <div style={{ color: "#64748b", fontSize: "12px", marginTop: "4px" }}>PDF, TXT, or DOCX — up to 10MB</div>
          </>
        )}
      </div>

      {/* Result */}
      {result && (
        <div style={{ marginTop: "16px", padding: "16px", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: "10px" }}>
          <div style={{ color: "#15803d", fontSize: "14px", fontWeight: 600, marginBottom: "8px" }}>Processed successfully</div>
          <div style={{ display: "flex", gap: "24px" }}>
            {[
              ["Events found", result.events_extracted],
              ["Conflicts detected", result.conflicts_detected],
            ].map(([label, val]) => (
              <div key={label}>
                <div style={{ color: "#64748b", fontSize: "12px" }}>{label}</div>
                <div style={{ color: "#1e293b", fontSize: "20px", fontWeight: 700 }}>{val ?? "—"}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div style={{ marginTop: "16px", padding: "16px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "10px" }}>
          <div style={{ color: "#dc2626", fontSize: "14px" }}>{error}</div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
// Conflict Card — clear and scannable
// ─────────────────────────────────────────────
function ConflictCard({ conflict }) {
  const isCritical = conflict.severity === "critical";
  return (
    <div style={{
      padding: "16px",
      borderRadius: "12px",
      background: isCritical ? "#fef2f2" : "#fffbeb",
      border: `1px solid ${isCritical ? "#fecaca" : "#fde68a"}`,
      marginBottom: "12px",
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
        <span style={{ fontSize: "15px", fontWeight: 700, color: "#1e293b" }}>
          {conflict.week_key || conflict.date}
        </span>
        <span style={{
          padding: "4px 10px", borderRadius: "8px", fontSize: "11px", fontWeight: 700,
          background: isCritical ? "#ef4444" : "#f59e0b",
          color: "#fff",
        }}>
          {isCritical ? "CRITICAL" : "WARNING"}
        </span>
      </div>
      <div style={{ fontSize: "14px", color: "#475569", marginBottom: "8px" }}>
        Load <strong style={{ color: "#1e293b" }}>{conflict.total_load}</strong>
        <span style={{ color: "#94a3b8" }}> / threshold </span>
        <strong style={{ color: "#1e293b" }}>{conflict.threshold}</strong>
      </div>
      {conflict.courses_affected?.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
          {conflict.courses_affected.map(c => (
            <span key={c} style={{ padding: "4px 10px", borderRadius: "8px", fontSize: "12px", fontWeight: 600, background: "#f1f5f9", color: "#475569" }}>{c}</span>
          ))}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
// Event Type Badge
// ─────────────────────────────────────────────
const EVENT_COLORS = {
  final: "#dc2626", midterm: "#ea580c", exam: "#d97706",
  quiz: "#ca8a04", presentation: "#7c3aed", project: "#2563eb",
  assignment: "#0891b2", homework: "#059669", lab: "#0d9488", reading: "#64748b",
};

function EventBadge({ type }) {
  const color = EVENT_COLORS[type] || "#64748b";
  return (
    <span style={{
      padding: "4px 10px", borderRadius: "8px", fontSize: "11px", fontWeight: 700,
      background: `${color}18`, color: color, textTransform: "uppercase", letterSpacing: "0.04em",
    }}>
      {type}
    </span>
  );
}

// ─────────────────────────────────────────────
// Stat Card — simple and readable
// ─────────────────────────────────────────────
function StatCard({ label, value, color = "#2563eb", icon }) {
  return (
    <div style={{
      background: "#fff",
      border: "1px solid #e2e8f0",
      borderRadius: "12px",
      padding: "20px",
      flex: 1,
      minWidth: "120px",
      boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
    }}>
      <div style={{ fontSize: "12px", color: "#64748b", fontWeight: 600, marginBottom: "8px", letterSpacing: "0.02em" }}>{label}</div>
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <span style={{ fontSize: "28px", fontWeight: 800, color, fontVariantNumeric: "tabular-nums" }}>{value}</span>
        <span style={{ color }}>{icon}</span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// Section Header
// ─────────────────────────────────────────────
function SectionHeader({ title, icon, action }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
      <h2 style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "#1e293b", display: "flex", alignItems: "center", gap: "8px" }}>
        <span style={{ color: "#64748b" }}>{icon}</span>
        {title}
      </h2>
      {action}
    </div>
  );
}

// ─────────────────────────────────────────────
// Card wrapper
// ─────────────────────────────────────────────
function Card({ children, style = {} }) {
  return (
    <div style={{
      background: "#fff",
      border: "1px solid #e2e8f0",
      borderRadius: "12px",
      padding: "24px",
      boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
      ...style,
    }}>
      {children}
    </div>
  );
}

// ─────────────────────────────────────────────
// Main App
// ─────────────────────────────────────────────
export default function BengalRAWR() {
  const [tab, setTab] = useState("dashboard");
  const [dashboard, setDashboard] = useState(null);
  const [events, setEvents] = useState([]);
  const [conflicts, setConflicts] = useState([]);
  const [weeklyWorkload, setWeeklyWorkload] = useState({});
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setApiError(null);
    try {
      const [dash, evts, conf, weekly] = await Promise.all([
        apiFetch("/dashboard/"),
        apiFetch("/events/"),
        apiFetch("/conflicts/"),
        apiFetch("/dashboard/weekly-workload/"),
      ]);
      setDashboard(dash);
      setEvents(evts);
      setConflicts(conf);
      setWeeklyWorkload(weekly.weekly_workload || {});
    } catch (e) {
      setApiError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: <Icon.Grid /> },
    { id: "upload", label: "Upload", icon: <Icon.Upload /> },
    { id: "events", label: "Events", icon: <Icon.Calendar /> },
    { id: "conflicts", label: "Conflicts", icon: <Icon.AlertTriangle /> },
  ];

  return (
    <div style={{
      minHeight: "100vh",
      background: "#f1f5f9",
      color: "#1e293b",
      fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif",
    }}>
      <style>{`
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #e2e8f0; }
        ::-webkit-scrollbar-thumb { background: #94a3b8; border-radius: 6px; }
        @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
        input:focus { border-color: #3b82f6 !important; box-shadow: 0 0 0 2px rgba(59,130,246,0.2); }

        .statsGrid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
        .dashboardTwoCol { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }

        @media (max-width: 980px) {
          .statsGrid { grid-template-columns: repeat(2, 1fr); }
          .dashboardTwoCol { grid-template-columns: 1fr; }
        }
        @media (max-width: 520px) {
          .statsGrid { grid-template-columns: 1fr; }
        }
      `}</style>

      {/* Header */}
      <header style={{
        borderBottom: "1px solid #e2e8f0",
        padding: "0 24px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        height: "56px",
        position: "sticky",
        top: 0,
        background: "#fff",
        boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
        zIndex: 100,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div style={{
            width: "36px", height: "36px", borderRadius: "10px",
            background: "linear-gradient(135deg, #2563eb, #7c3aed)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "18px",
          }}>🐯</div>
          <div>
            <div style={{ fontSize: "16px", fontWeight: 700, color: "#1e293b" }}>Bengal Rawr</div>
            <div style={{ fontSize: "11px", color: "#64748b", marginTop: "-1px" }}>Academic conflict detector</div>
          </div>
        </div>

        <nav style={{ display: "flex", gap: "6px" }}>
          {navItems.map(item => (
            <button
              key={item.id}
              onClick={() => setTab(item.id)}
              style={{
                display: "flex", alignItems: "center", gap: "8px",
                padding: "8px 16px", borderRadius: "8px", border: "none",
                cursor: "pointer", fontSize: "13px", fontWeight: 600,
                fontFamily: "inherit", transition: "all 0.15s",
                background: tab === item.id ? "#2563eb" : "transparent",
                color: tab === item.id ? "#fff" : "#475569",
              }}
            >
              {item.icon}
              {item.label}
              {item.id === "conflicts" && conflicts.length > 0 && (
                <span style={{
                  background: "#ef4444", color: "#fff", fontSize: "11px",
                  borderRadius: "10px", padding: "2px 6px", fontWeight: 700,
                }}>
                  {conflicts.length}
                </span>
              )}
            </button>
          ))}
        </nav>

        <button
          onClick={fetchAll}
          style={{
            padding: "8px 14px", borderRadius: "8px", border: "1px solid #e2e8f0",
            background: "#fff", color: "#475569", cursor: "pointer",
            fontSize: "12px", fontWeight: 600, fontFamily: "inherit", display: "flex", alignItems: "center", gap: "6px",
          }}
        >
          <Icon.Zap /> Refresh
        </button>
      </header>

      {/* Main content */}
      <main style={{ padding: "24px", maxWidth: "1200px", margin: "0 auto", animation: "fadeIn 0.3s ease" }}>

        {loading && (
          <div style={{ textAlign: "center", padding: "60px 0", color: "#64748b" }}>
            <div style={{ fontSize: "13px", animation: "pulse 1.5s infinite" }}>⏳ Loading data...</div>
          </div>
        )}

        {apiError && !loading && (
          <div style={{ padding: "16px 20px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "12px", marginBottom: "24px" }}>
            <div style={{ color: "#dc2626", fontSize: "14px", fontWeight: 500 }}>
              API error: {apiError}. Make sure the backend is running on port 8000.
            </div>
          </div>
        )}

        {/* ──────────── DASHBOARD TAB ──────────── */}
        {!loading && tab === "dashboard" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>

            {/* Summary stats */}
            <div className="statsGrid">
              <StatCard label="Courses" value={dashboard?.total_courses ?? 0} color="#2563eb" icon={<Icon.BookOpen />} />
              <StatCard label="Events" value={dashboard?.total_events ?? 0} color="#7c3aed" icon={<Icon.Calendar />} />
              <StatCard label="Conflict weeks" value={dashboard?.total_conflicts ?? 0} color="#f59e0b" icon={<Icon.AlertTriangle />} />
              <StatCard label="Critical weeks" value={dashboard?.critical_weeks ?? 0} color="#ef4444" icon={<Icon.Fire />} />
            </div>

            {/* Heatmap — full width, main focus */}
            <Card>
              <SectionHeader title="Workload heatmap (exams, presentations, projects, assignments)" icon={<Icon.Grid />} />
              <WorkloadHeatmap heatmapData={dashboard?.heatmap_data || {}} />
            </Card>

            {/* Two columns: Weekly workload + Upcoming events | Conflicts */}
            <div className="dashboardTwoCol">
              <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
                <Card>
                  <SectionHeader title="Weekly workload" icon={<Icon.Zap />} />
                  <WeeklyBarChart weeklyWorkload={weeklyWorkload} />
                  <div style={{ display: "flex", gap: "16px", marginTop: "12px", flexWrap: "wrap" }}>
                    {[["#3b82f6", "Normal"], ["#f59e0b", "Warning (≥7)"], ["#ef4444", "Critical (≥12)"]].map(([c, l]) => (
                      <div key={l} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <div style={{ width: "12px", height: "12px", borderRadius: "4px", background: c }} />
                        <span style={{ fontSize: "12px", color: "#64748b", fontWeight: 500 }}>{l}</span>
                      </div>
                    ))}
                  </div>
                </Card>
                <Card>
                  <SectionHeader title="Upcoming events" icon={<Icon.Calendar />} />
                  {(dashboard?.upcoming_events || []).length === 0 ? (
                    <div style={{ color: "#64748b", fontSize: "14px" }}>No upcoming events in the next 30 days.</div>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                      {dashboard.upcoming_events.map(evt => (
                        <div key={evt.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", padding: "14px", background: "#f8fafc", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
                          <div>
                            <div style={{ fontSize: "14px", fontWeight: 600, color: "#1e293b", marginBottom: "6px" }}>{evt.title}</div>
                            <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
                              <EventBadge type={evt.event_type} />
                              <span style={{ fontSize: "12px", color: "#64748b", fontWeight: 600 }}>{evt.course_code}</span>
                            </div>
                          </div>
                          <div style={{ textAlign: "right" }}>
                            <div style={{ fontSize: "13px", fontWeight: 600, color: "#475569" }}>{evt.date}</div>
                            <div style={{ fontSize: "12px", color: "#2563eb", fontWeight: 600, marginTop: "2px" }}>Load {evt.workload}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>
              </div>
              <Card>
                <SectionHeader title="Conflict alerts" icon={<Icon.AlertTriangle />} />
                {(dashboard?.recent_conflicts || []).length === 0 ? (
                  <div style={{ color: "#059669", fontSize: "14px", fontWeight: 500 }}>No conflicts detected.</div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "0" }}>
                    {dashboard.recent_conflicts.map(c => <ConflictCard key={c.id} conflict={c} />)}
                  </div>
                )}
              </Card>
            </div>
          </div>
        )}

        {/* ──────────── UPLOAD TAB ──────────── */}
        {!loading && tab === "upload" && (
          <div style={{ maxWidth: "600px" }}>
            <Card>
              <SectionHeader title="Upload Syllabus" icon={<Icon.Upload />} />
              <UploadPanel onUploaded={fetchAll} />
            </Card>
          </div>
        )}

        {/* ──────────── EVENTS TAB ──────────── */}
        {!loading && tab === "events" && (
          <Card>
            <SectionHeader
              title={`All Events (${events.length})`}
              icon={<Icon.Calendar />}
            />
            {events.length === 0 ? (
              <div style={{ color: "#64748b", fontSize: "14px", padding: "24px 0" }}>No events yet. Upload a syllabus to get started.</div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px" }}>
                  <thead>
                    <tr>
                      {["Course", "Title", "Type", "Date", "Load", "Verified"].map(h => (
                        <th key={h} style={{ textAlign: "left", padding: "12px 14px", color: "#64748b", fontWeight: 600, borderBottom: "2px solid #e2e8f0", fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.04em" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {events.map(evt => (
                      <tr key={evt.id} style={{ borderBottom: "1px solid #e2e8f0" }}
                        onMouseEnter={e => { e.currentTarget.style.background = "#f8fafc"; }}
                        onMouseLeave={e => { e.currentTarget.style.background = "transparent"; }}
                      >
                        <td style={{ padding: "12px 14px", color: "#2563eb", fontWeight: 600 }}>{evt.course_code || "—"}</td>
                        <td style={{ padding: "12px 14px", color: "#1e293b", maxWidth: "280px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{evt.title}</td>
                        <td style={{ padding: "12px 14px" }}><EventBadge type={evt.event_type} /></td>
                        <td style={{ padding: "12px 14px", color: "#475569" }}>{evt.date || "—"}</td>
                        <td style={{ padding: "12px 14px" }}>
                          <span style={{ color: evt.workload >= 5 ? "#ef4444" : evt.workload >= 3 ? "#f59e0b" : "#2563eb", fontWeight: 700 }}>{evt.workload}</span>
                        </td>
                        <td style={{ padding: "12px 14px" }}>
                          {evt.is_verified ? <span style={{ color: "#059669" }}><Icon.Check /></span> : <span style={{ color: "#94a3b8" }}><Icon.X /></span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        )}

        {/* ──────────── CONFLICTS TAB ──────────── */}
        {!loading && tab === "conflicts" && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px", alignItems: "flex-start" }}>
            <Card>
              <SectionHeader title={`Conflict weeks (${conflicts.length})`} icon={<Icon.Fire />} />
              {conflicts.length === 0 ? (
                <div style={{ color: "#059669", fontSize: "14px", fontWeight: 500, padding: "24px 0" }}>No conflict weeks. Your schedule looks manageable.</div>
              ) : (
                conflicts.map(c => <ConflictCard key={c.id} conflict={c} />)
              )}
            </Card>
            <Card>
              <SectionHeader title="Workload legend" icon={<Icon.Zap />} />
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {[
                  ["Final exam", 8, "#dc2626"],
                  ["Midterm / exam", 5, "#ef4444"],
                  ["Presentation / project", 3, "#f59e0b"],
                  ["Assignment / quiz", 2, "#3b82f6"],
                  ["Homework / lab", 1, "#059669"],
                ].map(([label, weight, color]) => (
                  <div key={label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 14px", background: "#f8fafc", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
                    <span style={{ fontSize: "14px", color: "#1e293b", fontWeight: 500 }}>{label}</span>
                    <span style={{ fontSize: "18px", fontWeight: 800, color }}>{weight}</span>
                  </div>
                ))}
                <div style={{ marginTop: "16px", padding: "14px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "10px" }}>
                  <div style={{ fontSize: "12px", color: "#64748b", marginBottom: "4px" }}>Weekly conflict threshold</div>
                  <div style={{ fontSize: "20px", fontWeight: 700, color: "#ef4444" }}>≥ 7 points</div>
                  <div style={{ fontSize: "12px", color: "#64748b", marginTop: "2px" }}>Critical at ≥ 12 points</div>
                </div>
              </div>
            </Card>
          </div>
        )}

      </main>
    </div>
  );
}
