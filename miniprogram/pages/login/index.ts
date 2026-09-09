import { login } from '../../utils/auth'

Page({
  data: {
    nickname: '',
    avatarUrl: '',
  },
  loading: false,

  onChooseAvatar(e: { detail: { avatarUrl: string } }) {
    this.setData({ avatarUrl: e.detail.avatarUrl })
  },

  onNicknameInput(e: WechatMiniprogram.Input) {
    this.setData({ nickname: e.detail.value })
  },

  async onLogin() {
    const { nickname, avatarUrl } = this.data
    if (!nickname) {
      wx.showToast({ title: '请输入昵称', icon: 'none' })
      return
    }
    if (this.loading) return
    this.loading = true
    wx.showLoading({ title: '登录中' })
    try {
      const res = await login(nickname, avatarUrl)
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
