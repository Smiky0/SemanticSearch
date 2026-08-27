import { useEffect, useState } from "react";

const SEARCH_MESSAGES = [
  "Searching through code...",
  "Scanning symbols...",
  "Looking through repositories...",
  "Finding relevant code...",
];

const EXPLAIN_MESSAGES = [
  "Analyzing code structure...",
  "Reading through symbols...",
  "Understanding relationships...",
  "Summarizing findings...",
  "Generating explanation...",
  "Building response...",
];

const TRACE_MESSAGES = [
  "Tracing code flow...",
  "Following function calls...",
  "Mapping execution paths...",
  "Analyzing dependencies...",
  "Building flow diagram...",
  "Connecting the dots...",
];

const MESSAGE_SETS = {
  search: SEARCH_MESSAGES,
  explain: EXPLAIN_MESSAGES,
  trace: TRACE_MESSAGES,
} as const;

interface Props {
  mode: "search" | "explain" | "trace";
}

export function LoadingIndicator({ mode }: Props) {
  const messages = MESSAGE_SETS[mode];
  const [index, setIndex] = useState(0);

  useEffect(() => {
    setIndex(0);
    const interval = setInterval(() => {
      setIndex((prev) => (prev + 1) % messages.length);
    }, 2000);
    return () => clearInterval(interval);
  }, [mode, messages.length]);

  return (
    <div className="flex items-center justify-center h-64">
      <div className="flex flex-col items-center gap-3">
        <div className="relative w-8 h-8">
          <div className="absolute inset-0 border-2 border-accent/20 rounded-full" />
          <div className="absolute inset-0 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        </div>
        <div className="text-center">
          <p className="text-sm text-foreground font-medium">{messages[index]}</p>
          <p className="text-xs text-subtle mt-1">
            {mode === "explain" && "This may take a moment"}
            {mode === "trace" && "Mapping code relationships"}
            {mode === "search" && ""}
          </p>
        </div>
      </div>
    </div>
  );
}
