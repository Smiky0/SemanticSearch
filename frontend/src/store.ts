import { create } from "zustand";
import type { Repository, SearchResult, LLMResponse, GraphData, NodeInfo } from "./schemas";

interface AppState {
  repositories: Repository[];
  selectedRepo: Repository | null;
  selectedNode: NodeInfo | null;
  searchResults: SearchResult[];
  explanation: LLMResponse | null;
  graphData: GraphData | null;
  loading: boolean;
  activeTab: "search" | "graph";
  error: string | null;
  theme: "light" | "dark";

  setRepositories: (repos: Repository[]) => void;
  addRepository: (repo: Repository) => void;
  updateRepository: (id: string, updates: Partial<Repository>) => void;
  removeRepository: (id: string) => void;
  setSelectedRepo: (repo: Repository | null) => void;
  setSelectedNode: (node: NodeInfo | null) => void;
  setSearchResults: (results: SearchResult[]) => void;
  setExplanation: (explanation: LLMResponse | null) => void;
  setGraphData: (data: GraphData | null) => void;
  setLoading: (loading: boolean) => void;
  setActiveTab: (tab: "search" | "graph") => void;
  setError: (error: string | null) => void;
  setTheme: (theme: "light" | "dark") => void;
  clearSelection: () => void;
}

export const useStore = create<AppState>((set) => ({
  repositories: [],
  selectedRepo: null,
  selectedNode: null,
  searchResults: [],
  explanation: null,
  graphData: null,
  loading: false,
  activeTab: "search",
  error: null,
  theme: (localStorage.getItem("theme") as "light" | "dark") || "dark",

  setRepositories: (repositories) => set({ repositories }),
  addRepository: (repo) =>
    set((s) => ({ repositories: [repo, ...s.repositories] })),
  updateRepository: (id, updates) =>
    set((s) => ({
      repositories: s.repositories.map((r) => (r.id === id ? { ...r, ...updates } : r)),
      selectedRepo:
        s.selectedRepo?.id === id ? { ...s.selectedRepo, ...updates } : s.selectedRepo,
    })),
  removeRepository: (id) =>
    set((s) => {
      const next = { repositories: s.repositories.filter((r) => r.id !== id) };
      if (s.selectedRepo?.id === id) {
        Object.assign(next, {
          selectedRepo: null,
          selectedNode: null,
          searchResults: [],
          explanation: null,
          graphData: null,
        });
      }
      return next;
    }),
  setSelectedRepo: (selectedRepo) =>
    set({ selectedRepo, selectedNode: null, searchResults: [], explanation: null }),
  setSelectedNode: (selectedNode) => set({ selectedNode }),
  setSearchResults: (searchResults) => set({ searchResults }),
  setExplanation: (explanation) => set({ explanation }),
  setGraphData: (graphData) => set({ graphData }),
  setLoading: (loading) => set({ loading }),
  setActiveTab: (activeTab) => set({ activeTab }),
  setError: (error) => set({ error }),
  setTheme: (theme) => {
    localStorage.setItem("theme", theme);
    document.documentElement.classList.toggle("dark", theme === "dark");
    set({ theme });
  },
  clearSelection: () =>
    set({
      selectedNode: null,
      searchResults: [],
      explanation: null,
      graphData: null,
    }),
}));
