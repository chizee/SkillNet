import { readFile, readdir, writeFile } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const frontend = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const dataDirectory = join(frontend, 'public', 'data')
const repository = JSON.parse(await readFile(join(frontend, 'src', 'demo.json'), 'utf8'))
const matchingCollection = skill => {
  const matches = repository.skills.filter(item => item.skillId === skill.skill_id && item.source.replaceAll('\r\n', '\n') === skill.source.replaceAll('\r\n', '\n'))
  if (matches.length === 1) return matches[0].collection
  const byPath = matches.filter(item => typeof skill.path === 'string' && skill.path.replaceAll('\\', '/').endsWith(item.path))
  return byPath.length === 1 ? byPath[0].collection : undefined
}
const collectionSizes = new Map()
for (const skill of repository.skills) {
  collectionSizes.set(skill.collection, (collectionSizes.get(skill.collection) ?? 0) + 1)
}

const snapshots = []
for (const file of (await readdir(dataDirectory)).filter(name => name.endsWith('.json') && name !== 'catalog.json').sort()) {
  const value = JSON.parse(await readFile(join(dataDirectory, file), 'utf8'))
  if (value.schema_version !== 1 || !Array.isArray(value.skills) || !Array.isArray(value.relations) || value.skills.length === 0) {
    throw new Error(`${file} is not a GraphSnapshot v1 file`)
  }
  const collections = new Set(value.skills.map(matchingCollection))
  const collection = collections.size === 1 ? [...collections][0] : undefined
  const name = collection || file.replace(/\.json$/i, '').replaceAll('-', ' ')
  const total = collection ? collectionSizes.get(collection) : undefined
  snapshots.push({
    id: `analysis:${file}`,
    file,
    title: `${name} · Analysis results`,
    label: `${name} (${value.skills.length}${total ? `/${total}` : ''})`,
    collection: collection ?? null,
    skillCount: value.skills.length,
    librarySkillCount: total ?? null,
  })
}

const output = join(frontend, 'src', 'catalog.json')
await writeFile(output, `${JSON.stringify({ snapshots }, null, 2)}\n`, 'utf8')
process.stdout.write(`Cataloged ${snapshots.length} analysis files in ${output}\n`)
