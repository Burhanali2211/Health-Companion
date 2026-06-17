import { useAppStore } from "../../store/appStore"

const SEVERITY = {
  extreme:  { bg: "#EFF6FF", border: "#BFDBFE", text: "#1D4ED8", dot: "#3B82F6" },
  high:     { bg: "#EFF6FF", border: "#BFDBFE", text: "#1D4ED8", dot: "#3B82F6" },
  moderate: { bg: "#F0FDF4", border: "#A7F3D0", text: "#065F46", dot: "#10B981" },
  mild:     { bg: "#F0FDF4", border: "#A7F3D0", text: "#065F46", dot: "#10B981" },
  pleasant: { bg: "#ECFDF5", border: "#6EE7B7", text: "#065F46", dot: "#34D399" },
  warm:     { bg: "#FFFBEB", border: "#FDE68A", text: "#92400E", dot: "#F59E0B" },
}

export default function SeasonCard() {
  const ctx       = useAppStore((s) => s.healthContext)
  const district  = useAppStore((s) => s.district)

  if (!ctx) {
    return (
      <div
        style={{
          height: "76px",
          borderRadius: "14px",
          background: "#F8FAFC",
          border: "1px solid #E2E8F0",
          animation: "pulse_dot 1.5s ease-in-out infinite",
        }}
      />
    )
  }

  const { season, day_number, district: dist, temp_min, temp_max } = ctx
  const c = SEVERITY[season.severity] ?? SEVERITY.warm

  return (
    <div
      style={{
        borderRadius: "14px",
        background: c.bg,
        border: `1px solid ${c.border}`,
        padding: "12px 14px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexShrink: 0,
      }}
    >
      <div>
        <div
          className="urdu"
          style={{ fontSize: "22px", fontWeight: 700, color: "#1E293B", lineHeight: 1.2 }}
        >
          {season.name_ur}
        </div>
        <div
          style={{
            fontSize: "11px",
            color: "#64748B",
            marginTop: "3px",
            fontFamily: "Inter, sans-serif",
          }}
        >
          {season.name_en} · Day {day_number} · {dist?.name ?? district}
        </div>
      </div>

      <div style={{ textAlign: "right" }}>
        <div
          style={{
            fontSize: "26px",
            fontWeight: 800,
            color: "#1E293B",
            fontFamily: "Inter, sans-serif",
            lineHeight: 1,
          }}
        >
          {temp_min}°<span style={{ color: "#94A3B8", fontSize: "18px" }}>/</span>{temp_max}°
        </div>
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "4px",
            marginTop: "5px",
            padding: "2px 8px",
            borderRadius: "100px",
            background: c.border,
          }}
        >
          <div
            style={{
              width: "5px",
              height: "5px",
              borderRadius: "50%",
              background: c.dot,
            }}
          />
          <span
            style={{
              fontSize: "9px",
              fontWeight: 700,
              color: c.text,
              fontFamily: "Inter, sans-serif",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            {season.severity}
          </span>
        </div>
      </div>
    </div>
  )
}
