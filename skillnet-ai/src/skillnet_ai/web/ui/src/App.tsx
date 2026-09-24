import { useEffect, useMemo, useRef, useState } from 'react'
import { ArrowRight, CircleHelp, GitBranch, Search, Upload, X } from 'lucide-react'
import { relationLabel, skillShortName } from './data'
import { SkillInspector, RelationInspector } from './Inspectors'
import { useWorkspace } from './useWorkspace'
import { GraphView } from './GraphView'
import './styles.css'

function compactNumber(value: number) {
  return new Intl.NumberFormat('en-US').format(value)
}

export default function App() {
  const {
    dataset,
    importedDatasets,
    localLibraries,
    localData,
    sourceId,
    collection,
    selectedSkillId,
    setSelectedSkillId,
    error,
    setError,
    loading,
    restoring,
    openLocalLibrary,
    connectLocalLibrary,
    createPersonalLibrary,
    updateIndex,
    forgetLocalLibrary,
    importFile,
    removeImport,
    changeLibrary,
    changeContent,
  } = useWorkspace()
  const [sourcePathInput, setSourcePathInput] = useState('')
  const [indexPathInput, setIndexPathInput] = useState('')
  const [selectedRelationId, setSelectedRelationId] = useState<string | null>(null)
  const [focusedLine, setFocusedLine] = useState<number | null>(null)
  const [query, setQuery] = useState('')
  const [depth, setDepth] = useState<1 | 2>(1)
  const [viewMode, setViewMode] = useState<'graph' | 'list'>('graph')
  const [relationQuery, setRelationQuery] = useState('')
  const [relationType, setRelationType] = useState<'all' | 'compose_with' | 'similar_to'>('all')
  const fileInput = useRef<HTMLInputElement>(null)
  const skillList = useRef<HTMLDivElement>(null)
  const graphCanvas = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setSelectedRelationId(null)
    setFocusedLine(null)
    setQuery('')
    setRelationQuery('')
    setRelationType('all')
    setDepth(1)
    setSourcePathInput('')
    setIndexPathInput('')
  }, [dataset, collection, sourceId])

  const addLocalLibrary = () => void connectLocalLibrary(sourcePathInput)
  const setLocalIndex = () => {
    if (!indexPathInput.trim()) {
      setError('Enter an analysis folder path.')
      return
    }
    void updateIndex(indexPathInput.trim())
  }
  const useDefaultIndex = () => void updateIndex()
  const graphDataset = useMemo(
    () =>
      dataset.kind === 'snapshot' && relationType !== 'all'
        ? {
            ...dataset,
            relations: dataset.relations.filter((relation) => relation.type === relationType),
          }
        : dataset,
    [dataset, relationType],
  )
  const relationRows = useMemo(() => {
    const needle = relationQuery.trim().toLocaleLowerCase()
    if (!needle) return graphDataset.relations
    const byId = new Map(dataset.skills.map((skill) => [skill.id, skill]))
    return graphDataset.relations.filter((relation) => {
      const source = byId.get(relation.source)
      const target = byId.get(relation.target)
      return [
        relation.source,
        relation.target,
        source?.name,
        target?.name,
        ...relation.contexts.flatMap((context) => [context.scenario, context.explanation]),
      ].some((value) => value?.toLocaleLowerCase().includes(needle))
    })
  }, [graphDataset, dataset.skills, relationQuery])
  const analysisCounts = useMemo(
    () => ({
      compose: dataset.relations.filter((relation) => relation.type === 'compose_with').length,
      similar: dataset.relations.filter((relation) => relation.type === 'similar_to').length,
    }),
    [dataset],
  )
  const selectedSkill = useMemo(
    () => dataset.skills.find((skill) => skill.id === selectedSkillId) ?? dataset.skills[0],
    [dataset, selectedSkillId],
  )
  const selectedRelation = useMemo(
    () => dataset.relations.find((relation) => relation.id === selectedRelationId) ?? null,
    [dataset, selectedRelationId],
  )
  const related = useMemo(
    () =>
      dataset.relations.filter(
        (relation) =>
          relation.source === selectedSkill?.id || relation.target === selectedSkill?.id,
      ),
    [dataset, selectedSkill],
  )
  const relationCounts = useMemo(() => {
    const counts = new Map<string, number>()
    dataset.relations.forEach((relation) => {
      counts.set(relation.source, (counts.get(relation.source) ?? 0) + 1)
      counts.set(relation.target, (counts.get(relation.target) ?? 0) + 1)
    })
    return counts
  }, [dataset])
  const filteredSkills = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase()
    return dataset.skills.filter(
      (skill) =>
        !needle ||
        `${skill.name} ${skill.description} ${skill.id}`.toLocaleLowerCase().includes(needle),
    )
  }, [dataset, query])
  const displayedSkills = filteredSkills.slice(0, 200)
  const skillNames = useMemo(
    () => new Map(dataset.skills.map((skill) => [skill.id, skillShortName(skill)])),
    [dataset.skills],
  )
  const relationSkillName = (id: string) => skillNames.get(id) ?? id
  useEffect(() => {
    const list = skillList.current
    if (!list) return
    const rows = Array.from(list.querySelectorAll<HTMLButtonElement>('.skill-row'))
    const row = rows.find((item) => item.dataset.skillId === selectedSkillId)
    if (row && rows[0]) list.scrollTop = Math.max(0, row.offsetTop - rows[0].offsetTop)
  }, [selectedSkillId, dataset, filteredSkills])
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
  }, [selectedSkillId, depth, dataset])

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
  const emptyLocalLibrary =
    collection.startsWith('local:') &&
    sourceId === 'local-source' &&
    localData?.source.skills.length === 0
  const showWorkbench = !restoring && collection !== 'personal' && !emptyLocalLibrary
  const currentLibrary = localLibraries.find((item) => item.id === collection)

  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="site-header-inner">
          <a href="https://skillnet.openkg.cn/" className="brand" aria-label="SkillNet website">
            <img src="/skillnet.png" alt="SkillNet" />
          </a>
          <div className="header-spacer" />
          <a
            className="header-link"
            href="https://github.com/zjunlp/SkillNet"
            target="_blank"
            rel="noreferrer"
          >
            GitHub <ArrowRight size={14} />
          </a>
        </div>
      </header>

      <main>
        <fieldset className="dataset-controls" disabled={loading || restoring}>
          <section className="dataset-bar" aria-label="Current data source">
            <label className="collection-control">
              Skill library{' '}
              <select
                value={collection}
                aria-label="Skill library"
                disabled={loading || restoring}
                onChange={(event) => changeLibrary(event.target.value)}
              >
                <optgroup label="My skill library">
                  <option value="personal">My skill library</option>
                  {localLibraries.map((item) => (
                    <option key={item.id} value={item.id}>
                      Local: {item.name}
                    </option>
                  ))}
                </optgroup>
                {importedDatasets.length > 0 && (
                  <optgroup label="Imported snapshots">
                    {importedDatasets.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.dataset.title}
                      </option>
                    ))}
                  </optgroup>
                )}
              </select>
            </label>
            <label className="collection-control">
              View{' '}
              <select
                value={sourceId}
                aria-label="View"
                disabled={
                  loading ||
                  restoring ||
                  collection === 'personal' ||
                  collection.startsWith('imported:')
                }
                onChange={(event) => changeContent(event.target.value)}
              >
                {collection === 'personal' ? (
                  <option value="personal">No folder selected</option>
                ) : collection.startsWith('imported:') ? (
                  <option value="imported">Imported analysis snapshot</option>
                ) : collection.startsWith('local:') ? (
                  <>
                    <option value="local-source">Current skill files</option>
                    {localData?.analysis && (
                      <option value="local-analysis">
                        Analysis results ({localData.analysis.skills.length}/
                        {localData.source.skills.length})
                      </option>
                    )}
                  </>
                ) : null}
              </select>
            </label>
            {collection !== 'personal' && (
              <details className="local-library-menu">
                <summary>Local folders</summary>
                <div>
                  <label>
                    Skills folder path
                    <input
                      value={sourcePathInput}
                      onChange={(event) => setSourcePathInput(event.target.value)}
                      placeholder="Absolute path to the skills folder"
                    />
                  </label>
                  <button type="button" onClick={addLocalLibrary}>
                    Add skill library
                  </button>
                  {currentLibrary && (
                    <>
                      <p className="local-path">Current: {currentLibrary.sourcePath}</p>
                      <button type="button" onClick={() => void openLocalLibrary(currentLibrary)}>
                        Refresh folder
                      </button>
                      <label>
                        Custom analysis folder
                        <input
                          value={indexPathInput}
                          onChange={(event) => setIndexPathInput(event.target.value)}
                          placeholder={currentLibrary.indexPath ?? 'Default: .skillnet'}
                        />
                      </label>
                      {currentLibrary.indexPath && (
                        <p className="local-path">Analysis folder: {currentLibrary.indexPath}</p>
                      )}
                      <button type="button" onClick={() => void setLocalIndex()}>
                        Connect analysis folder
                      </button>
                      {currentLibrary.indexPath && (
                        <button type="button" onClick={() => void useDefaultIndex()}>
                          Use default .skillnet
                        </button>
                      )}
                      <button type="button" onClick={() => void forgetLocalLibrary()}>
                        Remove skill library
                      </button>
                    </>
                  )}
                </div>
              </details>
            )}
            <div className="dataset-actions">
              <button
                type="button"
                className="primary-button"
                onClick={() => fileInput.current?.click()}
                disabled={loading || restoring}
              >
                <Upload size={16} /> {loading ? 'Loading…' : 'Import graph.json'}
              </button>
              {collection.startsWith('imported:') && (
                <button
                  type="button"
                  className="text-button"
                  onClick={() => void removeImport()}
                  disabled={loading}
                >
                  Remove import
                </button>
              )}
              <input
                ref={fileInput}
                type="file"
                accept=".json,application/json"
                className="visually-hidden"
                aria-label="Choose graph.json file"
                onChange={(event) => {
                  const file = event.target.files?.[0]
                  event.target.value = ''
                  void importFile(file)
                }}
              />
            </div>
            {collection !== 'personal' && !emptyLocalLibrary && (
              <div className="dataset-summary" aria-label="Data summary">
                {dataset.kind === 'source' ? (
                  <span>
                    <strong>{compactNumber(dataset.skills.length)}</strong> skills
                  </span>
                ) : (
                  <>
                    <span>
                      <strong>{compactNumber(analysisCounts.compose)}</strong> composable
                    </span>
                    <span>
                      <strong>{compactNumber(analysisCounts.similar)}</strong> similar
                    </span>
                  </>
                )}
              </div>
            )}
          </section>
        </fieldset>
        {collection.startsWith('local:') &&
          sourceId === 'local-analysis' &&
          localData &&
          (localData.changedSkills > 0 ||
            localData.removedSkills > 0 ||
            localData.addedSkills > 0) && (
            <div className="stale-banner" role="status">
              The analysis snapshot differs from the skills folder: {localData.changedSkills} skill
              source files changed, and {localData.removedSkills} skills were removed, and{' '}
              {localData.addedSkills} have not been analyzed. Relationships and evidence still use
              the source from analysis time. Run SkillNet analyze again to update them.
            </div>
          )}
        {localData?.analysisError && (
          <div className="stale-banner" role="status">
            Analysis could not be loaded: {localData.analysisError} Current skill files are still
            available.
          </div>
        )}
        {localData && localData.warnings.length > 0 && (
          <details className="stale-banner">
            <summary>{localData.warnings.length} skill file(s) could not be read</summary>
            {localData.warnings.map((warning, index) => (
              <p key={index}>{warning}</p>
            ))}
          </details>
        )}
        {error && (
          <div className="error-banner" role="alert">
            <CircleHelp size={18} /> {error}
            <button type="button" onClick={() => setError(null)} aria-label="Dismiss error">
              <X size={17} />
            </button>
          </div>
        )}

        {!restoring && collection === 'personal' && (
          <fieldset className="dataset-controls" disabled={loading}>
            <section className="onboarding" aria-label="My skill library">
              <div className="onboarding-intro">
                <span>My skill library</span>
                <h1>
                  {localLibraries.length ? 'Choose a skills folder' : 'Your skill library is empty'}
                </h1>
                <p>Your skills stay in a folder on your computer.</p>
              </div>
              {localLibraries.length > 0 && (
                <div className="onboarding-connected">
                  <h2>Connected folders</h2>
                  {localLibraries.map((library) => (
                    <button
                      type="button"
                      key={library.id}
                      onClick={() => void openLocalLibrary(library, 'local-source')}
                    >
                      <span>
                        {library.name}
                        <small>{library.sourcePath}</small>
                      </span>
                      <ArrowRight size={16} />
                    </button>
                  ))}
                </div>
              )}
              <div className="onboarding-grid">
                <div className="onboarding-choice">
                  <h2>Start with an empty folder</h2>
                  <p>
                    Click to create <code>.skillnet/skills</code> in your home folder and connect it
                    here.
                  </p>
                  <button
                    type="button"
                    className="primary-button"
                    onClick={() => void createPersonalLibrary()}
                    disabled={loading}
                  >
                    Create my skill library
                  </button>
                </div>
                <div className="onboarding-choice">
                  <h2>Use existing skills</h2>
                  <p>
                    Enter a folder that directly contains skill subfolders. Each skill subfolder
                    needs a <code>SKILL.md</code> file.
                  </p>
                  <label>
                    Absolute path to skills folder
                    <input
                      value={sourcePathInput}
                      onChange={(event) => setSourcePathInput(event.target.value)}
                      placeholder="For example, C:\Users\me\skills"
                    />
                  </label>
                  <button
                    type="button"
                    className="onboarding-secondary"
                    onClick={addLocalLibrary}
                    disabled={loading}
                  >
                    Connect existing folder
                  </button>
                </div>
              </div>
            </section>
          </fieldset>
        )}

        {!restoring && emptyLocalLibrary && (
          <fieldset className="dataset-controls" disabled={loading}>
            <section className="onboarding" aria-label="Empty local skill library">
              <div className="onboarding-intro">
                <span>Local skill library</span>
                <h1>This folder has no skills yet</h1>
                <p>
                  The folder is connected. Add skill subfolders at the path below, then click
                  Refresh folder.
                </p>
              </div>
              <div className="onboarding-empty-path">
                <strong>Skills folder</strong>
                <code>{currentLibrary?.sourcePath}</code>
              </div>
              <div className="onboarding-next">
                <h2>How to add skills</h2>
                <p>
                  Copy existing skill folders here, or use this path when you download or create
                  skills with SkillNet. Each skill needs its own subfolder with a{' '}
                  <code>SKILL.md</code> file.
                </p>
                <code>
                  skillnet download &lt;GitHub skill folder URL&gt; --target-dir &quot;
                  {currentLibrary?.sourcePath}&quot;
                </code>
                <p>
                  Creating skills also requires a model configuration. After adding skills, run{' '}
                  <code>skillnet analyze &quot;{currentLibrary?.sourcePath}&quot;</code> to analyze
                  relationships.
                </p>
                <button
                  type="button"
                  className="primary-button"
                  onClick={() => {
                    if (currentLibrary) void openLocalLibrary(currentLibrary, 'local-source')
                  }}
                  disabled={loading}
                >
                  Refresh folder
                </button>
              </div>
            </section>
          </fieldset>
        )}

        {showWorkbench && (
          <>
            <section className="workbench-heading">
              <h1>Skills and relationships</h1>
            </section>

            <section className="workspace" aria-label="Skill exploration workspace">
              <aside className="skill-panel">
                <div className="panel-title">
                  <strong>Skill list</strong>
                  <span className="count-pill">{filteredSkills.length}</span>
                </div>
                <label className="search-box">
                  <Search size={17} />
                  <input
                    type="search"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Search name, capability, or ID"
                    aria-label="Search skills"
                  />
                  {query && (
                    <button type="button" onClick={() => setQuery('')} aria-label="Clear search">
                      <X size={14} />
                    </button>
                  )}
                </label>
                <div className="list-caption">
                  <span>
                    {query ? `${filteredSkills.length} matches` : 'All skills'}
                    {filteredSkills.length > 200 &&
                      ' (showing the first 200; search to narrow the list)'}
                  </span>
                </div>
                <div className="skill-list" role="list" ref={skillList}>
                  {filteredSkills.length === 0 && (
                    <div className="no-results">
                      No matching skills found.
                      <button type="button" onClick={() => setQuery('')}>
                        Clear search
                      </button>
                    </div>
                  )}
                  {displayedSkills.map((skill) => {
                    const active = skill.id === selectedSkill?.id
                    const count = relationCounts.get(skill.id) ?? 0
                    return (
                      <button
                        type="button"
                        className={`skill-row ${active ? 'is-active' : ''}`}
                        key={skill.id}
                        data-skill-id={skill.id}
                        onClick={() => selectSkill(skill.id)}
                        aria-current={active ? 'true' : undefined}
                      >
                        <span className="skill-row-top">
                          <strong>{skillShortName(skill)}</strong>
                          <ArrowRight size={15} />
                        </span>
                        <span className="skill-row-description">
                          {skill.description || 'View skill source and relationships'}
                        </span>
                        <span className="skill-row-bottom">
                          <span>{skill.id}</span>
                          <span className="skill-row-markers">
                            {count > 0 && (
                              <span>
                                <GitBranch size={12} /> {count}
                              </span>
                            )}
                          </span>
                        </span>
                      </button>
                    )
                  })}
                </div>
              </aside>

              <div className="graph-panel">
                <div className="panel-title graph-panel-title">
                  <strong>Relationship view</strong>
                  {dataset.kind === 'snapshot' && (
                    <div className="graph-view-controls">
                      <div className="graph-tools">
                        <button
                          type="button"
                          className={viewMode === 'graph' ? 'is-on' : ''}
                          onClick={() => setViewMode('graph')}
                          aria-pressed={viewMode === 'graph'}
                        >
                          Graph
                        </button>
                        <button
                          type="button"
                          className={viewMode === 'list' ? 'is-on' : ''}
                          onClick={() => setViewMode('list')}
                          aria-pressed={viewMode === 'list'}
                        >
                          List
                        </button>
                      </div>
                      {viewMode === 'graph' && (
                        <div className="graph-tools">
                          <button
                            type="button"
                            className={depth === 1 ? 'is-on' : ''}
                            onClick={() => setDepth(1)}
                            aria-pressed={depth === 1}
                          >
                            1 hop
                          </button>
                          <button
                            type="button"
                            className={depth === 2 ? 'is-on' : ''}
                            onClick={() => setDepth(2)}
                            aria-pressed={depth === 2}
                          >
                            2 hops
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
                {dataset.kind === 'snapshot' && (
                  <div className="graph-subtitle">
                    <span>
                      {viewMode === 'graph' ? (
                        <>
                          Focused on{' '}
                          <strong>{selectedSkill ? skillShortName(selectedSkill) : '—'}</strong>
                        </>
                      ) : (
                        `${relationRows.length} relationships`
                      )}
                    </span>
                    <label className="graph-relation-control">
                      Relationship{' '}
                      <select
                        value={relationType}
                        onChange={(event) => {
                          setRelationType(
                            event.target.value as 'all' | 'compose_with' | 'similar_to',
                          )
                          setSelectedRelationId(null)
                        }}
                      >
                        <option value="all">All</option>
                        <option value="compose_with">Composable</option>
                        <option value="similar_to">Similar</option>
                      </select>
                    </label>
                    {viewMode === 'graph' && (
                      <span className="graph-limit">
                        Showing up to {depth === 1 ? 10 : 16} neighbors; see all relationships in
                        List
                      </span>
                    )}
                  </div>
                )}
                {dataset.kind === 'source' ? (
                  <div className="graph-empty">
                    <strong>
                      {localData?.analysisStatus === 'error'
                        ? 'Analysis unavailable'
                        : localData?.analysis
                          ? 'Analysis results available'
                          : 'Not analyzed yet'}
                    </strong>
                    <span>
                      {localData?.analysis
                        ? 'Choose an analysis snapshot from View to inspect relationships and evidence.'
                        : 'Run SkillNet analyze to discover composable and similar skills.'}
                    </span>
                    {currentLibrary && !localData?.analysis && (
                      <code>skillnet analyze "{currentLibrary.sourcePath}"</code>
                    )}
                  </div>
                ) : viewMode === 'graph' ? (
                  <div className="graph-canvas" ref={graphCanvas}>
                    {selectedSkill && (
                      <GraphView
                        dataset={graphDataset}
                        selectedSkillId={selectedSkill.id}
                        selectedRelationId={selectedRelationId}
                        depth={depth}
                        onSelectSkill={selectSkill}
                        onSelectRelation={selectRelation}
                      />
                    )}
                  </div>
                ) : (
                  <div className="relation-list-view">
                    <label className="relation-search">
                      <Search size={16} />
                      <input
                        type="search"
                        value={relationQuery}
                        onChange={(event) => setRelationQuery(event.target.value)}
                        placeholder="Search skills, scenarios, or explanations"
                        aria-label="Search relationships"
                      />
                    </label>
                    <div className="relation-list" role="list">
                      {relationRows.length === 0 ? (
                        <p className="relation-list-empty">No matching relationships.</p>
                      ) : (
                        relationRows.map((relation) => (
                          <button
                            type="button"
                            key={relation.id}
                            className={`relation-row ${selectedRelationId === relation.id ? 'is-active' : ''}`}
                            onClick={() => selectRelation(relation.id)}
                          >
                            <span className="relation-row-path">
                              <strong>{relationSkillName(relation.source)}</strong>
                              <span>{relation.type === 'similar_to' ? '↔' : '→'}</span>
                              <strong>{relationSkillName(relation.target)}</strong>
                            </span>
                            <span className="relation-row-detail">
                              <small className={`relation-badge ${relation.type}`}>
                                {relationLabel(relation.type)}
                              </small>
                              <span>
                                {relation.contexts[0]?.scenario ||
                                  relation.contexts[0]?.explanation}
                              </span>
                            </span>
                          </button>
                        ))
                      )}
                    </div>
                  </div>
                )}
                {dataset.kind === 'snapshot' && (
                  <div className="graph-footer">
                    <div className="legend">
                      <span>
                        <i className="legend-line compose" /> Composable
                      </span>
                      <span>
                        <i className="legend-line similar" /> Similar
                      </span>
                    </div>
                    <span className="graph-desktop-help">
                      {viewMode === 'graph'
                        ? 'Click a node or line for details'
                        : 'Click a relationship to view its scenario and evidence'}
                    </span>
                    <span className="graph-mobile-help">
                      {viewMode === 'graph'
                        ? 'Swipe across the graph; tap a node or line for details'
                        : 'Tap a relationship to view its scenario and evidence'}
                    </span>
                  </div>
                )}
              </div>

              <aside className="detail-panel">
                <div className="panel-title">
                  <strong>{selectedRelation ? 'Relationship details' : 'Skill details'}</strong>
                </div>
                {selectedRelation ? (
                  <RelationInspector
                    relation={selectedRelation}
                    dataset={dataset}
                    onFocus={focusEvidence}
                    onSelectSkill={selectSkill}
                  />
                ) : (
                  selectedSkill && (
                    <SkillInspector
                      skill={selectedSkill}
                      dataset={dataset}
                      related={related}
                      focusedLine={focusedLine}
                      onFocus={focusEvidence}
                      onSelectRelation={selectRelation}
                    />
                  )
                )}
              </aside>
            </section>
          </>
        )}
      </main>
    </div>
  )
}
