// 输入邀请码加入群组
import { post } from '../../../utils/request'

Page({
  data: {
    inviteCode: ''
  },

  onCodeInput(e: WechatMiniprogram.Input) {
    this.setData({ inviteCode: e.detail.value.trim() })
  },

  async onSubmit() {
    const inviteCode = this.data.inviteCode
    if (!inviteCode) {
      wx.showToast({ title: '请输入邀请码', icon: 'none' })
      return
    }
    try {
      const group = await post<{ id: number }>('/groups/join-by-code', { invite_code: inviteCode })
      wx.showToast({ title: '加入成功' })
      wx.redirectTo({ url: `/pages/group/detail/index?id=${group.id}` })
    } catch (err) {
      console.error('加入群组失败', err)
      wx.showToast({ title: '加入失败，请检查邀请码', icon: 'none' })
    }
  }
})
