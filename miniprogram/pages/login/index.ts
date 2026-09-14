import { login } from '../../utils/auth'

Page({
  data: {
    nickname: '',
    avatarUrl: '',
    // 登录成功后的回跳目标（分享卡片落地引导登录时使用）
    redirect: '',
  },
  loading: false,

  onLoad(options: Record<string, string>) {
    const redirect = options.redirect || ''
    if (redirect) {
      this.setData({ redirect: decodeURIComponent(redirect) })
    }
  },

  /** 登录成功后：优先跳回分享目标页，否则返回上一页 */
  afterLogin() {
    if (this.data.redirect) {
      wx.redirectTo({
        url: this.data.redirect,
        fail: () => wx.navigateBack()
      })
    } else {
      wx.navigateBack()
    }
  },

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
      setTimeout(() => this.afterLogin(), 800)
    } catch (err) {
      console.error('登录失败', err)
      wx.showToast({ title: '登录失败', icon: 'none' })
    } finally {
      this.loading = false
      wx.hideLoading()
    }
  }
})
