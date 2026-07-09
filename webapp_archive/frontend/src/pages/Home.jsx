import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useAppStore }  from "../store/appStore"
import { useSeasonData } from "../hooks/useSeasonData"
import KangriAlert from "../components/ui/KangriAlert"
import { IconTherm, IconMic, IconRun, IconDiet } from "../components/ui/icons"

// Helper for simple clothes advice (Empathetic)
function getWearAdvice(seasonId) {
  if (seasonId === "chilla_kalan") return "It's freezing today. Keep your Pheran close and Kangri safe.";
  if (seasonId === "chilla_khurd") return "Still quite cold out there. A warm Pheran & Scarf will help.";
  if (seasonId === "chilla_bachha") return "The cold is leaving us. A light sweater is perfect.";
  if (seasonId === "grind") return "It's quite warm today. Keep it light with cotton clothes.";
  return "Wear comfortable local clothes suitable for today.";
}

// Helper for simple diet advice (Empathetic)
function getDietAdvice(seasonId) {
  if (seasonId === "chilla_kalan") return "Warm yourself up with some Harissa and a hot cup of Nun Chai.";
  if (seasonId === "chilla_khurd") return "Some warm soup or beans will feel great today.";
  if (seasonId === "chilla_bachha") return "Time to welcome fresh vegetables back to your plate.";
  if (seasonId === "grind") return "Stay hydrated and avoid heavy meats today.";
  return "Enjoy some healthy local food today.";
}

export default function Home() {
  const navigate      = useNavigate()
  const ageMode       = useAppStore((s) => s.ageMode)
  const currentSeason = useAppStore((s) => s.currentSeason)
  const healthContext = useAppStore((s) => s.healthContext)
  const district      = useAppStore((s) => s.district)
  useSeasonData()

  const temp     = healthContext?.temp_min != null ? healthContext.temp_min : "—"
  const dayNum   = healthContext?.day_number ?? 1
  const seasonName = currentSeason?.name_en ?? "Season"
  
  // Calculate season progress (assuming Chilla Kalan is 40 days for simple math)
  const totalDays = seasonName.includes("Kalan") ? 40 : 20;
  const progressPercent = Math.min(100, Math.round((dayNum / totalDays) * 100));
  
  const safetyScore = temp < 0 ? 30 : (temp < 10 ? 60 : 90);
  const wearAdvice = getWearAdvice(currentSeason?.id)
  const dietAdvice = getDietAdvice(currentSeason?.id)

  // Quick Timer State
  const initialTime = 120; // 2 minutes
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

  const timerProgress = ((initialTime - timeLeft) / initialTime) * 100;

  const toggleTimer = () => {
    if (timeLeft === 0) setTimeLeft(initialTime);
    setIsPlaying(!isPlaying);
  }

  // Daily Checklist State (Pain-Point Focus)
  const [checklist, setChecklist] = useState([
    { id: 1, title: "Relieve Joint Pain", time: "2 min stretch", icon: <IconRun size={16}/>, checked: false },
    { id: 2, title: "I feel very cold", time: "Quick warm up", icon: <IconTherm size={16}/>, checked: false },
    { id: 3, title: "Sore throat", time: "Home remedy", icon: <IconDiet size={16}/>, checked: false },
    { id: 4, title: "Talk to AI Companion", time: "Voice chat", icon: <IconMic size={16}/>, checked: false },
  ]);

  const toggleCheck = (id) => {
    setChecklist(checklist.map(item => item.id === id ? { ...item, checked: !item.checked } : item));
  }

  const completedTasks = checklist.filter(t => t.checked).length;

  return (
    <div className="flex flex-col w-full min-h-screen pb-12 px-4 lg:px-8 pt-6">
      
      {/* --- Welcome Text (Pure English) --- */}
      <h1 className="text-[48px] font-medium text-[#1A1A1A] tracking-tight mb-8 pl-2 leading-none">
        Good Morning
      </h1>

      {/* --- Main 2-Column Psychological Layout --- */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-8 pb-8">
        
        {/* --- Primary Column (Hero & Action) - 60% Width --- */}
        <div className="col-span-1 lg:col-span-7 flex flex-col gap-8">
           
           {/* 1. Hero Weather Card */}
           <div className="h-[340px] w-full rounded-[40px] overflow-hidden relative shadow-[0_20px_60px_-15px_rgba(0,0,0,0.15)] group">
             <img src="https://images.unsplash.com/photo-1548685913-fe6678babe8d?q=80&w=800&auto=format&fit=crop" className="w-full h-full object-cover transition-transform duration-1000 group-hover:scale-105" alt="Season" />
             <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent"></div>
             
             <div className="absolute top-6 right-6 flex flex-col items-end gap-2">
                <span className="text-[56px] leading-none text-white font-light tracking-tighter drop-shadow-lg">{temp}°</span>
                <div className={`px-4 py-1.5 rounded-full backdrop-blur-md border text-[13px] font-medium ${temp < 0 ? 'bg-blue-500/20 text-blue-100 border-blue-400/30' : 'bg-emerald-500/20 text-emerald-100 border-emerald-400/30'}`}>
                  {temp < 0 ? "Freezing Today" : "Weather Good"}
                </div>
             </div>
             
             <div className="absolute bottom-8 left-8 right-8 flex flex-col md:flex-row items-start md:items-end justify-between gap-4">
                <div>
                  <h3 className="text-white text-[32px] font-medium tracking-tight mb-1">{seasonName}</h3>
                  <p className="text-white/80 text-[15px] flex items-center gap-2">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>
                    {district ?? "Kashmir Valley"}
                  </p>
                </div>
                <div className="px-5 py-2 rounded-full border border-white/30 bg-black/30 backdrop-blur-md text-white text-[15px] font-medium shadow-sm">
                  Severity: {currentSeason?.severity ?? "Moderate"}
                </div>
             </div>
           </div>

           {/* 2. Action Center: How are you feeling? (Dark High-Contrast Card to draw eye) */}
           <div className="flex-1 min-h-[300px] ref-card-dark p-8 flex flex-col relative overflow-hidden">
              <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full blur-3xl -mr-20 -mt-20"></div>
              
              <div className="flex justify-between items-end mb-8 pb-4 border-b border-white/10 relative z-10">
                <h3 className="text-white text-[24px] font-medium tracking-tight">How are you feeling?</h3>
                <span className="text-[20px] font-medium text-[#F4D160] leading-none bg-[#F4D160]/10 px-4 py-1.5 rounded-full">
                  {completedTasks}/{checklist.length} solved
                </span>
              </div>

              <div className="flex-1 overflow-y-auto pr-2 flex flex-col gap-4 relative z-10">
                {checklist.map((task) => (
                  <button key={task.id} onClick={() => toggleCheck(task.id)} className="flex items-center justify-between group text-left w-full outline-none bg-white/5 hover:bg-white/10 p-4 rounded-2xl transition-all border border-white/5 hover:border-white/20">
                    <div className="flex items-center gap-5">
                      <div className={`w-12 h-12 rounded-full flex items-center justify-center transition-colors shadow-sm ${task.checked ? 'bg-[#F4D160] text-[#1A1A1A]' : 'bg-white/10 text-white group-hover:bg-white/20'}`}>
                        {task.icon}
                      </div>
                      <div className="flex flex-col">
                        <span className={`text-[16px] font-medium mb-1 transition-colors ${task.checked ? 'text-white/40 line-through' : 'text-white'}`}>{task.title}</span>
                        <span className="text-[#A0A0A0] text-[13px]">{task.time}</span>
                      </div>
                    </div>
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center border-2 transition-all ${task.checked ? 'bg-[#F4D160] border-[#F4D160] text-[#1A1A1A] scale-110' : 'border-[#737373] scale-100'}`}>
                      {task.checked && <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>}
                    </div>
                  </button>
                ))}
              </div>
           </div>
           
        </div>

        {/* --- Secondary Column (Ambient/Widgets) - 40% Width --- */}
        <div className="col-span-1 lg:col-span-5 flex flex-col gap-6">
           
           {/* Today's Advice Box */}
           <div className="ref-card p-6 lg:p-8 flex flex-col border border-[#F0F0F0]">
             <div className="flex items-center justify-between pb-4 border-b border-[#F0F0F0] mb-6">
               <span className="text-[#1A1A1A] text-[18px] font-medium tracking-tight">Today's Focus</span>
               <div className="flex items-center gap-2 bg-[#F9F9F9] border border-[#E8E8E8] rounded-full px-3 py-1.5 shadow-sm">
                 <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                 <span className="text-[12px] font-bold text-[#4A4A4A]">Score: {safetyScore}</span>
               </div>
             </div>
             
             <div className="flex flex-col gap-6">
               <div className="flex items-start gap-4">
                 <div className="w-12 h-12 rounded-full border border-[#E8E8E8] flex items-center justify-center bg-[#F9F9F9] shrink-0 text-[#1A1A1A]">
                    <IconDiet size={20} />
                 </div>
                 <div className="flex flex-col pt-0.5">
                   <span className="text-[#1A1A1A] text-[15px] font-bold mb-1">Today's Kitchen</span>
                   <span className="text-[#737373] text-[14px] leading-relaxed">{dietAdvice}</span>
                 </div>
               </div>

               <div className="flex items-start gap-4">
                 <div className="w-12 h-12 rounded-full border border-[#E8E8E8] flex items-center justify-center bg-[#F9F9F9] shrink-0 text-[#1A1A1A]">
                    <IconRun size={20} />
                 </div>
                 <div className="flex flex-col pt-0.5">
                   <span className="text-[#1A1A1A] text-[15px] font-bold mb-1">Stay Warm</span>
                   <span className="text-[#737373] text-[14px] leading-relaxed">{temp < 0 ? "Stay indoors today. It's too cold outside." : "It's safe to take a walk outside today."}</span>
                 </div>
               </div>
             </div>
           </div>

           {/* Simple Timeline Card */}
           <div className="ref-card p-6 lg:p-8 flex flex-col relative border border-[#F0F0F0]">
              <h3 className="text-[#1A1A1A] text-[18px] font-medium mb-2 tracking-tight">Season Timeline</h3>
              <div className="flex items-baseline justify-between mb-8">
                <div className="flex items-baseline gap-2">
                  <span className="text-[32px] font-light tracking-tight text-[#1A1A1A]">{dayNum} / {totalDays}</span>
                  <span className="text-[13px] text-[#737373] font-medium">Days</span>
                </div>
                <div className="flex items-center gap-2">
                   <span className="text-[13px] font-bold text-[#A0A0A0] uppercase tracking-wider">{progressPercent}%</span>
                </div>
              </div>
              
              <div className="w-full h-[60px] relative overflow-visible">
                {/* Smooth Line Graph SVG */}
                <svg className="absolute inset-0 w-full h-full overflow-visible" preserveAspectRatio="none" viewBox="0 0 100 100">
                  <defs>
                    <linearGradient id="lineGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#F4D160" stopOpacity="0.4"/>
                      <stop offset="100%" stopColor="#F4D160" stopOpacity="0.0"/>
                    </linearGradient>
                  </defs>
                  <path d="M 0 100 L 0 60 C 20 60, 30 80, 50 50 C 70 20, 80 40, 100 30 L 100 100 Z" fill="url(#lineGrad)" />
                  <path d="M 0 60 C 20 60, 30 80, 50 50 C 70 20, 80 40, 100 30" fill="none" stroke="#F4D160" strokeWidth="4" strokeLinecap="round" className="drop-shadow-sm" />
                  {/* Progress Indicator Dot */}
                  <circle cx={progressPercent} cy={100 - progressPercent * 0.7} r="5" fill="#F4D160" className="drop-shadow-[0_0_8px_rgba(244,209,96,0.8)]" />
                </svg>
                
                {/* X-Axis Labels */}
                <div className="absolute bottom-[-24px] left-0 w-full flex justify-between px-1">
                  <span className="text-[11px] text-[#A0A0A0] font-medium">Start</span>
                  <span className="text-[11px] text-[#1A1A1A] font-bold">Now</span>
                  <span className="text-[11px] text-[#A0A0A0] font-medium">End</span>
                </div>
              </div>
           </div>

           {/* 2-Column Row for smaller widgets */}
           <div className="grid grid-cols-2 gap-6">
             {/* Quick Breathing Timer */}
             <div className="ref-card p-6 flex flex-col relative border border-[#F0F0F0] items-center justify-center">
                <h3 className="text-[#1A1A1A] text-[16px] font-medium mb-4 w-full text-center">Breathe</h3>
                <div className="relative flex items-center justify-center mb-6">
                   <svg className="w-24 h-24 transform -rotate-90">
                     <circle cx="50%" cy="50%" r="45%" stroke="#F3F3F3" strokeWidth="8" fill="transparent" strokeDasharray="4 6" />
                     <circle cx="50%" cy="50%" r="45%" stroke="#F4D160" strokeWidth="8" fill="transparent" strokeDasharray="283%" strokeDashoffset={`${283 * (1 - timerProgress/100)}%`} className="transition-all duration-1000 linear" strokeLinecap="round"/>
                   </svg>
                   <div className="absolute flex flex-col items-center">
                     <span className="text-[20px] font-medium text-[#1A1A1A] tracking-tighter leading-none mb-1">{formatTime(timeLeft)}</span>
                   </div>
                </div>
                <button onClick={toggleTimer} className="w-full py-2.5 rounded-full bg-[#2B2B2B] text-white text-[13px] font-medium hover:bg-[#3A3A3A] transition-colors shadow-sm">
                  {isPlaying ? "Pause" : (timeLeft < initialTime ? "Resume" : "Start")}
                </button>
             </div>

             {/* What to Wear Card */}
             <div className="ref-card p-6 flex flex-col border border-[#F0F0F0] justify-between">
                <h3 className="text-[#1A1A1A] text-[16px] font-medium mb-3">Wear Today</h3>
                <p className="text-[13px] text-[#737373] leading-relaxed mb-4 line-clamp-3">
                  {wearAdvice}
                </p>
                <div className="flex flex-col gap-2 w-full mt-auto">
                   <div className="flex items-center justify-between bg-[#F9F9F9] rounded-lg p-2 border border-[#E8E8E8]">
                     <span className="text-[11px] text-[#A0A0A0] font-medium">Outer</span>
                     <span className="text-[#1A1A1A] text-[12px] font-medium">Pheran</span>
                   </div>
                   <div className="flex items-center justify-between bg-[#2B2B2B] rounded-lg p-2">
                     <span className="text-[11px] text-[#A0A0A0] font-medium">Inner</span>
                     <span className="text-white text-[12px] font-medium">Thermal</span>
                   </div>
                </div>
             </div>
           </div>

        </div>

      </div>
      <div className="shrink-0"><KangriAlert /></div>
    </div>
  )
}

