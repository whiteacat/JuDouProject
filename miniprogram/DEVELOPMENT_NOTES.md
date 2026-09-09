# 小程序开发注意事项

## URL 参数传递：必须编解码配对

**问题背景：** 本项目已多次因 URL 参数编码/解码不匹配导致页面标题或数据显示为 `%E5%8F...` 等编码字符。

**规则：**

- **发送端**用 `encodeURIComponent` 编码的参数，**接收端**必须用 `decodeURIComponent` 解码
- 每新增一个页面间跳转并携带中文参数时，必须同时检查两端

**发送端示例：**

```typescript
wx.navigateTo({
  url: `/pages/group/events/index?group_id=${group.id}&group_name=${encodeURIComponent(group.name)}`
})
```

**接收端示例：**

```typescript
onLoad(options: Record<string, string>) {
  const groupName = decodeURIComponent(options.group_name || '')
}
```

**自查清单：**

- [ ] 所有 `encodeURIComponent(...)` 调用，对应的接收页面是否都有 `decodeURIComponent`
- [ ] 新增页面跳转时，参数是否需要编码（含中文/特殊字符就必须编码）
- [ ] 使用 `wx.navigateTo` / `wx.redirectTo` / `wx.switchTab` 携带参数时逐一检查

---

## 预设头像 URL 显示

**规则：** 预设头像使用 `preset://avatar/X` 协议标识，不能直接作为 `<image src>` 使用。

**必须**通过 `resolveAvatarSrc()` 转换为本地路径后再绑定到模板：

```typescript
import { resolveAvatarSrc } from '../../../utils/avatar'

// 在 setData 时转换
this.setData({ avatar_src: resolveAvatarSrc(item.avatar_url || '') })
```

```xml
<image wx:if="{{avatar_src}}" src="{{avatar_src}}" />
<view wx:else>{{short}}</view>
```

**禁止**在 WXML 中直接使用 `{{avatar_url}}` 作为 `<image src>`。
