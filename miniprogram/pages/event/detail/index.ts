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
}

interface EventMember {
  user_id: number
  joined_at: string
  nickname: string
  avatar_url: string
  short?: string
}

const STATUS_TEXT: Record<string, string> = {
  RECRUITING: '招募中',
  CONFIRMED: '已确认',
  COMPLETED: '已完成',
  CANCELLED: '已取消'
}

/** 招募中的组队若已过聚餐时间，标记为已过期。 */
function statusTextOf(status: string, eventTime: string): string {
  if (
    (status === 'RECRUITING' || status === 'CONFIRMED') &&
    new Date(eventTime).getTime() < Date.now()
  ) {
    return '已过期'
  }
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
    eventId: 0,
    event: null as EventDetail | null,
    members: [] as EventMember[],
    userId: 0,
    joined: false,
    isCreator: false,
    reviewed: false,
    statusText: ''
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

      this.setData({
        event: { ...event, time_display: formatTime(event.event_time) },
        members: members.map((m) => ({ ...m, short: m.nickname ? m.nickname[0] : '?' })),
        userId,
        joined,
        isCreator: event.creator_id === userId,
        reviewed,
        statusText: statusTextOf(event.status, event.event_time)
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

  onShareAppMessage() {
    const ev = this.data.event
    return {
      title: ev ? `「${ev.title}」组队中，快来加入` : '聚豆·组队聚餐',
      path: ev ? `/pages/event/detail/index?id=${ev.id}` : '/pages/index/index'
    }
  },

  async onJoin() {
    const { eventId } = this.data
    try {
      await post(`/events/${eventId}/join`)
      wx.showToast({ title: '加入成功' })
      this.load()
    } catch (err) {
      console.error('加入失败', err)
      wx.showToast({ title: '加入失败，可能已满员', icon: 'none' })
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
