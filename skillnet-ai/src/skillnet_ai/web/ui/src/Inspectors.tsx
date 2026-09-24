import { useEffect, useMemo } from 'react'
import { ArrowDownRight, ArrowRight, FileText } from 'lucide-react'
import { relationLabel, sourceLines } from './data'
import type { Dataset, Evidence, Relation, Skill } from './data'

function getProfileItems(
  profile: Record<string, unknown> | undefined,
  key: string,
): Array<{ text: string; lines: number[] }> {
  const entries = profile?.[key]
  if (!Array.isArray(entries)) return []
  return entries.flatMap((item) => {
    if (
      typeof item !== 'object' ||
      item === null ||
      !('text' in item) ||
      typeof item.text !== 'string'
    )
      return []
    const evidence = 'evidence' in item && Array.isArray(item.evidence) ? item.evidence : []
    const lines = (evidence as unknown[]).flatMap((citation: unknown) =>
      typeof citation === 'object' &&
      citation !== null &&
      'line' in citation &&
      typeof citation.line === 'number'
        ? [citation.line]
        : [],
    )
    return [{ text: item.text, lines }]
  })
}

function SourceViewer({ skill, focusedLine }: { skill: Skill; focusedLine: number | null }) {
  const lines = useMemo(() => sourceLines(skill.source), [skill.source])
  useEffect(() => {
    if (focusedLine === null) return
    const timer = window.setTimeout(
      () =>
        document
          .getElementById(`source-line-${focusedLine}`)
          ?.scrollIntoView({ behavior: 'smooth', block: 'center' }),
      60,
    )
    return () => window.clearTimeout(timer)
  }, [skill.id, focusedLine])
  return (
    <div className="source-frame" aria-label={`${skill.name} SKILL.md source`}>
      {lines.map((line, index) => (
        <div
          id={`source-line-${index + 1}`}
          key={`${skill.id}-${index}`}
          className={`source-line ${focusedLine === index + 1 ? 'is-highlighted' : ''}`}
        >
          <span className="source-number">{index + 1}</span>
          <span className="source-text">{line || ' '}</span>
        </div>
      ))}
    </div>
  )
}

function EvidenceLink({
  evidence,
  onFocus,
}: {
  evidence: Evidence
  onFocus: (skillId: string, line: number) => void
}) {
  return (
    <button
      type="button"
      className="evidence-link"
      onClick={() => onFocus(evidence.skillId, evidence.line)}
    >
      <FileText size={14} /> {evidence.skillId.split('::').at(-1)} · L{evidence.line}{' '}
      <ArrowRight size={13} />
    </button>
  )
}

export function RelationInspector({
  relation,
  dataset,
  onFocus,
  onSelectSkill,
}: {
  relation: Relation
  dataset: Dataset
  onFocus: (skillId: string, line: number) => void
  onSelectSkill: (id: string) => void
}) {
  const byId = new Map(dataset.skills.map((skill) => [skill.id, skill]))
  return (
    <div className="inspector-content">
      <div className="relation-provenance">
        <div className={`relation-badge ${relation.type}`}>{relationLabel(relation.type)}</div>
        <span>Model analysis</span>
      </div>
      <div className="relation-path">
        <button type="button" onClick={() => onSelectSkill(relation.source)}>
          {byId.get(relation.source)?.name ?? relation.source}
        </button>
        <span>{relation.type === 'similar_to' ? '↔' : '→'}</span>
        <button type="button" onClick={() => onSelectSkill(relation.target)}>
          {byId.get(relation.target)?.name ?? relation.target}
        </button>
      </div>
      {relation.contexts.map((context, index) => (
        <section className="inspector-section" key={index}>
          <div className="section-index">Scenario {String(index + 1).padStart(2, '0')}</div>
          <h3>{context.scenario}</h3>
          <p>{context.explanation}</p>
          {context.conditions.length > 0 && (
            <div className="condition-list">
              {context.conditions.map((condition, conditionIndex) => (
                <span key={conditionIndex}>{condition}</span>
              ))}
            </div>
          )}
          <div className="evidence-group">
            <span className="field-label">Source text</span>
            {context.sourceEvidence.map((evidence, evidenceIndex) => (
              <EvidenceLink key={evidenceIndex} evidence={evidence} onFocus={onFocus} />
            ))}
          </div>
          {context.targetEvidence.length > 0 && (
            <div className="evidence-group">
              <span className="field-label">Target text</span>
              {context.targetEvidence.map((evidence, evidenceIndex) => (
                <EvidenceLink key={evidenceIndex} evidence={evidence} onFocus={onFocus} />
              ))}
            </div>
          )}
        </section>
      ))}
    </div>
  )
}

export function SkillInspector({
  skill,
  dataset,
  related,
  focusedLine,
  onFocus,
  onSelectRelation,
}: {
  skill: Skill
  dataset: Dataset
  related: Relation[]
  focusedLine: number | null
  onFocus: (skillId: string, line: number) => void
  onSelectRelation: (id: string) => void
}) {
  const groups = [
    ['when_to_use', 'When to use'],
    ['inputs', 'Inputs'],
    ['outputs', 'Outputs'],
    ['constraints', 'Constraints'],
    ['tools', 'Tools'],
  ] as const
  const byId = new Map(dataset.skills.map((item) => [item.id, item]))
  return (
    <div className="inspector-content">
      <h2>{skill.name}</h2>
      <div className="skill-path">
        <FileText size={14} /> {dataset.kind === 'snapshot' ? 'Source at analysis time: ' : ''}
        {skill.path || skill.id}
      </div>
      <div className="capability-card">
        <div className="field-label">
          Capability summary · {skill.profile ? 'Model extracted' : 'SKILL.md description'}
        </div>
        <p>{skill.description || 'No capability summary is available. Read the source below.'}</p>
      </div>
      {skill.profile && <div className="profile-source-label">Skill profile · Model extracted</div>}
      {skill.profile && (
        <div className="profile-groups">
          {groups.map(([key, title]) => {
            const items = getProfileItems(skill.profile, key)
            if (items.length === 0) return null
            return (
              <section className="profile-group" key={key}>
                <h3>{title}</h3>
                {items.map((item, index) => (
                  <div className="profile-item" key={index}>
                    <span>{item.text}</span>
                    {item.lines.map((line) => (
                      <button key={line} type="button" onClick={() => onFocus(skill.id, line)}>
                        L{line}
                      </button>
                    ))}
                  </div>
                ))}
              </section>
            )
          })}
        </div>
      )}
      <section className="inspector-section related-section">
        <div className="section-heading">
          <h3>Related connections</h3>
          <span>{related.length}</span>
        </div>
        {related.length === 0 ? (
          <p className="muted">No relationships are recorded in this dataset.</p>
        ) : (
          <div className="related-list">
            {related.map((relation) => {
              const otherId = relation.source === skill.id ? relation.target : relation.source
              const other = byId.get(otherId)
              return (
                <button
                  type="button"
                  key={relation.id}
                  onClick={() => onSelectRelation(relation.id)}
                >
                  <span className={`small-dot ${relation.type}`} />
                  <span>{other?.name ?? otherId}</span>
                  <small>{relationLabel(relation.type)}</small>
                  <ArrowDownRight size={14} />
                </button>
              )
            })}
          </div>
        )}
      </section>
      <section className="inspector-section source-section">
        <div className="section-heading">
          <h3>SKILL.md source</h3>
          <span>{sourceLines(skill.source).length} lines</span>
        </div>
        <SourceViewer skill={skill} focusedLine={focusedLine} />
      </section>
    </div>
  )
}
