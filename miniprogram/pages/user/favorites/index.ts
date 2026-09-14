// 我的收藏页：收藏的活动列表，点击跳转详情，支持取消收藏
import { get, del } from '../../../utils/request'
import { resolveCoverSrc } from '../../../utils/cover'

interface FavItem {
  id: number
  title: string
  cover_url: string | null
  budget: number | null
  event_time: string
  status: string
  current_members: number
  max_members: number
  restaurant_name: string | null
  favorited_at?: string | null
  // 前端加工字段
  cover_src?: string
  time_display?: string
  budget_text?: string
  status_text?: string
}

const STATUS_TEXT: Record<string, string> = {
  RECRUITING: '招募中',
  CONFIRMED: '已确认',
  COMPLETED: '已完成',
  CANCELLED: '已取消',
  EXPIRED: '已失效'
}

function pad(n: number): string {
  return String(n).padStart(2, '0')
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

Page({
  data: {
    items: [] as FavItem[],
    loading: false,
    loaded: false
  },

  onShow() {
    this.load()
  },

  async load() {
    if (this.data.loading) return
    this.setData({ loading: true })
    try {
      const items = await get<FavItem[]>('/favorites')
      this.setData({
        items: items.map((e) => ({
          ...e,
          cover_src: resolveCoverSrc(e.cover_url),
          time_display: formatTime(e.event_time),
          budget_text: e.budget != null ? `¥${e.budget}/人` : '',
          status_text: STATUS_TEXT[e.status] || e.status
        })),
        loaded: true
      })
    } catch (err) {
      console.error('加载收藏列表失败', err)
      wx.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  goDetail(e: WechatMiniprogram.TouchEvent) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/event/detail/index?id=${id}` })
  },

  async onRemove(e: WechatMiniprogram.TouchEvent) {
    const id = Number(e.currentTarget.dataset.id)
    try {
      await del(`/favorites/${id}`)
      this.setData({ items: this.data.items.filter((it) => it.id !== id) })
      wx.showToast({ title: '已取消收藏', icon: 'none' })
    } catch (err) {
      console.error('取消收藏失败', err)
      wx.showToast({ title: '操作失败', icon: 'none' })
    }
  },

  goHome() {
    wx.switchTab({ url: '/pages/index/index' })
  }
})
