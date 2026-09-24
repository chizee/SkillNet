import demoJson from './demo.json'

export type RelationType = 'source_reference' | 'compose_with' | 'similar_to'

export interface Skill {
  id: string
  skillId?: string
  name: string
  description: string
  source: string
  path: string
  collection?: string
  profile?: Record<string, unknown>
}

export interface Evidence {
  skillId: string
  line: number
}

export interface RelationContext {
  scenario: string
  explanation: string
  conditions: string[]
  sourceEvidence: Evidence[]
  targetEvidence: Evidence[]
}

export interface Relation {
  id: string
  source: string
  target: string
  type: RelationType
  contexts: RelationContext[]
}

export interface Dataset {
  kind: 'demo' | 'snapshot'
  title: string
  skills: Skill[]
  relations: Relation[]
}

interface DemoBundle {
  skills: Array<{ id: string; skillId: string; name: string; description: string; source: string; path: string; collection: string }>
  references: Array<{ source: string; target: string; type: 'source_reference'; line: number; excerpt: string }>
}

const demo = demoJson as DemoBundle

export const demoDataset: Dataset = {
  kind: 'demo',
  title: 'Repository skills',
  skills: demo.skills,
  relations: demo.references.map((reference, index) => ({
    id: `reference-${index}`,
    source: reference.source,
    target: reference.target,
    type: 'source_reference',
    contexts: [{
      scenario: 'Explicit document reference',
      explanation: reference.excerpt,
      conditions: [],
      sourceEvidence: [{ skillId: reference.source, line: reference.line }],
      targetEvidence: [],
    }],
  })),
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function nonemptyString(value: unknown, name: string): string {
  if (typeof value !== 'string' || !value.trim()) throw new Error(`${name} is missing or is not text.`)
  return value
}

function citationLines(value: unknown, name: string, skillId: string, maxLine: number): Evidence[] {
  if (!Array.isArray(value) || value.length === 0) throw new Error(`${name} has no evidence lines.`)
  return value.map((item, index) => {
    if (!isRecord(item) || !Number.isInteger(item.line) || (item.line as number) < 1 || (item.line as number) > maxLine) {
      throw new Error(`${name}[${index}] has an invalid line number.`)
    }
    return { skillId, line: item.line as number }
  })
}

export function parseSnapshot(value: unknown, title: string, collection?: string): Dataset {
  if (!isRecord(value) || value.schema_version !== 1) {
    throw new Error('Only GraphSnapshot v1 is supported.')
  }
  if (!Array.isArray(value.skills) || !Array.isArray(value.relations)) {
    throw new Error('The file is missing a skills or relations array.')
  }
  if (value.skills.length === 0) throw new Error('The snapshot has no skills.')
  if (value.skills.length > 5000 || value.relations.length > 20000) {
    throw new Error('The limit is 5,000 skills and 20,000 relationships. Import a smaller file.')
  }
  const skills: Skill[] = value.skills.map((item: unknown, index: number) => {
    if (!isRecord(item)) throw new Error(`skills[${index}] is not an object.`)
    const profile = isRecord(item.profile) ? item.profile : undefined
    const capability = profile && isRecord(profile.capability) ? profile.capability.text : undefined
    return {
      id: nonemptyString(item.skill_id, `skills[${index}].skill_id`),
      name: nonemptyString(item.name, `skills[${index}].name`),
      description: typeof capability === 'string' ? capability : '',
      source: nonemptyString(item.source, `skills[${index}].source`),
      path: typeof item.path === 'string' ? item.path : '',
      collection,
      profile,
    }
  })
  const byId = new Map(skills.map(skill => [skill.id, skill]))
  const lineCount = (id: string) => byId.get(id)?.source.split('\n').length ?? 0
  if (byId.size !== skills.length) throw new Error('The snapshot contains duplicate skill_id values.')
  const relations: Relation[] = value.relations.map((item: unknown, index: number) => {
    if (!isRecord(item)) throw new Error(`relations[${index}] is not an object.`)
    const source = nonemptyString(item.source, `relations[${index}].source`)
    const target = nonemptyString(item.target, `relations[${index}].target`)
    if (!byId.has(source) || !byId.has(target)) throw new Error(`relations[${index}] refers to a missing skill.`)
    if (item.type !== 'compose_with' && item.type !== 'similar_to') {
      throw new Error(`relations[${index}] has an unsupported relationship type.`)
    }
    if (!Array.isArray(item.contexts) || item.contexts.length === 0) {
      throw new Error(`relations[${index}].contexts is empty.`)
    }
    const contexts: RelationContext[] = item.contexts.map((context: unknown, contextIndex: number) => {
      if (!isRecord(context)) throw new Error(`relations[${index}].contexts[${contextIndex}] is not an object.`)
      return {
        scenario: nonemptyString(context.scenario, `relations[${index}].contexts[${contextIndex}].scenario`),
        explanation: nonemptyString(context.explanation, `relations[${index}].contexts[${contextIndex}].explanation`),
        conditions: Array.isArray(context.conditions) ? context.conditions.filter((entry): entry is string => typeof entry === 'string') : [],
        sourceEvidence: citationLines(context.source_evidence, 'source_evidence', source, lineCount(source)),
        targetEvidence: citationLines(context.target_evidence, 'target_evidence', target, lineCount(target)),
      }
    })
    return { id: `relation-${index}`, source, target, type: item.type, contexts }
  })
  return {
    kind: 'snapshot',
    title,
    skills,
    relations,
  }
}

export function relationLabel(type: RelationType): string {
  switch (type) {
    case 'compose_with': return 'Composable'
    case 'similar_to': return 'Similar'
    case 'source_reference': return 'Document reference'
  }
}

export function skillShortName(skill: Skill): string {
  const collection = skill.collection || skill.path.match(/(?:^|\/)skills\/([^/]+)\//)?.[1]
  const prefix = collection?.toLowerCase().replace(/[^a-z0-9]+/g, '-')
  const name = prefix && skill.name.toLowerCase().startsWith(`${prefix}-`) ? skill.name.slice(prefix.length + 1) : skill.name
  return name.replaceAll('-', ' ')
}
