// 创建群组页
import { post } from '../../../utils/request'

Page({
  data: {
    name: ''
  },

  onNameInput(e: WechatMiniprogram.Input) {
    this.setData({ name: e.detail.value })
  },

  async onSubmit() {
    const name = (this.data.name || '').trim()
    if (!name) {
      wx.showToast({ title: '请输入群组名称', icon: 'none' })
      return
    }
    try {
      const group = await post<{ id: number }>('/groups', { name })
      wx.showToast({ title: '创建成功' })
      wx.redirectTo({ url: `/pages/group/detail/index?id=${group.id}` })
    } catch (err) {
      console.error('创建群组失败', err)
      wx.showToast({ title: '创建失败', icon: 'none' })
    }
  }
})
