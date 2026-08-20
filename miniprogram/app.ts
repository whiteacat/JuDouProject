// 小程序入口：启动时若未登录则静默登录（wx.login -> 后端换 token）
import { UserProfile, isLoggedIn, login } from './utils/auth'

App({
  globalData: {
    token: '',
    userInfo: null as UserProfile | null
  },

  onLaunch() {
    this.bootstrap()
  },

  async bootstrap() {
    if (isLoggedIn()) {
      this.globalData.token = wx.getStorageSync('token')
      this.globalData.userInfo = wx.getStorageSync('userInfo')
      return
    }
    try {
      const res = await login()
      this.globalData.token = res.access_token
      this.globalData.userInfo = res.user
    } catch (err) {
      console.error('静默登录失败', err)
    }
  }
})
