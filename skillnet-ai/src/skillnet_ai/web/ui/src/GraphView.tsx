import { useMemo } from 'react'
import type { Dataset, Relation, Skill } from './data'
import { relationLabel, skillShortName } from './data'

interface GraphViewProps {
  dataset: Dataset
  selectedSkillId: string
  selectedRelationId: string | null
  depth: 1 | 2
  onSelectSkill: (id: string) => void
  onSelectRelation: (id: string) => void
}

function getVisible(dataset: Dataset, selectedSkillId: string, depth: 1 | 2) {
  const maxNodes = depth === 1 ? 11 : 17
  const levels = new Map([[selectedSkillId, 0]])
  let frontier = [selectedSkillId]
  for (let step = 0; step < depth; step += 1) {
    const next: string[] = []
    for (const id of frontier) {
      for (const relation of dataset.relations) {
        if (relation.source !== id && relation.target !== id) continue
        const neighbor = relation.source === id ? relation.target : relation.source
        if (!levels.has(neighbor) && levels.size < maxNodes) {
          levels.set(neighbor, step + 1)
          next.push(neighbor)
        }
      }
    }
    frontier = next
  }
  return {
    skills: dataset.skills.filter((skill) => levels.has(skill.id)),
    relations: dataset.relations.filter((relation) => {
      const sourceLevel = levels.get(relation.source)
      const targetLevel = levels.get(relation.target)
      if (sourceLevel === undefined || targetLevel === undefined) return false
      if (sourceLevel === 0 || targetLevel === 0) return true
      return depth === 2 && Math.abs(sourceLevel - targetLevel) === 1
    }),
  }
}

function labelLines(skill: Skill): string[] {
  const label = skillShortName(skill)
  if (label.length <= 17) return [label]
  const words = label.split(' ')
  if (words.length < 2) return [label.slice(0, 16) + '…']
  const middle = Math.ceil(words.length / 2)
  return [words.slice(0, middle).join(' ').slice(0, 17), words.slice(middle).join(' ').slice(0, 17)]
}

function edgeCoordinates(
  source: { x: number; y: number },
  target: { x: number; y: number },
  offset: number,
  startPad: number,
  endPad: number,
) {
  const dx = target.x - source.x
  const dy = target.y - source.y
  const distance = Math.hypot(dx, dy) || 1
  const offsetX = (-dy * offset) / distance
  const offsetY = (dx * offset) / distance
  return {
    x1: source.x + (dx * startPad) / distance + offsetX,
    y1: source.y + (dy * startPad) / distance + offsetY,
    x2: target.x - (dx * endPad) / distance + offsetX,
    y2: target.y - (dy * endPad) / distance + offsetY,
  }
}

export function GraphView({
  dataset,
  selectedSkillId,
  selectedRelationId,
  depth,
  onSelectSkill,
  onSelectRelation,
}: GraphViewProps) {
  const visible = useMemo(
    () => getVisible(dataset, selectedSkillId, depth),
    [dataset, selectedSkillId, depth],
  )
  const byId = useMemo(() => new Map(dataset.skills.map((skill) => [skill.id, skill])), [dataset])
  const parallelOffsets = useMemo(() => {
    const pairs = new Map<string, Relation[]>()
    for (const relation of visible.relations) {
      const key = JSON.stringify([relation.source, relation.target].sort())
      const group = pairs.get(key) ?? []
      group.push(relation)
      pairs.set(key, group)
    }
    const offsets = new Map<string, { offset: number; count: number }>()
    for (const group of pairs.values()) {
      group.sort((a, b) => a.type.localeCompare(b.type) || a.source.localeCompare(b.source))
      group.forEach((relation, index) =>
        offsets.set(relation.id, {
          offset: (index - (group.length - 1) / 2) * 12,
          count: group.length,
        }),
      )
    }
    return offsets
  }, [visible.relations])
  const positions = useMemo(() => {
    const map = new Map<string, { x: number; y: number }>()
    map.set(selectedSkillId, { x: 340, y: 223 })
    const others = visible.skills.filter((skill) => skill.id !== selectedSkillId)
    others.forEach((skill, index) => {
      const angle = -Math.PI / 2 + (Math.PI * 2 * index) / Math.max(others.length, 1)
      const radiusX = others.length <= 6 ? 225 : 260
      const radiusY = others.length <= 6 ? 147 : 173
      map.set(skill.id, { x: 340 + Math.cos(angle) * radiusX, y: 223 + Math.sin(angle) * radiusY })
    })
    return map
  }, [visible.skills, selectedSkillId])

  if (visible.relations.length === 0) {
    return (
      <div className="graph-empty">
        <div className="graph-empty-symbol">○</div>
        <strong>No relationships to show</strong>
        <span>This skill has no recorded relationships.</span>
      </div>
    )
  }

  return (
    <svg
      className={`graph-svg ${depth === 2 ? 'is-expanded' : ''}`}
      viewBox="0 0 680 460"
      role="group"
      aria-label={`Local relationship graph centered on ${byId.get(selectedSkillId)?.name ?? selectedSkillId}`}
    >
      <defs>
        <marker
          id="arrow-compose"
          markerWidth="8"
          markerHeight="8"
          refX="6"
          refY="4"
          orient="auto"
          markerUnits="userSpaceOnUse"
        >
          <path d="M0 0 L8 4 L0 8" fill="none" stroke="#2c947f" strokeWidth="1.6" />
        </marker>
      </defs>
      {visible.relations.map((relation: Relation) => {
        const source = positions.get(relation.source)
        const target = positions.get(relation.target)
        if (!source || !target) return null
        const direction = relation.source < relation.target ? 1 : -1
        const lane = parallelOffsets.get(relation.id)
        const edge = edgeCoordinates(
          source,
          target,
          (lane?.offset ?? 0) * direction,
          relation.source === selectedSkillId ? 18 : 13,
          relation.target === selectedSkillId ? 19 : 14,
        )
        const selected = selectedRelationId === relation.id
        const secondary = relation.source !== selectedSkillId && relation.target !== selectedSkillId
        const marker = relation.type === 'compose_with' ? 'url(#arrow-compose)' : undefined
        const activate = () => onSelectRelation(relation.id)
        return (
          <g
            key={relation.id}
            className={`graph-edge ${relation.type} ${(lane?.count ?? 0) > 1 ? 'is-parallel' : ''} ${secondary ? 'is-secondary' : ''} ${selected ? 'is-selected' : ''}`}
            role="button"
            tabIndex={0}
            aria-label={`${byId.get(relation.source)?.name} ${relationLabel(relation.type)} ${byId.get(relation.target)?.name}`}
            onClick={activate}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                activate()
              }
            }}
          >
            <line {...edge} className="edge-line" markerEnd={marker} />
            <line {...edge} className="edge-hit" />
          </g>
        )
      })}
      {visible.skills.map((skill) => {
        const position = positions.get(skill.id)
        if (!position) return null
        const active = skill.id === selectedSkillId
        const lines = labelLines(skill)
        const labelAbove = position.y < 223
        const activate = () => onSelectSkill(skill.id)
        return (
          <g
            key={skill.id}
            className={`graph-node ${active ? 'is-active' : ''}`}
            transform={`translate(${position.x}, ${position.y})`}
            role="button"
            tabIndex={0}
            aria-label={`View skill ${skill.name}`}
            onClick={activate}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                activate()
              }
            }}
          >
            <circle r="18" className="node-hit" />
            {active && <circle r="17" className="node-halo" />}
            <circle r={active ? 12 : 8} className="node-circle" />
            {active && <circle r="3" className="node-core" />}
            {!active && (
              <text
                textAnchor="middle"
                y={labelAbove ? -20 - (lines.length - 1) * 16 : 25}
                className="node-label"
              >
                {lines.map((line, index) => (
                  <tspan key={index} x="0" dy={index === 0 ? 0 : 16}>
                    {line}
                  </tspan>
                ))}
              </text>
            )}
          </g>
        )
      })}
    </svg>
  )
}
