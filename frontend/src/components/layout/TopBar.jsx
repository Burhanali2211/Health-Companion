import { useNavigate, useLocation } from "react-router-dom"
import AgeModeToggle from "../ui/AgeModeToggle"
import NetworkBadge from "../ui/NetworkBadge"

export default function TopBar() {
  const navigate = useNavigate()
  const location = useLocation()
  
  const currentPath = location.pathname;

  const getPillClass = (path) => {
    if (currentPath === path) {
      return "px-5 py-2 rounded-full bg-[#2B2B2B] text-white text-sm font-medium shadow-sm transition-all";
    }
    return "px-5 py-2 rounded-full text-[#4A4A4A] text-sm font-medium hover:bg-[#EBE5D9] transition-all";
  }

  return (
    <div className="flex items-center justify-between w-full px-4 lg:px-6 pt-4 pb-2 shrink-0 z-50 relative">
      {/* Logo Equivalent */}
      <div className="flex items-center gap-2 px-5 py-2.5 rounded-full border border-[#D4D4D4] bg-[#F5EFE4]/30 backdrop-blur-sm">
        <span className="font-medium text-lg tracking-tight text-[#1A1A1A]">WatanSehat</span>
      </div>

      {/* Center Pills Nav */}
      <div className="hidden md:flex items-center gap-2 bg-[#F3EDE1] rounded-full p-1.5 shadow-[inset_0_2px_4px_rgba(0,0,0,0.02)] border border-[#E8E1D5]">
        <button onClick={() => navigate("/")} className={getPillClass("/")}>Dashboard</button>
        <button onClick={() => navigate("/diet")} className={getPillClass("/diet")}>Diet Advice</button>
        <button onClick={() => navigate("/exercise")} className={getPillClass("/exercise")}>Exercise</button>
        <button onClick={() => navigate("/companion")} className={getPillClass("/companion")}>AI Helper</button>
      </div>

      {/* Right Tools */}
      <div className="flex items-center gap-3">
        <AgeModeToggle />
        <button onClick={() => window.location.reload()} className="w-10 h-10 rounded-full bg-white flex items-center justify-center shadow-sm border border-[#E8E8E8] text-[#4A4A4A] hover:bg-[#F9F9F9] transition-colors">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 2v6h-6M3 12a9 9 0 102.5-6.5L2 9"/></svg>
        </button>
      </div>
    </div>
  )
}
