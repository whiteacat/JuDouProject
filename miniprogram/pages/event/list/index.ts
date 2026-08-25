// 我的组队列表页：我创建或加入的所有组队
import { get } from '../../../utils/request'

interface MyEvent {
  id: number
  title: string
  event_time: string
  status: string
  current_members: number
  max_members: number
  restaurant: { id: number; name: string } | null
  time_display?: string
  status_text?: string
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
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${m}-${day} ${h}:${min}`
}

Page({
  data: {
    events: [] as MyEvent[],
    loading: false
  },

  onShow() {
    this.fetchEvents()
  },

  async fetchEvents() {
    this.setData({ loading: true })
    try {
      const events = await get<MyEvent[]>('/events/mine')
      this.setData({
        events: events.map((e) => ({
          ...e,
          time_display: formatTime(e.event_time),
          status_text: statusTextOf(e.status)
        }))
      })
    } catch (err) {
      console.error('加载我的组队失败', err)
      wx.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  goDetail(e: WechatMiniprogram.TouchEvent) {
    const { id } = e.currentTarget.dataset
    wx.navigateTo({ url: `/pages/event/detail/index?id=${id}` })
  }
})
