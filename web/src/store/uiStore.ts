import { create } from 'zustand'

type UiStore = {
  settingsOpen: boolean
  toast: string | null
  openSettings: () => void
  closeSettings: () => void
  showToast: (message: string) => void
  clearToast: () => void
}

export const useUiStore = create<UiStore>((set) => ({
  settingsOpen: false,
  toast: null,
  openSettings: () => set({ settingsOpen: true }),
  closeSettings: () => set({ settingsOpen: false }),
  showToast: (message) => set({ toast: message }),
  clearToast: () => set({ toast: null }),
}))
