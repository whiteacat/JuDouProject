// 我的页：用户信息卡 + 功能菜单 + 退出登录（未登录态引导）
import { UserProfile, getUserProfile, isLoggedIn } from '../../../utils/auth'

const PRESET_AVATAR_MAP: Record<string, string> = {
  'preset://avatar/1': '/assets/icons/preset-avatars/1.png',
  'preset://avatar/2': '/assets/icons/preset-avatars/2.png',
  'preset://avatar/3': '/assets/icons/preset-avatars/3.png',
  'preset://avatar/4': '/assets/icons/preset-avatars/4.png',
  'preset://avatar/5': '/assets/icons/preset-avatars/5.png',
  'preset://avatar/6': '/assets/icons/preset-avatars/6.png',
  'preset://avatar/7': '/assets/icons/preset-avatars/7.png',
  'preset://avatar/8': '/assets/icons/preset-avatars/8.png',
}

function resolveAvatarSrc(url: string): string {
  return PRESET_AVATAR_MAP[url] || url
}

Page({
  data: {
    loggedIn: false,
    user: null as (UserProfile & { short?: string; avatar_src?: string }) | null
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
          }
        : null
    })
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
