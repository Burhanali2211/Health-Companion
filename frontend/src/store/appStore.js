import { create } from "zustand"

export const useAppStore = create((set) => ({
  ageMode: "jawaan",       // bacha | jawaan | buzurg
  district: "srinagar",
  isOnline: navigator.onLine,
  currentSeason: null,
  healthContext: null,

  setAgeMode: (mode) => set({ ageMode: mode }),
  setDistrict: (d) => set({ district: d }),
  setOnline: (v) => set({ isOnline: v }),
  setHealthContext: (ctx) => set({
    healthContext: ctx,
    currentSeason: ctx?.season ?? null,
  }),
}))
