import React from "react";

interface Props {
  code: string;
  language?: string;
  startLine?: number;
}

function tokenizeLine(line: string): React.ReactNode[] {
  const tokens: React.ReactNode[] = [];
  let remaining = line;
  let key = 0;

  const patterns: [RegExp, string][] = [
    [/^(#.*)$/, "tok-comment"],
    [/^(\/\/.*)$/, "tok-comment"],
    [/^(\/\*[\s\S]*?\*\/)/, "tok-comment"],
    [/^("""[\s\S]*?"""|'''[\s\S]*?''')/, "tok-string"],
    [/^("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')/, "tok-string"],
    [/^(@\w+)/, "tok-decorator"],
    [/^\b(import|from|as|def|class|return|if|elif|else|for|while|try|except|finally|with|yield|raise|pass|break|continue|and|or|not|is|in|lambda|async|await|global|nonlocal|assert|del)\b/, "tok-keyword"],
    [/^\b(const|let|var|function|export|default|new|typeof|instanceof|void|delete|throw|catch|switch|case|do|typeof|interface|type|enum|extends|implements|abstract|readonly|private|protected|public|static|override|declare|namespace|module|require|true|false|null|undefined|this|super)\b/, "tok-keyword"],
    [/^\b(True|False|None|self|cls)\b/, "tok-self"],
    [/^\b(print|len|range|str|int|float|list|dict|set|tuple|bool|type|isinstance|hasattr|getattr|setattr|super|property|staticmethod|classmethod|enumerate|zip|map|filter|sorted|reversed|any|all|min|max|sum|abs|round|open|input|format|Exception|ValueError|TypeError|KeyError|IndexError|AttributeError|RuntimeError|StopIteration|NotImplementedError)\b/, "tok-builtin"],
    [/^\b([A-Z]\w*)\b/, "tok-class"],
    [/^\b(\d+\.?\d*(?:e[+-]?\d+)?)\b/, "tok-number"],
    [/^(\w+)(?=\s*\()/, "tok-function"],
    [/^(\w+)(?=\s*:)/, "tok-property"],
    [/^(\w+)/, "tok-variable"],
    [/^([{}()\[\]])/, ""],
    [/^([=<>!]+|[+\-*/%|&^~])/, "tok-operator"],
    [/^([.,;:])/, ""],
    [/^\s+/, ""],
  ];

  while (remaining.length > 0) {
    let matched = false;
    for (const [pattern, cls] of patterns) {
      const m = remaining.match(pattern);
      if (m) {
        tokens.push(
          cls ? (
            <span key={key++} className={cls}>
              {m[0]}
            </span>
          ) : (
            <span key={key++}>{m[0]}</span>
          ),
        );
        remaining = remaining.slice(m[0].length);
        matched = true;
        break;
      }
    }
    if (!matched) {
      tokens.push(<span key={key++}>{remaining[0]}</span>);
      remaining = remaining.slice(1);
    }
  }

  return tokens;
}

export function CodeViewer({ code, language: _language, startLine = 1 }: Props) {
  const lines = code.split("\n");

  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 overflow-auto">
        <div className="one-dark">
          <pre className="!bg-[#282c34] !m-0 !rounded-none !py-3">
            {lines.map((line, i) => (
              <div key={i} className="code-line">
                <span className="line-number">{startLine + i}</span>
                <span className="code-content">{tokenizeLine(line)}</span>
              </div>
            ))}
          </pre>
        </div>
      </div>
    </div>
  );
}
