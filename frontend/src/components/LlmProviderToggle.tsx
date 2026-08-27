import { useEffect, useRef, useState } from "react";
import { useStore } from "../store";
import { api } from "../services/api";
import { Cloud, Laptop, Loader2, Check, AlertCircle, ChevronDown } from "lucide-react";
import { cn } from "../lib/utils";

export function LlmProviderDropdown() {
  const { llmProvider, setLlmProvider, providers, setProviders, setError } = useStore();
  const [open, setOpen] = useState(false);
  const [switching, setSwitching] = useState(false);
  const [loading, setLoading] = useState(true);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const fetchProviders = async () => {
    setLoading(true);
    try {
      const data = await api.getLlmProvider();
      setProviders(data.providers);
      if (data.active_llm) {
        setLlmProvider(data.active_llm);
      }
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProviders();
  }, []);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelect = async (providerId: string) => {
    if (providerId === llmProvider || switching) return;
    setSwitching(true);
    try {
      await api.setLlmProvider(providerId);
      setLlmProvider(providerId);
      setOpen(false);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to switch provider";
      setError(message);
    } finally {
      setSwitching(false);
    }
  };

  const activeProvider = providers.find((p) => p.id === llmProvider);
  const activeModel = activeProvider?.model || "";
  const isActiveAvailable = activeProvider?.available ?? true;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setOpen(!open)}
        disabled={loading}
        className={cn(
          "flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs w-full",
          "bg-elevated hover:bg-highlight transition-colors",
          !isActiveAvailable && "border border-danger/30",
        )}
      >
        {loading ? (
          <Loader2 className="w-4 h-4 animate-spin text-muted shrink-0" />
        ) : llmProvider === "ollama" ? (
          <Laptop className="w-4 h-4 text-accent shrink-0" />
        ) : (
          <Cloud className="w-4 h-4 shrink-0" />
        )}
        <div className="flex flex-col items-start min-w-0 flex-1">
          <span className="text-foreground font-medium truncate w-full text-left">
            {activeProvider?.label || llmProvider}
          </span>
          <span className="text-subtle truncate w-full text-left font-mono text-[11px]">
            {activeModel}
          </span>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {!isActiveAvailable && <AlertCircle className="w-4 h-4 text-danger" />}
          <ChevronDown
            className={cn(
              "w-4 h-4 text-muted transition-transform",
              open && "rotate-180",
            )}
          />
        </div>
      </button>

      {open && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-elevated border border-border rounded-lg shadow-lg z-50 overflow-hidden">
          {providers.length === 0 && !loading && (
            <div className="px-3 py-2 text-xs text-muted">No providers found</div>
          )}
          {providers.map((p) => (
            <button
              key={p.id}
              onClick={() => p.available && handleSelect(p.id)}
              disabled={!p.available || switching}
              className={cn(
                "w-full text-left px-3 py-3 flex items-start gap-3 transition-colors",
                p.available
                  ? "hover:bg-highlight cursor-pointer"
                  : "opacity-40 cursor-not-allowed",
                p.id === llmProvider && "bg-highlight",
              )}
            >
              <div className="mt-0.5 shrink-0">
                {p.type === "local" ? (
                  <Laptop className="w-4 h-4 text-accent" />
                ) : (
                  <Cloud className="w-4 h-4" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-foreground">{p.label}</span>
                  {p.id === llmProvider && <Check className="w-4 h-4 text-accent" />}
                  {!p.available && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-danger/10 text-danger font-medium">
                      Unavailable
                    </span>
                  )}
                </div>
                <span className="text-[11px] text-subtle font-mono">{p.model}</span>
                {p.error && (
                  <p className="text-[11px] text-danger/70 mt-0.5 leading-relaxed">{p.error}</p>
                )}
                {p.available && p.id !== llmProvider && (
                  <p className="text-[11px] text-success/70 mt-0.5">Ready to use</p>
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
