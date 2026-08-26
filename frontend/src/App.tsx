import { useEffect, useCallback } from "react";
import { useStore } from "./store";
import { api } from "./services/api";
import { SearchPanel } from "./components/SearchPanel";
import { ResultsPanel, CodePanel } from "./components/ResultsPanel";
import { ExplanationPanel } from "./components/ExplanationPanel";
import { GraphPanel } from "./components/GraphPanel";
import { Sidebar } from "./components/Sidebar";
import { ThemeToggle } from "./components/ThemeToggle";
import { AlertCircle, X } from "lucide-react";

export default function App() {
  const {
    selectedRepo,
    selectedNode,
    explanation,
    activeTab,
    error,
    setRepositories,
    updateRepository,
    setError,
    setActiveTab,
  } = useStore();

  const loadRepos = useCallback(async () => {
    try {
      const repos = await api.listRepositories();
      setRepositories(repos);
    } catch {
      setError("Failed to load repositories. Please check if the server is running.");
    }
  }, [setRepositories, setError]);

  useEffect(() => {
    loadRepos();
  }, [loadRepos]);

  // Poll indexing status
  useEffect(() => {
    if (!selectedRepo || selectedRepo.status === "completed" || selectedRepo.status === "failed")
      return;

    const interval = setInterval(async () => {
      try {
        const status = await api.getIndexingStatus(selectedRepo.id);
        updateRepository(selectedRepo.id, {
          status: status.status,
          file_count: status.file_count,
          symbol_count: status.symbol_count,
          error_message: status.error_message,
        });
        if (status.status === "completed" || status.status === "failed") {
          clearInterval(interval);
          loadRepos();
        }
      } catch {
        // polling errors are non-critical
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [selectedRepo?.id, selectedRepo?.status, updateRepository, loadRepos]);

  const isError = activeTab === "search";

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      <Sidebar />

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <div className="flex items-center border-b border-border bg-surface">
          <div className="flex-1 p-4">
            <SearchPanel />
          </div>
          <div className="pr-4">
            <ThemeToggle />
          </div>
        </div>

        {/* Error banner */}
        {error && (
          <div className="mx-4 mt-3 px-4 py-3 bg-danger/10 border border-danger/20 rounded-lg flex items-start justify-between">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-danger mt-0.5 shrink-0" />
              <p className="text-sm text-danger">{error}</p>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-danger/60 hover:text-danger ml-2 shrink-0"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Indexing failure banner */}
        {selectedRepo &&
          selectedRepo.status === "failed" &&
          selectedRepo.error_message &&
          !error && (
            <div className="mx-4 mt-3 px-4 py-3 bg-danger/10 border border-danger/20 rounded-lg">
              <div className="flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-danger mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-medium text-danger">Indexing Failed</p>
                  <p className="text-xs text-danger/70 mt-1">{selectedRepo.error_message}</p>
                </div>
              </div>
            </div>
          )}

        {/* Main content */}
        <div className="flex-1 flex overflow-hidden">
          <div className="flex-1 flex flex-col overflow-hidden border-r border-border">
            {/* Tabs */}
            <div className="flex border-b border-border bg-surface">
              <button
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                  activeTab === "search"
                    ? "border-b-2 border-accent text-foreground"
                    : "text-muted hover:text-foreground"
                }`}
                onClick={() => setActiveTab("search")}
              >
                Results
              </button>
              <button
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                  activeTab === "graph"
                    ? "border-b-2 border-accent text-foreground"
                    : "text-muted hover:text-foreground"
                }`}
                onClick={() => setActiveTab("graph")}
              >
                Graph
              </button>
            </div>

            <div className="flex-1 overflow-auto">
              {isError ? <ResultsPanel /> : <GraphPanel />}
            </div>
          </div>

          {/* Right panel */}
          <div className="w-[45%] overflow-auto bg-surface">
            {selectedNode ? (
              <CodePanel />
            ) : explanation ? (
              <ExplanationPanel />
            ) : (
              <div className="flex items-center justify-center h-full text-muted">
                <div className="text-center">
                  <p className="text-sm">Select a result to view code</p>
                  <p className="text-xs mt-1 text-subtle">
                    or run an explanation to see analysis
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
