import { useEffect } from "react"
import axios from "axios"
import { useAppStore } from "../store/appStore"

export function useSeasonData() {
  const district        = useAppStore((s) => s.district)
  const setHealthContext = useAppStore((s) => s.setHealthContext)
  const healthContext   = useAppStore((s) => s.healthContext)

  useEffect(() => {
    let cancelled = false

    async function fetchContext() {
      try {
        const res = await axios.get(`/api/context/${district}`)
        if (!cancelled) setHealthContext(res.data.data)
      } catch {
        // API unavailable — keep any previously loaded context
      }
    }

    fetchContext()
    return () => { cancelled = true }
  }, [district, setHealthContext])

  return healthContext
}
