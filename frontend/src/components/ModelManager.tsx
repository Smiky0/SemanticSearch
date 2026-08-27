import { useState, useEffect } from "react";
import { api } from "../services/api";
import type { ModelConfig } from "../schemas";
import {
  Plus,
  Trash2,
  Loader2,
  Check,
  X,
  Cloud,
  Server,
  Pencil,
  AlertCircle,
  Zap,
} from "lucide-react";
import { cn } from "../lib/utils";

const PROVIDER_PRESETS: Record<
  string,
  {
    label: string;
    type: "cloud" | "local";
    placeholder_key?: string;
    placeholder_model?: string;
    placeholder_embedding?: string;
    default_url?: string;
  }
> = {
  gemini: {
    label: "Google Gemini",
    type: "cloud",
    placeholder_key: "AIza...",
    placeholder_model: "gemini-2.5-flash",
    placeholder_embedding: "gemini-embedding-001",
  },
  openai: {
    label: "OpenAI",
    type: "cloud",
    placeholder_key: "sk-...",
    placeholder_model: "gpt-4o-mini",
    placeholder_embedding: "text-embedding-3-small",
  },
  anthropic: {
    label: "Anthropic Claude",
    type: "cloud",
    placeholder_key: "sk-ant-...",
    placeholder_model: "claude-sonnet-4-20250514",
  },
  ollama: {
    label: "Ollama (Local)",
    type: "local",
    placeholder_model: "qwen2.5-coder:3b",
    placeholder_embedding: "nomic-embed-text",
    default_url: "http://localhost:11434",
  },
  custom: {
    label: "Custom (OpenAI-compat)",
    type: "cloud",
    placeholder_model: "model-name",
    default_url: "http://localhost:8000",
  },
};

const EMPTY_FORM: Partial<ModelConfig> = {
  name: "",
  type: "cloud",
  provider: "gemini",
  api_key: "",
  base_url: "",
  llm_model: "",
  llm_max_tokens: 8192,
  llm_temperature: 0.7,
  embedding_model: "",
  embedding_dimensions: 768,
  timeout: 120,
};

function ModelFormDialog({
  editingId,
  initialForm,
  onClose,
  onSaved,
}: {
  editingId: string | null;
  initialForm: Partial<ModelConfig>;
  onClose: () => void;
  onSaved: (model: ModelConfig) => void;
}) {
  const [form, setForm] = useState<Partial<ModelConfig>>(initialForm);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleProviderChange = (provider: string) => {
    const preset = PROVIDER_PRESETS[provider];
    if (!preset) return;
    setForm((f) => ({
      ...f,
      provider: provider as ModelConfig["provider"],
      type: preset.type,
      base_url: preset.default_url || "",
      llm_model: preset.placeholder_model || "",
      embedding_model: preset.placeholder_embedding || "",
    }));
  };

  const handleSave = async () => {
    if (!form.name?.trim()) {
      setError("Name is required");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      let model: ModelConfig;
      if (editingId) {
        model = await api.updateModel(editingId, form);
      } else {
        model = await api.createModel(form);
      }
      onSaved(model);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save model");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-surface border border-border rounded-xl shadow-2xl w-[440px] max-h-[80vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-border">
          <h2 className="text-sm font-medium">{editingId ? "Edit Model" : "Add Model"}</h2>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-elevated text-muted hover:text-foreground">
            <X className="w-4 h-4" />
          </button>
        </div>

        {error && (
          <div className="mx-5 mt-3 px-3 py-2 bg-danger/10 border border-danger/20 rounded-lg flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-danger shrink-0" />
            <p className="text-xs text-danger flex-1">{error}</p>
          </div>
        )}

        {/* Form */}
        <div className="flex-1 overflow-auto px-5 py-4 space-y-4">
          {/* Name */}
          <div>
            <label className="text-xs text-muted mb-1.5 block">Name</label>
            <input
              type="text"
              value={form.name || ""}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="My Gemini instance"
              className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>

          {/* Provider */}
          <div>
            <label className="text-xs text-muted mb-1.5 block">Provider</label>
            <div className="grid grid-cols-5 gap-2">
              {Object.entries(PROVIDER_PRESETS).map(([key, preset]) => (
                <button
                  key={key}
                  onClick={() => handleProviderChange(key)}
                  className={cn(
                    "px-2 py-2 text-xs rounded-lg border transition-colors text-center font-medium",
                    form.provider === key
                      ? "border-accent bg-accent/10 text-accent"
                      : "border-border bg-background text-muted hover:text-foreground hover:border-border",
                  )}
                >
                  {key === "anthropic" ? "Claude" : preset.label.split(" ")[0]}
                </button>
              ))}
            </div>
          </div>

          {/* API Key */}
          {form.type === "cloud" && form.provider !== "custom" && (
            <div>
              <label className="text-xs text-muted mb-1.5 block">API Key</label>
              <input
                type="password"
                value={form.api_key || ""}
                onChange={(e) => setForm((f) => ({ ...f, api_key: e.target.value }))}
                placeholder={PROVIDER_PRESETS[form.provider || "gemini"]?.placeholder_key}
                className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-1 focus:ring-accent font-mono"
              />
            </div>
          )}

          {/* Base URL */}
          {(form.type === "local" || form.provider === "custom") && (
            <div>
              <label className="text-xs text-muted mb-1.5 block">Base URL</label>
              <input
                type="text"
                value={form.base_url || ""}
                onChange={(e) => setForm((f) => ({ ...f, base_url: e.target.value }))}
                placeholder={PROVIDER_PRESETS[form.provider || "ollama"]?.default_url}
                className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-1 focus:ring-accent font-mono"
              />
            </div>
          )}

          {/* LLM Model */}
          <div>
            <label className="text-xs text-muted mb-1.5 block">LLM Model</label>
            <input
              type="text"
              value={form.llm_model || ""}
              onChange={(e) => setForm((f) => ({ ...f, llm_model: e.target.value }))}
              placeholder={PROVIDER_PRESETS[form.provider || "gemini"]?.placeholder_model}
              className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>

          {/* Embedding Model */}
          <div>
            <label className="text-xs text-muted mb-1.5 block">
              Embedding Model <span className="text-subtle">(for search)</span>
            </label>
            <input
              type="text"
              value={form.embedding_model || ""}
              onChange={(e) => setForm((f) => ({ ...f, embedding_model: e.target.value }))}
              placeholder={PROVIDER_PRESETS[form.provider || "gemini"]?.placeholder_embedding}
              className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>

          {/* Advanced */}
          <div className="border-t border-border pt-3">
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-xs text-muted hover:text-foreground transition-colors"
            >
              {showAdvanced ? "Hide" : "Show"} advanced options
            </button>

            {showAdvanced && (
              <div className="grid grid-cols-2 gap-3 mt-3">
                <div>
                  <label className="text-xs text-muted mb-1.5 block">Embedding Dimensions</label>
                  <input
                    type="number"
                    value={form.embedding_dimensions || 768}
                    onChange={(e) => setForm((f) => ({ ...f, embedding_dimensions: parseInt(e.target.value) || 768 }))}
                    className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-1 focus:ring-accent"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted mb-1.5 block">Max Tokens</label>
                  <input
                    type="number"
                    value={form.llm_max_tokens || 8192}
                    onChange={(e) => setForm((f) => ({ ...f, llm_max_tokens: parseInt(e.target.value) || 8192 }))}
                    className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-1 focus:ring-accent"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted mb-1.5 block">Temperature</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="2"
                    value={form.llm_temperature || 0.7}
                    onChange={(e) => setForm((f) => ({ ...f, llm_temperature: parseFloat(e.target.value) || 0.7 }))}
                    className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-1 focus:ring-accent"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted mb-1.5 block">Timeout (seconds)</label>
                  <input
                    type="number"
                    value={form.timeout || 120}
                    onChange={(e) => setForm((f) => ({ ...f, timeout: parseInt(e.target.value) || 120 }))}
                    className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-1 focus:ring-accent"
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-3.5 border-t border-border flex items-center justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium rounded-lg border border-border text-muted hover:text-foreground hover:bg-elevated transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !form.name?.trim()}
            className="px-4 py-2 text-sm font-medium bg-primary text-background rounded-lg hover:opacity-90 disabled:opacity-40 transition-opacity flex items-center gap-2"
          >
            {saving && <Loader2 className="w-4 h-4 animate-spin" />}
            {editingId ? "Update" : "Add Model"}
          </button>
        </div>
      </div>
    </div>
  );
}

export function ModelManager() {
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formDraft, setFormDraft] = useState<Partial<ModelConfig>>(EMPTY_FORM);
  const [healthCache, setHealthCache] = useState<
    Record<string, { available: boolean; error?: string; models?: string[] }>
  >({});
  const [error, setError] = useState<string | null>(null);

  const loadModels = async () => {
    try {
      const data = await api.listModels();
      setModels(data);
    } catch {
      setError("Failed to load models");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadModels();
  }, []);

  const checkHealth = async (modelId: string) => {
    try {
      const result = await api.checkModelHealth(modelId);
      setHealthCache((prev) => ({ ...prev, [modelId]: result }));
    } catch {
      setHealthCache((prev) => ({
        ...prev,
        [modelId]: { available: false, error: "Health check failed" },
      }));
    }
  };

  const handleDelete = async (modelId: string) => {
    try {
      await api.deleteModel(modelId);
      setModels((prev) => prev.filter((m) => m.id !== modelId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete model");
    }
  };

  const handleActivate = async (modelId: string) => {
    try {
      await api.activateModel(modelId);
      setModels((prev) => prev.map((m) => ({ ...m, active: m.id === modelId })));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to activate model");
    }
  };

  const openAdd = () => {
    setEditingId(null);
    setFormDraft({ ...EMPTY_FORM });
    setShowDialog(true);
  };

  const openEdit = (model: ModelConfig) => {
    setEditingId(model.id);
    setFormDraft({ ...model });
    setShowDialog(true);
  };

  const handleModelSaved = (model: ModelConfig) => {
    if (editingId) {
      setModels((prev) => prev.map((m) => (m.id === editingId ? model : m)));
    } else {
      setModels((prev) => [...prev, model]);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-4">
        <Loader2 className="w-4 h-4 text-accent animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {showDialog && (
        <ModelFormDialog
          editingId={editingId}
          initialForm={formDraft}
          onClose={() => setShowDialog(false)}
          onSaved={handleModelSaved}
        />
      )}

      {error && (
        <div className="flex items-center gap-2 px-2 py-1.5 bg-danger/10 border border-danger/20 rounded-md">
          <AlertCircle className="w-4 h-4 text-danger shrink-0" />
          <p className="text-xs text-danger flex-1 truncate">{error}</p>
          <button onClick={() => setError(null)} className="text-danger/60 hover:text-danger shrink-0">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Model list */}
      {models.length > 0 && (
        <div className="space-y-1">
          {models.map((model) => {
            const health = healthCache[model.id];
            return (
              <div
                key={model.id}
                className={cn(
                  "px-2.5 py-2 rounded-lg border transition-colors",
                  model.active
                    ? "border-accent/30 bg-accent/5"
                    : "border-border/50 hover:bg-elevated/50",
                )}
              >
                <div className="flex items-center gap-2">
                  {model.type === "cloud" ? (
                    <Cloud className="w-4 h-4 text-accent shrink-0" />
                  ) : (
                    <Server className="w-4 h-4 text-accent shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-medium truncate">{model.name}</span>
                      {model.active && (
                        <span className="text-[10px] px-1 py-0.5 rounded bg-accent/10 text-accent font-medium shrink-0">
                          Active
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-subtle truncate">
                      {model.provider} &middot; {model.llm_model || "no model"}
                    </p>
                  </div>
                  <div className="flex items-center gap-0.5 shrink-0">
                    {health && (
                      <span
                        className={cn(
                          "text-[10px] px-1 py-0.5 rounded font-medium",
                          health.available
                            ? "bg-success/10 text-success"
                            : "bg-danger/10 text-danger",
                        )}
                      >
                        {health.available ? "OK" : "Err"}
                      </span>
                    )}
                    <button
                      onClick={() => checkHealth(model.id)}
                      className="p-1.5 rounded hover:bg-elevated text-subtle hover:text-foreground"
                      title="Check health"
                    >
                      <Zap className="w-4 h-4" />
                    </button>
                    {!model.active && (
                      <button
                        onClick={() => handleActivate(model.id)}
                        className="p-1.5 rounded hover:bg-elevated text-subtle hover:text-foreground"
                        title="Set as active"
                      >
                        <Check className="w-4 h-4" />
                      </button>
                    )}
                    <button
                      onClick={() => openEdit(model)}
                      className="p-1.5 rounded hover:bg-elevated text-subtle hover:text-foreground"
                      title="Edit"
                    >
                      <Pencil className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(model.id)}
                      className="p-1.5 rounded hover:bg-danger/10 text-subtle hover:text-danger"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                {health && health.error && (
                  <p className="text-[11px] text-danger/80 mt-1 ml-6">{health.error}</p>
                )}
              </div>
            );
          })}
        </div>
      )}

      {models.length === 0 && (
        <p className="text-[11px] text-subtle text-center py-1">
          No models configured yet
        </p>
      )}

      {/* Add button */}
      <button
        onClick={openAdd}
        className="w-full flex items-center justify-center gap-2 px-3 py-2 text-xs font-medium border border-dashed border-border rounded-lg text-muted hover:text-foreground hover:border-accent/50 hover:bg-elevated/50 transition-colors"
      >
        <Plus className="w-4 h-4" />
        Add Model
      </button>
    </div>
  );
}
