// 群组活动列表页：带分类筛选（聚餐/游玩/约会/其他），数据来自当前群组
import { get } from '../../../utils/request'
import { resolveCoverSrc } from '../../../utils/cover'

interface EventItem {
  id: number
  title: string
  event_time: string
  status: string
  current_members: number
  max_members: number
  restaurant: { id: number; name: string } | null
  cover_url?: string
  budget?: number | null
  time_display?: string
  status_text?: string
  category?: string
  cover_src?: string
  budget_text?: string
}

const TABS = ['推荐', '聚餐', '游玩', '约会', '其他']

// 分类关键词（后端暂无 category 字段，按标题归类）
const PLAY_KEYWORDS = ['电影', '展览', '密室', '桌游', '户外', 'KTV', '游乐', '剧本', '爬山', '徒步', '游泳', '运动', '游玩']
const DATE_KEYWORDS = ['约会', '咖啡', '下午茶', '看展', '双人']

function categoryOf(title: string): string {
  const t = title || ''
  if (PLAY_KEYWORDS.some((kw) => t.includes(kw))) return '游玩'
  if (DATE_KEYWORDS.some((kw) => t.includes(kw))) return '约会'
  if (['火锅', '聚餐', '吃饭', '烧烤', '海鲜', '日料', '川菜', '西餐', '甜品', '宵夜', '早茶', '烤肉', '烤肉', '自助餐'].some((kw) => t.includes(kw))) return '聚餐'
  return '其他'
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

function formatTime(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  if (isToday) return `今天 ${h}:${min}`
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${m}-${day} ${h}:${min}`
}

function safeDecode(value: string): string {
  if (!value) return ''
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

Page({
  data: {
    tabs: TABS,
    tabIndex: 0,
    events: [] as EventItem[],
    loading: false,
    groupName: '',
    groupId: 0
  },

  onLoad(options: Record<string, string>) {
    const groupId = Number(options.group_id || 0)
    const groupName = safeDecode(options.group_name)
    // 支持从首页快捷入口携带 category 参数定位初始 tab
    let tabIndex = 0
    if (options.category) {
      const idx = TABS.indexOf(safeDecode(options.category))
      if (idx > 0) tabIndex = idx
    }
    this.setData({ groupId, groupName, tabIndex })
  },

  onShow() {
    if (this.data.groupId) {
      this.fetchEvents()
    }
  },

  onTabChange(e: WechatMiniprogram.TouchEvent) {
    const index = Number(e.currentTarget.dataset.index)
    this.setData({ tabIndex: index })
    this.applyFilter()
  },

  async fetchEvents() {
    const { groupId } = this.data
    if (!groupId) return
    this.setData({ loading: true })
    try {
      const events = await get<EventItem[]>(`/groups/${groupId}/events`)
      const all = events.map((e) => ({
        ...e,
        time_display: formatTime(e.event_time),
        status_text: statusTextOf(e.status),
        category: categoryOf(e.title),
        cover_src: resolveCoverSrc(e.cover_url),
        budget_text: e.budget != null ? `¥${e.budget}/人` : '',
      }))
      this.allEvents = all
      this.applyFilter()
    } catch {
      wx.showToast({ title: '加载失败', icon: 'none' })
      this.setData({ events: [] })
    } finally {
      this.setData({ loading: false })
    }
  },

  allEvents: [] as EventItem[],

  applyFilter() {
    const tab = TABS[this.data.tabIndex]
    const events = tab === '推荐'
      ? this.allEvents
      : this.allEvents.filter((e) => e.category === tab)
    this.setData({ events })
  },

  goDetail(e: WechatMiniprogram.TouchEvent) {
    const { id } = e.currentTarget.dataset
    wx.navigateTo({ url: `/pages/event/detail/index?id=${id}` })
  },

  joinEvent(e: WechatMiniprogram.TouchEvent) {
    const { id } = e.currentTarget.dataset
    wx.navigateTo({ url: `/pages/event/detail/index?id=${id}&action=join` })
  }
})
