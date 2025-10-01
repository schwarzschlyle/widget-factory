import React, { useMemo, useState } from "react";
import * as Babel from "@babel/standalone";

type BabelTranspilerProps = {
  code: string;
  componentName?: string;
  headersMap?: object;
  darkMode?: boolean;
};

export const BabelTranspiler: React.FC<BabelTranspilerProps> = ({
  code,
  componentName = "WidgetComponent",
  headersMap,
  darkMode,
}) => {
  const [errorInfo, setErrorInfo] = useState<{
    error: any;
    code: string;
    transpiled?: string;
  } | null>(null);

  const TranspiledComponent = useMemo(() => {
    try {
      // Transpile the code from TSX/JSX to JS
      const transpiled = Babel.transform(code, {
        presets: ["react", "typescript"],
        filename: "widget.tsx",
      }).code;
      // eslint-disable-next-line no-console
      console.log("[BabelTranspiler] Transpiled code:\n", transpiled);

      // eslint-disable-next-line no-new-func
      const exports = {};
      const require = (mod: string) => {
        if (mod === "react") return React;
        throw new Error("Only 'react' can be required");
      };
      // Wrap the transpiled code in a function to simulate a module
      const func = new Function("exports", "require", "React", `${transpiled}; return exports;`);
      const moduleExports = func(exports, require, React);

      setErrorInfo(null);
      // Return the exported component
      return moduleExports[componentName] || null;
    } catch (err: any) {
      // Verbose logging
      // eslint-disable-next-line no-console
      console.error("Babel transpilation error:", err);
      // eslint-disable-next-line no-console
      console.error("Code that caused error:\n", code);
      setErrorInfo({
        error: err,
        code,
      });
      return null;
    }
  }, [code, componentName]);

  const [showDetails, setShowDetails] = useState(false);

  if (!TranspiledComponent) {
    // Prominently log the error and stack trace
    if (errorInfo) {
      // eslint-disable-next-line no-console
      console.error("[BabelTranspiler] Transpilation failed:", errorInfo.error?.message);
      // eslint-disable-next-line no-console
      if (errorInfo.error?.stack) console.error("[BabelTranspiler] Stack trace:", errorInfo.error.stack);
      // eslint-disable-next-line no-console
      console.error("[BabelTranspiler] Code that caused error:\n", errorInfo.code);
    }
    return (
      <div style={{ color: "red", fontFamily: "monospace", fontSize: 14, padding: 8 }}>
        <strong>Failed to transpile component.</strong>
        {errorInfo && (
          <div>
            <button
              style={{
                marginTop: 8,
                padding: "2px 8px",
                fontSize: 12,
                cursor: "pointer",
                borderRadius: 4,
                border: "1px solid #ccc",
                background: "#fff",
              }}
              onClick={() => setShowDetails((v) => !v)}
            >
              {showDetails ? "Hide Details" : "Show Details"}
            </button>
            {showDetails && (
              <div style={{ marginTop: 8, maxHeight: 400, overflow: "auto", background: "#f9f9f9", border: "1px solid #eee", padding: 8 }}>
                <div>
                  <strong>Error:</strong> {errorInfo.error?.message}
                </div>
                <div>
                  <strong>Stack:</strong>
                  <pre style={{ whiteSpace: "pre-wrap" }}>{errorInfo.error?.stack}</pre>
                </div>
                <div>
                  <strong>Code:</strong>
                  <pre style={{ whiteSpace: "pre-wrap", fontSize: 12 }}>{errorInfo.code}</pre>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  return <TranspiledComponent headersMap={headersMap} darkMode={darkMode} />;
};

export default BabelTranspiler;
