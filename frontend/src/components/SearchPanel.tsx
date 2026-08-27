import { useState } from "react";
import { useStore } from "../store";
import { api } from "../services/api";
import { Search, Sparkles, Network, Loader2 } from "lucide-react";
import { cn } from "../lib/utils";

export function SearchPanel() {
  const {
    selectedRepo,
    setSearchResults,
    setExplanation,
    setGraphData,
    setActiveTab,
    setLoading,
    setLoadingMode,
    setError,
    setAIMode,
    aiMode,
    loading,
  } = useStore();

  const [query, setQuery] = useState("");

  const disabled = !selectedRepo || selectedRepo.status !== "completed";

  const handleSearch = async () => {
    if (!query.trim() || disabled || loading) return;

    setLoading(true);
    setLoadingMode(aiMode ? "explain" : "search");
    setSearchResults([]);
    setExplanation(null);
    setError(null);

    try {
      if (aiMode) {
        const res = await api.explain(selectedRepo!.id, query);
        setExplanation(res);
      } else {
        const res = await api.search(selectedRepo!.id, query);
        setSearchResults(res.results);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "An unexpected error occurred";
      setError(message);
    } finally {
      setLoading(false);
      setLoadingMode(null);
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
      {/* AI mode toggle */}
      <button
        onClick={() => setAIMode(!aiMode)}
        disabled={disabled}
        className={cn(
          "flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg transition-all",
          "bg-elevated hover:bg-highlight",
          disabled && "opacity-40 cursor-not-allowed",
        )}
        title={aiMode ? "AI mode ON" : "AI mode OFF"}
      >
        <Sparkles className={cn("w-4 h-4", aiMode ? "text-accent animate-pulse" : "text-subtle")} />
        <span className={cn("hidden sm:inline", aiMode ? "text-accent" : "text-muted")}>AI</span>
        <div
          className={cn(
            "relative w-8 h-[18px] rounded-full transition-colors",
            aiMode ? "bg-accent" : "bg-border",
          )}
        >
          <div
            className={cn(
              "absolute top-[2px] w-[14px] h-[14px] rounded-full bg-background transition-all shadow-sm",
              aiMode ? "left-[calc(100%-16px)]" : "left-[2px]",
            )}
          />
        </div>
      </button>

      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-subtle" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder={
            disabled
              ? "Select a completed repository first"
              : aiMode
                ? "Ask anything about your code..."
                : "Search code... e.g. 'Where is authentication implemented?'"
          }
          className="w-full pl-9 pr-4 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-1 focus:ring-accent placeholder:text-subtle"
          disabled={disabled}
        />
      </div>
      <button
        onClick={handleSearch}
        disabled={disabled || !query.trim() || loading}
        className={cn(
          "px-4 py-2 text-sm font-medium rounded-lg transition-all",
          aiMode
            ? "bg-accent text-background hover:opacity-90 disabled:opacity-40"
            : "bg-primary text-background hover:opacity-90 disabled:opacity-40",
        )}
      >
        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Search"}
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
