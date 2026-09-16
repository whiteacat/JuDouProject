// 我的评价详情页：五维评分 + 文字评价 + 关联信息（餐厅/群/活动）
import { get } from '../../../utils/request'

interface ReviewDetail {
  id: number
  restaurant_id: number
  restaurant_name: string
  group_id: number
  group_name: string | null
  event_id: number
  event_title: string | null
  overall_score: number
  taste_score: number
  value_score: number
  environment_score: number
  service_score: number
  traffic_score: number
  content: string
  created_at: string
  // 前端加工
  score_items?: { label: string; value: number }[]
  time_display?: string
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${day} ${h}:${min}`
}

Page({
  data: {
    review: null as ReviewDetail | null,
    loading: true,
    notFound: false
  },

  onLoad(options: Record<string, string>) {
    const id = Number(options.id || 0)
    if (!id) {
      this.setData({ loading: false, notFound: true })
      return
    }
    this.setData({ reviewId: id })
    this.loadDetail(id)
  },

  async loadDetail(id: number) {
    try {
      const review = await get<ReviewDetail>(`/users/me/reviews/${id}`)
      this.setData({
        review: {
          ...review,
          time_display: formatDate(review.created_at),
          score_items: [
            { label: '口味', value: review.taste_score },
            { label: '性价比', value: review.value_score },
            { label: '环境', value: review.environment_score },
            { label: '服务', value: review.service_score },
            { label: '交通便利', value: review.traffic_score }
          ]
        },
        loading: false
      })
    } catch (err) {
      console.error('加载评价详情失败', err)
      this.setData({ loading: false, notFound: true })
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  goRestaurant() {
    const r = this.data.review
    if (r) wx.navigateTo({ url: `/pages/restaurant/detail/index?id=${r.restaurant_id}` })
  },

  goEvent() {
    const r = this.data.review
    if (r) wx.navigateTo({ url: `/pages/event/detail/index?id=${r.event_id}` })
  }
})
