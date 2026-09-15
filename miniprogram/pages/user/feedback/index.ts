// 帮助与反馈页：常见问题 FAQ + 反馈表单（提交到 /feedbacks）
import { post } from '../../../utils/request'

const FAQS = [
  {
    q: '如何创建群组？',
    a: '进入「群组」页 → 点击右上角「+」→ 输入群组名称（可选封面）→ 创建后获得邀请码，发给群友即可加入。'
  },
  {
    q: '如何邀请好友加入群组？',
    a: '进入群组详情页，点功能区的「邀请好友」分享给微信好友；好友点开卡片后登录即可一键加入（需你在卡片中携带的邀请码）。'
  },
  {
    q: '如何创建活动并拉人？',
    a: '进入群组详情页 → 「发起活动」→ 填写标题/时间/人数上限（可选地点与人均预算）→ 创建后群成员可点「加入组队」。人满后活动自动确认。'
  },
  {
    q: '活动确认/取消后对方会收到提醒吗？',
    a: '会。活动确认、取消、完成等状态变更会写入「我的通知」（个人中心 → 我的通知），已加入成员可及时查看。'
  },
  {
    q: '收藏的活动在哪里看？',
    a: '个人中心 → 「我的收藏」，可再次进入活动详情查看或取消收藏。'
  },
  {
    q: '头像怎么更换？',
    a: '个人中心 → 「资料」→ 选择微信头像或相册图片，支持双指缩放与拖动裁剪，保存后对所有群友可见。'
  }
]

Page({
  data: {
    faqs: FAQS,
    expanded: 0, // 当前展开的 FAQ 下标（-1 表示都收起）
    // 反馈表单
    kind: 'suggestion',
    kinds: [
      { value: 'suggestion', label: '建议' },
      { value: 'bug', label: '问题' },
      { value: 'other', label: '其他' }
    ],
    content: '',
    contact: '',
    submitting: false,
    contactError: ''
  },

  toggleFaq(e: WechatMiniprogram.TouchEvent) {
    const i = Number(e.currentTarget.dataset.index)
    this.setData({ expanded: this.data.expanded === i ? -1 : i })
  },

  onKindChange(e: WechatMiniprogram.TouchEvent) {
    this.setData({ kind: e.currentTarget.dataset.value as string })
  },

  onContentInput(e: WechatMiniprogram.Input) {
    this.setData({ content: e.detail.value })
  },

  onContactInput(e: WechatMiniprogram.Input) {
    this.setData({ contact: e.detail.value })
  },

  async submitFeedback() {
    const content = (this.data.content || '').trim()
    if (!content) {
      wx.showToast({ title: '请填写反馈内容', icon: 'none' })
      return
    }
    if (content.length > 500) {
      wx.showToast({ title: '内容最多 500 字', icon: 'none' })
      return
    }
    const contact = (this.data.contact || '').trim()
    if (contact && !/^1\d{10}$|^[\w.-]+@[\w.-]+$/.test(contact)) {
      this.setData({ contactError: '请填写手机号或邮箱' })
      return
    }
    if (this.data.submitting) return
    this.setData({ submitting: true })
    wx.showLoading({ title: '提交中' })
    try {
      const payload: Record<string, string> = { content, kind: this.data.kind }
      if (contact) payload.contact = contact
      await post('/feedbacks', payload)
      wx.hideLoading()
      this.setData({ content: '', contact: '', contactError: '' })
      wx.showToast({ title: '反馈已提交，感谢支持' })
    } catch (err) {
      wx.hideLoading()
      console.error('反馈提交失败', err)
      wx.showToast({ title: '提交失败，请重试', icon: 'none' })
    } finally {
      this.setData({ submitting: false })
    }
  }
})
