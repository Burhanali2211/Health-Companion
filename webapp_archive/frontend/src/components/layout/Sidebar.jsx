import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useAppStore } from "../../store/appStore"

const EMERGENCY_CONTACTS = [
  { label: "Ambulance",       number: "108",            icon: "🚑" },
  { label: "SMHS Hospital",   number: "0194-2430151",   icon: "🏥" },
  { label: "Lal Ded Hospital",number: "0194-2476651",   icon: "🏥" },
  { label: "Police",          number: "100",            icon: "🚔" },
  { label: "Fire Brigade",    number: "101",            icon: "🔥" },
  { label: "SKIMS Soura",     number: "0194-2401013",   icon: "🏥" },
]

const KANGRI_SAFETY = [
  "Always keep a window or door slightly open when using Kangri indoors.",
  "Never sleep with Kangri inside a sealed room — CO gas is odourless and fatal.",
  "Check for excessive drowsiness or headache — early signs of CO poisoning.",
  "Keep Kangri at least 30cm away from bedding and clothing.",
  "Children and elderly should not sleep in rooms with active Kangri.",
]

const FIRST_AID = [
  { title: "Bleeding", steps: "Apply firm pressure with clean cloth. Elevate the limb. Don't remove embedded objects. Seek help if bleeding doesn't stop in 10 min." },
  { title: "Burns", steps: "Cool with running water for 10–20 min. Don't use ice, butter, or toothpaste. Cover with clean non-fluffy material. Go to hospital for serious burns." },
  { title: "Fracture", steps: "Immobilise the injured area — don't try to straighten it. Apply a splint if available. Keep patient warm and calm. Go to hospital immediately." },
  { title: "Hypothermia", steps: "Move to warm indoor space immediately. Remove wet clothing. Wrap in blankets. Give warm (not hot) drinks if conscious. Call 108." },
  { title: "Seizure", steps: "Clear the area around them. Don't restrain — let the seizure pass. Place on side after. Don't put anything in mouth. Call 108 if it lasts >5 min." },
]

function SectionHeader({ label, open, onToggle }) {
  return (
    <button
      onClick={onToggle}
      className="w-full flex items-center justify-between px-3 py-2 rounded-xl hover:bg-[#F0EBE0] transition-colors group"
    >
      <span className="text-[12px] font-semibold text-[#6B6B6B] uppercase tracking-widest">{label}</span>
      <svg
        width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
        className={`text-[#A0A0A0] transition-transform duration-200 ${open ? "rotate-180" : ""}`}
      >
        <path d="M6 9l6 6 6-6"/>
      </svg>
    </button>
  )
}

function formatTime(isoString) {
  const d = new Date(isoString)
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

function formatDate(isoString) {
  const d = new Date(isoString)
  const today = new Date()
  const isToday = d.toDateString() === today.toDateString()
  if (isToday) return "Today"
  return d.toLocaleDateString([], { month: "short", day: "numeric" })
}

export default function Sidebar() {
  const navigate = useNavigate()
  const sidebarOpen   = useAppStore((s) => s.sidebarOpen)
  const setSidebarOpen = useAppStore((s) => s.setSidebarOpen)
  const chatHistory   = useAppStore((s) => s.chatHistory)
  const clearChatHistory = useAppStore((s) => s.clearChatHistory)
  const newChat       = useAppStore((s) => s.newChat)

  const [openSection, setOpenSection] = useState("history") // history | emergency | kangri | firstaid
  const [expandedFirstAid, setExpandedFirstAid] = useState(null)

  function toggleSection(name) {
    setOpenSection((prev) => (prev === name ? null : name))
  }

  function handleNewChat() {
    newChat()
    navigate("/companion")
    setSidebarOpen(false)
  }

  function handleHistoryClick(chat) {
    navigate("/companion")
    setSidebarOpen(false)
  }

  // Group chats by date
  const groupedChats = chatHistory.reduce((acc, chat) => {
    const date = formatDate(chat.timestamp)
    if (!acc[date]) acc[date] = []
    acc[date].push(chat)
    return acc
  }, {})

  return (
    <>
      {/* Backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/20 backdrop-blur-[2px]"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar Panel */}
      <div
        className={`fixed top-0 left-0 h-full w-[300px] z-50 flex flex-col bg-[#FAF7F2] border-r border-[#E8E0D0] shadow-2xl transition-transform duration-300 ease-in-out ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 pt-4 pb-3 border-b border-[#EDE8DE]">
          <div className="flex items-center gap-2">
            <span className="w-7 h-7 rounded-lg bg-[#E8821A] flex items-center justify-center text-white text-[13px] font-bold shadow-sm">W</span>
            <span className="font-semibold text-[15px] text-[#1A1A1A] tracking-tight">Health Wellness Companion</span>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="w-8 h-8 rounded-full hover:bg-[#EDE8DE] flex items-center justify-center text-[#6B6B6B] transition-colors"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>

        {/* New Chat Button */}
        <div className="px-3 py-3">
          <button
            onClick={handleNewChat}
            className="w-full flex items-center gap-2.5 px-4 py-3 rounded-xl bg-[#1A1A1A] text-white hover:bg-[#2B2B2B] transition-colors shadow-sm active:scale-[0.98]"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 5v14M5 12h14"/>
            </svg>
            <span className="text-[14px] font-medium">New Chat</span>
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto px-3 pb-4 space-y-1">

          {/* ── Chat History ─────────────────────────── */}
          <SectionHeader label="Chat History" open={openSection === "history"} onToggle={() => toggleSection("history")} />

          {openSection === "history" && (
            <div className="mt-1 space-y-1">
              {chatHistory.length === 0 ? (
                <div className="px-3 py-6 text-center">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="mx-auto mb-2 text-[#C0B8AC]">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                  </svg>
                  <p className="text-[12px] text-[#A0A0A0]">No conversations yet.</p>
                  <p className="text-[11px] text-[#B0B0B0] mt-0.5">Start a new chat to begin.</p>
                </div>
              ) : (
                <>
                  {Object.entries(groupedChats).map(([date, chats]) => (
                    <div key={date}>
                      <p className="text-[10px] text-[#B0A898] font-medium uppercase tracking-widest px-3 py-1.5">{date}</p>
                      {chats.map((chat) => (
                        <button
                          key={chat.id}
                          onClick={() => handleHistoryClick(chat)}
                          className="w-full text-left px-3 py-2.5 rounded-xl hover:bg-[#EDE8DE] transition-colors group"
                        >
                          <p className="text-[13px] text-[#2A2A2A] font-medium leading-tight truncate">{chat.query}</p>
                          <p className="text-[11px] text-[#A0A0A0] mt-0.5 truncate">{chat.responsePreview}</p>
                          <p className="text-[10px] text-[#C0B8AC] mt-0.5">{formatTime(chat.timestamp)}</p>
                        </button>
                      ))}
                    </div>
                  ))}
                  <button
                    onClick={clearChatHistory}
                    className="w-full text-center text-[11px] text-[#C0392B] hover:text-[#A03020] py-2 transition-colors"
                  >
                    Clear history
                  </button>
                </>
              )}
            </div>
          )}

          <div className="h-px bg-[#EDE8DE] my-2" />

          {/* ── Medical Kit ─────────────────────────── */}
          <p className="text-[10px] font-bold text-[#E8821A] uppercase tracking-widest px-3 py-1">Medical Kit</p>

          {/* Emergency Contacts */}
          <SectionHeader label="Emergency Contacts" open={openSection === "emergency"} onToggle={() => toggleSection("emergency")} />
          {openSection === "emergency" && (
            <div className="mt-1 space-y-1 px-1">
              {EMERGENCY_CONTACTS.map((c) => (
                <div key={c.number} className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-white border border-[#EDE8DE]">
                  <div className="flex items-center gap-2.5">
                    <span className="text-[18px]">{c.icon}</span>
                    <div>
                      <p className="text-[12px] font-semibold text-[#1A1A1A]">{c.label}</p>
                      <p className="text-[11px] text-[#6B6B6B] font-mono">{c.number}</p>
                    </div>
                  </div>
                  <a
                    href={`tel:${c.number}`}
                    className="w-8 h-8 rounded-full bg-[#22C55E] flex items-center justify-center shadow-sm active:scale-95 transition-transform"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12 19.79 19.79 0 0 1 1.61 3.4 2 2 0 0 1 3.6 1.22h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 8.82a16 16 0 0 0 6.29 6.29l.95-.95a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/>
                    </svg>
                  </a>
                </div>
              ))}
            </div>
          )}

          {/* Kangri CO Safety */}
          <SectionHeader label="Kangri CO Safety" open={openSection === "kangri"} onToggle={() => toggleSection("kangri")} />
          {openSection === "kangri" && (
            <div className="mt-1 px-1 space-y-1.5">
              <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-[#FEF2E0] border border-[#F5D9A0]">
                <span className="text-[18px]">⚠️</span>
                <p className="text-[11px] text-[#92400E] font-semibold">Carbon Monoxide is invisible & odourless</p>
              </div>
              {KANGRI_SAFETY.map((tip, i) => (
                <div key={i} className="flex gap-2.5 px-3 py-2.5 rounded-xl bg-white border border-[#EDE8DE]">
                  <span className="w-5 h-5 rounded-full bg-[#FEF3C7] flex items-center justify-center text-[10px] font-bold text-[#92400E] shrink-0 mt-0.5">{i + 1}</span>
                  <p className="text-[12px] text-[#3A3A3A] leading-relaxed">{tip}</p>
                </div>
              ))}
            </div>
          )}

          {/* First Aid */}
          <SectionHeader label="First Aid Quick Ref" open={openSection === "firstaid"} onToggle={() => toggleSection("firstaid")} />
          {openSection === "firstaid" && (
            <div className="mt-1 px-1 space-y-1.5">
              {FIRST_AID.map((item, i) => (
                <div key={i} className="rounded-xl border border-[#EDE8DE] overflow-hidden">
                  <button
                    onClick={() => setExpandedFirstAid(expandedFirstAid === i ? null : i)}
                    className="w-full flex items-center justify-between px-3 py-2.5 bg-white hover:bg-[#FAF7F2] transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-[#C0392B] shrink-0"/>
                      <span className="text-[13px] font-semibold text-[#1A1A1A]">{item.title}</span>
                    </div>
                    <svg
                      width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                      strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
                      className={`text-[#A0A0A0] transition-transform duration-200 ${expandedFirstAid === i ? "rotate-180" : ""}`}
                    >
                      <path d="M6 9l6 6 6-6"/>
                    </svg>
                  </button>
                  {expandedFirstAid === i && (
                    <div className="px-4 py-3 bg-[#FEFCF8] border-t border-[#EDE8DE]">
                      <p className="text-[12px] text-[#3A3A3A] leading-relaxed">{item.steps}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-[#EDE8DE]">
          <p className="text-[10px] text-[#B0A898] text-center">Health Wellness Companion · Kashmir Health Companion</p>
        </div>
      </div>
    </>
  )
}
