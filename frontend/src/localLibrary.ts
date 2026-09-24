import { parseSnapshot } from './data'
import type { Dataset } from './data'

export interface LocalLibrary {
  id: string
  name: string
  sourcePath: string
  indexPath?: string
}

export interface LocalLibraryData {
  source: Dataset
  analysis: Dataset | null
  changedSkills: number
  removedSkills: number
}

interface LocalResponse {
  name: string
  source: Dataset
  graph: unknown | null
  changedSkills: number
  removedSkills: number
}

export async function createDefaultLibrary(): Promise<string> {
  const response = await fetch('/api/local-library', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'create-default' }),
  })
  if (!response.headers.get('content-type')?.includes('application/json')) throw new Error('To create a local skill library, open the app with npm run dev or npm run preview.')
  const value = await response.json() as { sourcePath?: string; error?: string }
  if (!response.ok || !value.sourcePath) throw new Error(value.error || 'Could not create the local skill library.')
  return value.sourcePath
}

export async function readLocalLibrary(library: LocalLibrary): Promise<LocalLibraryData> {
  const response = await fetch('/api/local-library', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sourcePath: library.sourcePath, indexPath: library.indexPath || null }),
  })
  if (!response.headers.get('content-type')?.includes('application/json')) throw new Error('To use local folders, open the app with npm run dev or npm run preview.')
  const value = await response.json() as LocalResponse | { error: string }
  if (!response.ok) throw new Error('error' in value ? value.error : 'Could not read the local skill library.')
  if (!('source' in value)) throw new Error('Invalid local skill library response.')
  const analysis = value.graph ? parseSnapshot(value.graph, `${value.name} · Current analysis snapshot`) : null
  const source = { ...value.source, skills: value.source.skills.map(skill => ({ ...skill, collection: library.id })) }
  return { source, analysis, changedSkills: value.changedSkills, removedSkills: value.removedSkills }
}
