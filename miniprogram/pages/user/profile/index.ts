// 我的页：用户信息卡 + 数据统计 + 功能菜单 + 退出登录（未登录态引导）
import { UserProfile, getUserProfile, isLoggedIn } from '../../../utils/auth'
import { resolveAvatarSrc } from '../../../utils/avatar'
import { get } from '../../../utils/request'

interface UserStats {
  group_count: number
  event_count: number
  review_count: number
}

Page({
  data: {
    loggedIn: false,
    user: null as (UserProfile & { short?: string; avatar_src?: string; signature?: string }) | null,
    stats: { group_count: 0, event_count: 0, review_count: 0 } as UserStats
  },

  onShow() {
    this.refresh()
  },

  async refresh() {
    if (!isLoggedIn()) {
      this.setData({ loggedIn: false, user: null })
      return
    }
    const profile = getUserProfile()
    this.setData({
      loggedIn: true,
      user: profile
        ? {
            ...profile,
            short: profile.nickname ? profile.nickname[0] : '聚',
            avatar_src: resolveAvatarSrc(profile.avatar_url || ''),
            signature: profile.signature || '',
          }
        : null
    })
    this.loadStats()
  },

  async loadStats() {
    try {
      const stats = await get<UserStats>('/users/me/stats')
      this.setData({ stats })
    } catch {
      // 静默失败
    }
  },

  goLogin() {
    wx.navigateTo({ url: '/pages/login/index' })
  },

  goEdit() {
    wx.navigateTo({ url: '/pages/user/edit/index' })
  },

  goEvents() {
    wx.navigateTo({ url: '/pages/event/list/index' })
  },

  goGroups() {
    wx.navigateTo({ url: '/pages/group/mine/index' })
  },

  goReviews() {
    wx.navigateTo({ url: '/pages/review/mine/index' })
  },

  goFavorites() {
    wx.showToast({ title: '收藏功能开发中', icon: 'none' })
  },

  goPreferences() {
    wx.showToast({ title: '偏好设置开发中', icon: 'none' })
  },

  goPrivacy() {
    wx.showToast({ title: '隐私设置开发中', icon: 'none' })
  },

  goFeedback() {
    wx.showToast({ title: '帮助与反馈开发中', icon: 'none' })
  },

  goAbout() {
    wx.showToast({ title: '关于我们开发中', icon: 'none' })
  },

  onLogout() {
    wx.showModal({
      title: '退出登录',
      content: '确定要退出当前账号吗？',
      success: (res) => {
        if (res.confirm) {
          wx.removeStorageSync('token')
          wx.removeStorageSync('userInfo')
          this.setData({ loggedIn: false, user: null })
          wx.showToast({ title: '已退出登录' })
        }
      }
    })
  }
})
