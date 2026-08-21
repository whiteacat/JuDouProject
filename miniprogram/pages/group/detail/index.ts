// 群组主页：群信息、邀请码、成员列表、功能入口
import { get } from '../../../utils/request'

interface Member {
  user_id: number
  role: string
  joined_at: string
  nickname: string
  avatar_url: string
  short?: string
}

interface GroupDetail {
  id: number
  name: string
  avatar_url: string
  owner_id: number
  invite_code: string
  member_count: number
}

Page({
  data: {
    groupId: 0,
    group: null as GroupDetail | null,
    members: [] as Member[]
  },

  onLoad(options: Record<string, string>) {
    const groupId = Number(options.id || 0)
    if (!groupId) {
      wx.showToast({ title: '缺少群组参数', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 800)
      return
    }
    this.setData({ groupId })
    this.fetchDetail()
  },

  // 群组分享：落地到本页（接收人未入群时，详情接口会提示无权限）
  onShareAppMessage() {
    const group = this.data.group
    return {
      title: group ? `「${group.name}」邀请你一起聚餐` : '聚豆·群组聚餐组队',
      path: group ? `/pages/group/detail/index?id=${group.id}` : '/pages/index/index'
    }
  },

  onShow() {
    // 分享落地后可能先跳登录再返回，此时重新加载
    if (this.data.groupId && !this.data.group) {
      this.fetchDetail()
    }
  },

  async fetchDetail() {
    const { groupId } = this.data
    if (!groupId) return
    try {
      const [group, members] = await Promise.all([
        get<GroupDetail>(`/groups/${groupId}`),
        get<Member[]>(`/groups/${groupId}/members`)
      ])
      this.setData({
        group,
        members: members.map((m) => ({
          ...m,
          short: m.nickname ? m.nickname[0] : '?'
        }))
      })
    } catch (err) {
      console.error('加载群组失败', err)
      const statusCode = (err as { statusCode?: number })?.statusCode
      if (statusCode === 401) {
        wx.showToast({ title: '请先登录', icon: 'none' })
        wx.navigateTo({ url: '/pages/login/index' })
        return
      }
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  onCopyCode() {
    const code = this.data.group ? this.data.group.invite_code : ''
    if (!code) return
    wx.setClipboardData({ data: code })
  },

  goRestaurants() {
    const group = this.data.group
    if (!group) return
    wx.navigateTo({
      url: `/pages/group/restaurants/index?group_id=${group.id}&group_name=${encodeURIComponent(group.name)}`
    })
  },

  goGroupEvents() {
    const group = this.data.group
    if (!group) return
    wx.navigateTo({
      url: `/pages/group/events/index?group_id=${group.id}&group_name=${encodeURIComponent(group.name)}`
    })
  },

  goCreateEvent() {
    const group = this.data.group
    if (!group) return
    wx.navigateTo({
      url: `/pages/event/create/index?group_id=${group.id}&group_name=${encodeURIComponent(group.name)}`
    })
  }
})
