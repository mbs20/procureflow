/**
 * Centralized coordinate transformation engine for PDF evidence overlays.
 *
 * Transforms authoritative PDF point space bounding boxes [x0, y0, x1, y1]
 * into rendered browser viewport pixel space, correctly handling:
 * - Portrait and landscape dimensions
 * - Page rotation (0°, 90°, 180°, 270°)
 * - Zoom scale factors
 * - Responsive viewport container resizing
 */

export interface BoundingBoxCoordinates {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface PageViewportParameters {
  /** Current rendered viewport width in pixels */
  viewportWidth: number;
  /** Current rendered viewport height in pixels */
  viewportHeight: number;
  /** Page rotation angle in degrees (0, 90, 180, 270) */
  rotation: number;
  /** Native unrotated page width in PDF points (default: 612 for standard letter) */
  originalWidth: number;
  /** Native unrotated page height in PDF points (default: 792 for standard letter) */
  originalHeight: number;
}

/**
 * Transforms an authoritative PDF bounding box [x0, y0, x1, y1]
 * to pixel coordinates relative to the rendered canvas/SVG container.
 */
export function transformEvidenceBboxToViewport(
  rawBbox: [number, number, number, number] | number[] | null | undefined,
  params: PageViewportParameters
): BoundingBoxCoordinates | null {
  if (!rawBbox || rawBbox.length < 4) {
    return null;
  }

  const [rawX0, rawY0, rawX1, rawY1] = rawBbox;
  // Ensure x0 <= x1 and y0 <= y1
  const x0 = Math.min(rawX0, rawX1);
  const x1 = Math.max(rawX0, rawX1);
  const y0 = Math.min(rawY0, rawY1);
  const y1 = Math.max(rawY0, rawY1);

  const { viewportWidth, viewportHeight, rotation, originalWidth, originalHeight } = params;

  if (viewportWidth <= 0 || viewportHeight <= 0 || originalWidth <= 0 || originalHeight <= 0) {
    return null;
  }

  // Normalize rotation to 0, 90, 180, 270
  const normalizedRotation = ((rotation % 360) + 360) % 360;

  switch (normalizedRotation) {
    case 90: {
      const scaleX = viewportWidth / originalHeight;
      const scaleY = viewportHeight / originalWidth;
      return {
        x: (originalHeight - y1) * scaleX,
        y: x0 * scaleY,
        width: (y1 - y0) * scaleX,
        height: (x1 - x0) * scaleY,
      };
    }

    case 180: {
      const scaleX = viewportWidth / originalWidth;
      const scaleY = viewportHeight / originalHeight;
      return {
        x: (originalWidth - x1) * scaleX,
        y: (originalHeight - y1) * scaleY,
        width: (x1 - x0) * scaleX,
        height: (y1 - y0) * scaleY,
      };
    }

    case 270: {
      const scaleX = viewportWidth / originalHeight;
      const scaleY = viewportHeight / originalWidth;
      return {
        x: y0 * scaleX,
        y: (originalWidth - x1) * scaleY,
        width: (y1 - y0) * scaleX,
        height: (x1 - x0) * scaleY,
      };
    }

    case 0:
    default: {
      const scaleX = viewportWidth / originalWidth;
      const scaleY = viewportHeight / originalHeight;
      return {
        x: x0 * scaleX,
        y: y0 * scaleY,
        width: (x1 - x0) * scaleX,
        height: (y1 - y0) * scaleY,
      };
    }
  }
}
