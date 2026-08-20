// 餐厅详情页：餐厅信息 + 群聚合评分（"我们群怎么看这家店"）+ 群成员评价
import { get } from '../../../utils/request'

interface GroupStats {
  visit_count: number
  score: number | null
  taste: number | null
  value: number | null
  environment: number | null
  service: number | null
  traffic: number | null
}

interface RestaurantInfo {
  id: number
  name: string
  category: string
  address: string
  phone: string | null
}

interface ReviewItem {
  id: number
  user_id: number
  nickname: string
  avatar_url: string
  overall_score: number
  content: string
}

interface ScoreBar {
  label: string
  score: number
  percent: number
}

Page({
  data: {
    groupId: 0,
    groupName: '',
    restaurantId: 0,
    restaurant: null as RestaurantInfo | null,
    stats: null as GroupStats | null,
    bars: [] as ScoreBar[],
    reviews: [] as ReviewItem[]
  },

  onLoad(options: Record<string, string>) {
    const groupId = Number(options.group_id || 0)
    const restaurantId = Number(options.restaurant_id || 0)
    if (!groupId || !restaurantId) {
      wx.showToast({ title: '缺少参数', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 800)
      return
    }
    this.setData({
      groupId,
      groupName: options.group_name || '',
      restaurantId
    })
    this.load()
  },

  async load() {
    const { groupId, restaurantId } = this.data
    try {
      const [detail, reviews] = await Promise.all([
        get<{ restaurant: RestaurantInfo; group_stats: GroupStats }>(
          `/groups/${groupId}/restaurants/${restaurantId}`
        ),
        get<ReviewItem[]>(`/groups/${groupId}/restaurants/${restaurantId}/reviews`)
      ])
      const s = detail.group_stats
      const bars: ScoreBar[] = [
        { label: '口味', score: s.taste || 0, percent: ((s.taste || 0) / 5) * 100 },
        { label: '性价比', score: s.value || 0, percent: ((s.value || 0) / 5) * 100 },
        { label: '环境', score: s.environment || 0, percent: ((s.environment || 0) / 5) * 100 },
        { label: '服务', score: s.service || 0, percent: ((s.service || 0) / 5) * 100 },
        { label: '交通', score: s.traffic || 0, percent: ((s.traffic || 0) / 5) * 100 }
      ].filter((b) => b.score > 0)
      this.setData({
        restaurant: detail.restaurant,
        stats: detail.group_stats,
        bars,
        reviews
      })
    } catch (err) {
      console.error('加载餐厅详情失败', err)
      const statusCode = (err as { statusCode?: number })?.statusCode
      if (statusCode === 401) {
        wx.showToast({ title: '请先登录', icon: 'none' })
        wx.navigateTo({ url: '/pages/login/index' })
        return
      }
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  goCreateEvent() {
    const { groupId, groupName, restaurant } = this.data
    if (!restaurant) return
    wx.navigateTo({
      url:
        `/pages/event/create/index?group_id=${groupId}` +
        `&group_name=${encodeURIComponent(groupName)}` +
        `&restaurant_id=${restaurant.id}` +
        `&restaurant_name=${encodeURIComponent(restaurant.name)}`
    })
  }
})
