import { useNavigate } from "react-router-dom"

export default function Buzurg() {
  const navigate = useNavigate()
  
  return (
    <div className="flex flex-col h-full bg-[#1A1A2E] relative">
      <div className="absolute top-4 left-4 z-10">
        <button onClick={() => navigate(-1)} className="flex items-center justify-center w-12 h-12 bg-white/10 rounded-full text-white/80 hover:bg-white/20 transition-colors">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
      </div>
      
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <span className="text-6xl">👴</span>
          <p className="font-latin text-[#D4AC0D] text-[32px] tracking-tight font-extrabold mt-5 drop-shadow-md">Elderly Companion</p>
          <p className="font-latin text-white text-[22px] mt-1 font-bold opacity-90">Coming Soon</p>
          <p className="font-latin text-white/50 text-sm mt-2">Buzurg Mode — Week 4</p>
        </div>
      </div>
    </div>
  )
}
