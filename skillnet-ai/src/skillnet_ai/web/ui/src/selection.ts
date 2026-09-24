import type { Dataset } from './data'

export function firstConnectedSkill(dataset: Dataset): string {
  const counts = new Map<string, number>()
  for (const relation of dataset.relations) {
    counts.set(relation.source, (counts.get(relation.source) ?? 0) + 1)
    counts.set(relation.target, (counts.get(relation.target) ?? 0) + 1)
  }
  return dataset.skills.reduce(
    (best, skill) => ((counts.get(skill.id) ?? 0) > (counts.get(best) ?? 0) ? skill.id : best),
    dataset.skills[0]?.id ?? '',
  )
}
