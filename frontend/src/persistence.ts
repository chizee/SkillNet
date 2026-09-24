const databaseName = 'skillnet-workbench'
const storeName = 'imports'
const librariesStore = 'libraries'
const viewKey = 'skillnet-workbench-view-v1'
import type { LocalLibrary } from './localLibrary'

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
      if (!request.result.objectStoreNames.contains(storeName)) request.result.createObjectStore(storeName)
      if (!request.result.objectStoreNames.contains(librariesStore)) request.result.createObjectStore(librariesStore, { keyPath: 'id' })
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

export async function loadImports(): Promise<SavedImport[]> {
  const database = await openDatabase()
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(storeName, 'readonly')
    const values = transaction.objectStore(storeName).getAll()
    const keys = transaction.objectStore(storeName).getAllKeys()
    transaction.oncomplete = () => {
      database.close()
      resolve((values.result as Array<{ name: string; json: string }>).map((item, index) => ({ id: `imported:${String(keys.result[index])}`, ...item })))
    }
    transaction.onerror = () => { database.close(); reject(transaction.error) }
  })
}

export async function saveImport(value: SavedImport): Promise<void> {
  const database = await openDatabase()
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(storeName, 'readwrite')
    transaction.objectStore(storeName).put({ name: value.name, json: value.json }, value.id.slice('imported:'.length))
    transaction.oncomplete = () => { database.close(); resolve() }
    transaction.onerror = () => { database.close(); reject(transaction.error) }
  })
}

export async function clearImport(id: string): Promise<void> {
  const database = await openDatabase()
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(storeName, 'readwrite')
    transaction.objectStore(storeName).delete(id.slice('imported:'.length))
    transaction.oncomplete = () => { database.close(); resolve() }
    transaction.onerror = () => { database.close(); reject(transaction.error) }
  })
}

export async function loadLocalLibraries(): Promise<LocalLibrary[]> {
  const database = await openDatabase()
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(librariesStore, 'readonly')
    const request = transaction.objectStore(librariesStore).getAll()
    request.onsuccess = () => resolve(request.result as LocalLibrary[])
    request.onerror = () => reject(request.error)
    transaction.oncomplete = () => database.close()
    transaction.onerror = () => database.close()
  })
}

export async function saveLocalLibrary(library: LocalLibrary): Promise<void> {
  const database = await openDatabase()
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(librariesStore, 'readwrite')
    transaction.objectStore(librariesStore).put(library)
    transaction.oncomplete = () => { database.close(); resolve() }
    transaction.onerror = () => { database.close(); reject(transaction.error) }
  })
}

export async function removeLocalLibrary(id: string): Promise<void> {
  const database = await openDatabase()
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(librariesStore, 'readwrite')
    transaction.objectStore(librariesStore).delete(id)
    transaction.oncomplete = () => { database.close(); resolve() }
    transaction.onerror = () => { database.close(); reject(transaction.error) }
  })
}

export function loadView(): SavedView | null {
  try {
    const value = JSON.parse(localStorage.getItem(viewKey) ?? 'null') as unknown
    if (typeof value !== 'object' || value === null || !('collection' in value) || !('sourceId' in value) || !('selectedSkillId' in value)) return null
    if (typeof value.collection !== 'string' || typeof value.sourceId !== 'string' || typeof value.selectedSkillId !== 'string') return null
    return value as SavedView
  } catch {
    return null
  }
}

export function saveView(view: SavedView): void {
  try {
    localStorage.setItem(viewKey, JSON.stringify(view))
  } catch {
    // Browsing still works when local storage is disabled.
  }
}
