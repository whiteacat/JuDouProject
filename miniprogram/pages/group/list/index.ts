// 群组列表页：展示我加入的群组，入口：创建 / 加入（自定义导航栏）
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
    statusBarHeight: 20,
    navHeight: 44,
    // 胶囊按钮位置：+ 号按钮右边界与胶囊左边对齐，避免重叠
    addRightOffset: 170,
    groups: [] as GroupItem[],
    filteredGroups: [] as GroupItem[],
    keyword: '',
    loading: false
  },

  onLoad() {
    const sysInfo = wx.getSystemInfoSync()
    let addRightOffset = 170
    let navHeight = 44
    try {
      const menu = wx.getMenuButtonBoundingClientRect()
      // 导航内容区高度与胶囊一致，+ 号距右侧 = 胶囊左边界到屏幕右缘 + 16rpx 间距
      navHeight = menu.height
      addRightOffset = Math.round(menu.right - menu.left + 8)
    } catch (e) {
      // 忽略，使用默认值
    }
    this.setData({ statusBarHeight: sysInfo.statusBarHeight || 20, navHeight, addRightOffset })
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
    const keyword = e.detail.value
    const kw = keyword.toLowerCase()
    const filtered = kw
      ? this.data.groups.filter((g) => g.name.toLowerCase().includes(kw))
      : this.data.groups
    this.setData({ keyword, filteredGroups: filtered })
  },

  onClearSearch() {
    this.setData({ keyword: '', filteredGroups: this.data.groups })
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
