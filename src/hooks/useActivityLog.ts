// ============================================================================
// IMPORTS
// ============================================================================

import { useCallback, useEffect, useState } from 'react'

// ============================================================================
// CONSTANTS
// ============================================================================

const hasElectronAPI = (): boolean =>
  typeof window !== 'undefined' && window.electronAPI !== undefined

// ============================================================================
// CUSTOM HOOKS
// ============================================================================

/**
 * Manages the activity log displayed in the UI.
 *
 * On mount:  fetches all historical entries from the log file on disk via IPC.
 * At runtime: prepends new entries pushed live from the Main process.
 * Both sources are deduplicated by order — historical entries are the base,
 * live entries are prepended as they arrive.
 */
const useActivityLog = () => {
  // ── STATE ─────────────────────────────────────────────────────────────────
  const [entries, setEntries] = useState<string[]>([])

  // ── EFFECTS — Load historical entries on mount ────────────────────────────
  useEffect(() => {
    if (!hasElectronAPI()) return

    window.electronAPI!.log.getEntries().then((historical) => {
      if (historical.length > 0) {
        setEntries(historical)
      }
    }).catch(() => {
      // Log file unreadable or IPC unavailable — start with empty state
    })
  }, [])

  // ── EFFECTS — Subscribe to live entries pushed from Main ──────────────────
  useEffect(() => {
    if (!hasElectronAPI()) return

    const unsubscribe = window.electronAPI!.log.onNewEntry(({ entry }) => {
      // Prepend so newest entries appear first (matching historical order)
      setEntries((prev) => [entry, ...prev])
    })

    return unsubscribe
  }, [])

  // ── ACTIONS ───────────────────────────────────────────────────────────────
  const exportLog = useCallback(async (): Promise<void> => {
    if (!hasElectronAPI()) return
    await window.electronAPI!.log.export()
  }, [])

  return { entries, exportLog }
}

export default useActivityLog
