import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useAppStore }  from "../store/appStore"
import { useSeasonData } from "../hooks/useSeasonData"
import KangriAlert from "../components/ui/KangriAlert"
import { IconTherm, IconMic, IconRun, IconDiet } from "../components/ui/icons"

// Helper for simple clothes advice
function getWearAdvice(seasonId) {
  if (seasonId === "chilla_kalan") return "Heavy Pheran, Thermal inside. Keep Kangri safely.";
  if (seasonId === "chilla_khurd") return "Warm Pheran & Scarf. Weather is still cold.";
  if (seasonId === "chilla_bachha") return "Light Sweater. Cold is leaving.";
  if (seasonId === "grind") return "Cotton clothes. Weather is hot.";
  return "Wear local clothes suitable for today.";
}

// Helper for simple diet advice
function getDietAdvice(seasonId) {
  if (seasonId === "chilla_kalan") return "Eat warm foods like Harissa. Drink Nun Chai.";
  if (seasonId === "chilla_khurd") return "Eat beans and warm soups.";
  if (seasonId === "chilla_bachha") return "Start eating fresh vegetables.";
  if (seasonId === "grind") return "Drink a lot of water. Avoid heavy meat.";
  return "Eat healthy local food.";
}

export default function Home() {
  const navigate      = useNavigate()
  const ageMode       = useAppStore((s) => s.ageMode)
  const currentSeason = useAppStore((s) => s.currentSeason)
  const healthContext = useAppStore((s) => s.healthContext)
  const district      = useAppStore((s) => s.district)
  const isBuzurg      = ageMode === "buzurg"
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

  // Daily Checklist State
  const [checklist, setChecklist] = useState([
    { id: 1, title: "Morning Stretch (5 min)", time: "Morning", icon: <IconRun size={16}/>, checked: false },
    { id: 2, title: "Drink Warm Water", time: "Morning", icon: <IconDiet size={16}/>, checked: false },
    { id: 3, title: "Eat Healthy Lunch", time: "Afternoon", icon: <IconDiet size={16}/>, checked: false },
    { id: 4, title: "Check AI Advice", time: "Anytime", icon: <IconMic size={16}/>, checked: false },
  ]);

  const toggleCheck = (id) => {
    setChecklist(checklist.map(item => item.id === id ? { ...item, checked: !item.checked } : item));
  }

  const completedTasks = checklist.filter(t => t.checked).length;

  return (
    <div className="flex flex-col w-full min-h-screen pb-12 px-4 lg:px-6 pt-4">
      
      {/* --- Welcome Text --- */}
      <h1 className="text-[42px] font-medium text-[#1A1A1A] tracking-tight mb-8 pl-2">
        Welcome in, {isBuzurg ? "Janab" : "Dost"}
      </h1>

      {/* --- Main 3-Column Layout --- */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-5 pb-8">
        
        {/* Left Column (Advice) */}
        <div className="col-span-1 lg:col-span-3 flex flex-col gap-5">
           <div className="h-[280px] w-full rounded-[32px] overflow-hidden relative shadow-[0_10px_40px_-10px_rgba(0,0,0,0.15)] group">
             <img src="https://images.unsplash.com/photo-1548685913-fe6678babe8d?q=80&w=600&auto=format&fit=crop" className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105" alt="Season" />
             <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent"></div>
             <div className="absolute top-5 right-5 flex flex-col items-end gap-2">
                <span className="text-[42px] leading-none text-white font-light tracking-tighter drop-shadow-md">{temp}°</span>
                <div className={`px-3 py-1 rounded-full backdrop-blur-md border text-[11px] font-medium ${temp < 0 ? 'bg-blue-500/20 text-blue-100 border-blue-400/30' : 'bg-emerald-500/20 text-emerald-100 border-emerald-400/30'}`}>
                  {temp < 0 ? "Very Cold" : "Weather Good"}
                </div>
             </div>
             <div className="absolute bottom-6 left-6 right-6 flex items-end justify-between">
                <div>
                  <h3 className="text-white text-[24px] font-medium tracking-tight mb-1">{seasonName}</h3>
                  <p className="text-white/70 text-[13px]">{district ?? "Kashmir Valley"}</p>
                </div>
                <div className="px-4 py-1.5 rounded-full border border-white/30 bg-black/20 backdrop-blur-md text-white text-[14px] font-medium">
                  {currentSeason?.severity ?? "Moderate"}
                </div>
             </div>
           </div>

           <div className="flex-1 ref-card p-6 flex flex-col justify-between min-h-0 overflow-y-auto">
             <div className="flex flex-col gap-4">
               <div className="flex items-center justify-between pb-3 border-b border-[#F0F0F0]">
                 <span className="text-[#1A1A1A] text-[15px] font-medium">Today's Advice</span>
                 <div className="flex items-center gap-1.5 bg-[#F9F9F9] border border-[#E8E8E8] rounded-full px-2 py-1">
                   <svg className="w-3.5 h-3.5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2.5"><path strokeLinecap="round" strokeLinejoin="round" d="M20 7h-9M14 17H5M20 12H9"/></svg>
                   <span className="text-[11px] font-bold text-[#4A4A4A]">Score: {safetyScore}</span>
                 </div>
               </div>
               
               <div className="flex items-start gap-3 pb-3">
                 <div className="w-10 h-10 rounded border border-[#E8E8E8] flex items-center justify-center bg-[#F9F9F9] shrink-0">
                    <IconDiet size={18} />
                 </div>
                 <div className="flex flex-col">
                   <span className="text-[#1A1A1A] text-[14px] font-bold mb-1">Diet Tip</span>
                   <span className="text-[#737373] text-[13px] leading-snug">{dietAdvice}</span>
                 </div>
               </div>

               <div className="flex items-start gap-3 pb-3">
                 <div className="w-10 h-10 rounded border border-[#E8E8E8] flex items-center justify-center bg-[#F9F9F9] shrink-0">
                    <IconRun size={18} />
                 </div>
                 <div className="flex flex-col">
                   <span className="text-[#1A1A1A] text-[14px] font-bold mb-1">Exercise Tip</span>
                   <span className="text-[#737373] text-[13px] leading-snug">{temp < 0 ? "Stay indoors today. Too cold outside." : "It is safe to walk outside today."}</span>
                 </div>
               </div>
             </div>
           </div>
        </div>

        {/* Middle Column (Timeline & Timer) */}
        <div className="col-span-1 lg:col-span-6 flex flex-col gap-5">
           <div className="flex flex-col md:flex-row gap-5 h-auto md:h-[280px]">
             {/* Simple Timeline Card */}
             <div className="flex-1 ref-card p-7 flex flex-col relative">
                <h3 className="text-[#1A1A1A] text-[20px] font-medium mb-1">Season Timeline</h3>
                <div className="flex items-baseline justify-between mb-6">
                  <div className="flex items-baseline gap-2">
                    <span className="text-[28px] font-light tracking-tight text-[#1A1A1A]">{dayNum} / {totalDays}</span>
                    <span className="text-[12px] text-[#737373] leading-tight">Days</span>
                  </div>
                  <div className="flex items-center gap-2">
                     <span className="text-[11px] font-bold text-[#A0A0A0] uppercase tracking-wider">{progressPercent}%</span>
                  </div>
                </div>
                
                <div className="flex-1 w-full relative pb-2 overflow-visible">
                  {/* Smooth Line Graph SVG */}
                  <svg className="absolute inset-0 w-full h-full overflow-visible" preserveAspectRatio="none" viewBox="0 0 100 100">
                    <defs>
                      <linearGradient id="lineGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#F4D160" stopOpacity="0.4"/>
                        <stop offset="100%" stopColor="#F4D160" stopOpacity="0.0"/>
                      </linearGradient>
                    </defs>
                    <path 
                      d="M 0 100 L 0 60 C 20 60, 30 80, 50 50 C 70 20, 80 40, 100 30 L 100 100 Z" 
                      fill="url(#lineGrad)" 
                    />
                    <path 
                      d="M 0 60 C 20 60, 30 80, 50 50 C 70 20, 80 40, 100 30" 
                      fill="none" 
                      stroke="#F4D160" 
                      strokeWidth="3" 
                      strokeLinecap="round" 
                      className="drop-shadow-sm"
                    />
                    {/* Progress Indicator Dot */}
                    <circle 
                      cx={progressPercent} 
                      cy={100 - progressPercent * 0.7} // Approximate position on curve
                      r="4" 
                      fill="#F4D160" 
                      className="drop-shadow-[0_0_8px_rgba(244,209,96,0.8)]"
                    />
                  </svg>
                  
                  {/* X-Axis Labels */}
                  <div className="absolute bottom-[-16px] left-0 w-full flex justify-between px-1">
                    <span className="text-[10px] text-[#A0A0A0] font-medium">Start</span>
                    <span className="text-[10px] text-[#1A1A1A] font-bold">Now</span>
                    <span className="text-[10px] text-[#A0A0A0] font-medium">End</span>
                  </div>
                </div>
             </div>

             {/* Functional Quick Timer */}
             <div className="flex-1 ref-card p-7 flex flex-col relative">
                <button onClick={() => navigate("/exercise")} className="absolute top-6 right-6 px-3 py-1.5 rounded-full border border-[#E8E8E8] text-[11px] font-medium hover:bg-[#F9F9F9] transition-colors">
                  More
                </button>
                <h3 className="text-[#1A1A1A] text-[20px] font-medium mb-auto">Quick Breathing</h3>
                
                <div className="self-center relative flex items-center justify-center mb-auto mt-2">
                   <svg className="w-36 h-36 transform -rotate-90">
                     <circle cx="50%" cy="50%" r="45%" stroke="#F3F3F3" strokeWidth="12" fill="transparent" strokeDasharray="4 6" />
                     <circle cx="50%" cy="50%" r="45%" stroke="#F4D160" strokeWidth="12" fill="transparent" strokeDasharray="283%" strokeDashoffset={`${283 * (1 - timerProgress/100)}%`} className="transition-all duration-1000 linear" strokeLinecap="round"/>
                   </svg>
                   <div className="absolute flex flex-col items-center">
                     <span className="text-[28px] font-light text-[#1A1A1A] tracking-tighter leading-none mb-1">{formatTime(timeLeft)}</span>
                     <span className="text-[11px] text-[#737373] font-medium">Breathe in, out</span>
                   </div>
                </div>

                <div className="flex items-center justify-center w-full mt-4">
                  <button onClick={toggleTimer} className="w-32 h-12 rounded-full bg-[#2B2B2B] flex items-center justify-center gap-2 text-white shadow-sm hover:bg-[#3A3A3A] transition-colors">
                    {isPlaying ? (
                      <><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M6 4h4v16H6zm8 0h4v16h-4z"/></svg> <span className="font-medium text-[14px]">Pause</span></>
                    ) : (
                      <><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M5 3l14 9-14 9V3z"/></svg> <span className="font-medium text-[14px]">{timeLeft < initialTime ? "Resume" : "Start"}</span></>
                    )}
                  </button>
                </div>
             </div>
           </div>

           {/* Routine Calendar */}
           <div className="flex-1 ref-card p-6 flex flex-col min-h-0">
             <div className="flex items-center justify-between mb-4 px-2">
               <span className="text-[18px] font-medium text-[#1A1A1A]">Healthy Routine</span>
               <button onClick={() => window.location.reload()} className="px-4 py-1.5 rounded-full bg-white border border-[#E8E8E8] text-[#1A1A1A] text-[12px] font-medium shadow-sm">Today</button>
             </div>

             <div className="flex-1 relative border-t border-[#F0F0F0] overflow-hidden mt-2">
                <div className="absolute top-4 left-0 w-full flex items-center gap-4">
                  <span className="text-[12px] text-[#A0A0A0] w-14 text-right">8:00 AM</span>
                  <div className="flex-1 bg-[#2B2B2B] rounded-full px-5 py-3 flex items-center justify-between shadow-sm">
                     <div className="flex flex-col">
                       <span className="text-white text-[14px] font-medium mb-0.5">Morning Walk or Stretch</span>
                       <span className="text-[#A0A0A0] text-[12px]">Gets your blood moving.</span>
                     </div>
                  </div>
                </div>
                
                <div className="absolute top-24 left-0 w-full flex items-center gap-4">
                  <span className="text-[12px] text-[#A0A0A0] w-14 text-right">10:00 AM</span>
                  <div className="w-2/3 ml-auto bg-white border border-[#E8E8E8] rounded-full px-5 py-3 flex items-center justify-between shadow-sm">
                     <div className="flex flex-col">
                       <span className="text-[#1A1A1A] text-[14px] font-medium mb-0.5">Drink Warm Water</span>
                       <span className="text-[#737373] text-[12px]">Helps throat and digestion.</span>
                     </div>
                  </div>
                </div>
             </div>
           </div>
        </div>

        {/* Right Column (Clothes & Checklist) */}
        <div className="col-span-1 lg:col-span-3 flex flex-col gap-5">
           
           {/* What to Wear Card */}
           <div className="min-h-[160px] ref-card p-6 flex flex-col justify-between">
              <div className="flex flex-col items-start mb-4">
                <h3 className="text-[#1A1A1A] text-[20px] font-medium mb-2">What to Wear</h3>
                <span className="text-[14px] font-medium text-[#1A1A1A] leading-snug">{wearAdvice}</span>
              </div>
              <div className="flex gap-2 w-full mt-auto">
                 <div className="flex-1 flex flex-col gap-2">
                   <span className="text-[11px] text-[#A0A0A0]">Outer</span>
                   <div className="h-8 bg-[#F4D160] rounded-full flex items-center px-4 text-[#1A1A1A] text-[12px] font-medium">Pheran</div>
                 </div>
                 <div className="flex-1 flex flex-col gap-2">
                   <span className="text-[11px] text-[#A0A0A0]">Inner</span>
                   <div className="h-8 bg-[#2B2B2B] rounded-full flex items-center px-3 text-white text-[12px]">Thermal</div>
                 </div>
              </div>
           </div>

           {/* Functional Checklist */}
           <div className="flex-1 ref-card-dark p-7 flex flex-col min-h-0">
              <div className="flex justify-between items-end mb-8 border-b border-white/10 pb-4">
                <h3 className="text-white text-[20px] font-medium">Daily Checklist</h3>
                <span className="text-[28px] font-light text-[#F4D160] leading-none">{completedTasks}/{checklist.length}</span>
              </div>

              <div className="flex-1 overflow-y-auto pr-2 flex flex-col gap-5">
                {checklist.map((task) => (
                  <button key={task.id} onClick={() => toggleCheck(task.id)} className="flex items-center justify-between group text-left w-full outline-none">
                    <div className="flex items-center gap-4">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center transition-colors ${task.checked ? 'bg-[#F4D160] text-[#1A1A1A]' : 'bg-white/10 text-white/80 group-hover:bg-white/20'}`}>
                        {task.icon}
                      </div>
                      <div className="flex flex-col">
                        <span className={`text-[14px] font-medium mb-0.5 transition-colors ${task.checked ? 'text-white/50 line-through' : 'text-white'}`}>{task.title}</span>
                        <span className="text-[#A0A0A0] text-[12px]">{task.time}</span>
                      </div>
                    </div>
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center border transition-all ${task.checked ? 'bg-[#F4D160] border-[#F4D160] text-[#1A1A1A] scale-110' : 'border-[#737373] scale-100'}`}>
                      {task.checked && <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>}
                    </div>
                  </button>
                ))}
              </div>
           </div>
        </div>

      </div>
      <div className="shrink-0"><KangriAlert /></div>
    </div>
  )
}
