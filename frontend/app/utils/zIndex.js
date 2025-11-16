// Z-index hierarchy management
// Lower values are behind higher values
// Leave gaps between levels for future additions

export const Z_INDEX = {
  // Base content
  BASE: 1,

  // Sticky elements (headers, nav)
  STICKY_NAV: 100,
  DESKTOP_NAV: 110,
  MOBILE_NAV: 120,

  // Floating elements
  FLOATING_BUTTON: 500,
  FLOATING_ANNOTATE: 510,
  HELP_BUTTON: 520,

  // Dropdowns and menus
  DROPDOWN: 1000,
  AUTOCOMPLETE: 1010,

  // Tooltips
  TOOLTIP: 2000,

  // Modals and overlays
  MODAL_BACKDROP: 5000,
  MODAL: 5010,

  // Onboarding
  ONBOARDING_BACKDROP: 9997,
  ONBOARDING_PROGRESS: 9998,

  // Tour overlay (highest priority)
  TOUR_BACKDROP: 10000,
  TOUR_SPOTLIGHT: 10001,
  TOUR_TOOLTIP: 10002,

  // Error boundary (absolute highest)
  ERROR_BOUNDARY: 10010
};

// Helper function to get z-index value
export function getZIndex(layer) {
  return Z_INDEX[layer] || Z_INDEX.BASE;
}

// Helper function to create z-index style
export function zIndexStyle(layer) {
  return { zIndex: getZIndex(layer) };
}