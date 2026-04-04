// ─── Email Types ───

export interface Email {
  id: string
  provider: 'gmail' | 'outlook'
  external_id: string
  thread_id: string | null
  sender: string
  recipients: string[]
  subject: string
  received_at: string
  labels: string[]
  markdown_body: string
  created_at: string
}

export interface EmailAnalysis {
  id: string
  email_id: string
  category: string
  urgency: string
  sentiment: string
  summary: string
  action_items: ActionItem[]
  created_at: string
}

export interface ActionItem {
  description: string
  priority: string
  due_date: string | null
}

// ─── Topic Types ───

export interface Topic {
  id: string
  name: string
  email_count: number
  snapshots: TopicSnapshot[]
  created_at: string
  updated_at: string
}

export interface TopicSnapshot {
  timestamp: string
  summary: string
  email_count: number
}

// ─── Summary Types ───

export interface Summary {
  id: string
  summary_type: 'morning' | 'evening'
  date: string
  markdown_body: string
  diff_hash: string
  created_at: string
}

// ─── Task Types ───

export type TaskStatus = 'pending' | 'in_progress' | 'done' | 'cancelled'
export type TaskPriority = 'none' | 'low' | 'medium' | 'high'

export interface Task {
  id: string
  title: string
  notes: string | null
  status: TaskStatus
  priority: TaskPriority
  due_date: string | null
  completed_at: string | null
  position: number
  list_id: string | null
  parent_task_id: string | null
  source_email_id: string | null
  subtasks: Task[]
  created_at: string
  updated_at: string
}

export interface TaskList {
  id: string
  name: string
  position: number
  created_at: string
  updated_at: string
}

export interface CreateTaskPayload {
  title: string
  notes?: string
  status?: TaskStatus
  priority?: TaskPriority
  due_date?: string | null
  list_id?: string | null
  parent_task_id?: string | null
}

export interface UpdateTaskPayload {
  title?: string
  notes?: string
  status?: TaskStatus
  priority?: TaskPriority
  due_date?: string | null
  position?: number
  list_id?: string | null
}

export interface CreateTaskListPayload {
  name: string
}

export interface UpdateTaskListPayload {
  name?: string
  position?: number
}

// ─── Calendar Types ───

export interface CalendarEvent {
  id: string
  provider: 'google' | 'outlook'
  external_id: string
  calendar_id: string
  title: string
  description: string | null
  start_at: string
  end_at: string
  all_day: boolean
  location: string | null
  status: 'confirmed' | 'tentative' | 'cancelled'
  organizer: string | null
  attendees: CalendarAttendee[]
  created_at: string
  updated_at: string
}

export interface CalendarAttendee {
  email: string
  name: string | null
  status: string
}

export interface CalendarSource {
  id: string
  provider: 'google' | 'outlook'
  account: string
  calendar_name: string
  color: string
  enabled: boolean
}

// ─── Chat Types ───

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  context?: ChatContext
}

export interface ChatContext {
  scope: 'global' | 'project' | 'topic' | 'email'
  scope_id?: string
  scope_name?: string
}

// ─── Theme Types ───

export type ThemeMode = 'light' | 'dark' | 'system'

export interface ThemeColors {
  primary: string
  primaryHover: string
  accent: string
  accentHover: string
  bgPrimary: string
  bgSecondary: string
  bgTertiary: string
  bgSidebar: string
  textPrimary: string
  textSecondary: string
  textMuted: string
  border: string
  borderHover: string
  success: string
  warning: string
  error: string
  info: string
}

export interface ThemePreset {
  name: string
  label: string
  colors: {
    light: ThemeColors
    dark: ThemeColors
  }
}

// ─── API Types ───

export interface ApiError {
  detail: string
}

export interface PaginationParams {
  limit?: number
  offset?: number
}

// ─── Ingestion Types ───

export interface AuthUrlResponse {
  url: string
}

export interface SyncResponse {
  synced: number
  provider: string
}

export interface FetchResponse {
  fetched: number
  provider: string
  next_page_token: string | null
}
