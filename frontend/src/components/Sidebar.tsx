import { useState } from "react";
import { useStore } from "../store";
import { api } from "../services/api";
import {
  Trash2,
  RefreshCw,
  AlertCircle,
  Loader2,
  ChevronRight,
  FolderOpen,
} from "lucide-react";
import { cn } from "../lib/utils";

export function Sidebar() {
  const {
    repositories,
    selectedRepo,
    setSelectedRepo,
    addRepository,
    removeRepository,
    updateRepository,
    setError,
    setRepositories,
  } = useStore();

  const [indexPath, setIndexPath] = useState("");
  const [indexing, setIndexing] = useState(false);
  const [indexError, setIndexError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const handleIndex = async () => {
    const path = indexPath.trim();
    if (!path) return;

    setIndexing(true);
    setIndexError(null);

    try {
      const repo = await api.indexRepository(path);
      addRepository(repo);
      setSelectedRepo(repo);
      setIndexPath("");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to start indexing";
      setIndexError(message);
    } finally {
      setIndexing(false);
    }
  };

  const handleDelete = async (e: React.MouseEvent, repoId: string) => {
    e.stopPropagation();
    setActionLoading(repoId);
    try {
      await api.deleteRepository(repoId);
      removeRepository(repoId);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Delete failed";
      setError(message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleReindex = async (e: React.MouseEvent, repo: (typeof repositories)[0]) => {
    e.stopPropagation();
    setActionLoading(repo.id);
    try {
      updateRepository(repo.id, { status: "pending", error_message: null });
      const updated = await api.indexRepository(repo.path);
      updateRepository(repo.id, {
        status: updated.status,
        file_count: updated.file_count,
        symbol_count: updated.symbol_count,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Reindex failed";
      updateRepository(repo.id, { status: "failed", error_message: message });
    } finally {
      setActionLoading(null);
    }
  };

  const handleRetry = async (e: React.MouseEvent, repo: (typeof repositories)[0]) => {
    e.stopPropagation();
    await handleReindex(e, repo);
  };

  const handleRefresh = async () => {
    try {
      const repos = await api.listRepositories();
      setRepositories(repos);
    } catch {
      setError("Failed to refresh repositories");
    }
  };

  const statusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <span className="w-2 h-2 rounded-full bg-success shrink-0" />;
      case "indexing":
      case "pending":
        return <Loader2 className="w-3 h-3 text-warning animate-spin shrink-0" />;
      case "failed":
        return <span className="w-2 h-2 rounded-full bg-danger shrink-0" />;
      default:
        return <span className="w-2 h-2 rounded-full bg-subtle shrink-0" />;
    }
  };

  return (
    <div className="w-72 border-r border-border flex flex-col bg-surface h-full">
      {/* Header */}
      <div className="p-4 border-b border-border flex items-center justify-between">
        <h1 className="font-semibold text-sm tracking-tight">Semantic Code Search</h1>
        <button
          onClick={handleRefresh}
          className="p-1 rounded hover:bg-elevated text-muted hover:text-foreground transition-colors"
          title="Refresh"
        >
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Index input */}
      <div className="p-3 border-b border-border space-y-2">
        <div className="flex items-center gap-2">
          <FolderOpen className="w-4 h-4 text-muted shrink-0" />
          <input
            type="text"
            value={indexPath}
            onChange={(e) => {
              setIndexPath(e.target.value);
              setIndexError(null);
            }}
            onKeyDown={(e) => e.key === "Enter" && handleIndex()}
            placeholder="/path/to/repo"
            className="flex-1 px-2.5 py-1.5 text-sm bg-background border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-accent placeholder:text-subtle"
            disabled={indexing}
          />
        </div>
        <button
          onClick={handleIndex}
          disabled={indexing || !indexPath.trim()}
          className="w-full px-3 py-1.5 text-sm font-medium bg-primary text-background rounded-md hover:opacity-90 disabled:opacity-40 transition-opacity"
        >
          {indexing ? (
            <span className="flex items-center justify-center gap-2">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              Indexing...
            </span>
          ) : (
            "Index Repository"
          )}
        </button>
        {indexError && (
          <div className="flex items-start gap-2 px-2 py-2 bg-danger/10 border border-danger/20 rounded-md">
            <AlertCircle className="w-3.5 h-3.5 text-danger mt-0.5 shrink-0" />
            <p className="text-xs text-danger leading-relaxed">{indexError}</p>
          </div>
        )}
      </div>

      {/* Repository list */}
      <div className="flex-1 overflow-auto p-2">
        <p className="text-xs text-subtle px-2 py-1 uppercase tracking-wider font-medium">
          Repositories
        </p>
        {repositories.length === 0 && (
          <p className="text-xs text-subtle px-2 py-4 text-center">
            No repositories indexed yet
          </p>
        )}
        {repositories.map((repo) => (
          <div
            key={repo.id}
            onClick={() => setSelectedRepo(repo)}
            className={cn(
              "group w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors cursor-pointer mb-0.5",
              selectedRepo?.id === repo.id
                ? "bg-elevated text-foreground"
                : "text-muted hover:bg-elevated/50 hover:text-foreground",
            )}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 min-w-0">
                {statusIcon(repo.status)}
                <span className="font-medium truncate">{repo.name}</span>
              </div>
              <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                {(repo.status === "completed" || repo.status === "failed") && (
                  <button
                    onClick={(e) =>
                      repo.status === "failed" ? handleRetry(e, repo) : handleReindex(e, repo)
                    }
                    className="p-1 rounded hover:bg-highlight text-subtle hover:text-foreground"
                    title={repo.status === "failed" ? "Retry" : "Reindex"}
                  >
                    <RefreshCw className="w-3 h-3" />
                  </button>
                )}
                <button
                  onClick={(e) => handleDelete(e, repo.id)}
                  disabled={actionLoading === repo.id}
                  className="p-1 rounded hover:bg-danger/10 text-subtle hover:text-danger"
                  title="Delete"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            </div>
            <div className="flex items-center gap-2 mt-1 ml-5">
              <span className="text-xs capitalize text-muted">{repo.status}</span>
              {repo.status === "completed" && (
                <span className="text-xs text-subtle">
                  {repo.file_count} files &middot; {repo.symbol_count} symbols
                </span>
              )}
            </div>
            {repo.status === "failed" && repo.error_message && (
              <div className="flex items-start gap-1.5 mt-1.5 ml-5">
                <AlertCircle className="w-3 h-3 text-danger mt-0.5 shrink-0" />
                <p className="text-xs text-danger/80 leading-relaxed truncate" title={repo.error_message}>
                  {repo.error_message}
                </p>
              </div>
            )}
            {selectedRepo?.id === repo.id && (
              <ChevronRight className="w-3 h-3 text-accent absolute right-3 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100" />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
