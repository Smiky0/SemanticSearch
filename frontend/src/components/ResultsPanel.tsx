import { useStore } from "../store";
import { CodeViewer } from "./CodeViewer";
import { FileCode, BookOpen } from "lucide-react";

export function ResultsPanel() {
  const { searchResults, explanation, loading, setSelectedNode, selectedNode } = useStore();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center gap-3 text-muted">
          <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          <span className="text-sm">Searching...</span>
        </div>
      </div>
    );
  }

  if (explanation) {
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
                className="block text-left text-xs text-accent hover:underline mb-1 font-mono"
              >
                {src.file_path}:{src.start_line}&ndash;{src.end_line}{" "}
                <span className="text-muted">{src.symbol_name}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  if (searchResults.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-muted text-sm">
        No results. Try a search query above.
      </div>
    );
  }

  return (
    <div className="divide-y divide-border">
      {searchResults.map((r) => (
        <button
          key={r.node.id}
          onClick={() => setSelectedNode(r.node)}
          className={`w-full text-left p-4 hover:bg-elevated/50 transition-colors ${
            selectedNode?.id === r.node.id ? "bg-elevated" : ""
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <FileCode className="w-3.5 h-3.5 text-accent shrink-0" />
              <span className="text-sm font-medium">{r.node.symbol_name}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs px-1.5 py-0.5 rounded bg-elevated text-muted capitalize">
                {r.node.symbol_type}
              </span>
              <span className="text-xs text-accent font-mono">
                {(r.score * 100).toFixed(1)}%
              </span>
            </div>
          </div>
          <div className="text-xs text-subtle mb-2 font-mono ml-5">
            {r.node.file_path}:{r.node.start_line}&ndash;{r.node.end_line}
          </div>
          <div className="one-dark ml-5">
            <pre className="!rounded-md !text-xs max-h-24 overflow-hidden">
              <code>
                {r.node.source_code.slice(0, 300)}
                {r.node.source_code.length > 300 ? "..." : ""}
              </code>
            </pre>
          </div>
        </button>
      ))}
    </div>
  );
}

export function CodePanel() {
  const { selectedNode, explanation } = useStore();

  if (selectedNode) {
    return (
      <div className="h-full flex flex-col">
        <div className="px-4 py-2.5 border-b border-border bg-surface">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileCode className="w-4 h-4 text-accent" />
              <span className="text-sm font-medium">{selectedNode.symbol_name}</span>
              <span className="text-xs px-1.5 py-0.5 rounded bg-elevated text-muted capitalize">
                {selectedNode.symbol_type}
              </span>
            </div>
            <span className="text-xs text-subtle font-mono">
              {selectedNode.file_path}:{selectedNode.start_line}&ndash;{selectedNode.end_line}
            </span>
          </div>
          {selectedNode.docstring && (
            <p className="text-xs text-muted mt-1 italic">{selectedNode.docstring}</p>
          )}
        </div>
        <CodeViewer
          code={selectedNode.source_code}
          language={selectedNode.language}
          startLine={selectedNode.start_line}
        />
      </div>
    );
  }

  if (explanation) {
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
              <div key={i} className="text-xs font-mono text-muted mb-1">
                {src.file_path}:{src.start_line}&ndash;{src.end_line}{" "}
                <span className="text-foreground">{src.symbol_name}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center h-full text-muted">
      <div className="text-center">
        <FileCode className="w-8 h-8 mx-auto mb-3 text-subtle" />
        <p className="text-sm">Select a result to view code</p>
        <p className="text-xs mt-1 text-subtle">or run an explanation to see analysis</p>
      </div>
    </div>
  );
}
