# Frontend Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix four regressions in the shadcn/Tailwind migration: no map, wrong colors, mismatched styling, and chart panel overlaying the map.

**Architecture:** Minimal-patch approach — fix CSS variable palette, move MapLibre CSS to global stylesheet, adjust Tailwind classes on existing components, restructure chart panel from absolute overlay to column-flex sibling.

**Tech Stack:** Next.js 16 (App Router), Tailwind CSS v4, shadcn/ui, MapLibre GL, TypeScript

---

## Files Modified

| File | What changes |
|---|---|
| `frontend/app/globals.css` | Add MapLibre CSS import; replace blue-tinted CSS vars with neutral-dark + green palette |
| `frontend/components/map/MapView.tsx` | Remove MapLibre CSS import (moved to globals) |
| `frontend/components/sidebar/Sidebar.tsx` | Logo color `text-white` → `text-[#22c55e]`; width `w-[360px]` → `w-[340px]` |
| `frontend/components/sidebar/P2PTab.tsx` | Add `uppercase tracking-wider` to every `Label` |
| `frontend/components/sidebar/CoverageTab.tsx` | Add `uppercase tracking-wider` to every `Label` |
| `frontend/app/page.tsx` | Map area `flex-col`; wrap `MapView` in `flex-1 min-h-0 relative` div |
| `frontend/components/panels/ChartPanel.tsx` | Remove `absolute bottom-0 left-0 right-0`; make it a normal block strip |

---

### Task 1: Fix the map (move MapLibre CSS to globals)

**Files:**
- Modify: `frontend/components/map/MapView.tsx`
- Modify: `frontend/app/globals.css`

- [ ] **Step 1: Remove MapLibre CSS import from MapView.tsx**

In `frontend/components/map/MapView.tsx`, remove line 3:
```diff
-import 'maplibre-gl/dist/maplibre-gl.css'
```

- [ ] **Step 2: Add MapLibre CSS import to globals.css**

At the very top of `frontend/app/globals.css` (before other imports):
```diff
+@import 'maplibre-gl/dist/maplibre-gl.css';
 @import "tw-animate-css";
 @import "shadcn/tailwind.css";
```

- [ ] **Step 3: Start dev server and verify map renders**

```bash
cd /home/bortre/03-final/nowires/frontend && npm run dev
```

Open `http://localhost:3000`. The map (OSM tiles + hillshade) should be visible in the right panel. If it's still blank, check the browser console for errors.

- [ ] **Step 4: Commit**

```bash
cd /home/bortre/03-final/nowires
git add frontend/components/map/MapView.tsx frontend/app/globals.css
git commit -m "fix: move maplibre CSS to globals so Turbopack includes it"
```

---

### Task 2: Fix colors — replace blue-grey palette with neutral-dark + green

**Files:**
- Modify: `frontend/app/globals.css`

- [ ] **Step 1: Replace the `:root` CSS variable block**

In `frontend/app/globals.css`, replace the entire `:root { ... }` block (lines 49–82) with:

```css
:root {
  --background: oklch(0.07 0 0);
  --foreground: oklch(0.93 0 0);
  --card: oklch(0.10 0 0);
  --card-foreground: oklch(0.93 0 0);
  --popover: oklch(0.10 0 0);
  --popover-foreground: oklch(0.93 0 0);
  --primary: oklch(0.72 0.22 145);
  --primary-foreground: oklch(0.10 0 0);
  --secondary: oklch(0.18 0 0);
  --secondary-foreground: oklch(0.93 0 0);
  --muted: oklch(0.16 0 0);
  --muted-foreground: oklch(0.60 0 0);
  --accent: oklch(0.18 0 0);
  --accent-foreground: oklch(0.93 0 0);
  --destructive: oklch(0.55 0.22 25);
  --border: oklch(1 0 0 / 16%);
  --input: oklch(1 0 0 / 12%);
  --ring: oklch(0.72 0.22 145);
  --radius: 0.375rem;
  --chart-1: oklch(0.72 0.22 145);
  --chart-2: oklch(0.60 0.18 145);
  --chart-3: oklch(0.48 0.14 145);
  --chart-4: oklch(0.36 0.10 145);
  --chart-5: oklch(0.24 0.06 145);
  --sidebar: oklch(0.10 0 0);
  --sidebar-foreground: oklch(0.93 0 0);
  --sidebar-primary: oklch(0.72 0.22 145);
  --sidebar-primary-foreground: oklch(0.10 0 0);
  --sidebar-accent: oklch(0.18 0 0);
  --sidebar-accent-foreground: oklch(0.93 0 0);
  --sidebar-border: oklch(1 0 0 / 16%);
  --sidebar-ring: oklch(0.72 0.22 145);
}
```

> `oklch(0.72 0.22 145)` is the oklch equivalent of `#22c55e` (Tailwind green-500). The neutral backgrounds use chroma=0 (pure grey, no hue bias).

- [ ] **Step 2: Verify in browser**

With the dev server running, `http://localhost:3000` should now show:
- Near-black background (no blue tint)
- Sidebar is dark neutral, not blue-grey
- Primary buttons are green
- Input borders are more visible

- [ ] **Step 3: Commit**

```bash
cd /home/bortre/03-final/nowires
git add frontend/app/globals.css
git commit -m "fix: replace blue-grey oklch palette with neutral-dark + green matching master"
```

---

### Task 3: Fix logo color and sidebar width

**Files:**
- Modify: `frontend/components/sidebar/Sidebar.tsx`

- [ ] **Step 1: Change logo color and sidebar width**

In `frontend/components/sidebar/Sidebar.tsx`, make two changes:

Change the outer div width:
```diff
-<div className="w-[360px] flex-shrink-0 h-full bg-[#0d0d1a] border-r border-white/10 flex flex-col overflow-hidden">
+<div className="w-[340px] flex-shrink-0 h-full bg-[#161616] border-r border-white/10 flex flex-col overflow-hidden">
```

Change the `h2` logo color:
```diff
-<h2 className="text-lg font-bold text-white">nowires</h2>
+<h2 className="text-lg font-bold text-[#22c55e]">nowires</h2>
```

- [ ] **Step 2: Verify in browser**

Logo "nowires" should be green. Sidebar should be 340px wide.

- [ ] **Step 3: Commit**

```bash
cd /home/bortre/03-final/nowires
git add frontend/components/sidebar/Sidebar.tsx
git commit -m "fix: restore green logo and 340px sidebar width matching master"
```

---

### Task 4: Fix label styling in P2PTab

**Files:**
- Modify: `frontend/components/sidebar/P2PTab.tsx`

- [ ] **Step 1: Add uppercase + tracking to every Label**

In `frontend/components/sidebar/P2PTab.tsx`, every `<Label className="text-xs ...">` needs `uppercase tracking-wider` added. There are ~15 labels. Make this change to all of them:

```diff
-<Label className="text-xs text-muted-foreground">TX</Label>
+<Label className="text-xs text-muted-foreground uppercase tracking-wider">TX</Label>

-<Label className="text-xs text-muted-foreground">RX</Label>
+<Label className="text-xs text-muted-foreground uppercase tracking-wider">RX</Label>

-<Label className="text-xs">TX Height (m)</Label>
+<Label className="text-xs uppercase tracking-wider">TX Height (m)</Label>

-<Label className="text-xs">RX Height (m)</Label>
+<Label className="text-xs uppercase tracking-wider">RX Height (m)</Label>

-<Label className="text-xs">Freq (MHz)</Label>
+<Label className="text-xs uppercase tracking-wider">Freq (MHz)</Label>

-<Label className="text-xs">Polarization</Label>
+<Label className="text-xs uppercase tracking-wider">Polarization</Label>

-<Label className="text-xs">Climate</Label>
+<Label className="text-xs uppercase tracking-wider">Climate</Label>

-<Label className="text-xs">TX Power (dBm)</Label>
+<Label className="text-xs uppercase tracking-wider">TX Power (dBm)</Label>

-<Label className="text-xs">Cable Loss (dB)</Label>
+<Label className="text-xs uppercase tracking-wider">Cable Loss (dB)</Label>

-<Label className="text-xs">TX Gain (dBi)</Label>
+<Label className="text-xs uppercase tracking-wider">TX Gain (dBi)</Label>

-<Label className="text-xs">RX Gain (dBi)</Label>
+<Label className="text-xs uppercase tracking-wider">RX Gain (dBi)</Label>

-<Label className="text-xs">RX Sensitivity (dBm)</Label>
+<Label className="text-xs uppercase tracking-wider">RX Sensitivity (dBm)</Label>

-<Label className="text-xs">Time %</Label>
+<Label className="text-xs uppercase tracking-wider">Time %</Label>

-<Label className="text-xs">Location %</Label>
+<Label className="text-xs uppercase tracking-wider">Location %</Label>

-<Label className="text-xs">Situation %</Label>
+<Label className="text-xs uppercase tracking-wider">Situation %</Label>

-<Label className="text-xs">K-factor (earth curvature)</Label>
+<Label className="text-xs uppercase tracking-wider">K-factor (earth curvature)</Label>
```

- [ ] **Step 2: Verify in browser**

All form labels in the P2P tab should appear in uppercase with wider letter spacing, matching master.

- [ ] **Step 3: Commit**

```bash
cd /home/bortre/03-final/nowires
git add frontend/components/sidebar/P2PTab.tsx
git commit -m "fix: uppercase + tracking on P2PTab labels to match master"
```

---

### Task 5: Fix label styling in CoverageTab

**Files:**
- Modify: `frontend/components/sidebar/CoverageTab.tsx`

- [ ] **Step 1: Add uppercase + tracking to every Label in CoverageTab**

In `frontend/components/sidebar/CoverageTab.tsx`, apply the same pattern — add `uppercase tracking-wider` to every `<Label className="text-xs ...">`:

```diff
-<Label className="text-xs text-muted-foreground">TX Location</Label>
+<Label className="text-xs text-muted-foreground uppercase tracking-wider">TX Location</Label>

-<Label className="text-xs">TX Height (m)</Label>
+<Label className="text-xs uppercase tracking-wider">TX Height (m)</Label>

-<Label className="text-xs">RX Height (m)</Label>
+<Label className="text-xs uppercase tracking-wider">RX Height (m)</Label>

-<Label className="text-xs">Freq (MHz)</Label>
+<Label className="text-xs uppercase tracking-wider">Freq (MHz)</Label>

-<Label className="text-xs">TX Power (dBm)</Label>
+<Label className="text-xs uppercase tracking-wider">TX Power (dBm)</Label>

-<Label className="text-xs">TX Gain (dBi)</Label>
+<Label className="text-xs uppercase tracking-wider">TX Gain (dBi)</Label>

-<Label className="text-xs">RX Gain (dBi)</Label>
+<Label className="text-xs uppercase tracking-wider">RX Gain (dBi)</Label>

-<Label className="text-xs">RX Sensitivity (dBm)</Label>
+<Label className="text-xs uppercase tracking-wider">RX Sensitivity (dBm)</Label>

-<Label className="text-xs">Antenna Pattern</Label>
+<Label className="text-xs uppercase tracking-wider">Antenna Pattern</Label>

-<Label className="text-xs">Azimuth (°)</Label>
+<Label className="text-xs uppercase tracking-wider">Azimuth (°)</Label>

-<Label className="text-xs">Beamwidth (°)</Label>
+<Label className="text-xs uppercase tracking-wider">Beamwidth (°)</Label>

-<Label className="text-xs">Output Pixels</Label>
+<Label className="text-xs uppercase tracking-wider">Output Pixels</Label>

-<Label className="text-xs">Terrain Detail</Label>
+<Label className="text-xs uppercase tracking-wider">Terrain Detail</Label>

-<Label className="text-xs">Polarization</Label>
+<Label className="text-xs uppercase tracking-wider">Polarization</Label>

-<Label className="text-xs">Climate</Label>
+<Label className="text-xs uppercase tracking-wider">Climate</Label>

-<Label className="text-xs">Time %</Label>
+<Label className="text-xs uppercase tracking-wider">Time %</Label>

-<Label className="text-xs">Location %</Label>
+<Label className="text-xs uppercase tracking-wider">Location %</Label>

-<Label className="text-xs">Situation %</Label>
+<Label className="text-xs uppercase tracking-wider">Situation %</Label>

-<Label className="text-xs">Cable Loss (dB)</Label>
+<Label className="text-xs uppercase tracking-wider">Cable Loss (dB)</Label>

-<Label className="text-xs">Overlay Opacity</Label>
+<Label className="text-xs uppercase tracking-wider">Overlay Opacity</Label>
```

- [ ] **Step 2: Verify in browser**

Coverage tab labels should match P2P tab labels — uppercase with letter spacing.

- [ ] **Step 3: Commit**

```bash
cd /home/bortre/03-final/nowires
git add frontend/components/sidebar/CoverageTab.tsx
git commit -m "fix: uppercase + tracking on CoverageTab labels to match master"
```

---

### Task 6: Fix chart panel layout (above map, not overlay)

**Files:**
- Modify: `frontend/app/page.tsx`
- Modify: `frontend/components/panels/ChartPanel.tsx`

- [ ] **Step 1: Update ChartPanel to remove absolute positioning**

In `frontend/components/panels/ChartPanel.tsx`, change the outer div:

```diff
-<div className="absolute bottom-0 left-0 right-0 h-64 bg-[#0d0d1a]/95 border-t border-white/10 flex flex-col z-10">
+<div className="h-64 bg-[#161616] border-t border-white/10 flex flex-col flex-shrink-0">
```

- [ ] **Step 2: Update page.tsx map area to flex-col**

In `frontend/app/page.tsx`, change the map area container:

```diff
-      <div className="flex-1 relative min-w-0">
-        <MapView
+      <div className="flex-1 flex flex-col min-w-0 min-h-0">
+        <div className="flex-1 relative min-h-0">
+        <MapView
           clickMode={activeTab}
           onMapClick={handleMapClick}
           txCoords={txCoords}
           rxCoords={rxCoords}
           covTxCoords={covTxCoords}
           p2pResult={p2pResult}
           coverageResult={coverageResult}
           coverageOpacity={coverageOpacity}
           sites={sites}
         />

         {sitesVisible && sites.length > 0 && (
           <SitesPanel
             sites={sites}
             onToggle={handleSiteToggle}
             onOpacity={handleSiteOpacity}
             onDelete={handleSiteDelete}
             onClearAll={handleClearSites}
             onClose={() => setSitesVisible(false)}
           />
         )}
+        </div>

         {chartVisible && p2pResult && (
           <ChartPanel
             result={p2pResult}
             onClose={() => setChartVisible(false)}
           />
         )}
       </div>
```

- [ ] **Step 3: Verify in browser**

Run a P2P analysis (place TX and RX on map, click Analyze Path). The terrain chart panel should appear **below the map** (map shrinks up), not overlaying it. The SitesPanel absolute positioning inside the map div is unaffected.

- [ ] **Step 4: Commit**

```bash
cd /home/bortre/03-final/nowires
git add frontend/app/page.tsx frontend/components/panels/ChartPanel.tsx
git commit -m "fix: chart panel column layout — sits below map instead of overlaying it"
```
