// The shapes of the data the back end sends. Each type mirrors a Python
// function's answer; if the back end changes a field, update it here and
// TypeScript will point to every place in the page that needs to follow.

export type Match = 'yes' | 'partial' | 'no'
export type Importance = 'core' | 'must' | 'nice'
export type Level = 'junior' | 'not stated' | 'senior'

// One line of a fit review (fit_rules.py, Requirement).
export type Requirement = {
  requirement: string
  importance: Importance
  evidence: string
  match: Match
}

// A fit review, after the code checks (fit_rules.check_and_score).
export type Fit = {
  score: number | null // null: too few requirements to score, shown as "?"
  summary: string
  notes: string[]
  requirements: Requirement[]
  work_mode: string
  years_required: number
  model: string // who scored it, e.g. "Claude"
  scored: string // when, "2026-10-14 21:05"
  cv: string // fingerprint of the CV it was scored against
  defence_related?: boolean
}

// One table row (pipeline.jobs_for_display, without the posting text).
export type Job = {
  url: string // the listing's link; also the job's id everywhere
  title: string
  company: string
  field: string
  industry: string
  company_size: string
  city: string // the listing's city (often in Hebrew)
  location: string // the company site's own location, "" if unknown
  distance_km: number | null
  updated: string // "2026-10-03"
  data_level: string
  level: Level
  level_reason: string
  industries: Record<string, string> // {industry id: reason}
  has_text: boolean
  apply_url: string
  source: string // where the posting text came from: "Comeet", "Workday"...
  work_mode: string // stated by the company's site, "" if not
  fit: Fit | null
  applied: string | null // the date you marked it, or null
  years: number | null // years of experience the posting asks for; null if unknown
  for_graduates: boolean // the posting is aimed at recent graduates
  first_seen: string // when it first appeared in your list, "2026-10-25T15:24:07"; "" if in the first one
  hidden: string | null // why your preferences hide it, or null if shown
}

// GET /api/jobs
export type JobsAnswer = { jobs: Job[]; hidden_count: number }

// GET /api/hidden: one row per hidden job.
export type HiddenJob = { title: string; company: string; reason: string }

// The CV currently loaded (data/cv_info.json).
export type CvInfo = {
  name: string
  characters: number
  uploaded: string
  professional_years?: number
}

// GET /api/status
export type Status = {
  cv: CvInfo | null
  jobs_updated: string | null
  home: string
  default_max_km: number
  default_fields: string[]
  credit: string
  scorer: Scorer | null // the AI connection in use; null if none was added yet
  setup_needed: boolean // first run: no preferences saved yet
  startup_problem: string | null // e.g. data saved by a newer version of the app
  version: string // this app's version, e.g. "0.1.0"
  update: AppUpdate | null // a newer version on GitHub, if there is one
  new_since: string | null // the end of your previous visit: jobs that appeared after it are new
}

// The AI connection that scores (connections.py), as /api/status describes it.
export type Scorer = {
  id: string // e.g. "c1"
  name: string // the name you gave it, e.g. "Claude Code"
  kind: string // "claude", "ollama" or "api"
  batch_size: number // jobs per request
}

// The progress of a background task: GET /api/fit/status and /api/update/status.
export type Progress = { running: boolean; done: number; total: number; error: string }
export type FitProgress = Progress & {
  stop_requested: boolean
  started: number // when scoring began, in seconds since 1970
}
export type UpdateSummary = { jobs: number; hidden: number; new_postings: number }
export type UpdateProgress = Progress & { stage: string; summary: UpdateSummary | null }

// One scoring batch from GET /api/fit/log (scoring.py writes these).
export type BatchRecord = {
  time: string // "2026-10-17 03:21"
  provider?: string // recorded from 2026-10-18 on
  connection?: string // the AI connection that made it, e.g. "c1"
  model: string
  jobs: number
  input_tokens: number
  cache_write_tokens: number
  cache_read_tokens: number
  output_tokens: number
  cost_equivalent_usd: number // the pay-per-use price; on a subscription, usage instead
  seconds?: number // recorded from 2026-10-18 on
}

// ---- AI connections (connections.py) -------------------------------------------

export type ConnectionKind = 'claude' | 'anthropic' | 'ollama' | 'api'

// What you choose when adding or changing a connection.
export type ConnectionFields = {
  name: string
  kind: ConnectionKind
  service?: string // for 'api': a key of `services` below, or 'custom'
  base_url?: string // for a custom service
  model?: string
}

// A saved connection, as the page sees it: never the key, only a hint of it.
export type Connection = Required<ConnectionFields> & {
  id: string
  key_hint: string
  // For a Claude plan: how much of a 5-hour session 1,000 tokens cost, learned
  // from the % that /usage showed (connections.calibrate).
  calibration?: { percent_per_1k_tokens: number; percent: number; tokens: number }
}

// GET /api/connections (and the answer to every change).
export type ConnectionsAnswer = {
  active: string | null
  connections: Connection[]
  kinds: Record<ConnectionKind, string> // e.g. {claude: "Claude Code", ...}
  services: Record<string, string> // e.g. {groq: "Groq", ...}
}

// POST /api/connections/detect: what is on this PC. null: not looked for, or not running.
export type DetectAnswer = { claude: boolean | null; ollama: string[] | null; lmstudio: string[] | null }

// POST /api/connections/test
export type TestAnswer = { ok: boolean; error?: string; model?: string; seconds?: number }

// Which connection a models or test request is about: a saved one (by id), or
// one being set up (its fields). key, if given, is used instead of the saved one.
export type ConnectionTarget = { id?: string; fields?: ConnectionFields; key?: string }

// ---- Preferences (preferences.py) and places (places.py) ------------------------

// A town or village, with its position: your home, or a search result.
export type Place = { name: string; he?: string; lat: number; lon: number }

export type Preferences = {
  levels: string[] // "junior", "not stated", "senior"
  fields: string[] // ticked in the Fields filter when the page opens
  hide_industries: string[] // industry ids, e.g. "defence"
  max_age_days: number // 0: any age
  max_years: number | null // hide postings asking for more; null: no limit
  keep_unknown_years: boolean // with a limit, still show postings that don't say
  home: Place | null // null until you choose it in the setup
}

// GET /api/preferences: yours, and every choice the page can offer.
export type PreferencesAnswer = {
  preferences: Preferences
  levels: string[]
  fields: string[]
  industries: Record<string, string> // {id: label}
}

// POST /api/cv/suggest: preferences suggested from your CV (not saved yet).
export type Suggestions = {
  preferences: Preferences
  roles: string[] // job titles that suit the CV
  professional_years: number
}

// A newer version of the app (updates.py).
export type AppUpdate = {
  version: string // e.g. "0.2.0"
  notes: string // what's new, from the Release
  page: string // the Release page on GitHub
  installer: string // the Windows installer's download address, "" if none
}
