// 我的群组列表页：点击进入群组详情
import { get } from '../../../utils/request'

interface GroupItem {
  id: number
  name: string
  avatar_url: string
  member_count: number
}

Page({
  data: {
    groups: [] as GroupItem[],
    loading: false
  },

  onShow() {
    this.fetchGroups()
  },

  async fetchGroups() {
    this.setData({ loading: true })
    try {
      const groups = await get<GroupItem[]>('/groups')
      this.setData({ groups })
    } catch (err) {
      console.error('加载群组失败', err)
      wx.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  goDetail(e: WechatMiniprogram.TouchEvent) {
    const { id } = e.currentTarget.dataset
    wx.navigateTo({ url: `/pages/group/detail/index?id=${id}` })
  }
})
