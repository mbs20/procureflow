import React from "react";
import { SensitivityResponse } from "../../api/scoring";
import { TrendingUp, GitCommit, Info } from "lucide-react";

interface SensitivitySweepChartProps {
  sensitivityData: SensitivityResponse | null;
  isLoading?: boolean;
}

export const SensitivitySweepChart: React.FC<SensitivitySweepChartProps> = ({
  sensitivityData,
  isLoading = false,
}) => {
  if (isLoading) {
    return (
      <div className="glass-card rounded-xl p-8 text-center text-muted-foreground flex flex-col items-center justify-center space-y-3">
        <div className="h-6 w-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        <span className="text-xs">Computing deterministic sensitivity sweep across parameter space...</span>
      </div>
    );
  }

  if (!sensitivityData || sensitivityData.data_points.length === 0) {
    return (
      <div className="glass-card rounded-xl p-6 text-center text-muted-foreground text-xs">
        Select a criterion and run sensitivity analysis to inspect rank trajectory and crossover points.
      </div>
    );
  }

  const { data_points, crossover_points, sweep_criterion } = sensitivityData;

  // Extract supplier IDs from the first data point
  const supplierIds = Object.keys(data_points[0].supplier_scores);

  // Palette of colors for lines
  const colors = [
    "#38bdf8", // Sky blue
    "#34d399", // Emerald
    "#a78bfa", // Purple
    "#fbbf24", // Amber
    "#f87171", // Rose
    "#60a5fa", // Blue
  ];

  return (
    <div className="glass-card rounded-xl p-5 space-y-5 border border-border/80">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border/60 pb-3">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-emerald-400" />
            Sensitivity Trajectory: {sweep_criterion}
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Evaluating score stability as weight scales from {(data_points[0].weight * 100).toFixed(0)}% to{" "}
            {(data_points[data_points.length - 1].weight * 100).toFixed(0)}% with proportional redistribution.
          </p>
        </div>
      </div>

      {/* Crossover Highlights */}
      {crossover_points.length > 0 ? (
        <div className="space-y-2">
          <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
            <GitCommit className="h-3.5 w-3.5 text-primary" />
            Rank Crossover Points ({crossover_points.length})
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {crossover_points.map((cp, idx) => (
              <div
                key={idx}
                className="p-3 rounded-lg border border-primary/30 bg-primary/5 flex items-start gap-2 text-xs"
              >
                <div className="h-2 w-2 rounded-full bg-primary mt-1 shrink-0" />
                <div className="space-y-0.5">
                  <div className="font-semibold text-white font-mono">
                    Weight: {(cp.weight * 100).toFixed(1)}% (Score: {cp.score_at_crossover.toFixed(2)})
                  </div>
                  <div className="text-muted-foreground">
                    {cp.description || (
                      <>
                        <span className="text-foreground font-medium">{cp.supplier_a_name}</span> ranks equal/crossover with{" "}
                        <span className="text-foreground font-medium">{cp.supplier_b_name}</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="p-3 rounded-lg bg-secondary/30 border border-border/40 text-xs text-muted-foreground flex items-center gap-2">
          <Info className="h-4 w-4 text-muted-foreground shrink-0" />
          <span>No rank inversions observed within this weight range; rankings are stable.</span>
        </div>
      )}

      {/* SVG Trajectory Chart */}
      <div className="space-y-2">
        <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
          Score Trajectory Curves (0.00 – 100.00)
        </div>
        <div className="w-full bg-card/60 p-4 rounded-xl border border-border/70 overflow-x-auto">
          <svg viewBox="0 0 700 240" className="w-full h-48 overflow-visible font-mono text-[10px]">
            {/* Grid Lines */}
            {[0, 25, 50, 75, 100].map((score) => {
              const y = 200 - (score / 100) * 180;
              return (
                <g key={score}>
                  <line x1="40" y1={y} x2="680" y2={y} stroke="currentColor" strokeOpacity="0.1" strokeDasharray="3 3" />
                  <text x="32" y={y + 3} textAnchor="end" fill="currentColor" fillOpacity="0.5">
                    {score}
                  </text>
                </g>
              );
            })}

            {/* Trajectory Paths for each supplier */}
            {supplierIds.map((suppId, suppIdx) => {
              const color = colors[suppIdx % colors.length];
              const points = data_points.map((pt, i) => {
                const x = 50 + (i / (data_points.length - 1)) * 620;
                const score = pt.supplier_scores[suppId] || 0;
                const y = 200 - (score / 100) * 180;
                return `${x},${y}`;
              });

              return (
                <g key={suppId}>
                  <polyline
                    fill="none"
                    stroke={color}
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    points={points.join(" ")}
                  />
                  {/* Point circles */}
                  {data_points.map((pt, i) => {
                    const x = 50 + (i / (data_points.length - 1)) * 620;
                    const score = pt.supplier_scores[suppId] || 0;
                    const y = 200 - (score / 100) * 180;
                    return (
                      <circle
                        key={i}
                        cx={x}
                        cy={y}
                        r="3"
                        fill={color}
                        className="transition-transform hover:scale-150"
                      />
                    );
                  })}
                </g>
              );
            })}

            {/* X-axis tick labels */}
            {data_points.map((pt, i) => {
              if (i % Math.ceil(data_points.length / 8) !== 0 && i !== data_points.length - 1) return null;
              const x = 50 + (i / (data_points.length - 1)) * 620;
              return (
                <text key={i} x={x} y="220" textAnchor="middle" fill="currentColor" fillOpacity="0.6">
                  {(pt.weight * 100).toFixed(0)}%
                </text>
              );
            })}
          </svg>
        </div>
      </div>

      {/* Trajectory Data Table Summary */}
      <div className="overflow-x-auto rounded-lg border border-border/50">
        <table className="w-full text-left text-xs font-mono">
          <thead className="bg-secondary/40 border-b border-border text-[10px] uppercase text-muted-foreground">
            <tr>
              <th className="py-2 px-3">Weight</th>
              {supplierIds.map((suppId, idx) => (
                <th key={suppId} className="py-2 px-3">
                  <span style={{ color: colors[idx % colors.length] }}>Supplier #{idx + 1}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border/40 text-muted-foreground">
            {data_points.map((pt, idx) => (
              <tr key={idx} className="hover:bg-secondary/20">
                <td className="py-1.5 px-3 font-bold text-foreground">{(pt.weight * 100).toFixed(1)}%</td>
                {supplierIds.map((suppId) => (
                  <td key={suppId} className="py-1.5 px-3">
                    {(pt.supplier_scores[suppId] || 0).toFixed(2)} (Rank #{pt.ranks[suppId] || "—"})
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
