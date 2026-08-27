import { useState } from "react";
import { useStore } from "../store";
import { api } from "../services/api";
import {
  Trash2,
  RefreshCw,
  AlertCircle,
  Loader2,
  FolderSearch,
  Database,
  Settings2,
  ChevronDown,
} from "lucide-react";
import { cn } from "../lib/utils";
import { DirectoryBrowser } from "./DirectoryBrowser";
import { LlmProviderDropdown } from "./LlmProviderToggle";
import { ModelManager } from "./ModelManager";

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
  const [refreshing, setRefreshing] = useState(false);
  const [showBrowser, setShowBrowser] = useState(false);
  const [showModels, setShowModels] = useState(false);

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
    setRefreshing(true);
    try {
      const repos = await api.listRepositories();
      setRepositories(repos);
    } catch {
      setError("Failed to refresh repositories");
    } finally {
      setRefreshing(false);
    }
  };

  const statusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <span className="w-2.5 h-2.5 rounded-full bg-success shrink-0" />;
      case "indexing":
      case "pending":
        return <Loader2 className="w-4 h-4 text-warning animate-spin shrink-0" />;
      case "failed":
        return <span className="w-2.5 h-2.5 rounded-full bg-danger shrink-0" />;
      default:
        return <span className="w-2.5 h-2.5 rounded-full bg-subtle shrink-0" />;
    }
  };

  return (
    <div className="w-72 border-r border-border flex flex-col bg-surface h-full">
      {showBrowser && (
        <DirectoryBrowser
          onSelect={(path) => {
            setIndexPath(path);
            setShowBrowser(false);
          }}
          onClose={() => setShowBrowser(false)}
        />
      )}

      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between mb-3">
          <h1 className="font-semibold text-sm tracking-tight">Semantic Code Search</h1>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="p-2 rounded-lg hover:bg-elevated text-muted hover:text-foreground transition-colors disabled:opacity-50"
            aria-label="Refresh repository list"
          >
            <RefreshCw className={cn("w-4 h-4", refreshing && "animate-spin")} />
          </button>
        </div>
        <LlmProviderDropdown />
      </div>

      {/* Models section */}
      <div className="border-b border-border">
        <button
          onClick={() => setShowModels(!showModels)}
          className="flex items-center gap-2 w-full px-4 py-2.5 text-left hover:bg-elevated/50 transition-colors"
        >
          <Settings2 className="w-4 h-4 text-muted shrink-0" />
          <span className="text-xs font-medium text-muted uppercase tracking-wider flex-1">
            Models
          </span>
          <ChevronDown
            className={cn(
              "w-4 h-4 text-subtle transition-transform",
              showModels && "rotate-180",
            )}
          />
        </button>
        {showModels && (
          <div className="px-3 pb-3">
            <ModelManager />
          </div>
        )}
      </div>

      {/* Index input */}
      <div className="p-3 border-b border-border space-y-2">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowBrowser(true)}
            disabled={indexing}
            className="flex items-center gap-2 flex-1 min-w-0 px-3 py-2 text-sm bg-background border border-border rounded-md hover:bg-elevated transition-colors text-left disabled:opacity-50 overflow-hidden"
          >
            <FolderSearch className="w-4 h-4 text-muted shrink-0" />
            <span className={indexPath ? "text-foreground truncate" : "text-subtle truncate"}>
              {indexPath || "Browse for repository..."}
            </span>
          </button>
        </div>
        <button
          onClick={handleIndex}
          disabled={indexing || !indexPath.trim()}
          className="w-full px-3 py-2 text-sm font-medium bg-primary text-background rounded-md hover:opacity-90 disabled:opacity-40 transition-opacity flex items-center justify-center gap-2"
        >
          {indexing ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Indexing...
            </>
          ) : (
            "Index Repository"
          )}
        </button>
        {indexError && (
          <div className="flex items-start gap-2 px-2 py-2 bg-danger/10 border border-danger/20 rounded-md">
            <AlertCircle className="w-4 h-4 text-danger mt-0.5 shrink-0" />
            <p className="text-xs text-danger leading-relaxed">{indexError}</p>
          </div>
        )}
      </div>

      {/* Repository list */}
      <div className="flex-1 overflow-auto p-2">
        <div className="flex items-center gap-1.5 px-2 py-1">
          <Database className="w-4 h-4 text-subtle" />
          <p className="text-xs text-subtle uppercase tracking-wider font-medium">
            Repositories
          </p>
        </div>
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
              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                {(repo.status === "completed" || repo.status === "failed") && (
                  <button
                    onClick={(e) =>
                      repo.status === "failed" ? handleRetry(e, repo) : handleReindex(e, repo)
                    }
                    className="p-1.5 rounded hover:bg-highlight text-subtle hover:text-foreground"
                    title={repo.status === "failed" ? "Retry indexing" : "Reindex repository"}
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>
                )}
                <button
                  onClick={(e) => handleDelete(e, repo.id)}
                  disabled={actionLoading === repo.id}
                  className="p-1.5 rounded hover:bg-danger/10 text-subtle hover:text-danger"
                  title="Delete repository"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
            <div className="flex items-center gap-2 mt-1 ml-6">
              <span className="text-xs capitalize text-muted">{repo.status}</span>
              {repo.status === "completed" && (
                <span className="text-xs text-subtle">
                  {repo.file_count} files &middot; {repo.symbol_count} symbols
                </span>
              )}
            </div>
            {repo.status === "failed" && repo.error_message && (
              <div className="flex items-start gap-1.5 mt-1.5 ml-6">
                <AlertCircle className="w-4 h-4 text-danger mt-0.5 shrink-0" />
                <p className="text-xs text-danger/80 leading-relaxed truncate" title={repo.error_message}>
                  {repo.error_message}
                </p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
