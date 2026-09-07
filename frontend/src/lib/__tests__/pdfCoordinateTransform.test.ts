import { describe, it, expect } from "vitest";
import {
  transformEvidenceBboxToViewport,
  PageViewportParameters,
} from "../pdfCoordinateTransform";

describe("Centralized PDF Evidence Coordinate Mapping", () => {
  // 1. Standard US Letter Portrait Page (612 x 792 pt)
  const portraitBase: PageViewportParameters = {
    originalWidth: 612,
    originalHeight: 792,
    viewportWidth: 612,
    viewportHeight: 792,
    rotation: 0,
  };

  const sampleBbox: [number, number, number, number] = [50, 100, 250, 150];

  it("correctly maps coordinates for 0-degree unscaled portrait page", () => {
    const coords = transformEvidenceBboxToViewport(sampleBbox, portraitBase);
    expect(coords).not.toBeNull();
    expect(coords?.x).toBeCloseTo(50, 1);
    expect(coords?.y).toBeCloseTo(100, 1);
    expect(coords?.width).toBeCloseTo(200, 1);
    expect(coords?.height).toBeCloseTo(50, 1);
  });

  // 2. Landscape Page (792 x 612 pt)
  it("correctly maps coordinates on a native landscape page", () => {
    const landscapeParams: PageViewportParameters = {
      originalWidth: 792,
      originalHeight: 612,
      viewportWidth: 792,
      viewportHeight: 612,
      rotation: 0,
    };
    const landscapeBbox: [number, number, number, number] = [100, 80, 500, 120];
    const coords = transformEvidenceBboxToViewport(landscapeBbox, landscapeParams);
    expect(coords).not.toBeNull();
    expect(coords?.x).toBeCloseTo(100, 1);
    expect(coords?.y).toBeCloseTo(80, 1);
    expect(coords?.width).toBeCloseTo(400, 1);
    expect(coords?.height).toBeCloseTo(40, 1);
  });

  // 3. Page Rotated 90 Degrees Clockwise
  it("correctly maps coordinates when page is rotated 90 degrees clockwise", () => {
    const rot90Params: PageViewportParameters = {
      originalWidth: 612,
      originalHeight: 792,
      // At 90 deg, viewport width is scaled from originalHeight (792), viewport height from originalWidth (612)
      viewportWidth: 792,
      viewportHeight: 612,
      rotation: 90,
    };
    // Original bbox [50, 100, 250, 150]
    // x' = (originalHeight - y1) * (viewportWidth / originalHeight) = (792 - 150) * 1 = 642
    // y' = x0 * (viewportHeight / originalWidth) = 50 * 1 = 50
    // width' = (y1 - y0) * 1 = 50
    // height' = (x1 - x0) * 1 = 200
    const coords = transformEvidenceBboxToViewport(sampleBbox, rot90Params);
    expect(coords).not.toBeNull();
    expect(coords?.x).toBeCloseTo(642, 1);
    expect(coords?.y).toBeCloseTo(50, 1);
    expect(coords?.width).toBeCloseTo(50, 1);
    expect(coords?.height).toBeCloseTo(200, 1);
  });

  // 4. Page Rotated 180 Degrees
  it("correctly maps coordinates when page is rotated 180 degrees", () => {
    const rot180Params: PageViewportParameters = {
      originalWidth: 612,
      originalHeight: 792,
      viewportWidth: 612,
      viewportHeight: 792,
      rotation: 180,
    };
    // x' = (originalWidth - x1) = 612 - 250 = 362
    // y' = (originalHeight - y1) = 792 - 150 = 642
    const coords = transformEvidenceBboxToViewport(sampleBbox, rot180Params);
    expect(coords).not.toBeNull();
    expect(coords?.x).toBeCloseTo(362, 1);
    expect(coords?.y).toBeCloseTo(642, 1);
    expect(coords?.width).toBeCloseTo(200, 1);
    expect(coords?.height).toBeCloseTo(50, 1);
  });

  // 5. Page Rotated 270 Degrees
  it("correctly maps coordinates when page is rotated 270 degrees", () => {
    const rot270Params: PageViewportParameters = {
      originalWidth: 612,
      originalHeight: 792,
      viewportWidth: 792,
      viewportHeight: 612,
      rotation: 270,
    };
    // x' = y0 = 100
    // y' = (originalWidth - x1) = 612 - 250 = 362
    // width' = (y1 - y0) = 50
    // height' = (x1 - x0) = 200
    const coords = transformEvidenceBboxToViewport(sampleBbox, rot270Params);
    expect(coords).not.toBeNull();
    expect(coords?.x).toBeCloseTo(100, 1);
    expect(coords?.y).toBeCloseTo(362, 1);
    expect(coords?.width).toBeCloseTo(50, 1);
    expect(coords?.height).toBeCloseTo(200, 1);
  });

  // 6. Zoom Factor Changes (150% and 50%)
  it("correctly scales coordinates under zoom changes", () => {
    const zoom150: PageViewportParameters = {
      originalWidth: 612,
      originalHeight: 792,
      viewportWidth: 612 * 1.5,
      viewportHeight: 792 * 1.5,
      rotation: 0,
    };
    const coords150 = transformEvidenceBboxToViewport(sampleBbox, zoom150);
    expect(coords150?.x).toBeCloseTo(50 * 1.5, 1);
    expect(coords150?.y).toBeCloseTo(100 * 1.5, 1);
    expect(coords150?.width).toBeCloseTo(200 * 1.5, 1);
    expect(coords150?.height).toBeCloseTo(50 * 1.5, 1);

    const zoom50: PageViewportParameters = {
      originalWidth: 612,
      originalHeight: 792,
      viewportWidth: 612 * 0.5,
      viewportHeight: 792 * 0.5,
      rotation: 0,
    };
    const coords50 = transformEvidenceBboxToViewport(sampleBbox, zoom50);
    expect(coords50?.x).toBeCloseTo(25, 1);
    expect(coords50?.y).toBeCloseTo(50, 1);
    expect(coords50?.width).toBeCloseTo(100, 1);
    expect(coords50?.height).toBeCloseTo(25, 1);
  });

  // 7. Split-Pane Resizing (non-uniform aspect ratio viewport)
  it("correctly responds to split-pane width changes", () => {
    const resizedPane: PageViewportParameters = {
      originalWidth: 612,
      originalHeight: 792,
      viewportWidth: 500, // pane shrunk
      viewportHeight: 647.06, // maintained page aspect ratio
      rotation: 0,
    };
    const scale = 500 / 612;
    const coords = transformEvidenceBboxToViewport(sampleBbox, resizedPane);
    expect(coords?.x).toBeCloseTo(50 * scale, 1);
    expect(coords?.y).toBeCloseTo(100 * scale, 1);
    expect(coords?.width).toBeCloseTo(200 * scale, 1);
    expect(coords?.height).toBeCloseTo(50 * scale, 1);
  });

  // 8. Gracefully handles null/invalid bbox
  it("returns null for invalid or missing bounding boxes", () => {
    expect(transformEvidenceBboxToViewport(null, portraitBase)).toBeNull();
    expect(transformEvidenceBboxToViewport([], portraitBase)).toBeNull();
    expect(transformEvidenceBboxToViewport([1, 2], portraitBase)).toBeNull();
  });
});
