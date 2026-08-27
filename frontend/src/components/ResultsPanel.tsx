import Markdown from "react-markdown";
import { useStore } from "../store";
import { CodeViewer } from "./CodeViewer";
import { LoadingIndicator } from "./LoadingIndicator";
import { FileCode, BookOpen, SearchX, AlertTriangle } from "lucide-react";

function MarkdownContent({ content }: { content: string }) {
  return (
    <Markdown
      components={{
        h1: ({ children }) => (
          <h1 className="text-lg font-semibold mt-6 mb-3 text-foreground">{children}</h1>
        ),
        h2: ({ children }) => (
          <h2 className="text-base font-semibold mt-5 mb-2 text-foreground">{children}</h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-sm font-semibold mt-4 mb-2 text-foreground">{children}</h3>
        ),
        p: ({ children }) => (
          <p className="text-sm leading-relaxed mb-3 text-foreground">{children}</p>
        ),
        ul: ({ children }) => (
          <ul className="list-disc list-inside mb-3 space-y-1 text-sm text-foreground">
            {children}
          </ul>
        ),
        ol: ({ children }) => (
          <ol className="list-decimal list-inside mb-3 space-y-1 text-sm text-foreground">
            {children}
          </ol>
        ),
        li: ({ children }) => <li className="leading-relaxed">{children}</li>,
        code: ({ children, className }) => {
          const isInline = !className;
          if (isInline) {
            return (
              <code className="px-1.5 py-0.5 rounded bg-elevated text-accent font-mono text-xs">
                {children}
              </code>
            );
          }
          return (
            <div className="one-dark my-3">
              <pre className="!rounded-lg !text-xs">
                <code className={className}>{children}</code>
              </pre>
            </div>
          );
        },
        pre: ({ children }) => <>{children}</>,
        blockquote: ({ children }) => (
          <blockquote className="border-l-2 border-accent pl-4 my-3 text-sm text-muted italic">
            {children}
          </blockquote>
        ),
        strong: ({ children }) => (
          <strong className="font-semibold text-foreground">{children}</strong>
        ),
        em: ({ children }) => <em className="italic text-foreground">{children}</em>,
        a: ({ children, href }) => (
          <a
            href={href}
            className="text-accent hover:underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            {children}
          </a>
        ),
        hr: () => <hr className="my-4 border-border" />,
        table: ({ children }) => (
          <div className="overflow-x-auto my-3">
            <table className="text-sm border border-border rounded-lg overflow-hidden">
              {children}
            </table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className="bg-elevated">{children}</thead>
        ),
        th: ({ children }) => (
          <th className="px-3 py-2 text-left text-xs font-medium text-muted border-b border-border">
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="px-3 py-2 text-sm border-b border-border">{children}</td>
        ),
      }}
    >
      {content}
    </Markdown>
  );
}

export function ResultsPanel() {
  const {
    searchResults,
    explanation,
    loading,
    loadingMode,
    error,
    setSelectedNode,
    selectedNode,
    selectedRepo,
    aiMode,
  } = useStore();

  if (loading && loadingMode) {
    return <LoadingIndicator mode={loadingMode} />;
  }

  if (explanation) {
    return (
      <div className="p-5">
        <div className="flex items-center gap-2 mb-4">
          <BookOpen className="w-4 h-4 text-accent" />
          <h3 className="text-sm font-medium">Explanation</h3>
        </div>
        <MarkdownContent content={explanation.answer} />
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

  // Error state (non-banner errors shown inline)
  if (error && !loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center max-w-xs">
          <AlertTriangle className="w-10 h-10 mx-auto mb-3 text-danger" />
          <p className="text-sm font-medium text-foreground mb-1">Something went wrong</p>
          <p className="text-xs text-subtle leading-relaxed">{error}</p>
          <p className="text-xs text-subtle mt-3">
            Try again, or switch to a different provider in the sidebar.
          </p>
        </div>
      </div>
    );
  }

  // Empty state
  if (searchResults.length === 0 && !explanation && !loading) {
    const hasRepo = selectedRepo && selectedRepo.status === "completed";
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center max-w-xs">
          <SearchX className="w-10 h-10 mx-auto mb-3 text-subtle" />
          {hasRepo ? (
            <>
              <p className="text-sm font-medium text-foreground mb-1">No results found</p>
              <p className="text-xs text-subtle leading-relaxed">
                {aiMode
                  ? "The LLM couldn't find relevant code for your question. Try rephrasing or ask about a specific function or file."
                  : "No matching code found. Try different keywords, or switch to Explain mode for a broader analysis."}
              </p>
            </>
          ) : (
            <>
              <p className="text-sm font-medium text-foreground mb-1">
                Select a repository to get started
              </p>
              <p className="text-xs text-subtle leading-relaxed">
                Pick a completed repository from the sidebar, then search or explain your code.
              </p>
            </>
          )}
        </div>
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
          <h3 className="text-sm font-medium">Explanation</h3>
        </div>
        <MarkdownContent content={explanation.answer} />
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
        <p className="text-xs mt-1 text-subtle">
          or run an explanation to see analysis
        </p>
      </div>
    </div>
  );
}
