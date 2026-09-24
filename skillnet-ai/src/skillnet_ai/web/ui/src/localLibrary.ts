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
  analysisStatus: 'missing' | 'ready' | 'error'
  analysisError: string | null
  warnings: string[]
  changedSkills: number
  removedSkills: number
  addedSkills: number
}

interface LocalResponse extends Omit<LocalLibraryData, 'analysis'> {
  name: string
  sourcePath: string
  graph: unknown | null
}

async function localRequest(body: object, signal?: AbortSignal): Promise<unknown> {
  const response = await fetch('/api/local-library', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  if (!response.headers.get('content-type')?.includes('application/json')) {
    throw new Error('Start the local service with skillnet ui to use folders.')
  }
  const value = await response.json()
  if (!response.ok)
    throw new Error(value.error || value.detail || 'Could not read the local skill library.')
  return value
}

export async function initialLibraryPath(): Promise<string | null> {
  try {
    const response = await fetch('/api/config', { signal: AbortSignal.timeout(5000) })
    if (!response.ok || !response.headers.get('content-type')?.includes('application/json'))
      return null
    const value = await response.json()
    return typeof value.sourcePath === 'string' ? value.sourcePath : null
  } catch {
    return null
  }
}

export async function createDefaultLibrary(): Promise<string> {
  const value = (await localRequest({ action: 'create-default' })) as { sourcePath: string }
  return value.sourcePath
}

export async function readLocalLibrary(
  library: LocalLibrary,
  signal?: AbortSignal,
): Promise<LocalLibraryData> {
  const value = (await localRequest(
    { sourcePath: library.sourcePath, indexPath: library.indexPath || null },
    signal,
  )) as LocalResponse
  if (!value.source || !Array.isArray(value.source.skills))
    throw new Error('Invalid local library response.')
  let analysis: Dataset | null = null
  let analysisError = value.analysisError
  try {
    if (value.graph) analysis = parseSnapshot(value.graph, `${value.name} · Analysis results`)
  } catch (error) {
    analysisError = error instanceof Error ? error.message : 'Invalid analysis snapshot.'
  }
  return {
    source: value.source,
    analysis,
    analysisError,
    analysisStatus: analysisError ? 'error' : analysis ? 'ready' : 'missing',
    warnings: value.warnings,
    changedSkills: value.changedSkills,
    removedSkills: value.removedSkills,
    addedSkills: value.addedSkills,
  }
}
