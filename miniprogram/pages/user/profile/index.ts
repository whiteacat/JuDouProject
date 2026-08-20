// 我的页：用户信息卡 + 功能菜单 + 退出登录（未登录态引导）
import { UserProfile, getUserProfile, isLoggedIn } from '../../../utils/auth'

Page({
  data: {
    loggedIn: false,
    user: null as (UserProfile & { short?: string }) | null
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
        ? { ...profile, short: profile.nickname ? profile.nickname[0] : '聚' }
        : null
    })
  },

  goLogin() {
    wx.navigateTo({ url: '/pages/login/index' })
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
