import { useVoice } from "../hooks/useVoice"

export default function Companion() {
  const { state, transcript, response, startListening, stopListening } = useVoice()
  
  const isListening = state === "listening"
  const isProcessing = state === "processing"
  const isSpeaking = state === "speaking"
  
  return (
    <div className="flex flex-col w-full min-h-screen pb-12">
      
      {/* 
        Removed the sticky AI Companion header to save space, as requested.
        Removed the large card/window design around the microphone.
      */}

      <div className="flex-1 flex flex-col px-4 lg:px-6 mt-12 pb-8 max-w-4xl mx-auto w-full relative">
        
        {/* Simple, Floating Centered Microphone */}
        <div className="w-full flex flex-col items-center justify-center relative min-h-[200px]">
          
          <div className="absolute top-0 flex flex-col items-center gap-2">
             <span className={`w-2.5 h-2.5 rounded-full ${isListening ? 'bg-[#F4D160] animate-pulse' : (isProcessing ? 'bg-[#A0A0A0] animate-ping' : 'bg-[#D4D4D4]')}`}></span>
             <span className="text-[12px] font-medium text-[#A0A0A0] tracking-widest uppercase">
               {isSpeaking && response ? "Analysis Complete" : (
                 transcript ? "Listening..." : "Tap to Speak"
               )}
             </span>
          </div>

          <div className="relative flex items-center justify-center mt-12 mb-4">
            {/* Ripple layers */}
            {isListening && (
              <>
                <div className="absolute inset-0 bg-[#F4D160] rounded-full animate-ping opacity-30 scale-[1.3] duration-1000"></div>
                <div className="absolute inset-0 bg-[#F4D160] rounded-full animate-pulse opacity-50 scale-[1.15] duration-700"></div>
              </>
            )}
            {isProcessing && (
              <div className="absolute inset-0 border-4 border-[#F4D160] rounded-full animate-spin border-t-transparent opacity-40 scale-[1.15] duration-1000"></div>
            )}

            <button 
              type="button"
              onClick={() => {
                if (state === "idle" || state === "error" || state === "speaking") startListening()
                else if (state === "listening") stopListening()
              }}
              style={{ touchAction: 'none', WebkitTapHighlightColor: 'transparent' }}
              className={`relative z-10 w-32 h-32 md:w-40 md:h-40 flex items-center justify-center outline-none transition-all duration-500 cursor-pointer rounded-full ${
                isListening 
                  ? 'bg-[#F4D160] text-white shadow-[0_10px_40px_rgba(244,209,96,0.3)] scale-105' 
                  : 'bg-[#FDFBF7] border border-[#E8E1D5] text-[#F4D160] hover:bg-white shadow-[0_10px_30px_-10px_rgba(0,0,0,0.05)] hover:scale-105'
              }`}
            >
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                <line x1="12" x2="12" y1="19" y2="22"/>
              </svg>
            </button>
          </div>
          
          {state === "error" && (
            <p className="text-center text-[#EF4444] text-[13px] font-medium mt-2">
              Connection failed. Please tap again.
            </p>
          )}

        </div>

        {/* Conversation Content Below */}
        <div className="flex-1 flex flex-col pt-8 min-h-[300px]">
          
          {(!transcript && !response && state !== "processing") && (
             <div className="flex-1 flex flex-col items-center justify-center text-center opacity-50">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" className="mb-6 text-[#D4D4D4]"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                <h3 className="text-[20px] font-medium text-[#737373] mb-2">How can I help you?</h3>
             </div>
          )}

          {transcript && (
            <div className="w-full flex justify-end mb-12 animate-in slide-in-from-right-4 fade-in duration-500">
               <div className="max-w-[90%] md:max-w-[80%] flex flex-col items-end">
                 <span className="text-[11px] text-[#A0A0A0] font-medium uppercase tracking-widest mb-2">You</span>
                 <p className="text-[24px] md:text-[32px] font-light text-[#1A1A1A] leading-tight text-right tracking-tight bg-[#F4D160]/10 px-6 py-4 rounded-[24px] rounded-br-[8px]">
                   {transcript}
                 </p>
               </div>
            </div>
          )}

          {isProcessing && !response && (
            <div className="w-full flex justify-start mb-8 animate-pulse">
               <div className="max-w-[80%] flex flex-col items-start">
                 <span className="text-[11px] text-[#A0A0A0] font-medium uppercase tracking-widest mb-2">AI Companion</span>
                 <div className="flex gap-2 items-center h-[40px] px-4">
                   <span className="w-2.5 h-2.5 bg-[#D4D4D4] rounded-full animate-bounce"></span>
                   <span className="w-2.5 h-2.5 bg-[#D4D4D4] rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></span>
                   <span className="w-2.5 h-2.5 bg-[#D4D4D4] rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></span>
                 </div>
               </div>
            </div>
          )}

          {(response || isSpeaking) && (
            <div className="w-full flex justify-start mb-12 animate-in slide-in-from-left-4 fade-in duration-500">
               <div className="max-w-[95%] md:max-w-[85%] flex flex-col items-start">
                 <div className="flex items-center gap-3 mb-3">
                   <span className="w-6 h-6 rounded-full bg-[#F4D160] flex items-center justify-center shadow-sm">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#1A1A1A" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
                   </span>
                   <span className="text-[11px] text-[#A0A0A0] font-medium uppercase tracking-widest">AI Companion</span>
                 </div>
                 <p className="text-[20px] md:text-[24px] font-medium text-[#1A1A1A] leading-relaxed tracking-tight bg-white px-6 py-5 rounded-[24px] rounded-bl-[8px] shadow-sm">
                   {response?.response_text || "..."}
                 </p>
               </div>
            </div>
          )}

        </div>
      </div>
    </div>
  )
}
