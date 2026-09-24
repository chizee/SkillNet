import type { LocalLibrary } from './localLibrary'

const databaseName = 'skillnet-workbench'
const viewKey = 'skillnet-workbench-view-v1'

export interface SavedView {
  collection: string
  sourceId: string
  selectedSkillId: string
}
export interface SavedImport {
  id: string
  name: string
  json: string
}

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(databaseName, 2)
    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains('imports')) db.createObjectStore('imports')
      if (!db.objectStoreNames.contains('libraries'))
        db.createObjectStore('libraries', { keyPath: 'id' })
    }
    request.onsuccess = () => {
      request.result.onversionchange = () => request.result.close()
      resolve(request.result)
    }
    request.onerror = () => reject(request.error)
    request.onblocked = () =>
      reject(new Error('Close other SkillNet tabs to update browser storage.'))
  })
}

async function transaction<T>(
  store: string,
  mode: IDBTransactionMode,
  action: (store: IDBObjectStore) => () => T,
): Promise<T> {
  const db = await openDatabase()
  return new Promise((resolve, reject) => {
    try {
      const tx = db.transaction(store, mode)
      const result = action(tx.objectStore(store))
      tx.oncomplete = () => {
        db.close()
        try {
          resolve(result())
        } catch (error) {
          reject(error)
        }
      }
      tx.onabort = tx.onerror = () => {
        db.close()
        reject(tx.error || new Error('Browser storage transaction failed.'))
      }
    } catch (error) {
      db.close()
      reject(error)
    }
  })
}

export function loadImports(): Promise<SavedImport[]> {
  return transaction('imports', 'readonly', (store) => {
    const values = store.getAll()
    const keys = store.getAllKeys()
    return () =>
      values.result.flatMap((value: unknown, index): SavedImport[] => {
        if (
          typeof value !== 'object' ||
          value === null ||
          !('name' in value) ||
          !('json' in value) ||
          typeof value.name !== 'string' ||
          typeof value.json !== 'string'
        )
          return []
        return [
          { id: `imported:${String(keys.result[index])}`, name: value.name, json: value.json },
        ]
      })
  })
}
export function saveImport(value: SavedImport): Promise<void> {
  return transaction('imports', 'readwrite', (store) => {
    store.put({ name: value.name, json: value.json }, value.id.slice('imported:'.length))
    return () => undefined
  })
}
export function clearImport(id: string): Promise<void> {
  return transaction('imports', 'readwrite', (store) => {
    store.delete(id.slice('imported:'.length))
    return () => undefined
  })
}
export function loadLocalLibraries(): Promise<LocalLibrary[]> {
  return transaction('libraries', 'readonly', (store) => {
    const request = store.getAll()
    return () =>
      request.result.filter(
        (item: unknown): item is LocalLibrary =>
          typeof item === 'object' &&
          item !== null &&
          'id' in item &&
          typeof item.id === 'string' &&
          'name' in item &&
          typeof item.name === 'string' &&
          'sourcePath' in item &&
          typeof item.sourcePath === 'string' &&
          (!('indexPath' in item) ||
            item.indexPath === undefined ||
            typeof item.indexPath === 'string'),
      )
  })
}
export function saveLocalLibrary(library: LocalLibrary): Promise<void> {
  return transaction('libraries', 'readwrite', (store) => {
    store.put(library)
    return () => undefined
  })
}
export function removeLocalLibrary(id: string): Promise<void> {
  return transaction('libraries', 'readwrite', (store) => {
    store.delete(id)
    return () => undefined
  })
}
export function loadView(): SavedView | null {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(viewKey) ?? 'null')
    if (
      typeof value !== 'object' ||
      value === null ||
      !('collection' in value) ||
      !('sourceId' in value) ||
      !('selectedSkillId' in value)
    )
      return null
    if (
      typeof value.collection !== 'string' ||
      typeof value.sourceId !== 'string' ||
      typeof value.selectedSkillId !== 'string'
    )
      return null
    return value as SavedView
  } catch {
    return null
  }
}
export function saveView(view: SavedView): void {
  try {
    localStorage.setItem(viewKey, JSON.stringify(view))
  } catch {
    /* Browsing works without storage. */
  }
}
