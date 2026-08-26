import { useStore } from "../store";
import { api } from "../services/api";
import { BookOpen, ExternalLink } from "lucide-react";

export function ExplanationPanel() {
  const { explanation, selectedRepo, setSelectedNode } = useStore();

  const handleSourceClick = async (src: { file_path: string; symbol_name: string }) => {
    if (!selectedRepo) return;
    try {
      const results = await api.search(selectedRepo.id, src.symbol_name, 1);
      if (results.results.length > 0) {
        setSelectedNode(results.results[0].node);
      }
    } catch {
      // ignore
    }
  };

  if (!explanation) return null;

  return (
    <div className="p-5">
      <div className="flex items-center gap-2 mb-4">
        <BookOpen className="w-4 h-4 text-accent" />
        <h3 className="text-sm font-medium">Analysis</h3>
      </div>
      <div className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
        {explanation.answer}
      </div>
      {explanation.sources.length > 0 && (
        <div className="mt-6 border-t border-border pt-4">
          <p className="text-xs text-subtle uppercase tracking-wider font-medium mb-2">
            Sources
          </p>
          {explanation.sources.map((src, i) => (
            <button
              key={i}
              onClick={() => handleSourceClick(src)}
              className="flex items-center gap-1.5 text-xs text-accent hover:underline mb-1 font-mono"
            >
              <ExternalLink className="w-3 h-3" />
              {src.file_path}:{src.start_line}&ndash;{src.end_line}{" "}
              <span className="text-muted">{src.symbol_name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
