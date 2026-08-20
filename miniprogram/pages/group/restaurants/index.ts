// 群组餐厅库：我们群去过的餐厅与评分
import { get } from '../../../utils/request'

interface GroupRestaurantItem {
  restaurant: {
    id: number
    name: string
    category: string
    address: string
  }
  group_stats: {
    visit_count: number
    score: number | null
  }
}

Page({
  data: {
    groupId: 0,
    groupName: '',
    items: [] as GroupRestaurantItem[],
    loading: false
  },

  onLoad(options: Record<string, string>) {
    const groupId = Number(options.group_id || 0)
    if (!groupId) {
      wx.showToast({ title: '缺少群组参数', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 800)
      return
    }
    this.setData({
      groupId,
      groupName: options.group_name || ''
    })
    this.fetchLibrary()
  },

  async fetchLibrary() {
    const { groupId } = this.data
    this.setData({ loading: true })
    try {
      const items = await get<GroupRestaurantItem[]>(`/groups/${groupId}/restaurants`)
      this.setData({ items })
    } catch (err) {
      console.error('加载群组餐厅库失败', err)
      wx.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  goDetail(e: WechatMiniprogram.TouchEvent) {
    const { id } = e.currentTarget.dataset
    const { groupId, groupName } = this.data
    wx.navigateTo({
      url:
        `/pages/restaurant/detail/index?group_id=${groupId}` +
        `&group_name=${encodeURIComponent(groupName)}` +
        `&restaurant_id=${id}`
    })
  }
})
