'use client'

import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { LEVELS, SUBJECTS } from '@/lib/format'
import type { Level, TutorFiltersValue } from '@/types'

const ANY = 'any'

/** Subject, level and area filters, plus sort order. */
export default function TutorFilters({ value, onChange }: { value: TutorFiltersValue; onChange: (value: TutorFiltersValue) => void }) {
  return (
    <div className="grid gap-3 rounded-lg border bg-card p-4 sm:grid-cols-2 lg:grid-cols-4">
      <div className="space-y-1.5">
        <Label htmlFor="filter-subject">Subject</Label>
        <Select value={value.subject ?? ANY} onValueChange={(v) => onChange({ ...value, subject: v === ANY ? undefined : v })}>
          <SelectTrigger id="filter-subject"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value={ANY}>All subjects</SelectItem>
            {SUBJECTS.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="filter-level">Level</Label>
        <Select value={value.level ?? ANY} onValueChange={(v) => onChange({ ...value, level: v === ANY ? undefined : (v as Level) })}>
          <SelectTrigger id="filter-level"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value={ANY}>All levels</SelectItem>
            {LEVELS.map((l) => <SelectItem key={l.value} value={l.value}>{l.label}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="filter-area">Area</Label>
        <Input
          id="filter-area"
          placeholder="e.g. Lekki"
          value={value.area ?? ''}
          onChange={(e) => onChange({ ...value, area: e.target.value })}
        />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="filter-sort">Sort by</Label>
        <Select value={value.sort ?? 'name'} onValueChange={(v) => onChange({ ...value, sort: v as TutorFiltersValue['sort'] })}>
          <SelectTrigger id="filter-sort"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="name">Name</SelectItem>
            <SelectItem value="rating">Top rated</SelectItem>
            <SelectItem value="price">Lowest price</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  )
}
