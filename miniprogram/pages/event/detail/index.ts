// 组队详情页：信息、餐厅、成员、操作栏
import { get, post } from '../../../utils/request'

interface RestaurantBrief {
  id: number
  name: string
  longitude: number
  latitude: number
}

interface EventDetail {
  id: number
  group_id: number
  creator_id: number
  title: string
  event_time: string
  time_display?: string
  status: string
  min_members: number
  max_members: number
  current_members: number
  remark: string | null
  latitude: number | null
  longitude: number | null
  restaurant: RestaurantBrief | null
  expiry_mode: string
  expires_at: string | null
  expiry_display?: string
}

interface EventMember {
  user_id: number
  joined_at: string
  nickname: string
  avatar_url: string
  time_windows: { date: string; start: string; end: string }[]
  short?: string
}

const STATUS_TEXT: Record<string, string> = {
  RECRUITING: '招募中',
  CONFIRMED: '已确认',
  COMPLETED: '已完成',
  CANCELLED: '已取消',
  EXPIRED: '已失效'
}

function statusTextOf(status: string): string {
  return STATUS_TEXT[status] || status
}

/** 失效策略的展示文案。 */
function expiryDisplayOf(event: EventDetail): string {
  if (event.status === 'EXPIRED') {
    return event.expires_at ? `已于 ${formatTime(event.expires_at)} 失效` : '已失效'
  }
  if (event.expiry_mode === 'at_complete') return '完成聚餐后失效'
  if (event.expiry_mode === 'at_time' || event.expiry_mode === 'after_hours') {
    return event.expires_at ? `${formatTime(event.expires_at)} 失效` : '限时有效'
  }
  return '长期有效'
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${m}-${day} ${h}:${min}`
}

function pad(n: number): string {
  return String(n).padStart(2, '0')
}

function timeOnly(iso: string): string {
  const d = new Date(iso)
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function dayOf(iso: string): string {
  const d = new Date(iso)
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/** 完整 YYYY-MM-DD（picker mode=date 与后端 ISO 日期均需要年份）。 */
function fullDateOf(iso: string): string {
  const d = new Date(iso)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/** 由「HH:mm 基准 + 偏移小时」算出 HH:mm（默认窗口：聚餐前 1 小时 ~ 后 2 小时）。 */
function shiftTime(base: string, offsetHours: number): string {
  if (!base) return '00:00'
  const [h, m] = base.split(':').map(Number)
  const total = ((h * 60 + (m || 0) + offsetHours * 60) + 24 * 60) % (24 * 60)
  return `${pad(Math.floor(total / 60))}:${pad(total % 60)}`
}

interface GanttBlock {
  /** 可直接使用的 CSS 值（calc(...) 或 Nrpx） */
  left: string
  width: string
  text: string
  /** 压缩列/日期列上的小块：不显示时间文字 */
  tiny?: boolean
  /** 共同行块：无「全员共同」时段时退化为「人数最多」时段 */
  best?: boolean
}

interface GanttRow {
  label: string
  mine: boolean
  has_window: boolean
  blocks: GanttBlock[]
}

interface GanttCol {
  label: string
  kind: 'day' | 'gap'
  /** 聚餐日（高亮） */
  is_event?: boolean
  /** 日期粒度模式：该日有 ≥2 人重叠 */
  green?: boolean
}

interface Gantt {
  /** time = 天内时间轴（跨度≤7天）；day = 日期粒度（>7天，按天标绿） */
  mode: 'time' | 'day'
  /** grid-template-columns 值 */
  grid: string
  /** 内容最小宽度（rpx） */
  min_width: number
  /** 轨道宽度（rpx，不含名字列），所有行/表头轨道统一用它保证对齐 */
  track_width: number
  columns: GanttCol[]
  rows: GanttRow[]
  /** 顶部「共同」行块 */
  common: GanttBlock[]
  /** 聚餐参考线 left（CSS 值）；null 表示不显示 */
  event_left: string | null
  event_label: string
  /** 模式说明文案 */
  hint: string
}

interface OverlapSegment {
  date: string
  dateLabel: string
  start: string
  end: string
  count: number
  all: boolean
  missing: string[]
  missingText: string
}

interface OverlapDay {
  date: string
  /** 当日最大同时在空人数 */
  count: number
}

interface OverlapSummary {
  /** 已设置时段的成员数（重叠计算基准） */
  involved: number
  /** 未设置时段的成员数（不参与计算） */
  unset: number
  /** 全员都有空的时段；为空时展示 best */
  all: OverlapSegment[]
  /** 人数最多的时段（仅当无 all 段时返回） */
  best: OverlapSegment[]
  /** 有 ≥2 人重叠的日期（驱动甘特图展开/标绿） */
  days: OverlapDay[]
}

function parseDate(dateStr: string): Date {
  // YYYY-MM-DD -> 本地 Date（避免 new Date(iso) 按 UTC 解析的时区坑）
  const [y, m, d] = dateStr.split('-').map(Number)
  return new Date(y, m - 1, d)
}

function addDays(date: Date, days: number): Date {
  const d = new Date(date)
  d.setDate(d.getDate() + days)
  return d
}

function dateKey(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

/** date-only 字符串（YYYY-MM-DD）取 MM-DD 展示标签（避免 new Date 的 UTC 解析时区坑）。 */
function dateLabel(dateStr: string): string {
  const [, m, d] = dateStr.split('-')
  return `${m}-${d}`
}

/** 成员时段文字摘要：「8-24 18:00~21:00、8-25 12:00~14:00」；未设置显示「未设置」。 */
function windowTextOf(m: EventMember): string {
  if (!m.time_windows || m.time_windows.length === 0) return '未设置'
  const sorted = [...m.time_windows].sort((a, b) =>
    (a.date + a.start).localeCompare(b.date + b.start)
  )
  return sorted.map((w) => `${dateLabel(w.date)} ${w.start}~${w.end}`).join('、')
}

function minutesOf(hhmm: string): number {
  const [h, m] = hhmm.split(':').map(Number)
  return h * 60 + (m || 0)
}

const DAY_MS = 24 * 60 * 60 * 1000
/** 时间轴甘特图最大跨度（天），超过则切换为日期粒度展示 */
const MAX_GANTT_DAYS = 7

const LABEL_W = 120 // 名字列宽（rpx）
const DAY_W = 110 // 展开的日期列宽（天内时间轴，rpx）
const GAP_W = 36 // 折叠（无重叠）日期列宽（rpx）
const DAYMODE_W = 72 // 日期粒度模式的列宽（rpx）

/**
 * 非均匀甘特图：
 * - 跨度 ≤7 天：有重叠（≥2 人同天有空）或聚餐日的日期展开为全天列、列内按分钟定位时段；
 *   其余日期折叠成「…」窄列（当天有人设时段则显示一个点）。
 * - 跨度 >7 天：日期粒度，每天一列，绿色 = 当天有 ≥2 人重叠，蓝线 = 聚餐日。
 * 无任何时段返回 null。
 */
function buildGantt(event: EventDetail, members: EventMember[], userId: number, overlap: OverlapSummary | null): Gantt | null {
  const windows = members
    .filter((m) => m.time_windows && m.time_windows.length > 0)
    .map((m) => m.time_windows)
    .reduce((all, ws) => all.concat(ws), [] as { date: string; start: string; end: string }[])
  if (windows.length === 0) return null

  const eventDateKey = fullDateOf(event.event_time)
  let minDate = parseDate(eventDateKey)
  let maxDate = minDate
  for (const w of windows) {
    const t = parseDate(w.date)
    if (t < minDate) minDate = t
    if (t > maxDate) maxDate = t
  }
  const spanDays = Math.round((maxDate.getTime() - minDate.getTime()) / DAY_MS) + 1
  const isDayMode = spanDays > MAX_GANTT_DAYS

  const overlapDays = new Set((overlap ? overlap.days : []).map((d) => d.date))
  const dayKeys: string[] = []
  for (let i = 0; i < spanDays; i++) dayKeys.push(dateKey(addDays(minDate, i)))

  const columns: GanttCol[] = dayKeys.map((k) => {
    const isEvent = k === eventDateKey
    const expanded = !isDayMode && (overlapDays.has(k) || isEvent)
    return {
      label: expanded ? dateLabel(k) : isDayMode ? dateLabel(k) : '…',
      kind: expanded ? 'day' : 'gap',
      is_event: isEvent,
      green: isDayMode && overlapDays.has(k)
    }
  })

  const colW = (c: GanttCol): number =>
    c.kind === 'day' ? DAY_W : isDayMode ? DAYMODE_W : GAP_W
  const grid = `${LABEL_W}rpx ${columns.map((c) => `${colW(c)}rpx`).join(' ')}`
  const track_width = columns.reduce((s, c) => s + colW(c), 0)
  const min_width = LABEL_W + track_width

  // 每列起点 x（rpx，不含名字列）
  const colLeft: number[] = []
  {
    let x = 0
    for (const c of columns) {
      colLeft.push(x)
      x += colW(c)
    }
  }
  const keyIndex = new Map(dayKeys.map((k, i) => [k, i]))

  /** 生成某日期列内的块：展开日按分钟定位，折叠日/日期粒度列给一个整列小点 */
  const barIn = (
    k: string,
    startHHMM: string | null,
    endHHMM: string | null,
    text: string,
    best?: boolean
  ): GanttBlock => {
    const i = keyIndex.get(k) as number
    const col = columns[i]
    const w = colW(col)
    if (col.kind === 'day') {
      const s = minutesOf(startHHMM as string) / (24 * 60)
      const e = Math.max(minutesOf(endHHMM as string) / (24 * 60), s)
      return {
        left: `${LABEL_W + colLeft[i] + Math.round(w * s)}rpx`,
        width: `${Math.max(Math.round(w * (e - s)), 10)}rpx`,
        text,
        best
      }
    }
    return {
      left: `${LABEL_W + colLeft[i] + Math.round(w * 0.08)}rpx`,
      width: `${Math.round(w * 0.84)}rpx`,
      text,
      tiny: true,
      best
    }
  }

  const rows: GanttRow[] = members.map((m) => {
    const blocks: GanttBlock[] = []
    for (const w of m.time_windows || []) {
      if (!keyIndex.has(w.date)) continue
      blocks.push(barIn(w.date, w.start, w.end, `${w.start}~${w.end}`))
    }
    return {
      label: m.nickname || '成员',
      mine: m.user_id === userId,
      has_window: blocks.length > 0,
      blocks
    }
  })

  // 顶部「共同」行：时间轴模式放重叠时段；日期粒度模式按重叠日给绿块（标人数）
  const common: GanttBlock[] = []
  if (overlap) {
    if (isDayMode) {
      for (const d of overlap.days) {
        if (!keyIndex.has(d.date)) continue
        const all = d.count === overlap.involved
        common.push(barIn(d.date, null, null, all ? '全员' : `${d.count}人`, !all))
      }
    } else {
      const segs = overlap.all.length > 0 ? overlap.all : overlap.best
      const isAll = overlap.all.length > 0
      for (const seg of segs) {
        if (!keyIndex.has(seg.date)) continue
        common.push(
          barIn(seg.date, seg.start, seg.end, isAll ? `${seg.start}~${seg.end}` : `${seg.count}人`, !isAll)
        )
      }
    }
  }

  // 聚餐参考线：展开日落在当日分钟位置，其余列落在列中央
  let event_left: string | null = null
  const evIdx = keyIndex.get(eventDateKey)
  if (evIdx !== undefined) {
    const col = columns[evIdx]
    const w = colW(col)
    const x = col.kind === 'day'
      ? colLeft[evIdx] + Math.round((w * minutesOf(timeOnly(event.event_time))) / (24 * 60))
      : colLeft[evIdx] + Math.round(w / 2)
    event_left = `${LABEL_W + x}rpx`
  }

  const collapsed = columns.filter((c) => c.kind === 'gap').length
  const hint = isDayMode
    ? `跨度 ${spanDays} 天，仅按日期显示重叠（绿 = 当天 ≥2 人同时有空，蓝线 = 聚餐日）；具体时刻见上方文字`
    : collapsed > 0
      ? `无重叠的 ${collapsed} 天已折叠为「…」窄列；具体时刻见上方文字`
      : ''

  return {
    mode: isDayMode ? 'day' : 'time',
    grid,
    min_width,
    track_width,
    columns,
    rows,
    common,
    event_left,
    event_label: formatTime(event.event_time),
    hint
  }
}

function minutesToHHMM(mins: number): string {
  return `${pad(Math.floor(mins / 60))}:${pad(mins % 60)}`
}

/** 合并同一天内重叠/相邻的区间（分钟），返回按开始排序的不重叠区间。 */
function mergeIntervals(intervals: [number, number][]): [number, number][] {
  if (intervals.length === 0) return []
  const sorted = [...intervals].sort((a, b) => a[0] - b[0] || a[1] - b[1])
  const merged: [number, number][] = [sorted[0]]
  for (let i = 1; i < sorted.length; i++) {
    const last = merged[merged.length - 1]
    if (sorted[i][0] <= last[1]) last[1] = Math.max(last[1], sorted[i][1])
    else merged.push([sorted[i][0], sorted[i][1]])
  }
  return merged
}

/**
 * 按天计算成员间重叠时段（基准：已设置时段的成员）：
 * all = 全员都有空的时段；无 all 段时 best = 人数最多的前 5 段（附缺少谁）。
 * 少于 2 人有时段返回 null。
 */
function buildOverlaps(members: EventMember[]): OverlapSummary | null {
  const active = members.filter((m) => m.time_windows && m.time_windows.length > 0)
  if (active.length < 2) return null
  const M = active.length
  const idx = new Map<number, number>()
  active.forEach((m, i) => idx.set(m.user_id, i))

  // date -> 每个成员的当天区间列表（分钟）
  const byDate = new Map<string, [number, number][][]>()
  for (const m of active) {
    const mi = idx.get(m.user_id) as number
    for (const w of m.time_windows) {
      const s = minutesOf(w.start)
      const e = Math.max(minutesOf(w.end), s)
      let list = byDate.get(w.date)
      if (!list) {
        list = active.map(() => [] as [number, number][])
        byDate.set(w.date, list)
      }
      list[mi].push([s, e])
    }
  }

  const all: OverlapSegment[] = []
  const partial: OverlapSegment[] = []
  const dayMax = new Map<string, number>()
  for (const [date, lists] of byDate) {
    const merged = lists.map((ivs) => mergeIntervals(ivs))
    // 扫描线：区间端点之外覆盖状态不变，只需枚举端点区间
    const pts = new Set<number>([0, 24 * 60])
    for (const ivs of merged) {
      for (const iv of ivs) {
        pts.add(iv[0])
        pts.add(iv[1])
      }
    }
    const xs = [...pts].sort((a, b) => a - b)
    for (let i = 0; i < xs.length - 1; i++) {
      const a = xs[i]
      const b = xs[i + 1]
      const present: number[] = []
      for (let mi = 0; mi < M; mi++) {
        if (merged[mi].some(([s, e]) => s <= a && e >= b)) present.push(mi)
      }
      if (present.length < 2) continue
      const missingNames = active
        .filter((_, mi) => !present.includes(mi))
        .map((m) => m.nickname || '成员')
      const seg: OverlapSegment = {
        date,
        dateLabel: dateLabel(date),
        start: minutesToHHMM(a),
        end: minutesToHHMM(b),
        count: present.length,
        all: present.length === M,
        missing: missingNames,
        missingText: missingNames.join('、')
      }
      if (seg.all) all.push(seg)
      else partial.push(seg)
      const prev = dayMax.get(date) || 0
      if (present.length > prev) dayMax.set(date, present.length)
    }
  }

  all.sort((a, b) => (a.date + a.start).localeCompare(b.date + b.start))
  // 无「全员」时段时：取人数最多的前 5 段（按时间展示）
  let best: OverlapSegment[] = []
  if (all.length === 0 && partial.length > 0) {
    const maxCount = Math.max(...partial.map((s) => s.count))
    best = partial
      .filter((s) => s.count === maxCount)
      .sort((a, b) => (a.date + a.start).localeCompare(b.date + b.start))
      .slice(0, 5)
  }
  const days: OverlapDay[] = [...dayMax.entries()]
    .map(([date, count]) => ({ date, count }))
    .sort((a, b) => a.date.localeCompare(b.date))
  return { involved: M, unset: members.length - M, all, best, days }
}

Page({
  data: {
    eventId: 0,
    event: null as EventDetail | null,
    members: [] as EventMember[],
    userId: 0,
    joined: false,
    isCreator: false,
    reviewed: false,
    statusText: '',
    gantt: null as Gantt | null,
    // 共同重叠时段（null = 少于 2 人设置时段，不展示重叠区）
    overlap: null as OverlapSummary | null,
    // 甘特图默认折叠（文字摘要紧凑，时间轴按需展开）
    ganttOpen: false,
    // 成员时段文字摘要（与 gantt 同源，折叠时展示）
    windowTexts: [] as { label: string; mine: boolean; text: string }[],
    // 我的可参加时段编辑（未加入时随 join 提交；已加入时通过 my-windows 保存）
    myWindows: [] as { date: string; start: string; end: string }[],
    windowSaving: false
  },

  _redirecting: false,

  onLoad(options: Record<string, string>) {
    const eventId = Number(options.id || 0)
    if (!eventId) {
      wx.showToast({ title: '缺少组队参数', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 800)
      return
    }
    this.setData({ eventId })
    this.load()
  },

  onShow() {
    // 分享落地登录返回、评价返回等场景都需要重新加载（含已评价状态刷新）
    if (this.data.eventId) {
      this.load()
    }
  },

  async load() {
    const { eventId } = this.data
    try {
      const [event, members] = await Promise.all([
        get<EventDetail>(`/events/${eventId}`),
        get<EventMember[]>(`/events/${eventId}/members`)
      ])
      const info = wx.getStorageSync('userInfo') as { id?: number } | null
      const userId = info && info.id ? info.id : 0
      const joined = members.some((m) => m.user_id === userId)
      this._redirecting = false

      // 已完成且有餐厅且已加入：查询是否已评价
      let reviewed = false
      if (event.status === 'COMPLETED' && event.restaurant && joined) {
        try {
          const reviews = await get<{ user_id: number }[]>(
            `/groups/${event.group_id}/restaurants/${event.restaurant.id}/reviews`
          )
          reviewed = reviews.some((r) => r.user_id === userId)
        } catch (e) {
          console.error('查询评价状态失败', e)
        }
      }

      const me = members.find((m) => m.user_id === userId)
      // 我的时段编辑值：已设置则回填，否则默认聚餐日「前 1 小时 ~ 后 2 小时」一段
      const baseTime = timeOnly(event.event_time)
      const myWindows = me && me.time_windows && me.time_windows.length > 0
        ? me.time_windows.map((w) => ({ ...w }))
        : [{
            date: fullDateOf(event.event_time),
            start: shiftTime(baseTime, -1),
            end: shiftTime(baseTime, 2)
          }]
      const full = { ...event, time_display: formatTime(event.event_time) }
      const overlap = buildOverlaps(members)
      this.setData({
        event: { ...full, expiry_display: expiryDisplayOf(full) },
        members: members.map((m) => ({ ...m, short: m.nickname ? m.nickname[0] : '?' })),
        userId,
        joined,
        isCreator: event.creator_id === userId,
        reviewed,
        statusText: statusTextOf(event.status),
        overlap,
        gantt: buildGantt(full, members, userId, overlap),
        windowTexts: members.map((m) => ({
          label: m.user_id === userId ? '我' : m.nickname || '成员',
          mine: m.user_id === userId,
          text: windowTextOf(m)
        })),
        myWindows
      })
    } catch (err) {
      console.error('加载组队失败', err)
      const statusCode = (err as { statusCode?: number })?.statusCode
      if (statusCode === 401) {
        if (!this._redirecting) {
          this._redirecting = true
          wx.showToast({ title: '请先登录', icon: 'none' })
          wx.navigateTo({ url: '/pages/login/index' })
        }
        return
      }
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  goReview() {
    const { eventId } = this.data
    wx.navigateTo({ url: `/pages/event/review/index?id=${eventId}` })
  },

  onToggleGantt() {
    this.setData({ ganttOpen: !this.data.ganttOpen })
  },

  onAddMyWindow() {
    const { myWindows, event } = this.data
    if (myWindows.length >= 30) {
      wx.showToast({ title: '最多添加 30 个时段', icon: 'none' })
      return
    }
    if (!event) return
    const last = myWindows[myWindows.length - 1]
    const newWindow = {
      date: (last && last.date) || fullDateOf(event.event_time),
      start: last ? shiftTime(last.start, 2) : shiftTime(timeOnly(event.event_time), -1),
      end: last ? shiftTime(last.end, 2) : shiftTime(timeOnly(event.event_time), 2)
    }
    this.setData({ myWindows: [...myWindows, newWindow] })
  },

  onRemoveMyWindow(e: WechatMiniprogram.TouchEvent) {
    const index = Number(e.currentTarget.dataset.index)
    this.setData({ myWindows: this.data.myWindows.filter((_, i) => i !== index) })
  },

  onMyWindowDateChange(e: WechatMiniprogram.PickerChange) {
    const index = Number(e.currentTarget.dataset.index)
    this.setData({ [`myWindows[${index}].date`]: String(e.detail.value) })
  },

  onMyWindowStartChange(e: WechatMiniprogram.PickerChange) {
    const index = Number(e.currentTarget.dataset.index)
    this.setData({ [`myWindows[${index}].start`]: String(e.detail.value) })
  },

  onMyWindowEndChange(e: WechatMiniprogram.PickerChange) {
    const index = Number(e.currentTarget.dataset.index)
    this.setData({ [`myWindows[${index}].end`]: String(e.detail.value) })
  },

  /** 提交前校验：每段 end>start、同一天不重叠。通过返回数组，否则 toast 并返回 null。 */
  validateMyWindows(): { date: string; start: string; end: string }[] | null {
    const { myWindows } = this.data
    for (const w of myWindows) {
      if (!w.date || !w.start || !w.end) {
        wx.showToast({ title: '时段未填完整', icon: 'none' })
        return null
      }
      if (w.start >= w.end) {
        wx.showToast({ title: `${w.date} 时段结束需晚于开始`, icon: 'none' })
        return null
      }
    }
    const byDate = new Map<string, [number, number][]>()
    for (const w of myWindows) {
      const s = Number(w.start.replace(':', ''))
      const e = Number(w.end.replace(':', ''))
      const segs = byDate.get(w.date) || []
      segs.push([s, e])
      byDate.set(w.date, segs)
    }
    for (const [date, segs] of byDate) {
      segs.sort((a, b) => a[0] - b[0])
      for (let i = 1; i < segs.length; i++) {
        if (segs[i][0] < segs[i - 1][1]) {
          wx.showToast({ title: `${date} 时段有重叠`, icon: 'none' })
          return null
        }
      }
    }
    return [...myWindows].sort((a, b) => (a.date + a.start).localeCompare(b.date + b.start))
  },

  /** 未加入者提交可参加时段（随 join 一起发送） */
  async onJoin() {
    const { eventId } = this.data
    const timeWindows = this.validateMyWindows()
    if (!timeWindows) return
    try {
      await post(`/events/${eventId}/join`, { time_windows: timeWindows })
      wx.showToast({ title: '加入成功' })
      this.load()
    } catch (err) {
      console.error('加入失败', err)
      wx.showToast({ title: '加入失败，可能已满员', icon: 'none' })
    }
  },

  /** 已加入者保存/调整自己的可参加时段 */
  async onSaveMyWindows() {
    const { eventId } = this.data
    const timeWindows = this.validateMyWindows()
    if (!timeWindows) return
    this.setData({ windowSaving: true })
    try {
      await post(`/events/${eventId}/my-windows`, { time_windows: timeWindows })
      wx.showToast({ title: '已保存' })
      this.load()
    } catch (err) {
      console.error('保存可参加时段失败', err)
      wx.showToast({ title: '保存失败', icon: 'none' })
    } finally {
      this.setData({ windowSaving: false })
    }
  },

  onShareAppMessage() {
    const ev = this.data.event
    return {
      title: ev ? `「${ev.title}」组队中，快来加入` : '聚豆·组队聚餐',
      path: ev ? `/pages/event/detail/index?id=${ev.id}` : '/pages/index/index'
    }
  },

  async onLeave() {
    const { eventId } = this.data
    try {
      await post(`/events/${eventId}/leave`)
      wx.showToast({ title: '已退出' })
      this.load()
    } catch (err) {
      console.error('退出失败', err)
      wx.showToast({ title: '退出失败', icon: 'none' })
    }
  },

  async onComplete() {
    const { eventId } = this.data
    try {
      await post(`/events/${eventId}/complete`)
      wx.showToast({ title: '聚餐完成' })
      this.load()
    } catch (err) {
      console.error('完成失败', err)
      wx.showToast({ title: '操作失败', icon: 'none' })
    }
  },

  async onCancel() {
    const { eventId } = this.data
    try {
      await post(`/events/${eventId}/cancel`)
      wx.showToast({ title: '已取消' })
      this.load()
    } catch (err) {
      console.error('取消失败', err)
      wx.showToast({ title: '操作失败', icon: 'none' })
    }
  }
})
