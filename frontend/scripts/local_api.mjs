import { mkdir, readFile, readdir, realpath, stat } from 'node:fs/promises'
import { homedir } from 'node:os'
import { basename, isAbsolute, join } from 'node:path'

const maxGraphBytes = 20 * 1024 * 1024
const maxSourceBytes = 20 * 1024 * 1024

function fail(message, status = 400) {
  const error = new Error(message)
  error.status = status
  throw error
}

function sourceDescription(source) {
  const folded = source.match(/^description:\s*>-?\s*\n((?:[ \t]+.*\n)+)/m)
  if (folded) return folded[1].trim().split('\n').map(line => line.trim()).join(' ')
  return source.match(/^description:\s*(.+)$/m)?.[1].trim().replace(/^['"]|['"]$/g, '') ?? ''
}

async function skillSources(sourcePath) {
  if (typeof sourcePath !== 'string' || !isAbsolute(sourcePath)) fail('Enter an absolute path to the skills folder.')
  let root
  try { root = await realpath(sourcePath) } catch { fail('The skills folder does not exist or cannot be read.') }
  const entries = (await readdir(root, { withFileTypes: true })).filter(item => item.isDirectory() && !item.name.startsWith('.'))
  if (entries.length > 5000) fail('This app can read up to 5,000 skills.')
  const skills = []
  let totalBytes = 0
  for (const entry of entries) {
    const path = join(root, entry.name, 'SKILL.md')
    let source
    try { source = (await readFile(path, 'utf8')).replace(/^\uFEFF/, '').replaceAll('\r\n', '\n') } catch (error) {
      if (error.code === 'ENOENT') continue
      throw error
    }
    totalBytes += Buffer.byteLength(source)
    if (totalBytes > maxSourceBytes) fail('Skill source files exceed 20 MB. Choose a smaller library.')
    if (!source.trim()) continue
    skills.push({
      id: entry.name,
      name: source.match(/^name:\s*(.+)$/m)?.[1].trim().replace(/^['"]|['"]$/g, '') ?? entry.name,
      description: sourceDescription(source),
      source,
      path: `${basename(root)}/${entry.name}/SKILL.md`,
    })
  }
  skills.sort((a, b) => a.id.localeCompare(b.id))
  const ids = new Set(skills.map(skill => skill.id))
  const references = []
  const alternatives = [...ids].filter(id => id.includes('-')).sort((a, b) => b.length - a.length).map(id => id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  const referencePattern = alternatives.length ? new RegExp(`(^|[^a-zA-Z0-9-])(${alternatives.join('|')})(?![a-zA-Z0-9-])`, 'g') : null
  for (const skill of skills) {
    const seen = new Set()
    skill.source.split('\n').forEach((line, index) => {
      for (const match of referencePattern ? line.matchAll(referencePattern) : []) {
        const target = match[2]
        if (target === skill.id || seen.has(target)) continue
        seen.add(target)
        references.push({ id: `reference-${references.length}`, source: skill.id, target, type: 'source_reference',
          contexts: [{ scenario: 'Explicit document reference', explanation: line.trim(), conditions: [], sourceEvidence: [{ skillId: skill.id, line: index + 1 }], targetEvidence: [] }] })
      }
    })
  }
  return { root, source: { kind: 'demo', title: basename(root), skills, relations: references } }
}

async function currentGraph(sourceRoot, indexPath) {
  if (indexPath != null && (typeof indexPath !== 'string' || !isAbsolute(indexPath))) fail('The analysis folder path must be absolute.')
  const root = indexPath || join(sourceRoot, '.skillnet')
  let pointer
  try { pointer = (await readFile(join(root, 'CURRENT'), 'utf8')).trim() } catch (error) {
    if (!indexPath && error.code === 'ENOENT') return null
    fail('CURRENT was not found in the analysis folder.')
  }
  if (!/^snapshot-[A-Za-z0-9_-]+$/.test(pointer)) fail('CURRENT in the analysis folder is invalid.')
  const graphPath = join(root, pointer, 'graph.json')
  let size
  try { size = (await stat(graphPath)).size } catch { fail('The current analysis snapshot has no graph.json.') }
  if (size > maxGraphBytes) fail('The analysis snapshot exceeds 20 MB. Import a smaller file.')
  let graph
  try { graph = JSON.parse(await readFile(graphPath, 'utf8')) } catch { fail('The current graph.json is not valid JSON.') }
  if (graph?.schema_version !== 1 || !Array.isArray(graph.skills) || !Array.isArray(graph.relations)) fail('The current graph.json is not GraphSnapshot v1.')
  return graph
}

async function payload(input) {
  if (input?.action === 'create-default') {
    const sourcePath = join(homedir(), '.skillnet', 'skills')
    await mkdir(sourcePath, { recursive: true })
    return { sourcePath: await realpath(sourcePath) }
  }
  const { root, source } = await skillSources(input.sourcePath)
  const graph = await currentGraph(root, input.indexPath)
  const current = new Map(source.skills.map(skill => [skill.id, skill.source.replaceAll('\r\n', '\n')]))
  if (graph && !graph.skills.some(skill => current.has(skill.skill_id))) fail('The analysis folder and skill library have no skills in common. Check the paths.')
  const changedSkills = graph?.skills.filter(skill => current.has(skill.skill_id) && current.get(skill.skill_id) !== skill.source.replaceAll('\r\n', '\n')).length ?? 0
  const removedSkills = graph?.skills.filter(skill => !current.has(skill.skill_id)).length ?? 0
  return { name: source.title, source, graph, changedSkills, removedSkills }
}

function localMiddleware(req, res, next) {
  if (req.url?.split('?')[0] !== '/api/local-library') return next()
  const host = req.headers.host ?? ''
  const origin = req.headers.origin ?? ''
  if (req.method !== 'POST' || req.headers['content-type']?.split(';')[0] !== 'application/json' || origin !== `http://${host}` || !/^127\.0\.0\.1(?::\d+)?$|^localhost(?::\d+)?$/.test(host)) {
    res.writeHead(403).end()
    return
  }
  let body = ''
  req.on('data', chunk => {
    body += chunk
    if (body.length > 4096) req.destroy()
  })
  req.on('end', async () => {
    try {
      const result = await payload(JSON.parse(body))
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' }).end(JSON.stringify(result))
    } catch (error) {
      res.writeHead(error.status ?? 400, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' }).end(JSON.stringify({ error: error.message || 'Could not read the local skill library.' }))
    }
  })
}

export function localLibraryApi() {
  return {
    name: 'skillnet-local-library',
    configureServer(server) { server.middlewares.use(localMiddleware) },
    configurePreviewServer(server) { server.middlewares.use(localMiddleware) },
  }
}
