import { useState } from "react";
import { useStore } from "../store";
import { api } from "../services/api";
import { Search, Sparkles, GitBranch, Network, Loader2 } from "lucide-react";
import { cn } from "../lib/utils";

export function SearchPanel() {
  const {
    selectedRepo,
    setSearchResults,
    setExplanation,
    setGraphData,
    setActiveTab,
    setLoading,
    setError,
    loading,
  } = useStore();

  const [query, setQuery] = useState("");

  const disabled = !selectedRepo || selectedRepo.status !== "completed";

  const handleSearch = async (mode: "search" | "explain" | "trace") => {
    if (!query.trim() || disabled || loading) return;

    setLoading(true);
    setSearchResults([]);
    setExplanation(null);
    setError(null);

    try {
      if (mode === "search") {
        const res = await api.search(selectedRepo!.id, query);
        setSearchResults(res.results);
      } else if (mode === "explain") {
        const res = await api.explain(selectedRepo!.id, query);
        setExplanation(res);
      } else if (mode === "trace") {
        const res = await api.trace(selectedRepo!.id, query);
        setExplanation(res);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "An unexpected error occurred";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleGraph = async () => {
    if (!selectedRepo || selectedRepo.status !== "completed" || loading) return;
    setActiveTab("graph");
    setError(null);
    try {
      const data = await api.getGraph(selectedRepo.id);
      setGraphData(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load graph";
      setError(message);
    }
  };

  return (
    <div className="flex gap-2 items-center">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-subtle" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch("search")}
          placeholder={
            disabled
              ? "Select a completed repository first"
              : "Search code... e.g. 'Where is authentication implemented?'"
          }
          className="w-full pl-9 pr-4 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-1 focus:ring-accent placeholder:text-subtle"
          disabled={disabled}
        />
      </div>
      <button
        onClick={() => handleSearch("search")}
        disabled={disabled || !query.trim() || loading}
        className={cn(
          "px-4 py-2 text-sm font-medium rounded-lg transition-all",
          "bg-primary text-background hover:opacity-90 disabled:opacity-40",
        )}
      >
        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Search"}
      </button>
      <button
        onClick={() => handleSearch("explain")}
        disabled={disabled || !query.trim() || loading}
        className="px-4 py-2 text-sm font-medium rounded-lg bg-elevated text-foreground hover:bg-highlight disabled:opacity-40 transition-colors"
      >
        <Sparkles className="w-4 h-4 inline mr-1.5" />
        Explain
      </button>
      <button
        onClick={() => handleSearch("trace")}
        disabled={disabled || !query.trim() || loading}
        className="px-4 py-2 text-sm font-medium rounded-lg bg-elevated text-foreground hover:bg-highlight disabled:opacity-40 transition-colors"
      >
        <GitBranch className="w-4 h-4 inline mr-1.5" />
        Trace
      </button>
      <button
        onClick={handleGraph}
        disabled={disabled || loading}
        className="px-4 py-2 text-sm font-medium rounded-lg bg-elevated text-foreground hover:bg-highlight disabled:opacity-40 transition-colors"
      >
        <Network className="w-4 h-4 inline mr-1.5" />
        Graph
      </button>
    </div>
  );
}
