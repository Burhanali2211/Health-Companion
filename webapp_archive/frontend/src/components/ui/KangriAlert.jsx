import { useAppStore } from "../../store/appStore"

export default function KangriAlert() {
  const ctx = useAppStore((s) => s.healthContext)

  if (!ctx?.kangri_alert) return null

  return (
    <div className="flex items-center gap-3 px-3 py-2 rounded-[12px] bg-red-50/80 backdrop-blur border border-red-200 shrink-0">
      <div className="w-7 h-7 rounded-lg bg-red-100 flex items-center justify-center shrink-0">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#C0392B" strokeWidth="2.5" strokeLinecap="round">
          <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/>
          <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
      </div>
      <span className="text-[13px] text-red-800 flex-1 leading-snug font-latin font-medium">
        Kangri Warning — CO gas is dangerous, keep the room ventilated
      </span>
      <span className="text-[10px] font-bold tracking-widest uppercase text-red-700 bg-red-200/50 px-2 py-1 rounded shrink-0 font-latin">
        CO Alert
      </span>
    </div>
  )
}
