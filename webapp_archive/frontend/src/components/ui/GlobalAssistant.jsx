import { useLocation } from "react-router-dom"
import { useAppStore } from "../../store/appStore"
import { useVoice } from "../../hooks/useVoice"

export default function GlobalAssistant() {
  const location = useLocation()
  
  // Map route path to human-readable page context for the AI
  const pageContextMap = {
    "/": "Dashboard (Home)",
    "/diet": "Diet Advice Page",
    "/exercise": "Exercise and Workout Page",
    "/companion": "AI Companion Hub",
  }
  const pageContext = pageContextMap[location.pathname] || "Unknown Page"

  const ageMode = useAppStore((s) => s.ageMode)
  const { state, transcript, response, startListening, stopListening } = useVoice(ageMode, pageContext)

  const isListening = state === "listening"
  const isProcessing = state === "processing"
  const isSpeaking = state === "speaking"
  const isError = state === "error"

  const isActive = isListening || isProcessing || isSpeaking || transcript || response

  return (
    <div className="fixed bottom-6 right-6 z-[100] flex flex-col items-end">
      
      {/* Compact Soft Bubble for Transcript/Response */}
      {isActive && (
        <div className="mb-4 w-[280px] bg-white/90 backdrop-blur-xl rounded-[20px] rounded-br-[4px] p-4 shadow-[0_10px_30px_-10px_rgba(0,0,0,0.15)] border border-[#E8E1D5] animate-in slide-in-from-bottom-4 fade-in duration-300">
          
          {transcript && (
            <div className="mb-2">
              <span className="text-[9px] text-[#A0A0A0] font-bold uppercase tracking-widest block mb-0.5">You</span>
              <p className="text-[14px] text-[#1A1A1A] font-medium leading-tight">{transcript}</p>
            </div>
          )}

          {isProcessing && !response && (
             <div className="flex gap-1.5 items-center h-[16px] mt-2">
               <span className="w-1.5 h-1.5 bg-[#A0A0A0] rounded-full animate-bounce"></span>
               <span className="w-1.5 h-1.5 bg-[#A0A0A0] rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></span>
               <span className="w-1.5 h-1.5 bg-[#A0A0A0] rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></span>
             </div>
          )}

          {response && (
            <div className="mt-3 pt-3 border-t border-[#F0F0F0] animate-in fade-in zoom-in-95 duration-400">
              <div className="flex items-center gap-1.5 mb-1.5">
                <span className="w-3 h-3 rounded-full bg-[#F4D160] flex items-center justify-center">
                   <svg width="6" height="6" viewBox="0 0 24 24" fill="none" stroke="#1A1A1A" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
                </span>
                <span className="text-[9px] text-[#A0A0A0] font-bold uppercase tracking-widest">Saathi</span>
              </div>
              <p className="text-[13px] text-[#1A1A1A] leading-snug">
                {response.response_text}
              </p>
            </div>
          )}

          {isError && (
             <p className="text-[#EF4444] text-[12px] font-medium mt-1">Connection failed.</p>
          )}

        </div>
      )}

      {/* Floating Button with 4-Dot Wave Animation */}
      <div className="relative flex items-center justify-center">
        <button 
          type="button"
          onClick={() => {
            if (state === "idle" || state === "error" || state === "speaking") startListening()
            else if (state === "listening") stopListening()
          }}
          style={{ touchAction: 'none', WebkitTapHighlightColor: 'transparent' }}
          className={`relative z-10 w-14 h-14 flex items-center justify-center outline-none transition-all duration-300 cursor-pointer rounded-full ${
            (isListening || isProcessing) 
              ? 'bg-[#1A1A1A] shadow-[0_10px_25px_rgba(0,0,0,0.2)] scale-105' 
              : 'bg-[#1A1A1A] text-white hover:bg-[#2B2B2B] shadow-lg hover:scale-105'
          }`}
        >
          {isListening || isProcessing ? (
             <div className="flex items-center gap-1">
               <span className="w-1.5 h-1.5 bg-[#4285F4] rounded-full animate-bounce" style={{animationDuration: '0.8s'}}></span>
               <span className="w-1.5 h-1.5 bg-[#EA4335] rounded-full animate-bounce" style={{animationDuration: '0.8s', animationDelay: '0.15s'}}></span>
               <span className="w-1.5 h-1.5 bg-[#FBBC05] rounded-full animate-bounce" style={{animationDuration: '0.8s', animationDelay: '0.3s'}}></span>
               <span className="w-1.5 h-1.5 bg-[#34A853] rounded-full animate-bounce" style={{animationDuration: '0.8s', animationDelay: '0.45s'}}></span>
             </div>
          ) : isSpeaking ? (
             <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-white"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-white">
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
              <line x1="12" x2="12" y1="19" y2="22"/>
            </svg>
          )}
        </button>
      </div>

    </div>
  )
}
