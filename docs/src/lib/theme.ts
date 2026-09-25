// Plate colour: the one colour this site owns. Every site made from this
// scaffold shares the layout; the plate is what tells them apart.
//
// By default the plate is picked from the repo name, so two repos rarely match.
// To choose on purpose, set PLATE to one of the names below
// (see references/design-patterns.md for when each one fits).

type Plate = { l: number; c: number; h: number }

export const PLATES = {
  signal: { l: 0.7, c: 0.17, h: 22 },
  marigold: { l: 0.84, c: 0.14, h: 82 },
  chartreuse: { l: 0.88, c: 0.16, h: 118 },
  mint: { l: 0.85, c: 0.11, h: 165 },
  lagoon: { l: 0.8, c: 0.1, h: 205 },
  cobalt: { l: 0.72, c: 0.13, h: 262 },
  iris: { l: 0.76, c: 0.12, h: 298 },
  orchid: { l: 0.8, c: 0.11, h: 340 },
} satisfies Record<string, Plate>

export type PlateName = keyof typeof PLATES

const PLATE: PlateName | null = null

function pickPlateByName(key: string): PlateName {
  let hash = 0
  for (const ch of key) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0
  const names = Object.keys(PLATES) as PlateName[]
  return names[hash % names.length]
}

export const plateName: PlateName = PLATE ?? pickPlateByName('hyndsyght')
export const plate: Plate = PLATES[plateName]
