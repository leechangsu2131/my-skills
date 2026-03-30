import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import type { Space, Furniture, Item, QualityMetrics } from '../types'

const API = ''

async function fetchJSON<T>(url: string): Promise<T> {
  const res = await fetch(`${API}${url}`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.error || res.statusText)
  }
  return res.json()
}

async function postJSON<T>(url: string, body: Record<string, unknown>): Promise<T> {
  const res = await fetch(`${API}${url}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.error || res.statusText)
  }
  return res.json()
}

async function putJSON<T>(url: string, body: Record<string, unknown>): Promise<T> {
  const res = await fetch(`${API}${url}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.error || res.statusText)
  }
  return res.json()
}

async function deleteJSON<T>(url: string): Promise<T> {
  const res = await fetch(`${API}${url}`, { method: 'DELETE' })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.error || res.statusText)
  }
  return res.json()
}

// ─── Auth ───
export function useAuthStatus() {
  return useQuery({
    queryKey: ['auth-status'],
    queryFn: () => fetchJSON<{ authenticated: boolean }>('/api/auth/status'),
    staleTime: 60_000,
  })
}

// ─── Spaces ───
export function useSpaces() {
  return useQuery({
    queryKey: ['spaces'],
    queryFn: () => fetchJSON<Space[]>('/api/spaces'),
  })
}

export function useCreateSpace() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { name: string; description?: string }) =>
      postJSON('/api/spaces', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['spaces'] })
      toast.success('공간이 추가되었습니다')
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

// ─── Furniture ───
export function useFurnitureBySpace(spaceId: string | null) {
  return useQuery({
    queryKey: ['furniture', spaceId],
    queryFn: () => fetchJSON<Furniture[]>(`/api/spaces/${spaceId}/furniture`),
    enabled: !!spaceId,
  })
}

export function useCreateFurniture() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { name: string; space_id: string; type?: string; pos_x?: number; pos_y?: number; width?: number; height?: number; color?: string }) =>
      postJSON('/api/furniture', data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ['furniture', vars.space_id] })
      toast.success('가구가 추가되었습니다')
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useUpdateFurniturePosition() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ furnitureId, ...body }: { furnitureId: string; x?: number; y?: number; width?: number; height?: number }) =>
      putJSON(`/api/furniture/${furnitureId}/position`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['furniture'] })
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useDeleteFurniture() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (furnitureId: string) =>
      deleteJSON(`/api/furniture/${furnitureId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['furniture'] })
      toast.success('가구가 삭제되었습니다')
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

// ─── Items ───
export function useAllItems() {
  return useQuery({
    queryKey: ['all-data'],
    queryFn: async () => {
      const data = await fetchJSON<{
        spaces: Space[]
        furniture: Furniture[]
        items: Item[]
      }>('/api/data')
      return data
    },
  })
}

export function useSearch(query: string) {
  return useQuery({
    queryKey: ['search', query],
    queryFn: () => fetchJSON<{ query: string; results: Item[] }>(`/api/search?q=${encodeURIComponent(query)}`),
    enabled: query.length > 0,
  })
}

export function useCreateItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { name: string; furniture_id: string; category?: string; quantity?: number; memo?: string }) =>
      postJSON('/api/items', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['furniture'] })
      qc.invalidateQueries({ queryKey: ['all-data'] })
      toast.success('물건이 추가되었습니다')
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useUpdateItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ itemId, ...body }: { itemId: string; name?: string; furniture_id?: string; category?: string; quantity?: number; memo?: string }) =>
      putJSON(`/api/items/${itemId}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['furniture'] })
      qc.invalidateQueries({ queryKey: ['all-data'] })
      toast.success('물건이 수정되었습니다')
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useDeleteItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (itemId: string) =>
      deleteJSON(`/api/items/${itemId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['furniture'] })
      qc.invalidateQueries({ queryKey: ['all-data'] })
      toast.success('물건이 삭제되었습니다')
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

// ─── Data reload ───
export function useReloadData() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => fetchJSON('/api/data/reload'),
    onSuccess: () => {
      qc.invalidateQueries()
      toast.success('Google Sheets 데이터를 새로고침했습니다')
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

// ─── Quality Metrics (computed client-side) ───
export function useQualityMetrics() {
  const { data } = useAllItems()

  if (!data || !data.items?.length) return null

  const items = data.items
  const furniture = data.furniture

  const completeItems = items.filter((i: Item) => i.name && i.furniture_id)
  const requiredFieldsCompleteness = Math.round((completeItems.length / items.length) * 100)

  const assignedItems = items.filter((i: Item) => i.furniture_id)
  const furnitureAssignmentRate = Math.round((assignedItems.length / items.length) * 100)

  const nameCounts = new Map<string, number>()
  items.forEach((i: Item) => {
    nameCounts.set(i.name, (nameCounts.get(i.name) || 0) + 1)
  })
  const duplicateCount = Array.from(nameCounts.values()).filter(c => c > 1).reduce((a, b) => a + b, 0)
  const nameDuplicateRate = Math.round((duplicateCount / items.length) * 100)

  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
  const freshItems = items.filter((i: Item) => i.updated_at && new Date(i.updated_at) > thirtyDaysAgo)
  const dataFreshnessRate = items.some((i: Item) => i.updated_at)
    ? Math.round((freshItems.length / items.length) * 100)
    : 100

  return {
    requiredFieldsCompleteness,
    furnitureAssignmentRate,
    nameDuplicateRate,
    dataFreshnessRate,
    totalItems: items.length,
    totalFurniture: furniture.length,
  } as QualityMetrics
}
