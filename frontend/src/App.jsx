import { Routes, Route } from "react-router-dom"
import TopBar    from "./components/layout/TopBar"
import Home      from "./pages/Home"
import Diet      from "./pages/Diet"
import Exercise  from "./pages/Exercise"
import Buzurg    from "./pages/Buzurg"
import Companion from "./pages/Companion"
import GlobalAssistant from "./components/ui/GlobalAssistant"
import { useDragScroll } from "./hooks/useDragScroll"

export default function App() {
  const dragScrollProps = useDragScroll();

  return (
    <div className="w-screen h-screen overflow-hidden flex flex-col relative font-latin bg-transparent">
      <div 
        className="flex-1 w-full overflow-y-auto overflow-x-hidden relative" 
        style={{ scrollBehavior: 'smooth', overscrollBehavior: 'none', touchAction: 'pan-y' }}
        {...dragScrollProps}
      >
        {/* Global Navigation - scrolls naturally out of view */}
        <div className="w-full pb-2 pt-2 shrink-0">
          <TopBar />
        </div>

        <Routes>
          <Route path="/"          element={<Home />}      />
          <Route path="/diet"      element={<Diet />}      />
          <Route path="/exercise"  element={<Exercise />}  />
          <Route path="/buzurg"    element={<Buzurg />}    />
          <Route path="/companion" element={<Companion />} />
        </Routes>
        
        {/* Global Floating Assistant */}
        <GlobalAssistant />
      </div>
    </div>
  )
}
