import { useState, useRef, useEffect } from "react"
import { useAppStore } from "../../store/appStore"

const IconChild = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="8" r="5"/><path d="M20 21a8 8 0 0 0-16 0"/>
    <path d="M12 13v8"/>
  </svg>
)

const IconAdult = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
  </svg>
)

const IconElder = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22V6a2 2 0 0 1 2-2h4"/>
    <path d="M12 12h-2"/>
  </svg>
)

const modes = [
  { id: "shur", label: "Child", icon: <IconChild /> },
  { id: "jawan", label: "Adult", icon: <IconAdult /> },
  { id: "buzurg", label: "Elder", icon: <IconElder /> },
]

export default function AgeModeToggle() {
  const ageMode = useAppStore((s) => s.ageMode)
  const setAgeMode = useAppStore((s) => s.setAgeMode)
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef(null)

  const activeMode = modes.find(m => m.id === ageMode) || modes[1]

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-[#E8E8E8] shadow-sm hover:bg-[#F9F9F9] transition-colors text-[#1A1A1A]"
      >
        <span className="text-[#A0A0A0]">{activeMode.icon}</span>
        <span className="font-medium text-[14px]">{activeMode.label}</span>
        <svg 
          width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
          className={`text-[#A0A0A0] transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
        >
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-40 bg-white border border-[#E8E8E8] rounded-[16px] shadow-[0_10px_20px_-5px_rgba(0,0,0,0.1)] overflow-hidden z-50">
          <div className="flex flex-col p-1">
            {modes.map((mode) => (
              <button
                key={mode.id}
                onClick={() => {
                  setAgeMode(mode.id)
                  setIsOpen(false)
                }}
                className={`flex items-center gap-3 w-full px-3 py-2.5 rounded-[12px] text-left transition-colors ${
                  ageMode === mode.id ? 'bg-[#F9F9F9] text-[#1A1A1A] font-semibold' : 'text-[#737373] hover:bg-[#F3F3F3]'
                }`}
              >
                <span className={ageMode === mode.id ? 'text-[#F4D160]' : 'text-[#A0A0A0]'}>{mode.icon}</span>
                <span className="text-[14px]">{mode.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
