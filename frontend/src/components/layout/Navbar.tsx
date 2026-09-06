import { ShieldCheck, BookOpen, Github } from "lucide-react";

export const Navbar: React.FC = () => {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/40 glass-panel">
      <div className="container flex h-16 max-w-7xl items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 shadow-lg shadow-blue-500/20">
            <ShieldCheck className="h-6 w-6 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-display text-lg font-bold tracking-tight text-white">
                ProcureFlow
              </span>
              <span className="rounded-md bg-blue-500/10 px-2 py-0.5 text-xs font-semibold text-blue-400 border border-blue-500/20">
                OSS v0.1
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              Explainable RFQ Comparison & Decision Engine
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2 rounded-lg bg-secondary/60 px-3 py-1.5 text-xs font-medium text-foreground hover:bg-secondary hover:text-white transition-colors border border-border"
          >
            <BookOpen className="h-3.5 w-3.5 text-blue-400" />
            API Docs
          </a>
          <a
            href="https://github.com/mbs20/procureflow"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2 rounded-lg bg-secondary/60 px-3 py-1.5 text-xs font-medium text-foreground hover:bg-secondary hover:text-white transition-colors border border-border"
          >
            <Github className="h-3.5 w-3.5 text-white" />
            GitHub
          </a>
        </div>
      </div>
    </header>
  );
};
