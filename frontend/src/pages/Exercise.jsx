import { useState, useEffect } from "react"
import { useAppStore } from "../store/appStore"
import axios from "axios"
import { IconIndoor, IconOutdoor, IconBreathing, IconMorning } from "../components/ui/icons"

const TYPES = [
  { id: "indoor",    label: "Indoor",    icon: <IconIndoor size={18} /> },
  { id: "outdoor",   label: "Outdoor",   icon: <IconOutdoor size={18} /> },
  { id: "breathing", label: "Breathing", icon: <IconBreathing size={18} /> },
  { id: "morning",   label: "Morning",   icon: <IconMorning size={18} /> },
]

function ExerciseCard({ item }) {
  return (
    <div className="flex flex-col ref-card h-full hover:shadow-[0_20px_40px_-10px_rgba(0,0,0,0.1)] transition-shadow cursor-pointer overflow-hidden p-2">
      <div className="h-28 md:h-32 w-full rounded-[20px] md:rounded-[24px] bg-[#F3F3F3] shrink-0 overflow-hidden relative">
        {item.image_url ? (
           <img src={item.image_url} alt={item.name_en} className="w-full h-full object-cover" />
        ) : (
           <div className="w-full h-full bg-[#E8E1D5]"></div>
        )}
        {item.duration_min && (
          <div className="absolute top-2 right-2 md:top-3 md:right-3 bg-black/40 backdrop-blur-md text-white text-[10px] md:text-[11px] px-2 md:px-2.5 py-0.5 md:py-1 rounded-full font-medium tracking-wide">
            {item.duration_min} min
          </div>
        )}
      </div>
      <div className="p-3 md:p-4 flex flex-col justify-between flex-1">
        <div>
          <h2 className="font-medium text-[15px] md:text-[16px] text-[#1A1A1A] leading-snug mb-1.5 line-clamp-2">{item.name_en}</h2>
        </div>
        <p className="text-[12px] md:text-[13px] text-[#737373] line-clamp-2 leading-relaxed mt-1 md:mt-2">{item.science}</p>
      </div>
    </div>
  )
}

function OutdoorLock({ reasonEn }) {
  return (
    <div className="w-full h-full flex flex-col items-center justify-center p-6 md:p-8 text-center ref-card bg-white/50 backdrop-blur-sm">
      <div className="text-[24px] md:text-[28px] mb-3">🔒</div>
      <h3 className="font-medium text-[16px] md:text-[18px] text-[#1A1A1A] mb-2">Outdoor Locked</h3>
      <p className="text-[13px] md:text-[14px] text-[#737373] max-w-md">{reasonEn || "It is not safe for outdoor activities right now."}</p>
    </div>
  )
}

function WorkoutPlayer({ item, onClose }) {
  const isTimeBased = !!item.duration_min;
  const initialTime = isTimeBased ? item.duration_min * 60 : 0;
  
  const [isPlaying, setIsPlaying] = useState(false);
  const [timeLeft, setTimeLeft] = useState(initialTime);

  useEffect(() => {
    let timer;
    if (isPlaying && timeLeft > 0) {
      timer = setInterval(() => setTimeLeft(t => t - 1), 1000);
    } else if (timeLeft === 0 && isPlaying) {
      setIsPlaying(false);
    }
    return () => clearInterval(timer);
  }, [isPlaying, timeLeft]);

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const progress = isTimeBased ? ((initialTime - timeLeft) / initialTime) * 100 : 0;

  return (
    <div className="fixed inset-0 z-[100] bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 md:p-6 animate-in fade-in duration-200">
      <div className="w-full max-w-2xl ref-card p-6 md:p-8 flex flex-col md:flex-row relative overflow-hidden bg-white max-h-[90vh] overflow-y-auto">
        <button onClick={onClose} className="absolute top-4 right-4 md:top-6 md:right-6 w-8 h-8 md:w-10 md:h-10 rounded-full border border-[#E8E8E8] flex items-center justify-center hover:bg-[#F9F9F9] transition-colors z-10 text-[#1A1A1A]">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M18 6L6 18M6 6l12 12"/></svg>
        </button>
        
        {/* Left info side */}
        <div className="w-full md:w-1/2 md:pr-6 md:border-r border-[#F0F0F0] flex flex-col mb-8 md:mb-0">
          <div className="h-40 md:h-48 w-full rounded-[20px] md:rounded-[24px] bg-[#F3F3F3] mb-4 md:mb-6 overflow-hidden shrink-0">
             {item.image_url && <img src={item.image_url} className="w-full h-full object-cover" />}
          </div>
          <h1 className="font-medium text-[20px] md:text-[24px] text-[#1A1A1A] mb-2 md:mb-3 leading-tight tracking-tight pr-8 md:pr-0">{item.name_en}</h1>
          <p className="text-[13px] md:text-[14px] text-[#737373] leading-relaxed">{item.science}</p>
        </div>

        {/* Right Timer side */}
        <div className="w-full md:w-1/2 flex flex-col items-center justify-center md:pl-6 shrink-0">
          <h3 className="text-[#1A1A1A] text-[16px] md:text-[18px] font-medium mb-6 md:mb-8">Time Tracker</h3>
          
          <div className="self-center relative flex items-center justify-center mb-6 md:mb-8">
             <svg className="w-40 h-40 md:w-48 md:h-48 transform -rotate-90">
               <circle cx="50%" cy="50%" r="45%" stroke="#F3F3F3" strokeWidth="12" fill="transparent" strokeDasharray="4 6" />
               <circle 
                 cx="50%" cy="50%" r="45%" stroke="#F4D160" strokeWidth="12" fill="transparent" 
                 strokeDasharray="283%" strokeDashoffset={`${283 * (1 - progress/100)}%`} 
                 className="transition-all duration-1000 linear" strokeLinecap="round"
               />
             </svg>
             <div className="absolute flex flex-col items-center">
               <span className="text-[32px] md:text-[40px] font-light text-[#1A1A1A] tracking-tighter leading-none mb-1">
                 {isTimeBased ? formatTime(timeLeft) : item.sets}
               </span>
               <span className="text-[11px] md:text-[12px] text-[#737373] font-medium">
                 {isTimeBased ? "Remaining" : `Sets of ${item.reps}`}
               </span>
             </div>
          </div>

          <div className="flex items-center justify-center w-full mt-auto">
            {isTimeBased ? (
              <button onClick={() => setIsPlaying(!isPlaying)} className="w-36 md:w-40 h-12 md:h-14 rounded-full bg-[#2B2B2B] flex items-center justify-center gap-2 md:gap-3 text-white shadow-sm hover:bg-[#3A3A3A] transition-all active:scale-95">
                {isPlaying ? (
                  <><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M6 4h4v16H6zm8 0h4v16h-4z"/></svg> <span className="font-medium text-[14px] md:text-[15px]">Pause</span></>
                ) : (
                  <><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M5 3l14 9-14 9V3z"/></svg> <span className="font-medium text-[14px] md:text-[15px]">{timeLeft < initialTime ? "Resume" : "Start"}</span></>
                )}
              </button>
            ) : (
              <button onClick={onClose} className="w-36 md:w-40 h-12 md:h-14 rounded-full bg-[#2B2B2B] text-white flex items-center justify-center text-[14px] md:text-[15px] font-medium hover:bg-[#3A3A3A] transition-all active:scale-95">
                Finish Sets
              </button>
            )}
          </div>
        </div>

      </div>
    </div>
  )
}

export default function Exercise() {
  const ageMode       = useAppStore((s) => s.ageMode)
  const currentSeason = useAppStore((s) => s.currentSeason)
  
  const [activeType, setActiveType] = useState("indoor")
  const [items,      setItems]      = useState([])
  const [loading,    setLoading]    = useState(false)
  const [lockInfo,   setLockInfo]   = useState(null)
  const [selectedItem, setSelectedItem] = useState(null)

  const season = currentSeason?.id ?? "grind"

  useEffect(() => {
    setLoading(true)
    axios.get(`/api/exercise/${season}/${ageMode}/${activeType}`)
      .then((r) => {
        setItems(r.data.data ?? [])
        setLockInfo(r.data.outdoor_locked ? { reason_en: r.data.lock_reason_en } : null)
      })
      .catch(() => { setItems([]); setLockInfo(null) })
      .finally(() => setLoading(false))
  }, [season, ageMode, activeType])

  const isLocked = activeType === "outdoor" && lockInfo

  return (
    <div className="flex flex-col w-full min-h-screen pb-12">
      
      <div className="flex flex-col md:flex-row gap-6 px-4 lg:px-6 mt-4">
        
        {/* Left Sidebar - Pill Tabs (Scrolls horizontally on mobile, sticky vertically on desktop) */}
        <div className="w-full md:w-56 shrink-0 md:sticky md:top-32 h-fit z-30 bg-[#F3EDE1]/90 md:bg-transparent pb-2 md:pb-0">
          <div className="flex md:flex-col gap-2 md:gap-3 overflow-x-auto no-scrollbar">
            <span className="hidden md:block text-[13px] font-medium text-[#737373] px-4 mb-2 uppercase tracking-wider">Categories</span>
            {TYPES.map((t) => {
              const active = activeType === t.id
              return (
                <button
                  key={t.id}
                  onClick={() => setActiveType(t.id)}
                  className={`flex items-center gap-2 md:gap-3 px-4 md:px-5 py-2.5 md:py-3.5 rounded-full whitespace-nowrap transition-all ${
                    active ? 'bg-[#2B2B2B] text-white shadow-[0_10px_20px_-10px_rgba(0,0,0,0.3)]' : 'bg-white md:bg-transparent border md:border-transparent border-[#E8E8E8] text-[#4A4A4A] hover:bg-[#EBE5D9]'
                  }`}
                >
                  <div className={active ? 'text-[#F4D160]' : 'text-[#A0A0A0]'}>{t.icon}</div>
                  <span className="font-medium text-[14px] md:text-[15px]">{t.label}</span>
                </button>
              )
            })}
          </div>
        </div>

        {/* Right Content - Grid */}
        <div className="flex-1 flex flex-col">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 md:gap-5">
            {loading ? (
              [1, 2, 3, 4].map(i => (
                <div key={i} className="h-48 md:h-64 bg-white/50 rounded-[24px] animate-pulse"></div>
              ))
            ) : isLocked ? (
              <div className="col-span-full h-48 md:h-64"><OutdoorLock reasonEn={lockInfo.reason_en} /></div>
            ) : items.length === 0 ? (
              <div className="col-span-full flex items-center justify-center h-48 md:h-64 text-[#A0A0A0] font-medium text-[16px]">No exercises available right now.</div>
            ) : (
              items.map((item) => (
                <div key={item.id} onClick={() => setSelectedItem(item)} className="h-56 md:h-64">
                  <ExerciseCard item={item} />
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {selectedItem && (
        <WorkoutPlayer item={selectedItem} onClose={() => setSelectedItem(null)} />
      )}
    </div>
  )
}
