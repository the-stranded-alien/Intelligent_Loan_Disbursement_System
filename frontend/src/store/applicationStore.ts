import { create } from 'zustand'

interface Application {
  applicationId: string
  status: string
  currentStage: string | null
  applicantName: string
  loanAmount: number
}

interface ApplicationState {
  applications: Application[]
  selectedApplicationId: string | null

  setSelectedApplication: (id: string) => void
  addApplication: (app: Application) => void
  updateApplicationStatus: (id: string, status: string, stage: string) => void
  clearSelected: () => void
}

export const useApplicationStore = create<ApplicationState>((set) => ({
  applications: [],
  selectedApplicationId: null,

  setSelectedApplication: (id) => set({ selectedApplicationId: id }),

  addApplication: (app) =>
    set((state) => ({ applications: [...state.applications, app] })),

  updateApplicationStatus: (id, status, stage) =>
    set((state) => ({
      applications: state.applications.map((a) =>
        a.applicationId === id ? { ...a, status, currentStage: stage } : a,
      ),
    })),

  clearSelected: () => set({ selectedApplicationId: null }),
}))
