import { useOnlineStatus } from "../../hooks/useOnlineStatus"

export default function NetworkBadge() {
  const isOnline = useOnlineStatus()

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "5px",
        padding: "4px 10px",
        borderRadius: "100px",
        background: isOnline ? "#F0FDF4" : "#FFFBEB",
        border: `1px solid ${isOnline ? "#BBF7D0" : "#FDE68A"}`,
      }}
    >
      <div
        style={{
          width: "6px",
          height: "6px",
          borderRadius: "50%",
          background: isOnline ? "#22C55E" : "#F59E0B",
          animation: "pulse_dot 2s ease-in-out infinite",
          flexShrink: 0,
        }}
      />
      <span
        style={{
          fontSize: "11px",
          fontFamily: "Inter, sans-serif",
          fontWeight: 500,
          color: isOnline ? "#16A34A" : "#D97706",
          lineHeight: 1,
        }}
      >
        {isOnline ? "Online" : "Offline"}
      </span>
    </div>
  )
}
