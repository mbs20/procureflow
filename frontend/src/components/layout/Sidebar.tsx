import React from "react";
import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
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
  key: string;
  defaultName: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

const navItems: NavItem[] = [
  { key: "overview", defaultName: "Overview", href: "/", icon: Activity },
  { key: "rfqs", defaultName: "RFQs & Requests", href: "/rfqs", icon: Layers },
  { key: "intake", defaultName: "Document Ingestion", href: "/quotations", icon: FileText },
  { key: "review", defaultName: "Review & Leveling", href: "/review", icon: Sliders },
  { key: "matrix", defaultName: "Comparison Matrix", href: "/matrix", icon: Scale },
  { key: "scoring", defaultName: "Scoring & Evaluation", href: "/scoring", icon: Sliders },
  { key: "decisions", defaultName: "Decisions & Awards", href: "/decisions", icon: CheckCircle2 },
  { key: "audit", defaultName: "Audit Trail", href: "/audit", icon: History },
];

export const Sidebar: React.FC = () => {
  const location = useLocation();
  const { t } = useTranslation();

  return (
    <aside className="w-full md:w-64 md:shrink-0 border-r border-border/40 bg-card/30 flex flex-col justify-between p-4 md:min-h-[calc(100vh-4rem)]">
      <div className="space-y-6">
        <div>
          <div className="px-3 mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            {t("nav.pipelineTitle", "Procurement Pipeline")}
          </div>
          <nav className="flex overflow-x-auto gap-1 md:block md:space-y-1">
            {navItems.map((item) => {
              const isActive = location.pathname === item.href;
              const Icon = item.icon;
              const label = t(`nav.${item.key}`, item.defaultName);
              return (
                <Link
                  key={item.key}
                  to={item.href}
                  className={`flex shrink-0 whitespace-nowrap items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? "bg-primary text-primary-foreground shadow-md shadow-primary/25"
                      : "text-muted-foreground hover:bg-secondary/70 hover:text-foreground"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon className={`h-4 w-4 ${isActive ? "text-primary-foreground" : "text-muted-foreground"}`} />
                    <span>{label}</span>
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

    </aside>
  );
};
