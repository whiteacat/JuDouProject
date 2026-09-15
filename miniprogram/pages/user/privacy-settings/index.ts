// 隐私设置页：隐私政策/用户协议入口 + 清除本地缓存 + 退出登录
Page({
  data: {
    items: [
      { key: 'privacy', label: '隐私政策' },
      { key: 'terms', label: '用户协议' }
    ]
  },

  onTapItem(e: WechatMiniprogram.TouchEvent) {
    const key = e.currentTarget.dataset.key as string
    const doc = key === 'privacy' ? 'privacy' : 'terms'
    wx.navigateTo({ url: `/pages/user/privacy/index?doc=${doc}` })
  },

  clearCache() {
    wx.showModal({
      title: '清除缓存',
      content: '将清除本地缓存数据（不退出登录），确定继续？',
      success: async (res) => {
        if (!res.confirm) return
        const token = wx.getStorageSync('token')
        const userInfo = wx.getStorageSync('userInfo')
        wx.clearStorageSync()
        if (token) wx.setStorageSync('token', token)
        if (userInfo) wx.setStorageSync('userInfo', userInfo)
        wx.showToast({ title: '缓存已清除' })
      }
    })
  },

  onLogout() {
    wx.showModal({
      title: '退出登录',
      content: '确定退出当前账号吗？',
      success: (res) => {
        if (!res.confirm) return
        wx.clearStorageSync()
        wx.reLaunch({ url: '/pages/user/profile/index' })
      }
    })
  }
})
