import { useState, useEffect } from "react"
import { useAppStore } from "../store/appStore"
import axios from "axios"
import { IconMorning, IconAfternoon, IconEvening, IconShield, IconAvoid } from "../components/ui/icons"

const MEALS = [
  { id: "morning",   label: "Breakfast", icon: <IconMorning size={18} /> },
  { id: "afternoon", label: "Lunch",     icon: <IconAfternoon size={18} /> },
  { id: "evening",   label: "Dinner",    icon: <IconEvening size={18} /> },
  { id: "immunity",  label: "Immunity",  icon: <IconShield size={18} /> },
  { id: "avoid",     label: "Avoid",     icon: <IconAvoid size={18} /> },
]

function FoodRow({ item, isAvoid }) {
  return (
    <div className="w-full flex items-center p-4 ref-card mb-4 group cursor-pointer border border-transparent hover:border-[#F4D160] transition-all">
      <div className="w-20 h-20 rounded-[16px] bg-[#F3F3F3] shrink-0 overflow-hidden mr-5 shadow-[inset_0_2px_4px_rgba(0,0,0,0.05)]">
        {item.image_url && <img src={item.image_url} className="w-full h-full object-cover" alt="food" />}
      </div>
      
      <div className="flex-1 min-w-0 flex flex-col justify-center">
        <div className="flex flex-wrap items-center gap-2 md:gap-3 mb-1.5">
          <h2 className="text-[16px] md:text-[18px] font-medium text-[#1A1A1A] truncate tracking-tight">
            {item.name_en}
          </h2>
          {item.local_name && (
            <span className="text-[10px] md:text-[11px] bg-[#2B2B2B] text-white px-2.5 py-0.5 rounded-full font-medium tracking-wide">
              {item.local_name}
            </span>
          )}
          {isAvoid && (
            <span className="text-[10px] md:text-[11px] bg-[#E8E8E8] text-[#1A1A1A] px-2.5 py-0.5 rounded-full font-medium tracking-wide ml-auto">
              Skip this
            </span>
          )}
          {!isAvoid && item.season_fit && (
             <div className="flex items-center gap-1 ml-auto">
               <span className="w-1.5 h-1.5 rounded-full bg-[#F4D160]"></span>
               <span className="text-[11px] md:text-[12px] text-[#A0A0A0] font-medium">{item.season_fit}/10 Fit</span>
             </div>
          )}
        </div>
        
        <p className="text-[13px] md:text-[14px] text-[#737373] leading-relaxed line-clamp-2 pr-2 md:pr-4">
          {isAvoid ? item.reason_en : item.benefit_en}
        </p>
      </div>
    </div>
  )
}

export default function Diet() {
  const ageMode       = useAppStore((s) => s.ageMode)
  const currentSeason = useAppStore((s) => s.currentSeason)

  const [activeMeal, setActiveMeal] = useState("morning")
  const [items,      setItems]      = useState([])
  const [loading,    setLoading]    = useState(false)

  const season  = currentSeason?.id ?? "grind"
  const isAvoid = activeMeal === "avoid"

  useEffect(() => {
    if (!season) return
    setLoading(true)
    axios.get(`/api/diet/${season}/${ageMode}/${activeMeal}`)
      .then((r) => setItems(r.data.data ?? []))
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [season, ageMode, activeMeal])

  return (
    <div className="flex flex-col w-full min-h-screen pb-12">
      
      <div className="flex flex-col md:flex-row gap-6 px-4 lg:px-6 mt-4">
        
        {/* Left Sidebar - Pill Tabs (Scrolls horizontally on mobile, sticky vertically on desktop) */}
        <div className="w-full md:w-56 shrink-0 md:sticky md:top-32 h-fit z-30 bg-[#F3EDE1]/90 md:bg-transparent pb-2 md:pb-0">
          <div className="flex md:flex-col gap-2 md:gap-3 overflow-x-auto no-scrollbar">
            <span className="hidden md:block text-[13px] font-medium text-[#737373] px-4 mb-2 uppercase tracking-wider">Categories</span>
            {MEALS.map((m) => {
              const active = activeMeal === m.id
              return (
                <button
                  key={m.id}
                  onClick={() => setActiveMeal(m.id)}
                  className={`flex items-center gap-2 md:gap-3 px-4 md:px-5 py-2.5 md:py-3.5 rounded-full whitespace-nowrap transition-all ${
                    active ? 'bg-[#2B2B2B] text-white shadow-[0_10px_20px_-10px_rgba(0,0,0,0.3)]' : 'bg-white md:bg-transparent border md:border-transparent border-[#E8E8E8] text-[#4A4A4A] hover:bg-[#EBE5D9]'
                  }`}
                >
                  <div className={active ? 'text-[#F4D160]' : 'text-[#A0A0A0]'}>{m.icon}</div>
                  <span className="font-medium text-[14px] md:text-[15px]">{m.label}</span>
                </button>
              )
            })}
          </div>
        </div>

        {/* Right Content - Full Page Scroll */}
        <div className="flex-1 flex flex-col">
          {loading ? (
            <div className="animate-pulse space-y-4">
              {[1, 2, 3, 4].map(i => <div key={i} className="h-28 bg-white/50 rounded-[32px] w-full"></div>)}
            </div>
          ) : items.length === 0 ? (
            <div className="flex-1 flex items-center justify-center text-[#A0A0A0] font-medium text-[16px] py-20">
              No dietary advice available right now.
            </div>
          ) : (
            <div className="flex flex-col">
              {items.map((item) => (
                <FoodRow key={item.id} item={item} isAvoid={isAvoid} />
              ))}
            </div>
          )}
        </div>
        
      </div>
    </div>
  )
}
