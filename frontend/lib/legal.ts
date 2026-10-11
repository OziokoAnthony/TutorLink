/**
 * The business details the privacy notice and terms name. Until every one is filled in, both pages show a
 * "draft" banner, so an unfinished notice can't pass for the real one.
 */
export const LEGAL = {
  /** The registered business name, as on the CAC certificate. */
  company: '',
  /** The registered business address. */
  address: '',
  /** Where users write about their data and these terms. */
  email: '',
  /** When this version takes effect, e.g. "1 November 2026". */
  effectiveDate: '',
}

export const legalIsComplete = Object.values(LEGAL).every(Boolean)

/** A detail, or a visible gap while it's missing. */
export function detail(key: keyof typeof LEGAL): string {
  return LEGAL[key] || `[${key} to be filled in]`
}
