"use client";

import { useMemo } from "react";
import {
  Area,
  AreaChart,
  Line,
  ReferenceLine,
  XAxis,
  YAxis,
} from "recharts";
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  type ChartConfig,
} from "@/components/ui/chart";
import type { P2PResponse } from "@/lib/types";

interface Props {
  result: P2PResponse;
}

export default function ProfileChart({ result }: Props) {
  const { profile, horizons, flags } = result;

  const { data, chartConfig, horizonRefs } = useMemo(() => {
    if (!profile || profile.length === 0)
      return { data: [], chartConfig: {}, horizonRefs: [] };

    const d = profile.map((p) => ({
      d: +(p.d / 1000).toFixed(3),
      terrain: p.terrain_bulge,
      los: p.los,
      fresnelUpper: p.fresnel_upper,
      fresnelLower: p.fresnel_lower,
      fresnel60: p.fresnel_60,
    }));

    const cfg: ChartConfig = {
      terrain: { label: "Terrain (earth-curved)", color: "#8B5A2B" },
      los: { label: "LOS", color: "#3b82f6" },
      fresnel60: { label: "0.6 F1", color: "rgba(255,200,0,0.8)" },
      fresnelZone: { label: "Fresnel F1", color: "rgba(255,200,0,0.5)" },
    };

    if (profile.some((p) => p.violates_f1)) {
      cfg.violation = {
        label: "Fresnel violation",
        color: "rgba(239,68,68,0.85)",
      };
    }

    const refs = (horizons || []).map((h) => ({
      x: +(h.d_m / 1000).toFixed(3),
      label: h.role === "tx_horizon" ? "TX horizon" : "RX horizon",
    }));

    return { data: d, chartConfig: cfg, horizonRefs: refs };
  }, [profile, horizons]);

  if (!profile || profile.length === 0) return null;

  let flagLabel = "";
  let flagClass = "";
  if (flags?.los_blocked) {
    flagLabel = "LOS blocked";
    flagClass = "text-red-400";
  } else if (flags?.fresnel_60_violated) {
    flagLabel = "0.6 F1 violated";
    flagClass = "text-yellow-400";
  } else if (flags?.fresnel_f1_violated) {
    flagLabel = "F1 grazed";
    flagClass = "text-yellow-400";
  } else {
    flagLabel = "F1 clear";
    flagClass = "text-green-400";
  }

  return (
    <div>
      <ChartContainer config={chartConfig} className="h-[280px] w-full">
        <AreaChart
          data={data}
          margin={{ top: 8, right: 12, bottom: 4, left: 0 }}
        >
          <XAxis
            dataKey="d"
            type="number"
            tick={{ fontSize: 10, fill: "#aaa" }}
            tickLine={false}
            axisLine={{ stroke: "#555" }}
            label={{
              value: "Distance (km)",
              position: "insideBottomRight",
              offset: -4,
              fontSize: 11,
              fill: "#aaa",
            }}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#aaa" }}
            tickLine={false}
            axisLine={{ stroke: "#555" }}
            label={{
              value: "Elevation (m)",
              angle: -90,
              position: "insideLeft",
              offset: 8,
              fontSize: 11,
              fill: "#aaa",
            }}
          />
          <ChartLegend content={<ChartLegendContent />} />

          <Area
            type="monotone"
            dataKey="fresnelUpper"
            stroke="rgba(255,200,0,0.5)"
            strokeWidth={1}
            fill="rgba(255,200,0,0.12)"
            name="fresnelZone"
            dot={false}
            isAnimationActive={false}
          />
          <Area
            type="monotone"
            dataKey="fresnelLower"
            stroke="rgba(255,200,0,0.5)"
            strokeWidth={1}
            fill="rgba(255,200,0,0.08)"
            name="fresnelZone"
            dot={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="fresnel60"
            stroke="rgba(255,200,0,0.8)"
            strokeWidth={1}
            strokeDasharray="4 3"
            dot={false}
            name="fresnel60"
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="los"
            stroke="#3b82f6"
            strokeWidth={2}
            strokeDasharray="6 3"
            dot={false}
            name="los"
            isAnimationActive={false}
          />
          <Area
            type="monotone"
            dataKey="terrain"
            stroke="#8B5A2B"
            strokeWidth={2}
            fill="rgba(92,64,42,0.55)"
            name="terrain"
            dot={false}
            isAnimationActive={false}
          />

          {horizonRefs.map((ref, i) => (
            <ReferenceLine
              key={i}
              x={ref.x}
              stroke="#f59e0b"
              strokeWidth={1.5}
              strokeDasharray="3 3"
              label={{
                value: ref.label,
                position: "top",
                fill: "#f59e0b",
                fontSize: 10,
                offset: i % 2 === 0 ? 30 : -10,
              }}
            />
          ))}
        </AreaChart>
      </ChartContainer>
      <div className={`text-xs mt-1 font-medium ${flagClass}`}>{flagLabel}</div>
    </div>
  );
}