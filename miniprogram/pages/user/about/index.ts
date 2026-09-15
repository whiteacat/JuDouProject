// 关于我们页：版本信息 + 产品简介 + 协议入口
Page({
  data: {
    version: '1.0.0',
    items: [
      { key: 'privacy', label: '隐私政策' },
      { key: 'terms', label: '用户协议' },
      { key: 'feedback', label: '帮助与反馈' }
    ]
  },

  onTapItem(e: WechatMiniprogram.TouchEvent) {
    const key = e.currentTarget.dataset.key as string
    if (key === 'feedback') {
      wx.navigateTo({ url: '/pages/user/feedback/index' })
      return
    }
    if (key === 'privacy') {
      wx.navigateTo({ url: '/pages/user/privacy/index?doc=privacy' })
      return
    }
    if (key === 'terms') {
      wx.navigateTo({ url: '/pages/user/privacy/index?doc=terms' })
    }
  }
})
