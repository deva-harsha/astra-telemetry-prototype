export const ENTRY_SESSION_KEY = 'astra-mission-control-entered'

export function initialEntryPhase(storage) {
  try { return storage?.getItem(ENTRY_SESSION_KEY) === '1' ? 'hidden' : 'visible' } catch { return 'visible' }
}

export function entryTransitionMs(reducedMotion) {
  return reducedMotion ? 0 : 440
}

export function focusAfterEntry({ explore, consoleHeading, capabilities }) {
  if (explore && capabilities) {
    capabilities.open = true
    capabilities.querySelector('summary')?.focus()
    capabilities.scrollIntoView({ block: 'start' })
    return 'capabilities'
  }
  consoleHeading?.focus()
  return 'console'
}

export function showImportMapping({ expanded, validationRequested, compatibility }) {
  return expanded || !validationRequested || !compatibility || compatibility === 'invalid'
}
