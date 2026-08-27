import { useState, useEffect, useCallback } from "react";
import { api } from "../services/api";
import {
  ChevronRight,
  ChevronUp,
  FolderOpen,
  FolderGit2,
  Home,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { cn } from "../lib/utils";

interface Props {
  onSelect: (path: string) => void;
  onClose: () => void;
}

export function DirectoryBrowser({ onSelect, onClose }: Props) {
  const [currentPath, setCurrentPath] = useState("/");
  const [inputValue, setInputValue] = useState("/");
  const [parentPath, setParentPath] = useState<string | null>(null);
  const [entries, setEntries] = useState<
    { name: string; path: string; is_git: boolean }[]
  >([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pathValid, setPathValid] = useState(true);

  const navigate = useCallback(async (path: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.browseDirectories(path);
      setCurrentPath(data.current);
      setInputValue(data.current);
      setParentPath(data.parent);
      setEntries(data.entries);
      setPathValid(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to browse directory");
      setEntries([]);
      setPathValid(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    navigate(currentPath);
  }, []);

  const handleBack = () => {
    if (parentPath) navigate(parentPath);
  };

  const handleHome = () => {
    const home = navigator.platform.startsWith("Win") ? "C:\\" : "/";
    navigate(home);
  };

  const handlePathSubmit = () => {
    const path = inputValue.trim();
    if (path && path !== currentPath) {
      navigate(path);
    } else {
      setInputValue(currentPath);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-surface border border-border rounded-xl shadow-2xl w-[480px] max-h-[70vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <div className="flex items-center gap-2 min-w-0">
            <FolderOpen className="w-4 h-4 text-accent shrink-0" />
            <h2 className="text-sm font-medium">Browse for Repository</h2>
          </div>
          <button
            onClick={onClose}
            className="text-xs text-muted hover:text-foreground px-2 py-1 rounded hover:bg-elevated shrink-0"
          >
            Cancel
          </button>
        </div>

        {/* Path bar */}
        <div className="flex items-center gap-1.5 px-4 py-2 border-b border-border bg-elevated/50">
          <button
            onClick={handleHome}
            className="p-1 rounded hover:bg-highlight text-muted hover:text-foreground shrink-0"
            title="Go to root"
          >
            <Home className="w-3.5 h-3.5" />
          </button>
          {parentPath && (
            <button
              onClick={handleBack}
              className="p-1 rounded hover:bg-highlight text-muted hover:text-foreground shrink-0"
              title="Go up"
            >
              <ChevronUp className="w-3.5 h-3.5" />
            </button>
          )}
          <input
            type="text"
            value={inputValue}
            onChange={(e) => {
              setInputValue(e.target.value);
              setError(null);
              setPathValid(true);
            }}
            onKeyDown={(e) => e.key === "Enter" && handlePathSubmit()}
            onBlur={handlePathSubmit}
            className={cn(
              "flex-1 min-w-0 px-2 py-1 text-xs font-mono bg-background border rounded-md focus:outline-none focus:ring-1 focus:ring-accent truncate",
              error ? "border-danger text-danger" : "border-border text-foreground",
            )}
            placeholder="/path/to/directory"
          />
        </div>

        {/* Directory list */}
        <div className="flex-1 overflow-auto min-h-0">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-5 h-5 text-accent animate-spin" />
            </div>
          ) : error ? (
            <div className="flex items-center gap-2 px-4 py-8 text-center justify-center">
              <AlertCircle className="w-4 h-4 text-danger shrink-0" />
              <p className="text-sm text-danger">{error}</p>
            </div>
          ) : entries.length === 0 ? (
            <p className="text-xs text-subtle text-center py-8">
              No subdirectories found
            </p>
          ) : (
            <div className="py-1">
              {entries.map((entry) => (
                <button
                  key={entry.path}
                  onClick={() => navigate(entry.path)}
                  className={cn(
                    "w-full flex items-center gap-3 px-4 py-2.5 text-left text-sm transition-colors",
                    "hover:bg-elevated/50",
                  )}
                >
                  {entry.is_git ? (
                    <FolderGit2 className="w-4 h-4 text-accent shrink-0" />
                  ) : (
                    <FolderOpen className="w-4 h-4 text-muted shrink-0" />
                  )}
                  <span className="flex-1 truncate">{entry.name}</span>
                  {entry.is_git && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-accent/10 text-accent font-medium shrink-0">
                      Git
                    </span>
                  )}
                  <ChevronRight className="w-3.5 h-3.5 text-subtle shrink-0" />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-border flex items-center justify-between gap-3">
          <p
            className="text-xs text-subtle truncate min-w-0 flex-1"
            title={currentPath}
          >
            {currentPath}
          </p>
          <button
            onClick={() => onSelect(currentPath)}
            disabled={!pathValid || loading}
            className="px-4 py-1.5 text-sm font-medium bg-primary text-background rounded-lg hover:opacity-90 disabled:opacity-40 transition-opacity shrink-0"
          >
            Select Folder
          </button>
        </div>
      </div>
    </div>
  );
}
