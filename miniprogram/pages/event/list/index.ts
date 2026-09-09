// 附近活动列表页：带分类筛选的活动列表
import { get } from '../../../utils/request'
import { resolveAvatarSrc } from '../../../utils/avatar'

interface EventItem {
  id: number
  title: string
  event_time: string
  status: string
  current_members: number
  max_members: number
  restaurant: { id: number; name: string } | null
  category?: string
  budget?: string
  distance?: string
  cover_url?: string
  creator?: { nickname: string; avatar_url: string }
  time_display?: string
  status_text?: string
  creator_avatar_src?: string
}

const TABS = ['推荐', '聚餐', '游玩', '约会', '其他']

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

Page({
  data: {
    tabs: TABS,
    tabIndex: 0,
    events: [] as EventItem[],
    loading: false,
    locationText: ''
  },

  onShow() {
    this.fetchEvents()
  },

  onTabChange(e: WechatMiniprogram.TouchEvent) {
    const index = Number(e.currentTarget.dataset.index)
    this.setData({ tabIndex: index })
    this.fetchEvents()
  },

  async fetchEvents() {
    this.setData({ loading: true })
    try {
      const tab = TABS[this.data.tabIndex]
      const params: Record<string, string> = {}
      if (tab !== '推荐') params.category = tab
      const events = await get<EventItem[]>('/events/nearby', params)
      this.setData({
        events: events.map((e) => ({
          ...e,
          time_display: formatTime(e.event_time),
          status_text: statusTextOf(e.status),
          creator_avatar_src: resolveAvatarSrc(e.creator?.avatar_url || ''),
        }))
      })
    } catch {
      wx.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
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
