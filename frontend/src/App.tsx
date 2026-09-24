import { useEffect, useMemo, useRef, useState } from 'react'
import { ArrowDownRight, ArrowRight, CircleHelp, FileText, GitBranch, Search, Upload, X } from 'lucide-react'
import { demoDataset, parseSnapshot, relationLabel, skillShortName } from './data'
import type { Dataset, Evidence, Relation, Skill } from './data'
import catalogJson from './catalog.json'
import { clearImport, loadImports, loadLocalLibraries, loadView, removeLocalLibrary, saveImport, saveLocalLibrary, saveView } from './persistence'
import { createDefaultLibrary, readLocalLibrary } from './localLibrary'
import type { LocalLibrary, LocalLibraryData } from './localLibrary'
import evaluationsJson from './evaluations.json'
import { GraphView } from './GraphView'
import './styles.css'

function compactNumber(value: number) {
  return new Intl.NumberFormat('en-US').format(value)
}

function comparableLocalPath(value: string) {
  const path = value.replaceAll('\\', '/').replace(/\/+$/, '')
  return /^[a-zA-Z]:|^\/\//.test(path) ? path.toLowerCase() : path
}

interface BundledAnalysis { id: string; file: string; title: string; label: string; collection: string | null; skillCount: number; librarySkillCount: number | null }
const bundledAnalyses = catalogJson.snapshots as BundledAnalysis[]
const emptyPersonalDataset: Dataset = { kind: 'demo', title: 'My skill library', skills: [], relations: [] }
type EvaluationLevel = 'Good' | 'Average' | 'Poor'
type EvaluationDimension = 'safety' | 'completeness' | 'executability' | 'maintainability' | 'cost_awareness'
interface EvaluationReport {
  dimensions: Record<EvaluationDimension, { level: EvaluationLevel; reason: string }>
  injectionScan: { clean: boolean; complete: boolean; count: number }
}
const evaluations = evaluationsJson as Record<string, EvaluationReport>
const evaluationDimensions: Array<[EvaluationDimension, string]> = [
  ['safety', 'Safety'], ['completeness', 'Completeness'], ['executability', 'Executability'],
  ['maintainability', 'Maintainability'], ['cost_awareness', 'Cost awareness'],
]
const evaluationLevels: Record<EvaluationLevel, string> = { Good: 'Good', Average: 'Average', Poor: 'Poor' }

function evaluationFor(skill: Skill): EvaluationReport | null {
  const skillId = skill.skillId ?? skill.id
  const original = demoDataset.skills.find(item => item.skillId === skillId && item.collection === skill.collection)
  return original?.source.replaceAll('\r\n', '\n') === skill.source.replaceAll('\r\n', '\n') ? evaluations[skillId] ?? null : null
}

function firstConnectedSkill(dataset: Dataset): string {
  const counts = new Map<string, number>()
  for (const relation of dataset.relations) {
    counts.set(relation.source, (counts.get(relation.source) ?? 0) + 1)
    counts.set(relation.target, (counts.get(relation.target) ?? 0) + 1)
  }
  return dataset.skills.reduce((best, skill) => (counts.get(skill.id) ?? 0) > (counts.get(best) ?? 0) ? skill.id : best, dataset.skills[0]?.id ?? '')
}

function getProfileItems(profile: Record<string, unknown> | undefined, key: string): Array<{ text: string; lines: number[] }> {
  const entries = profile?.[key]
  if (!Array.isArray(entries)) return []
  return entries.flatMap(item => {
    if (typeof item !== 'object' || item === null || !('text' in item) || typeof item.text !== 'string') return []
    const evidence = 'evidence' in item && Array.isArray(item.evidence) ? item.evidence : []
    const lines = (evidence as unknown[]).flatMap((citation: unknown) => typeof citation === 'object' && citation !== null && 'line' in citation && typeof citation.line === 'number' ? [citation.line] : [])
    return [{ text: item.text, lines }]
  })
}

function SourceViewer({ skill, focusedLine }: { skill: Skill; focusedLine: number | null }) {
  const lines = useMemo(() => skill.source.split('\n'), [skill.source])
  useEffect(() => {
    if (focusedLine === null) return
    const timer = window.setTimeout(() => document.getElementById(`source-line-${focusedLine}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 60)
    return () => window.clearTimeout(timer)
  }, [skill.id, focusedLine])
  return (
    <div className="source-frame" aria-label={`${skill.name} SKILL.md source`}>
      {lines.map((line, index) => (
        <div id={`source-line-${index + 1}`} key={`${skill.id}-${index}`} className={`source-line ${focusedLine === index + 1 ? 'is-highlighted' : ''}`}>
          <span className="source-number">{index + 1}</span><span className="source-text">{line || ' '}</span>
        </div>
      ))}
    </div>
  )
}

function EvidenceLink({ evidence, onFocus }: { evidence: Evidence; onFocus: (skillId: string, line: number) => void }) {
  return <button type="button" className="evidence-link" onClick={() => onFocus(evidence.skillId, evidence.line)}><FileText size={14} /> {evidence.skillId.split('::').at(-1)} · L{evidence.line} <ArrowRight size={13} /></button>
}

function RelationInspector({ relation, dataset, onFocus, onSelectSkill }: { relation: Relation; dataset: Dataset; onFocus: (skillId: string, line: number) => void; onSelectSkill: (id: string) => void }) {
  const byId = new Map(dataset.skills.map(skill => [skill.id, skill]))
  return (
    <div className="inspector-content">
      <div className="relation-provenance"><div className={`relation-badge ${relation.type}`}>{relationLabel(relation.type)}</div><span>{dataset.kind === 'snapshot' ? 'Model analysis' : 'SKILL.md source reference'}</span></div>
      <div className="relation-path">
        <button type="button" onClick={() => onSelectSkill(relation.source)}>{byId.get(relation.source)?.name ?? relation.source}</button>
        <span>{relation.type === 'similar_to' ? '↔' : '→'}</span>
        <button type="button" onClick={() => onSelectSkill(relation.target)}>{byId.get(relation.target)?.name ?? relation.target}</button>
      </div>
      {relation.contexts.map((context, index) => (
        <section className="inspector-section" key={index}>
          <div className="section-index">Scenario {String(index + 1).padStart(2, '0')}</div>
          <h3>{context.scenario}</h3>
          <p>{context.explanation}</p>
          {context.conditions.length > 0 && <div className="condition-list">{context.conditions.map((condition, conditionIndex) => <span key={conditionIndex}>{condition}</span>)}</div>}
          <div className="evidence-group">
            <span className="field-label">Source text</span>
            {context.sourceEvidence.map((evidence, evidenceIndex) => <EvidenceLink key={evidenceIndex} evidence={evidence} onFocus={onFocus} />)}
          </div>
          {context.targetEvidence.length > 0 && <div className="evidence-group"><span className="field-label">Target text</span>{context.targetEvidence.map((evidence, evidenceIndex) => <EvidenceLink key={evidenceIndex} evidence={evidence} onFocus={onFocus} />)}</div>}
        </section>
      ))}
    </div>
  )
}

function SkillInspector({ skill, dataset, related, focusedLine, onFocus, onSelectRelation }: { skill: Skill; dataset: Dataset; related: Relation[]; focusedLine: number | null; onFocus: (skillId: string, line: number) => void; onSelectRelation: (id: string) => void }) {
  const groups = [
    ['when_to_use', 'When to use'],
    ['inputs', 'Inputs'],
    ['outputs', 'Outputs'],
    ['constraints', 'Constraints'],
    ['tools', 'Tools'],
  ] as const
  const byId = new Map(dataset.skills.map(item => [item.id, item]))
  const evaluation = evaluationFor(skill)
  return (
    <div className="inspector-content">
      <h2>{skill.name}</h2>
      <div className="skill-path"><FileText size={14} /> {dataset.kind === 'snapshot' ? 'Source at analysis time: ' : ''}{skill.path || skill.id}</div>
      <div className="capability-card"><div className="field-label">Capability summary · {skill.profile ? 'Model extracted' : 'SKILL.md description'}</div><p>{skill.description || 'No capability summary is available. Read the source below.'}</p></div>
      {evaluation && <section className="inspector-section evaluation-section">
        <div className="section-heading"><h3>Skill file evaluation</h3></div>
        <div className="evaluation-dimensions">{evaluationDimensions.map(([key, label]) => <details key={key}><summary><span>{label}</span><b className={`evaluation-level ${evaluation.dimensions[key].level.toLowerCase()}`}>{evaluationLevels[evaluation.dimensions[key].level]}</b></summary><p>{evaluation.dimensions[key].reason}</p></details>)}</div>
        <p className="evaluation-scan">Prompt injection prescreen: {evaluation.injectionScan.complete ? evaluation.injectionScan.clean ? 'No issues found' : `${evaluation.injectionScan.count} issue(s) found` : 'Not completed'}</p>
      </section>}
      {skill.profile && <div className="profile-source-label">Skill profile · Model extracted</div>}
      {skill.profile && <div className="profile-groups">{groups.map(([key, title]) => {
        const items = getProfileItems(skill.profile, key)
        if (items.length === 0) return null
        return <section className="profile-group" key={key}><h3>{title}</h3>{items.map((item, index) => <div className="profile-item" key={index}><span>{item.text}</span>{item.lines.map(line => <button key={line} type="button" onClick={() => onFocus(skill.id, line)}>L{line}</button>)}</div>)}</section>
      })}</div>}
      <section className="inspector-section related-section">
        <div className="section-heading"><h3>Related connections</h3><span>{related.length}</span></div>
        {related.length === 0 ? <p className="muted">No relationships are recorded in this dataset.</p> : <div className="related-list">{related.map(relation => {
          const otherId = relation.source === skill.id ? relation.target : relation.source
          const other = byId.get(otherId)
          return <button type="button" key={relation.id} onClick={() => onSelectRelation(relation.id)}><span className={`small-dot ${relation.type}`} /><span>{other?.name ?? otherId}</span><small>{relationLabel(relation.type)}</small><ArrowDownRight size={14} /></button>
        })}</div>}
      </section>
      <section className="inspector-section source-section">
        <div className="section-heading"><h3>SKILL.md source</h3><span>{skill.source.split('\n').length} lines</span></div>
        <SourceViewer skill={skill} focusedLine={focusedLine} />
      </section>
    </div>
  )
}

export default function App() {
  const [dataset, setDataset] = useState<Dataset>(emptyPersonalDataset)
  const [importedDatasets, setImportedDatasets] = useState<Array<{ id: string; dataset: Dataset }>>([])
  const [localLibraries, setLocalLibraries] = useState<LocalLibrary[]>([])
  const [localData, setLocalData] = useState<LocalLibraryData | null>(null)
  const [sourcePathInput, setSourcePathInput] = useState('')
  const [indexPathInput, setIndexPathInput] = useState('')
  const [sourceId, setSourceId] = useState('personal')
  const [collection, setCollection] = useState('personal')
  const [selectedSkillId, setSelectedSkillId] = useState('')
  const [selectedRelationId, setSelectedRelationId] = useState<string | null>(null)
  const [focusedLine, setFocusedLine] = useState<number | null>(null)
  const [query, setQuery] = useState('')
  const [evaluationOnly, setEvaluationOnly] = useState(false)
  const [depth, setDepth] = useState<1 | 2>(1)
  const [viewMode, setViewMode] = useState<'graph' | 'list'>('graph')
  const [relationQuery, setRelationQuery] = useState('')
  const [relationType, setRelationType] = useState<'all' | 'compose_with' | 'similar_to'>('all')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [restoring, setRestoring] = useState(true)
  const fileInput = useRef<HTMLInputElement>(null)
  const skillList = useRef<HTMLDivElement>(null)
  const graphCanvas = useRef<HTMLDivElement>(null)

  const collections = useMemo(() => {
    const counts = new Map<string, number>()
    demoDataset.skills.forEach(skill => counts.set(skill.collection ?? '', (counts.get(skill.collection ?? '') ?? 0) + 1))
    return Array.from(counts, ([name, count]) => ({ name, count }))
  }, [])
  useEffect(() => {
    let cancelled = false
    const restore = async () => {
      let imported: Array<{ id: string; dataset: Dataset }> = []
      try {
        const saved = await loadImports()
        imported = saved.flatMap(item => {
          try { return [{ id: item.id, dataset: parseSnapshot(JSON.parse(item.json) as unknown, item.name) }] }
          catch { return [] }
        })
      } catch {
        // An unavailable or damaged browser store should not block the bundled data.
      }
      if (cancelled) return
      setImportedDatasets(imported)
      let libraries: LocalLibrary[] = []
      try { libraries = await loadLocalLibraries() } catch { /* Browser storage may be unavailable. */ }
      if (cancelled) return
      setLocalLibraries(libraries)
      const view = loadView()
      const local = libraries.find(item => item.id === view?.collection)
      if (local) {
        try {
          const result = await readLocalLibrary(local)
          if (cancelled) return
          setLocalData(result)
          const selected = view?.sourceId === 'local-analysis' && result.analysis ? result.analysis : result.source
          setDataset(selected)
          setCollection(local.id)
          setSourceId(selected === result.analysis ? 'local-analysis' : 'local-source')
          setSelectedSkillId(selected.skills.some(skill => skill.id === view?.selectedSkillId) ? view!.selectedSkillId : firstConnectedSkill(selected))
        } catch {
          if (cancelled) return
          setError('The local skill library could not be read. Select it again from the Skill library menu.')
        }
      } else if (view?.sourceId === 'imported' && imported.some(item => item.id === view.collection)) {
        const saved = imported.find(item => item.id === view.collection)!
        setDataset(saved.dataset)
        setSourceId('imported')
        setCollection(saved.id)
        setSelectedSkillId(saved.dataset.skills.some(skill => skill.id === view.selectedSkillId) ? view.selectedSkillId : firstConnectedSkill(saved.dataset))
      } else {
        const analysis = bundledAnalyses.find(item => item.id === view?.sourceId && (item.collection ?? item.id) === view.collection)
        if (analysis) {
          try {
            const response = await fetch(`/data/${encodeURIComponent(analysis.file)}`)
            if (!response.ok) throw new Error('Could not read the analysis snapshot')
            const parsed = parseSnapshot(await response.json() as unknown, analysis.title, analysis.collection ?? undefined)
            if (cancelled) return
            setDataset(parsed)
            setSourceId(analysis.id)
            setCollection(analysis.collection ?? analysis.id)
            setSelectedSkillId(parsed.skills.some(skill => skill.id === view?.selectedSkillId) ? view!.selectedSkillId : firstConnectedSkill(parsed))
          } catch {
            if (cancelled) return
            setError('The last analysis snapshot could not be read. Returned to My skill library.')
          }
        } else if (view && (view.collection === 'all' || collections.some(item => item.name === view.collection))) {
          setDataset(demoDataset)
          setSourceId('local')
          setCollection(view.collection)
          setSelectedSkillId(demoDataset.skills.some(skill => skill.id === view.selectedSkillId && (view.collection === 'all' || skill.collection === view.collection))
            ? view.selectedSkillId
            : view.collection === 'all' ? firstConnectedSkill(demoDataset) : demoDataset.skills.find(skill => skill.collection === view.collection)?.id ?? '')
        }
      }
      if (!cancelled) setRestoring(false)
    }
    void restore()
    return () => { cancelled = true }
  }, [collections])
  useEffect(() => {
    if (!restoring) saveView({ collection, sourceId, selectedSkillId })
  }, [restoring, collection, sourceId, selectedSkillId])
  const visibleDataset = useMemo(() => {
    if (dataset.kind !== 'demo' || collection === 'all') return dataset
    const skills = dataset.skills.filter(skill => skill.collection === collection)
    const ids = new Set(skills.map(skill => skill.id))
    return { ...dataset, skills, relations: dataset.relations.filter(relation => ids.has(relation.source) && ids.has(relation.target)) }
  }, [dataset, collection])
  const graphDataset = useMemo(() => dataset.kind === 'snapshot' && relationType !== 'all'
    ? { ...visibleDataset, relations: visibleDataset.relations.filter(relation => relation.type === relationType) }
    : visibleDataset, [dataset.kind, visibleDataset, relationType])
  const relationRows = useMemo(() => {
    const needle = relationQuery.trim().toLocaleLowerCase()
    if (!needle) return graphDataset.relations
    const byId = new Map(visibleDataset.skills.map(skill => [skill.id, skill]))
    return graphDataset.relations.filter(relation => {
      const source = byId.get(relation.source)
      const target = byId.get(relation.target)
      return [relation.source, relation.target, source?.name, target?.name, ...relation.contexts.flatMap(context => [context.scenario, context.explanation])]
        .some(value => value?.toLocaleLowerCase().includes(needle))
    })
  }, [graphDataset, visibleDataset.skills, relationQuery])
  const analysisCounts = useMemo(() => ({
    compose: visibleDataset.relations.filter(relation => relation.type === 'compose_with').length,
    similar: visibleDataset.relations.filter(relation => relation.type === 'similar_to').length,
  }), [visibleDataset])
  const selectedSkill = useMemo(() => visibleDataset.skills.find(skill => skill.id === selectedSkillId) ?? visibleDataset.skills[0], [visibleDataset, selectedSkillId])
  const selectedRelation = useMemo(() => visibleDataset.relations.find(relation => relation.id === selectedRelationId) ?? null, [visibleDataset, selectedRelationId])
  const related = useMemo(() => visibleDataset.relations.filter(relation => relation.source === selectedSkill?.id || relation.target === selectedSkill?.id), [visibleDataset, selectedSkill])
  const relationCounts = useMemo(() => {
    const counts = new Map<string, number>()
    visibleDataset.relations.forEach(relation => {
      counts.set(relation.source, (counts.get(relation.source) ?? 0) + 1)
      counts.set(relation.target, (counts.get(relation.target) ?? 0) + 1)
    })
    return counts
  }, [visibleDataset])
  const evaluatedCount = useMemo(() => visibleDataset.skills.filter(skill => evaluationFor(skill)).length, [visibleDataset.skills])
  const filteredSkills = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase()
    return visibleDataset.skills.filter(skill => (!evaluationOnly || evaluationFor(skill)) && (!needle || `${skill.name} ${skill.description} ${skill.id}`.toLocaleLowerCase().includes(needle)))
  }, [visibleDataset, query, evaluationOnly])
  const displayedSkills = filteredSkills.slice(0, 200)
  const relationSkillName = (id: string) => {
    const skill = visibleDataset.skills.find(item => item.id === id)
    return skill ? skillShortName(skill) : id
  }
  useEffect(() => {
    const list = skillList.current
    if (!list) return
    const rows = Array.from(list.querySelectorAll<HTMLButtonElement>('.skill-row'))
    const row = rows.find(item => item.dataset.skillId === selectedSkillId)
    if (row && rows[0]) list.scrollTop = Math.max(0, row.offsetTop - rows[0].offsetTop)
  }, [selectedSkillId, visibleDataset, filteredSkills])
  useEffect(() => {
    const centerGraph = () => {
      const canvas = graphCanvas.current
      if (canvas && window.matchMedia('(max-width: 760px)').matches) {
        canvas.scrollLeft = (canvas.scrollWidth - canvas.clientWidth) / 2
      }
    }
    centerGraph()
    window.addEventListener('resize', centerGraph)
    return () => window.removeEventListener('resize', centerGraph)
  }, [selectedSkillId, depth, visibleDataset])

  const selectSkill = (id: string) => {
    setSelectedSkillId(id)
    setSelectedRelationId(null)
    setFocusedLine(null)
  }
  const selectRelation = (id: string) => {
    setSelectedRelationId(id)
    setFocusedLine(null)
  }
  const focusEvidence = (skillId: string, line: number) => {
    setSelectedSkillId(skillId)
    setSelectedRelationId(null)
    setFocusedLine(line)
  }
  const loadDemo = (name = 'all') => {
    setDataset(demoDataset)
    setLocalData(null)
    setSourceId('local')
    setCollection(name)
    setSelectedSkillId(name === 'all' ? firstConnectedSkill(demoDataset) : demoDataset.skills.find(skill => skill.collection === name)?.id ?? '')
    setSelectedRelationId(null)
    setFocusedLine(null)
    setQuery('')
    setEvaluationOnly(false)
    setRelationQuery('')
    setRelationType('all')
    setError(null)
    if (fileInput.current) fileInput.current.value = ''
  }
  const showPersonalLibrary = () => {
    setDataset(emptyPersonalDataset)
    setLocalData(null)
    setSourceId('personal')
    setCollection('personal')
    setSelectedSkillId('')
    setSelectedRelationId(null)
    setFocusedLine(null)
    setQuery('')
    setEvaluationOnly(false)
    setRelationQuery('')
    setRelationType('all')
    setError(null)
  }
  const loadBundledAnalysis = async (id: string) => {
    setLoading(true)
    setError(null)
    try {
      const analysis = bundledAnalyses.find(item => item.id === id)
      if (!analysis) throw new Error('The selected analysis was not found.')
      const response = await fetch(`/data/${encodeURIComponent(analysis.file)}`)
      if (!response.ok) throw new Error(`Could not load ${analysis.title}.`)
      const parsed = parseSnapshot(await response.json() as unknown, analysis.title, analysis.collection ?? undefined)
      setLocalData(null)
      setDataset(parsed)
      setSourceId(id)
      setCollection(analysis.collection ?? analysis.id)
      setSelectedSkillId(firstConnectedSkill(parsed))
      setSelectedRelationId(null)
      setFocusedLine(null)
      setQuery('')
      setEvaluationOnly(false)
      setRelationQuery('')
      setDepth(1)
      setRelationType('all')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load the analysis graph.')
    } finally {
      setLoading(false)
    }
  }
  const importFile = async (file: File | undefined) => {
    if (!file) return
    setLoading(true)
    setError(null)
    try {
      if (file.size > 20 * 1024 * 1024) throw new Error('The file exceeds 20 MB and cannot be imported.')
      const json = await file.text()
      const parsed = parseSnapshot(JSON.parse(json) as unknown, file.name)
      const id = `imported:${crypto.randomUUID()}`
      setLocalData(null)
      setImportedDatasets(previous => [...previous, { id, dataset: parsed }])
      setDataset(parsed)
      setSourceId('imported')
      setCollection(id)
      setSelectedSkillId(parsed.skills[0]?.id ?? '')
      setSelectedRelationId(null)
      setFocusedLine(null)
      setQuery('')
      setEvaluationOnly(false)
      setRelationQuery('')
      setRelationType('all')
      try {
        await saveImport({ id, name: file.name, json })
      } catch {
        setError('The snapshot is open, but the browser could not save this import. After a refresh, the previous snapshot may appear.')
      }
    } catch (cause) {
      setError(cause instanceof SyntaxError ? 'The file is not valid JSON.' : cause instanceof Error ? cause.message : 'Could not read this file.')
    } finally {
      setLoading(false)
      if (fileInput.current) fileInput.current.value = ''
    }
  }

  const openLocalLibrary = async (library: LocalLibrary, preferredSource = sourceId) => {
    setLoading(true)
    setError(null)
    try {
      const result = await readLocalLibrary(library)
      setLocalData(result)
      const selected = preferredSource === 'local-analysis' && result.analysis ? result.analysis : result.source
      setDataset(selected)
      setCollection(library.id)
      setSourceId(selected === result.analysis ? 'local-analysis' : 'local-source')
      setSelectedSkillId(selected.skills.some(skill => skill.id === selectedSkillId) ? selectedSkillId : firstConnectedSkill(selected))
      setSelectedRelationId(null)
      setFocusedLine(null)
      setQuery('')
      setRelationQuery('')
      setRelationType('all')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not read the local skill library.')
    } finally {
      setLoading(false)
    }
  }
  const connectLocalLibrary = async (sourcePath: string) => {
    setLoading(true)
    try {
      if (!sourcePath) throw new Error('Enter a skills folder path.')
      const existing = localLibraries.find(item => comparableLocalPath(item.sourcePath) === comparableLocalPath(sourcePath))
      if (existing) { await openLocalLibrary(existing, 'local-source'); setSourcePathInput(''); return }
      const library: LocalLibrary = { id: `local:${crypto.randomUUID()}`, name: sourcePath.replace(/[\\/]+$/, '').split(/[\\/]/).pop() || sourcePath, sourcePath }
      const result = await readLocalLibrary(library)
      await saveLocalLibrary(library)
      setLocalLibraries(previous => [...previous, library])
      setLocalData(result)
      setDataset(result.source)
      setCollection(library.id)
      setSourceId('local-source')
      setSelectedSkillId(firstConnectedSkill(result.source))
      setSelectedRelationId(null)
      setSourcePathInput('')
      setError(null)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not connect the local skill library.')
    } finally {
      setLoading(false)
    }
  }
  const addLocalLibrary = () => void connectLocalLibrary(sourcePathInput.trim())
  const createPersonalLibrary = async () => {
    setLoading(true)
    setError(null)
    try {
      const sourcePath = await createDefaultLibrary()
      await connectLocalLibrary(sourcePath)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not create the local skill library.')
    } finally {
      setLoading(false)
    }
  }
  const setLocalIndex = async () => {
    const library = localLibraries.find(item => item.id === collection)
    if (!library) return
    try {
      const indexPath = indexPathInput.trim()
      if (!indexPath) throw new Error('Enter an analysis output folder path.')
      const updated = { ...library, indexPath }
      const result = await readLocalLibrary(updated)
      if (!result.analysis) throw new Error('The selected folder has no graph.json pointed to by CURRENT.')
      await saveLocalLibrary(updated)
      setLocalLibraries(previous => previous.map(item => item.id === updated.id ? updated : item))
      setLocalData(result)
      setDataset(result.analysis)
      setSourceId('local-analysis')
      setSelectedSkillId(firstConnectedSkill(result.analysis))
      setIndexPathInput('')
      setError(null)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not read the analysis folder.')
    }
  }
  const useDefaultIndex = async () => {
    const library = localLibraries.find(item => item.id === collection)
    if (!library) return
    try {
      const updated = { ...library, indexPath: undefined }
      const result = await readLocalLibrary(updated)
      await saveLocalLibrary(updated)
      setLocalLibraries(previous => previous.map(item => item.id === updated.id ? updated : item))
      setLocalData(result)
      const selected = result.analysis ?? result.source
      setDataset(selected)
      setSourceId(result.analysis ? 'local-analysis' : 'local-source')
      setSelectedSkillId(firstConnectedSkill(selected))
      setIndexPathInput('')
      setError(null)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not read the default analysis folder.')
    }
  }
  const forgetLocalLibrary = async () => {
    const library = localLibraries.find(item => item.id === collection)
    if (!library) return
    try {
      await removeLocalLibrary(library.id)
      setLocalLibraries(previous => previous.filter(item => item.id !== library.id))
      showPersonalLibrary()
    } catch {
      setError('Could not remove the local skill library record.')
    }
  }

  const changeLibrary = (name: string) => {
    if (name === 'personal') {
      showPersonalLibrary()
      return
    }
    const local = localLibraries.find(item => item.id === name)
    if (local) {
      void openLocalLibrary(local, 'local-source')
    } else if (importedDatasets.some(item => item.id === name)) {
      const importedDataset = importedDatasets.find(item => item.id === name)!.dataset
      setLocalData(null)
      setDataset(importedDataset)
      setSourceId('imported')
      setCollection(name)
      setSelectedSkillId(firstConnectedSkill(importedDataset))
      setSelectedRelationId(null)
      setFocusedLine(null)
      setQuery('')
      setEvaluationOnly(false)
      setRelationQuery('')
      setRelationType('all')
      setError(null)
    } else if (bundledAnalyses.some(analysis => analysis.id === name && !analysis.collection)) {
      void loadBundledAnalysis(name)
    } else {
      loadDemo(name)
    }
  }

  const removeImport = async () => {
    setLoading(true)
    try {
      await clearImport(collection)
      setImportedDatasets(previous => previous.filter(item => item.id !== collection))
      showPersonalLibrary()
    } catch {
      setError('Could not remove the snapshot saved in this browser.')
    } finally {
      setLoading(false)
    }
  }

  const availableAnalyses = bundledAnalyses.filter(analysis => analysis.collection === collection || (!analysis.collection && analysis.id === collection))
  const emptyLocalLibrary = collection.startsWith('local:') && sourceId === 'local-source' && localData?.source.skills.length === 0
  const showWorkbench = !restoring && collection !== 'personal' && !emptyLocalLibrary
  const currentLibrary = localLibraries.find(item => item.id === collection)

  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="site-header-inner">
          <a href="https://skillnet.openkg.cn/" className="brand" aria-label="SkillNet website"><img src="/skillnet.png" alt="SkillNet" /></a>
          <div className="header-spacer" />
          <a className="header-link" href="https://github.com/zjunlp/SkillNet" target="_blank" rel="noreferrer">GitHub <ArrowRight size={14} /></a>
        </div>
      </header>

      <main>
        <section className="dataset-bar" aria-label="Current data source">
          <label className="collection-control">Skill library <select value={collection} disabled={loading || restoring} onChange={event => changeLibrary(event.target.value)}><optgroup label="My skill library"><option value="personal">My skill library</option>{localLibraries.map(item => <option key={item.id} value={item.id}>Local: {item.name}</option>)}</optgroup><optgroup label="Repository examples"><option value="all">All examples ({demoDataset.skills.length})</option>{collections.map(item => <option key={item.name} value={item.name}>{item.name} ({item.count})</option>)}</optgroup>{bundledAnalyses.some(analysis => !analysis.collection) && <optgroup label="Other analysis snapshots">{bundledAnalyses.filter(analysis => !analysis.collection).map(analysis => <option key={analysis.id} value={analysis.id}>{analysis.title}</option>)}</optgroup>}{importedDatasets.length > 0 && <optgroup label="Imported snapshots">{importedDatasets.map(item => <option key={item.id} value={item.id}>{item.dataset.title}</option>)}</optgroup>}</select></label>
          <label className="collection-control">Content <select value={sourceId} disabled={loading || restoring || collection === 'personal' || collection.startsWith('imported:')} onChange={event => { const id = event.target.value; if (id === 'local-source' && localData) { setDataset(localData.source); setSourceId(id); setSelectedSkillId(firstConnectedSkill(localData.source)); setSelectedRelationId(null) } else if (id === 'local-analysis' && localData?.analysis) { setDataset(localData.analysis); setSourceId(id); setSelectedSkillId(firstConnectedSkill(localData.analysis)); setSelectedRelationId(null) } else if (id === 'local') loadDemo(collection); else void loadBundledAnalysis(id) }}>{collection === 'personal' ? <option value="personal">No folder selected</option> : collection.startsWith('imported:') ? <option value="imported">Imported analysis snapshot</option> : collection.startsWith('local:') ? <><option value="local-source">SKILL.md source</option>{localData?.analysis && <option value="local-analysis">Current analysis snapshot ({localData.analysis.skills.length}/{localData.source.skills.length})</option>}</> : bundledAnalyses.some(analysis => !analysis.collection && analysis.id === collection) ? <option value={sourceId}>Analysis snapshot</option> : <><option value="local">SKILL.md source</option>{availableAnalyses.map(analysis => <option key={analysis.id} value={analysis.id}>Analysis snapshot ({analysis.skillCount}{analysis.librarySkillCount ? `/${analysis.librarySkillCount}` : ''})</option>)}</>}</select></label>
          {collection !== 'personal' && <details className="local-library-menu"><summary>Local folders</summary><div><label>Skills folder path<input value={sourcePathInput} onChange={event => setSourcePathInput(event.target.value)} placeholder="Absolute path to the skills folder" /></label><button type="button" onClick={addLocalLibrary}>Add skill library</button>{currentLibrary && <><p className="local-path">Current: {currentLibrary.sourcePath}</p><button type="button" onClick={() => void openLocalLibrary(currentLibrary)}>Refresh folder</button><label>Custom analysis folder<input value={indexPathInput} onChange={event => setIndexPathInput(event.target.value)} placeholder={currentLibrary.indexPath ?? 'Default: .skillnet'} /></label>{currentLibrary.indexPath && <p className="local-path">Analysis folder: {currentLibrary.indexPath}</p>}<button type="button" onClick={() => void setLocalIndex()}>Connect analysis folder</button>{currentLibrary.indexPath && <button type="button" onClick={() => void useDefaultIndex()}>Use default .skillnet</button>}<button type="button" onClick={() => void forgetLocalLibrary()}>Remove skill library</button></>}</div></details>}
          <div className="dataset-actions"><button type="button" className="primary-button" onClick={() => fileInput.current?.click()} disabled={loading || restoring}><Upload size={16} /> {loading ? 'Loading…' : 'Import graph.json'}</button>{collection.startsWith('imported:') && <button type="button" className="text-button" onClick={() => void removeImport()} disabled={loading}>Remove import</button>}<input ref={fileInput} type="file" accept=".json,application/json" className="visually-hidden" aria-label="Choose graph.json file" onChange={event => void importFile(event.target.files?.[0])} /></div>
          {collection !== 'personal' && !emptyLocalLibrary && <div className="dataset-summary" aria-label="Data summary">
            {dataset.kind === 'demo' ? <span><strong>{compactNumber(visibleDataset.relations.length)}</strong> document references</span> : <><span><strong>{compactNumber(analysisCounts.compose)}</strong> composable</span><span><strong>{compactNumber(analysisCounts.similar)}</strong> similar</span></>}
          </div>}
        </section>
        {collection.startsWith('local:') && sourceId === 'local-analysis' && localData && (localData.changedSkills > 0 || localData.removedSkills > 0) && <div className="stale-banner" role="status">The analysis snapshot differs from the skills folder: {localData.changedSkills} skill source files changed, and {localData.removedSkills} skills were removed. Relationships and evidence still use the source from analysis time. Run SkillNet analyze again to update them.</div>}
        {error && <div className="error-banner" role="alert"><CircleHelp size={18} /> {error}<button type="button" onClick={() => setError(null)} aria-label="Dismiss error"><X size={17} /></button></div>}

        {!restoring && collection === 'personal' && <section className="onboarding" aria-label="My skill library">
          <div className="onboarding-intro"><span>My skill library</span><h1>{localLibraries.length ? 'Choose a skills folder' : 'Your skill library is empty'}</h1><p>Your personal skills stay in a folder on your computer. Repository examples are kept separate.</p></div>
          {localLibraries.length > 0 && <div className="onboarding-connected"><h2>Connected folders</h2>{localLibraries.map(library => <button type="button" key={library.id} onClick={() => void openLocalLibrary(library, 'local-source')}><span>{library.name}<small>{library.sourcePath}</small></span><ArrowRight size={16} /></button>)}</div>}
          <div className="onboarding-grid"><div className="onboarding-choice"><h2>Start with an empty folder</h2><p>Click to create <code>.skillnet/skills</code> in your home folder and connect it here. It will not be added to the cloned repository.</p><button type="button" className="primary-button" onClick={() => void createPersonalLibrary()} disabled={loading}>Create my skill library</button></div><div className="onboarding-choice"><h2>Use existing skills</h2><p>Enter a folder that directly contains skill subfolders. Each skill subfolder needs a <code>SKILL.md</code> file.</p><label>Absolute path to skills folder<input value={sourcePathInput} onChange={event => setSourcePathInput(event.target.value)} placeholder="For example, C:\Users\me\skills" /></label><button type="button" className="onboarding-secondary" onClick={addLocalLibrary} disabled={loading}>Connect existing folder</button></div></div>
          <div className="onboarding-example"><span>Want to look around first? The repository includes WebShop, ALFWorld, and ScienceWorld examples.</span><button type="button" onClick={() => loadDemo()}>Browse repository examples <ArrowRight size={15} /></button></div>
        </section>}

        {!restoring && emptyLocalLibrary && <section className="onboarding" aria-label="Empty local skill library"><div className="onboarding-intro"><span>Local skill library</span><h1>This folder has no skills yet</h1><p>The folder is connected. Add skill subfolders at the path below, then click Refresh folder.</p></div><div className="onboarding-empty-path"><strong>Skills folder</strong><code>{currentLibrary?.sourcePath}</code></div><div className="onboarding-next"><h2>How to add skills</h2><p>Copy existing skill folders here, or use this path when you download or create skills with SkillNet. Each skill needs its own subfolder with a <code>SKILL.md</code> file.</p><code>skillnet download &lt;GitHub skill folder URL&gt; --target-dir &quot;{currentLibrary?.sourcePath}&quot;</code><p>Install the SkillNet SDK from this repository before using the download command. Creating skills also requires a model configuration. After adding skills, run <code>skillnet analyze &quot;{currentLibrary?.sourcePath}&quot;</code> to analyze relationships.</p><button type="button" className="primary-button" onClick={() => { if (currentLibrary) void openLocalLibrary(currentLibrary, 'local-source') }} disabled={loading}>Refresh folder</button></div><div className="onboarding-example"><span>You can also browse repository examples to see how skills and relationships appear.</span><button type="button" onClick={() => loadDemo()}>Browse repository examples <ArrowRight size={15} /></button></div></section>}

        {showWorkbench && <>
        <section className="workbench-heading"><h1>Skills and relationships</h1></section>

        <section className="workspace" aria-label="Skill exploration workspace">
          <aside className="skill-panel">
            <div className="panel-title"><strong>Skill list</strong><span className="count-pill">{filteredSkills.length}</span></div>
            <label className="search-box"><Search size={17} /><input type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder="Search name, capability, or ID" aria-label="Search skills" />{query && <button type="button" onClick={() => setQuery('')} aria-label="Clear search"><X size={14} /></button>}</label>
            <div className="list-caption"><span>{query || evaluationOnly ? `${filteredSkills.length} matches` : 'All skills'}{filteredSkills.length > 200 && ' (showing the first 200; search to narrow the list)'}</span><label className="evaluation-filter"><input type="checkbox" checked={evaluationOnly} disabled={evaluatedCount === 0} onChange={event => setEvaluationOnly(event.target.checked)} />Evaluated {evaluatedCount}</label></div>
            <div className="skill-list" role="list" ref={skillList}>
              {filteredSkills.length === 0 && <div className="no-results">No matching skills found.<button type="button" onClick={() => setQuery('')}>Clear search</button></div>}
              {displayedSkills.map(skill => {
                const active = skill.id === selectedSkill?.id
                const count = relationCounts.get(skill.id) ?? 0
                return <button type="button" className={`skill-row ${active ? 'is-active' : ''}`} key={skill.id} data-skill-id={skill.id} onClick={() => selectSkill(skill.id)} aria-current={active ? 'true' : undefined}><span className="skill-row-top"><strong>{skillShortName(skill)}</strong><ArrowRight size={15} /></span><span className="skill-row-description">{skill.description || 'View skill source and relationships'}</span><span className="skill-row-bottom"><span>{skill.skillId ?? skill.id}</span><span className="skill-row-markers">{evaluationFor(skill) && <span className="evaluated-mark">Evaluated</span>}{count > 0 && <span><GitBranch size={12} /> {count}</span>}</span></span></button>
              })}
            </div>
          </aside>

          <div className="graph-panel">
            <div className="panel-title graph-panel-title"><strong>Relationship view</strong><div className="graph-view-controls"><div className="graph-tools"><button type="button" className={viewMode === 'graph' ? 'is-on' : ''} onClick={() => setViewMode('graph')} aria-pressed={viewMode === 'graph'}>Graph</button><button type="button" className={viewMode === 'list' ? 'is-on' : ''} onClick={() => setViewMode('list')} aria-pressed={viewMode === 'list'}>List</button></div>{viewMode === 'graph' && <div className="graph-tools"><button type="button" className={depth === 1 ? 'is-on' : ''} onClick={() => setDepth(1)} aria-pressed={depth === 1}>1 hop</button><button type="button" className={depth === 2 ? 'is-on' : ''} onClick={() => setDepth(2)} aria-pressed={depth === 2}>2 hops</button></div>}</div></div>
            <div className="graph-subtitle"><span>{viewMode === 'graph' ? <>Focused on <strong>{selectedSkill ? skillShortName(selectedSkill) : '—'}</strong></> : `${relationRows.length} relationships`}</span>{dataset.kind === 'snapshot' && <label className="graph-relation-control">Relationship <select value={relationType} onChange={event => { setRelationType(event.target.value as 'all' | 'compose_with' | 'similar_to'); setSelectedRelationId(null) }}><option value="all">All</option><option value="compose_with">Composable</option><option value="similar_to">Similar</option></select></label>}{viewMode === 'graph' && dataset.kind === 'snapshot' && <span className="graph-limit">Showing up to {depth === 1 ? 10 : 16} neighbors; see all relationships in List</span>}</div>
            {viewMode === 'graph' ? <div className="graph-canvas" ref={graphCanvas}>{selectedSkill && <GraphView dataset={graphDataset} selectedSkillId={selectedSkill.id} selectedRelationId={selectedRelationId} depth={depth} onSelectSkill={selectSkill} onSelectRelation={selectRelation} />}</div> : <div className="relation-list-view"><label className="relation-search"><Search size={16} /><input type="search" value={relationQuery} onChange={event => setRelationQuery(event.target.value)} placeholder="Search skills, scenarios, or explanations" aria-label="Search relationships" /></label><div className="relation-list" role="list">{relationRows.length === 0 ? <p className="relation-list-empty">No matching relationships.</p> : relationRows.map(relation => <button type="button" key={relation.id} className={`relation-row ${selectedRelationId === relation.id ? 'is-active' : ''}`} onClick={() => selectRelation(relation.id)}><span className="relation-row-path"><strong>{relationSkillName(relation.source)}</strong><span>{relation.type === 'similar_to' ? '↔' : '→'}</span><strong>{relationSkillName(relation.target)}</strong></span><span className="relation-row-detail"><small className={`relation-badge ${relation.type}`}>{relationLabel(relation.type)}</small><span>{relation.contexts[0]?.scenario || relation.contexts[0]?.explanation}</span></span></button>)}</div></div>}
            <div className="graph-footer"><div className="legend">{dataset.kind === 'demo' ? <span><i className="legend-line reference" /> Document reference</span> : <><span><i className="legend-line compose" /> Composable</span><span><i className="legend-line similar" /> Similar</span></>}</div><span className="graph-desktop-help">{viewMode === 'graph' ? 'Click a node or line for details' : 'Click a relationship to view its scenario and evidence'}</span><span className="graph-mobile-help">{viewMode === 'graph' ? 'Swipe across the graph; tap a node or line for details' : 'Tap a relationship to view its scenario and evidence'}</span></div>
          </div>

          <aside className="detail-panel"><div className="panel-title"><strong>{selectedRelation ? 'Relationship details' : 'Skill details'}</strong></div>{selectedRelation ? <RelationInspector relation={selectedRelation} dataset={visibleDataset} onFocus={focusEvidence} onSelectSkill={selectSkill} /> : selectedSkill && <SkillInspector skill={selectedSkill} dataset={visibleDataset} related={related} focusedLine={focusedLine} onFocus={focusEvidence} onSelectRelation={selectRelation} />}</aside>
        </section>
        </>}

      </main>
    </div>
  )
}
