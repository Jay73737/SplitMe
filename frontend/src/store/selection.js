import { create } from "zustand";

export const useSelection = create((set) => ({
  selected: null,
  setSelected: (s) => set({ selected: s }),
  clear: () => set({ selected: null }),
}));