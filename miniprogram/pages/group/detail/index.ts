// 群组详情页：群信息、邀请码、成员列表、群公告、功能入口
import { get, post, put, del, patch } from '../../../utils/request'
import { resolveAvatarSrc } from '../../../utils/avatar'
import { GROUP_COVERS, resolveGroupCoverSrc } from '../../../utils/cover'

interface Member {
  user_id: number
  role: string
  joined_at: string
  nickname: string
  avatar_url: string
  short?: string
  avatar_src?: string
}

interface GroupDetail {
  id: number
  name: string
  avatar_url: string
  avatar_src?: string
  cover_url?: string | null
  cover_src?: string
  owner_id: number
  invite_code: string
  member_count: number
  active_count: number
}

interface EventBrief {
  id: number
  title: string
  event_time: string
  status: string
  current_members: number
  max_members: number
  time_display?: string
  status_text?: string
}

interface Announcement {
  id: number
  group_id: number
  content: string
  owner_id: number
  created_at: string
  updated_at: string
  time_display?: string
}

const STATUS_TEXT: Record<string, string> = {
  RECRUITING: '招募中',
  CONFIRMED: '已确认',
  COMPLETED: '已完成',
  CANCELLED: '已取消',
  EXPIRED: '已失效'
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${m}-${day} ${h}:${min}`
}

Page({
  data: {
    groupId: 0,
    group: null as GroupDetail | null,
    members: [] as Member[],
    showMembers: [] as Member[],
    owner: null as Member | null,
    // 成员网格恒展示前 8 人（完整列表见独立成员页）
    recentEvents: [] as EventBrief[],
    isMember: false,
    isOwner: false,
    // 群公告
    announcement: null as Announcement | null,
    // 公告编辑弹窗
    showAnnouncementEditor: false,
    announcementDraft: '',
    announcementSaving: false,
    // 邀请落地：分享卡片携带 invite=1 时启用引导（未登录→登录→带码入群）
    inviteMode: false,
    inviteJoining: false,
    inviteJoinReady: false,
    inviteCode: '',
    // 群组封面背景选择弹窗（仅群主）
    groupCovers: GROUP_COVERS,
    showCoverPicker: false,
    coverSaving: false
  },

  _redirecting: false,

  onLoad(options: Record<string, string>) {
    const groupId = Number(options.id || 0)
    if (!groupId) {
      wx.showToast({ title: '缺少群组参数', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 800)
      return
    }
    this.setData({ groupId })
    if (options.invite === '1') {
      this.setData({
        inviteMode: true,
        inviteCode: options.code || '',
        inviteJoinReady: !!options.code
      })
    }
    this.fetchDetail()
  },

  onShareAppMessage() {
    const group = this.data.group
    if (!group) {
      return { title: '聚豆·群组聚餐组队', path: '/pages/index/index' }
    }
    // 邀请落地链路：好友点开 → 登录 → 带邀请码一键入群
    const params = [`id=${group.id}`, 'invite=1']
    if (group.invite_code) {
      params.push(`code=${encodeURIComponent(group.invite_code)}`)
    }
    return {
      title: `「${group.name}」邀请你一起聚餐`,
      path: `/pages/group/detail/index?${params.join('&')}`
    }
  },

  onShow() {
    if (this.data.groupId && !this.data.group) {
      this.fetchDetail()
    }
  },

  async fetchDetail() {
    const { groupId } = this.data
    if (!groupId) return
    try {
      const [group, members, events] = await Promise.all([
        get<GroupDetail>(`/groups/${groupId}`),
        get<Member[]>(`/groups/${groupId}/members`),
        get<EventBrief[]>(`/groups/${groupId}/events`).catch(() => [])
      ])
      const info = wx.getStorageSync('userInfo') as { id?: number } | null
      const userId = info && info.id ? info.id : 0
      const avatarSrc = resolveAvatarSrc(group.avatar_url || '')
      const mappedMembers = members.map((m) => ({
        ...m,
        short: m.nickname ? m.nickname[0] : '?',
        avatar_src: resolveAvatarSrc(m.avatar_url || ''),
      }))
      const mappedEvents = events.slice(0, 3).map((e) => ({
        ...e,
        time_display: formatTime(e.event_time),
        status_text: STATUS_TEXT[e.status] || e.status,
      }))
      this.setData({
        group: {
          ...group,
          avatar_src: avatarSrc,
          cover_src: resolveGroupCoverSrc(group.cover_url)
        },
        members: mappedMembers,
        showMembers: mappedMembers.slice(0, 8),
        owner: mappedMembers.find((m) => m.role === 'OWNER') || null,
        recentEvents: mappedEvents,
        isMember: true,
        isOwner: group.owner_id === userId
      })
      this.loadAnnouncement()
    } catch (err) {
      console.error('加载群组失败', err)
      const statusCode = (err as { statusCode?: number })?.statusCode
      if (statusCode === 401) {
        if (!this._redirecting) {
          this._redirecting = true
          // 未登录：邀请落地链接回跳本页（携带邀请码），登录后自动入群
          const redirect = this.data.inviteMode
            ? `/pages/login/index?redirect=${encodeURIComponent(
                `/pages/group/detail/index?id=${this.data.groupId}&invite=1&code=${encodeURIComponent(this.data.inviteCode)}`
              )}`
            : '/pages/login/index'
          wx.showToast({ title: '请先登录', icon: 'none' })
          wx.navigateTo({ url: redirect })
        }
        return
      }
      if (statusCode === 404) {
        // 非成员：邀请落地时保留引导横幅，避免死胡同
        if (this.data.inviteMode && this.data.inviteCode) {
          return
        }
        wx.showToast({ title: '群组不存在或已失效', icon: 'none' })
        return
      }
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  /** 邀请落地入口：未登录跳登录页（登录后回跳本页），已登录直接带码入群 */
  onInviteEnter() {
    if (this.data.inviteJoining) return
    const info = wx.getStorageSync('userInfo') as { id?: number } | null
    if (!info || !info.id) {
      wx.navigateTo({
        url: `/pages/login/index?redirect=${encodeURIComponent(
          `/pages/group/detail/index?id=${this.data.groupId}&invite=1&code=${encodeURIComponent(this.data.inviteCode)}`
        )}`
      })
      return
    }
    this.joinFromInvite()
  },

  /** 已登录的邀请落地：带邀请码加入群组，成功后刷新页面 */
  async joinFromInvite() {
    const code = this.data.inviteCode
    if (!code) {
      wx.showModal({
        title: '缺少邀请码',
        content: '该分享链接未携带邀请码，请向群友索取邀请码后从「群组列表-输入邀请码」加入。',
        showCancel: false
      })
      return
    }
    this.setData({ inviteJoining: true })
    wx.showLoading({ title: '加入中' })
    try {
      const group = await post<{ id: number; name: string }>('/groups/join-by-code', {
        invite_code: code
      })
      wx.hideLoading()
      this._redirecting = false
      await this.fetchDetail()
      this.setData({ inviteMode: false })
      wx.showToast({ title: `已加入「${group.name}」`, icon: 'none' })
    } catch (err) {
      wx.hideLoading()
      const detail = (err as { data?: { detail?: string } })?.data?.detail
      console.error('邀请落地入群失败', err)
      wx.showToast({ title: detail || '入群失败，请检查邀请码', icon: 'none' })
    } finally {
      this.setData({ inviteJoining: false })
    }
  },

  /** 加载群公告（无公告时后端返回 404，属正常状态，静默置空不报错） */
  async loadAnnouncement() {
    try {
      const a = await get<Announcement>(`/groups/${this.data.groupId}/announcement`)
      this.setData({
        announcement: { ...a, time_display: a.updated_at ? formatTime(a.updated_at) : '' }
      })
    } catch (err: unknown) {
      this.setData({ announcement: null })
      // 404 = 暂无公告（预期状态）；其他错误才记录
      const code = (err as { statusCode?: number })?.statusCode
      if (code !== 404) {
        console.error('加载群公告失败', err)
      }
    }
  },

  /** 跳转独立群成员页（原 toggleMembers 就地展开/收起已废弃：
   * 功能区的「成员列表」与成员区的「查看更多」均跳转完整成员页） */
  goMembers() {
    wx.navigateTo({ url: `/pages/group/members/index?id=${this.data.groupId}` })
  },

  /** 打开封面背景选择弹窗（仅群主） */
  openCoverPicker() {
    if (!this.data.isOwner) return
    this.setData({ showCoverPicker: true })
  },

  closeCoverPicker() {
    this.setData({ showCoverPicker: false })
  },

  /** 群主选择封面背景 */
  async onPickCover(e: WechatMiniprogram.TouchEvent) {
    const key = e.currentTarget.dataset.key as string
    if (!key || this.data.coverSaving) return
    this.setData({ coverSaving: true })
    try {
      const group = await patch<GroupDetail>(`/groups/${this.data.groupId}/cover`, {
        cover_url: key
      })
      this.setData({
        group: {
          ...(this.data.group as GroupDetail),
          cover_url: group.cover_url,
          cover_src: resolveGroupCoverSrc(group.cover_url)
        },
        showCoverPicker: false
      })
      wx.showToast({ title: '封面已更新' })
    } catch (err) {
      console.error('更新封面失败', err)
      wx.showToast({ title: '更新失败', icon: 'none' })
    } finally {
      this.setData({ coverSaving: false })
    }
  },

  /** 群主清除封面（恢复默认背景） */
  async onClearCover() {
    if (this.data.coverSaving) return
    this.setData({ coverSaving: true })
    try {
      const group = await patch<GroupDetail>(`/groups/${this.data.groupId}/cover`, {
        cover_url: null
      })
      this.setData({
        group: {
          ...(this.data.group as GroupDetail),
          cover_url: group.cover_url,
          cover_src: resolveGroupCoverSrc(group.cover_url)
        },
        showCoverPicker: false
      })
      wx.showToast({ title: '已恢复默认背景' })
    } catch (err) {
      console.error('清除封面失败', err)
      wx.showToast({ title: '操作失败', icon: 'none' })
    } finally {
      this.setData({ coverSaving: false })
    }
  },

  /** 打开公告编辑器（群主：编辑已有或新建；成员：仅查看） */
  onAnnouncement() {
    if (this.data.isOwner) {
      this.setData({
        showAnnouncementEditor: true,
        announcementDraft: this.data.announcement?.content || ''
      })
    }
  },

  onAnnouncementInput(e: WechatMiniprogram.Input) {
    this.setData({ announcementDraft: e.detail.value })
  },

  closeAnnouncementEditor() {
    this.setData({ showAnnouncementEditor: false })
  },

  /** 群主保存公告 */
  async saveAnnouncement() {
    const content = (this.data.announcementDraft || '').trim()
    if (!content) {
      wx.showToast({ title: '公告内容不能为空', icon: 'none' })
      return
    }
    if (this.data.announcementSaving) return
    this.setData({ announcementSaving: true })
    try {
      const a = await put<Announcement>(`/groups/${this.data.groupId}/announcement`, { content })
      this.setData({
        announcement: { ...a, time_display: a.updated_at ? formatTime(a.updated_at) : '' },
        showAnnouncementEditor: false
      })
      wx.showToast({ title: '公告已更新' })
    } catch (err) {
      console.error('保存公告失败', err)
      wx.showToast({ title: '保存失败', icon: 'none' })
    } finally {
      this.setData({ announcementSaving: false })
    }
  },

  /** 群主删除公告 */
  onDeleteAnnouncement() {
    wx.showModal({
      title: '删除公告',
      content: '确定删除当前群公告吗？',
      success: async (res) => {
        if (!res.confirm) return
        try {
          await del(`/groups/${this.data.groupId}/announcement`)
          this.setData({
            announcement: null,
            showAnnouncementEditor: false
          })
          wx.showToast({ title: '公告已删除' })
        } catch (err) {
          console.error('删除公告失败', err)
          wx.showToast({ title: '删除失败', icon: 'none' })
        }
      }
    })
  },

  onMore() {
    wx.showActionSheet({
      itemList: ['分享群组', '退出群组'],
      success: (res) => {
        if (res.tapIndex === 0) {
          // 触发分享
        }
      }
    })
  },

  onCopyCode() {
    const code = this.data.group ? this.data.group.invite_code : ''
    if (!code) return
    wx.setClipboardData({ data: code })
  },

  goGroupEvents() {
    const group = this.data.group
    if (!group) return
    wx.navigateTo({
      url: `/pages/group/events/index?group_id=${group.id}&group_name=${encodeURIComponent(group.name)}`
    })
  },

  goCreateEvent() {
    const group = this.data.group
    if (!group) return
    wx.navigateTo({
      url: `/pages/event/create/index?group_id=${group.id}&group_name=${encodeURIComponent(group.name)}`
    })
  },

  goEventDetail(e: WechatMiniprogram.TouchEvent) {
    const { id } = e.currentTarget.dataset
    wx.navigateTo({ url: `/pages/event/detail/index?id=${id}` })
  }
})
