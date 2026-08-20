// 登录页占位：M1 接入微信登录（wx.login -> 后端换 token）
import { login } from '../../utils/auth'

Page({
  loading: false,

  async onLogin() {
    if (this.loading) return
    this.loading = true
    wx.showLoading({ title: '登录中' })
    try {
      const res = await login()
      wx.setStorageSync('userInfo', res.user)
      wx.showToast({ title: '登录成功' })
      setTimeout(() => wx.navigateBack(), 800)
    } catch (err) {
      console.error('登录失败', err)
      wx.showToast({ title: '登录失败', icon: 'none' })
    } finally {
      this.loading = false
      wx.hideLoading()
    }
  }
})
