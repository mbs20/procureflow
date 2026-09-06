import React from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Layers,
  FileText,
  Sliders,
  Scale,
  CheckCircle2,
  History,
  Activity,
} from "lucide-react";

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

const navItems: NavItem[] = [
  { name: "Overview", href: "/", icon: Activity },
  { name: "RFQs & Requests", href: "/rfqs", icon: Layers },
  { name: "Document Ingestion", href: "/quotations", icon: FileText },
  { name: "Review & Leveling", href: "/review", icon: Sliders },
  { name: "Comparison Matrix", href: "/matrix", icon: Scale },
  { name: "Decisions & Awards", href: "/decisions", icon: CheckCircle2 },
  { name: "Audit Trail", href: "/audit", icon: History },
];

export const Sidebar: React.FC = () => {
  const location = useLocation();

  return (
    <aside className="w-64 border-r border-border/40 bg-card/30 flex flex-col justify-between p-4 min-h-[calc(100vh-4rem)]">
      <div className="space-y-6">
        <div>
          <div className="px-3 mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Procurement Pipeline
          </div>
          <nav className="space-y-1">
            {navItems.map((item) => {
              const isActive = location.pathname === item.href;
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? "bg-primary text-primary-foreground shadow-md shadow-primary/25"
                      : "text-muted-foreground hover:bg-secondary/70 hover:text-foreground"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon className={`h-4 w-4 ${isActive ? "text-primary-foreground" : "text-muted-foreground"}`} />
                    <span>{item.name}</span>
                  </div>
                  {item.badge && (
                    <span className="rounded bg-primary/20 px-1.5 py-0.5 text-[10px] font-bold">
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>

      <div className="rounded-xl border border-border/60 bg-secondary/30 p-3.5 text-xs text-muted-foreground">
        <div className="font-semibold text-foreground mb-1 flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
          Engine Core Ready
        </div>
        <p className="text-[11px] leading-relaxed">
          Deterministic scoring & schema-enforced document extraction active.
        </p>
      </div>
    </aside>
  );
};
