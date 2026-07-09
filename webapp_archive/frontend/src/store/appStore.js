import { create } from "zustand"

export const useAppStore = create((set, get) => ({
  ageMode: "jawaan",       // bacha | jawaan | buzurg
  district: "srinagar",
  isOnline: navigator.onLine,
  currentSeason: null,
  healthContext: null,

  // Sidebar
  sidebarOpen: false,
  setSidebarOpen: (v) => set({ sidebarOpen: v }),
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),

  // Chat history — in-memory per session
  chatHistory: [],
  addChat: (chat) => set((s) => ({
    chatHistory: [
      { id: Date.now(), timestamp: new Date().toISOString(), ...chat },
      ...s.chatHistory,
    ].slice(0, 50), // cap at 50 entries
  })),
  clearChatHistory: () => set({ chatHistory: [] }),

  // Active companion conversation (for New Chat)
  activeConversation: null,
  setActiveConversation: (conv) => set({ activeConversation: conv }),
  newChat: () => set({ activeConversation: null }),

  setAgeMode: (mode) => set({ ageMode: mode }),
  setDistrict: (d) => set({ district: d }),
  setOnline: (v) => set({ isOnline: v }),
  setHealthContext: (ctx) => set({
    healthContext: ctx,
    currentSeason: ctx?.season ?? null,
  }),
}))
