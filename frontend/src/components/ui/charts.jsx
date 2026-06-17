export function WaveTemp({ color }) {
  return (
    <svg viewBox="0 0 80 24" fill="none" className="w-full h-6">
      <path
        d="M0 18 Q10 16 16 14 Q26 9 36 13 Q46 17 54 11 Q62 6 70 9 Q75 11 80 8"
        stroke={color} strokeWidth="1.5" strokeLinecap="round" fill="none"
      />
    </svg>
  )
}

export function WaveECG({ color }) {
  return (
    <svg viewBox="0 0 80 24" fill="none" className="w-full h-6">
      <path
        d="M0 16 L16 16 L18 7 L20 21 L22 12 L24 16 L46 16 L48 7 L50 21 L52 12 L54 16 L80 16"
        stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none"
      />
    </svg>
  )
}

export function WaveStep({ color }) {
  return (
    <svg viewBox="0 0 80 24" fill="none" className="w-full h-6">
      <path
        d="M0 20 L14 20 L14 14 L28 14 L28 8 L44 8 L44 12 L58 12 L58 16 L72 16 L72 18 L80 18"
        stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none"
      />
    </svg>
  )
}

export function ArcProgress({ pct, color, size = 48 }) {
  const r   = 18
  const cx  = 24
  const cy  = 24
  const circ = 2 * Math.PI * r
  const dash = (pct / 100) * circ
  return (
    <svg width={size} height={size} viewBox="0 0 48 48">
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#E2E8F0" strokeWidth="4"/>
      <circle
        cx={cx} cy={cy} r={r} fill="none"
        stroke={color} strokeWidth="4"
        strokeDasharray={`${dash} ${circ}`}
        strokeLinecap="round"
        transform="rotate(-90 24 24)"
      />
    </svg>
  )
}
