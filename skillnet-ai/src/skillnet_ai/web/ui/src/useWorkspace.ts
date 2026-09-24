import { useEffect, useRef, useState } from 'react'
import { parseSnapshot } from './data'
import type { Dataset } from './data'
import { createDefaultLibrary, initialLibraryPath, readLocalLibrary } from './localLibrary'
import type { LocalLibrary, LocalLibraryData } from './localLibrary'
import {
  clearImport,
  loadImports,
  loadLocalLibraries,
  loadView,
  removeLocalLibrary,
  saveImport,
  saveLocalLibrary,
  saveView,
} from './persistence'
import { firstConnectedSkill } from './selection'

const empty: Dataset = { kind: 'source', title: 'My skill library', skills: [], relations: [] }
type Imported = { id: string; dataset: Dataset }

function comparablePath(value: string) {
  const path = value.replaceAll('\\', '/').replace(/\/+$/, '')
  return /^[a-zA-Z]:|^\/\//.test(path) ? path.toLowerCase() : path
}

export function useWorkspace() {
  const [dataset, setDataset] = useState<Dataset>(empty)
  const [localData, setLocalData] = useState<LocalLibraryData | null>(null)
  const [localLibraries, setLocalLibraries] = useState<LocalLibrary[]>([])
  const [importedDatasets, setImportedDatasets] = useState<Imported[]>([])
  const [collection, setCollection] = useState('personal')
  const [sourceId, setSourceId] = useState('personal')
  const [selectedSkillId, setSelectedSkillId] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [restoring, setRestoring] = useState(true)
  const operation = useRef<AbortController | null>(null)

  const select = (
    data: Dataset,
    library: string,
    source: string,
    local: LocalLibraryData | null = null,
    selected = '',
  ) => {
    setDataset(data)
    setCollection(library)
    setSourceId(source)
    setLocalData(local)
    setSelectedSkillId(
      data.skills.some((skill) => skill.id === selected) ? selected : firstConnectedSkill(data),
    )
  }
  const selectLocal = (
    library: LocalLibrary,
    data: LocalLibraryData,
    preferred = 'local-source',
    selected = '',
  ) => {
    const analysis = preferred === 'local-analysis' && data.analysis
    select(
      analysis || data.source,
      library.id,
      analysis ? 'local-analysis' : 'local-source',
      data,
      selected,
    )
  }

  // Every asynchronous user action passes through one gate. Controls cannot launch
  // overlapping reads/writes, and unmounted or superseded requests cannot publish state.
  const run = async (work: (signal: AbortSignal) => Promise<() => void>) => {
    if (operation.current || restoring) return
    const controller = new AbortController()
    operation.current = controller
    setLoading(true)
    setError(null)
    try {
      const commit = await work(controller.signal)
      if (!controller.signal.aborted) commit()
    } catch (cause) {
      if (!controller.signal.aborted)
        setError(cause instanceof Error ? cause.message : 'Could not load the library.')
    } finally {
      if (!controller.signal.aborted) {
        operation.current = null
        setLoading(false)
      }
    }
  }

  useEffect(() => {
    const controller = new AbortController()
    operation.current = controller
    const restore = async () => {
      try {
        const [savedImports, libraries, initialPath] = await Promise.all([
          loadImports().catch(() => []),
          loadLocalLibraries().catch((): LocalLibrary[] => []),
          initialLibraryPath(),
        ])
        if (controller.signal.aborted) return
        const imported = savedImports.flatMap((item) => {
          try {
            return [{ id: item.id, dataset: parseSnapshot(JSON.parse(item.json), item.name) }]
          } catch {
            return []
          }
        })
        setImportedDatasets(imported)
        setLocalLibraries(libraries)
        const view = loadView()
        let local = initialPath
          ? libraries.find(
              (item) => comparablePath(item.sourcePath) === comparablePath(initialPath),
            )
          : libraries.find((item) => item.id === view?.collection)
        if (initialPath && !local) {
          local = {
            id: `local:initial:${encodeURIComponent(initialPath)}`,
            name:
              initialPath
                .replace(/[\\/]+$/, '')
                .split(/[\\/]/)
                .pop() || initialPath,
            sourcePath: initialPath,
          }
          // A command-line folder remains usable even if browser storage is unavailable.
          await saveLocalLibrary(local).catch(() => undefined)
          libraries.push(local)
        }
        if (local) {
          const result = await readLocalLibrary(local, controller.signal)
          if (controller.signal.aborted) return
          setLocalLibraries([...libraries])
          selectLocal(
            local,
            result,
            view?.collection === local.id ? view.sourceId : 'local-source',
            view?.selectedSkillId,
          )
        } else if (view?.sourceId === 'imported') {
          const item = imported.find((item) => item.id === view.collection)
          if (item) select(item.dataset, item.id, 'imported', null, view.selectedSkillId)
        }
      } catch (cause) {
        if (!controller.signal.aborted)
          setError(cause instanceof Error ? cause.message : 'Could not restore the last library.')
      } finally {
        if (!controller.signal.aborted) {
          operation.current = null
          setRestoring(false)
        }
      }
    }
    void restore()
    return () => {
      controller.abort()
      operation.current?.abort()
      operation.current = null
    }
    // Restoration runs once; later changes are explicit user operations.
  }, [])

  useEffect(() => {
    if (!restoring) saveView({ collection, sourceId, selectedSkillId })
  }, [restoring, collection, sourceId, selectedSkillId])

  const showPersonalLibrary = () => select(empty, 'personal', 'personal')
  const openLocalLibrary = (library: LocalLibrary, preferred = sourceId) =>
    run(async (signal) => {
      const result = await readLocalLibrary(library, signal)
      return () =>
        selectLocal(library, result, preferred, library.id === collection ? selectedSkillId : '')
    })
  const connect = async (sourcePath: string, signal: AbortSignal) => {
    if (!sourcePath.trim()) throw new Error('Enter a skills folder path.')
    const existing = localLibraries.find(
      (item) => comparablePath(item.sourcePath) === comparablePath(sourcePath),
    )
    const library = existing ?? {
      id: `local:${crypto.randomUUID()}`,
      name:
        sourcePath
          .replace(/[\\/]+$/, '')
          .split(/[\\/]/)
          .pop() || sourcePath,
      sourcePath,
    }
    const result = await readLocalLibrary(library, signal)
    let warning: string | null = null
    if (!existing)
      await saveLocalLibrary(library).catch(() => {
        warning = 'Folder opened, but the browser could not save its connection.'
      })
    return () => {
      if (!existing) setLocalLibraries((previous) => [...previous, library])
      selectLocal(library, result)
      setError(warning)
    }
  }
  const connectLocalLibrary = (path: string) => run((signal) => connect(path.trim(), signal))
  const createPersonalLibrary = () =>
    run(async (signal) => connect(await createDefaultLibrary(), signal))
  const updateIndex = (indexPath?: string) =>
    run(async (signal) => {
      const library = localLibraries.find((item) => item.id === collection)
      if (!library) throw new Error('Select a local library first.')
      const updated = { ...library, indexPath }
      const result = await readLocalLibrary(updated, signal)
      if (indexPath && !result.analysis)
        throw new Error(result.analysisError || 'The folder has no current analysis.')
      let warning: string | null = null
      await saveLocalLibrary(updated).catch(() => {
        warning = 'Analysis folder changed, but the browser could not save the connection.'
      })
      return () => {
        setLocalLibraries((previous) =>
          previous.map((item) => (item.id === updated.id ? updated : item)),
        )
        selectLocal(updated, result, 'local-analysis')
        setError(warning)
      }
    })
  const forgetLocalLibrary = () =>
    run(async () => {
      let warning: string | null = null
      await removeLocalLibrary(collection).catch(() => {
        warning = 'Connection removed for this session; it may reappear after reload.'
      })
      return () => {
        setLocalLibraries((previous) => previous.filter((item) => item.id !== collection))
        showPersonalLibrary()
        setError(warning)
      }
    })
  const importFile = (file?: File) => {
    if (!file) return Promise.resolve()
    return run(async () => {
      if (file.size > 20 * 1024 * 1024) throw new Error('The file exceeds 20 MB.')
      const json = await file.text()
      const parsed = parseSnapshot(JSON.parse(json), file.name)
      const id = `imported:${crypto.randomUUID()}`
      let warning: string | null = null
      await saveImport({ id, name: file.name, json }).catch(() => {
        warning = 'Snapshot opened, but the browser could not save it.'
      })
      return () => {
        setImportedDatasets((previous) => [...previous, { id, dataset: parsed }])
        select(parsed, id, 'imported')
        setError(warning)
      }
    })
  }
  const removeImport = () =>
    run(async () => {
      let warning: string | null = null
      await clearImport(collection).catch(() => {
        warning = 'Snapshot removed for this session; it may reappear after reload.'
      })
      return () => {
        setImportedDatasets((previous) => previous.filter((item) => item.id !== collection))
        showPersonalLibrary()
        setError(warning)
      }
    })
  const changeLibrary = (name: string) => {
    if (operation.current || restoring) return
    setError(null)
    if (name === 'personal') {
      showPersonalLibrary()
      return
    }
    const local = localLibraries.find((item) => item.id === name)
    const imported = importedDatasets.find((item) => item.id === name)
    if (local) void openLocalLibrary(local, 'local-source')
    else if (imported) select(imported.dataset, name, 'imported')
  }
  const changeContent = (id: string) => {
    if (operation.current || restoring) return
    if ((id === 'local-source' || id === 'local-analysis') && localData) {
      const library = localLibraries.find((item) => item.id === collection)
      if (library) selectLocal(library, localData, id, selectedSkillId)
    }
  }

  return {
    dataset,
    localData,
    localLibraries,
    importedDatasets,
    collection,
    sourceId,
    selectedSkillId,
    setSelectedSkillId,
    error,
    setError,
    loading,
    restoring,
    openLocalLibrary,
    connectLocalLibrary,
    createPersonalLibrary,
    updateIndex,
    forgetLocalLibrary,
    importFile,
    removeImport,
    changeLibrary,
    changeContent,
  }
}
