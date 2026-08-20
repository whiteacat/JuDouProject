// 我的评价列表页：我提交过的全部评价
import { get } from '../../../utils/request'

interface MyReview {
  id: number
  restaurant_id: number
  restaurant_name: string
  group_id: number
  group_name: string | null
  event_id: number
  event_title: string | null
  overall_score: number
  content: string
  created_at: string
  time_display?: string
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

Page({
  data: {
    reviews: [] as MyReview[],
    loading: false
  },

  onShow() {
    this.fetchReviews()
  },

  async fetchReviews() {
    this.setData({ loading: true })
    try {
      const reviews = await get<MyReview[]>('/users/me/reviews')
      this.setData({
        reviews: reviews.map((r) => ({ ...r, time_display: formatDate(r.created_at) }))
      })
    } catch (err) {
      console.error('加载我的评价失败', err)
      wx.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  }
})
