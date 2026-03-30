export interface Space {
  space_id: string
  name: string
  description: string
  furnitureCount?: number
}

export interface Furniture {
  furniture_id: string
  space_id: string
  name: string
  type: string
  pos_x: number
  pos_y: number
  width: number
  height: number
  color?: string
  notes?: string
  itemCount?: number
  items?: Item[]
}

export interface Item {
  item_id: string
  name: string
  furniture_id: string
  zone_id?: string
  category: string
  tags?: string[]
  memo: string
  photo_url?: string
  quantity: number
  context?: string
  created_at?: string
  updated_at?: string
  // Joined fields from search
  matchScore?: number
  furniture?: string
  space?: string
  path?: string
}

export interface Zone {
  zone_id: string
  furniture_id: string
  name: string
  position_desc?: string
}

export interface HistoryEntry {
  history_id: string
  item_id: string
  from_furniture: string
  from_zone?: string
  to_furniture: string
  to_zone?: string
  moved_at: string
  note?: string
}

export interface QualityMetrics {
  requiredFieldsCompleteness: number
  furnitureAssignmentRate: number
  nameDuplicateRate: number
  dataFreshnessRate: number
  totalItems: number
  totalFurniture: number
}
