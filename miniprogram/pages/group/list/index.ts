// 群组列表页：展示我加入的群组，入口：创建 / 加入
import { get } from '../../../utils/request'
import { resolveAvatarSrc } from '../../../utils/avatar'

interface GroupItem {
  id: number
  name: string
  avatar_url: string
  owner_id: number
  invite_code: string
  member_count: number
  avatar_src?: string
}

Page({
  data: {
    groups: [] as GroupItem[],
    filteredGroups: [] as GroupItem[],
    keyword: '',
    loading: false
  },

  onShow() {
    this.fetchGroups()
  },

  async fetchGroups() {
    this.setData({ loading: true })
    try {
      const groups = await get<GroupItem[]>('/groups')
      const mapped = groups.map((g) => ({
        ...g,
        avatar_src: resolveAvatarSrc(g.avatar_url || ''),
      }))
      this.setData({ groups: mapped, filteredGroups: mapped })
    } catch (err) {
      console.error('获取群组列表失败', err)
      wx.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  onSearch(e: WechatMiniprogram.Input) {
    const keyword = e.detail.value.toLowerCase()
    const filtered = keyword
      ? this.data.groups.filter((g) => g.name.toLowerCase().includes(keyword))
      : this.data.groups
    this.setData({ keyword, filteredGroups: filtered })
  },

  goDetail(e: WechatMiniprogram.TouchEvent) {
    const { id } = e.currentTarget.dataset
    wx.navigateTo({ url: `/pages/group/detail/index?id=${id}` })
  },

  goCreate() {
    wx.navigateTo({ url: '/pages/group/create/index' })
  },

  goJoin() {
    wx.navigateTo({ url: '/pages/group/join/index' })
  }
})
