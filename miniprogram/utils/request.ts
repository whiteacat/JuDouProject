// 带 token 的统一请求封装（401 时自动静默重登录并重试一次）
import { BASE_URL } from './config'

interface RequestOptions {
  url: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: Record<string, unknown>
  params?: Record<string, string | number>
  auth?: boolean
}

interface LoginUser {
  id: number
  nickname: string
  avatar_url: string
}

let reloginPromise: Promise<boolean> | null = null

/** 静默重新登录（并发 401 共享同一次登录）；返回是否成功。 */
function relogin(): Promise<boolean> {
  if (!reloginPromise) {
    const p = new Promise<boolean>((resolve) => {
      const finish = (ok: boolean) => {
        reloginPromise = null
        resolve(ok)
      }
      wx.login({
        success: (res) => {
          if (!res.code) {
            finish(false)
            return
          }
          request<{ access_token: string; user: LoginUser }>({
            url: '/auth/wechat/login',
            method: 'POST',
            data: { code: res.code },
            auth: false
          })
            .then((data) => {
              wx.setStorageSync('token', data.access_token)
              wx.setStorageSync('userInfo', data.user)
              finish(true)
            })
            .catch(() => finish(false))
        },
        fail: () => finish(false)
      })
    })
    reloginPromise = p
  }
  return reloginPromise
}

function buildUrl(url: string, params?: Record<string, string | number>): string {
  if (!params) return url
  const qs = Object.keys(params)
    .map((k) => `${encodeURIComponent(k)}=${encodeURIComponent(String(params[k]))}`)
    .join('&')
  return qs ? `${url}?${qs}` : url
}

function doRequest<T>(options: RequestOptions, isRetry = false): Promise<T> {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token') as string

    wx.request({
      url: buildUrl(`${BASE_URL}${options.url}`, options.params),
      method: options.method || 'GET',
      data: options.data,
      header: {
        'Content-Type': 'application/json',
        ...(options.auth !== false && token ? { Authorization: `Bearer ${token}` } : {})
      },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data as T)
          return
        }
        // token 失效（如后端 JWT_SECRET 变更后旧 token 验签失败）：静默重登录并重试一次
        // 登录接口本身不重试，避免循环
        if (
          res.statusCode === 401 &&
          !isRetry &&
          options.auth !== false &&
          !options.url.includes('/auth/wechat/login')
        ) {
          relogin().then((ok) => {
            if (ok) {
              doRequest<T>(options, true).then(resolve, reject)
            } else {
              reject(res)
            }
          }).catch(() => reject(res))
          return
        }
        reject(res)
      },
      fail(err) {
        reject(err)
      }
    })
  })
}

export function request<T = unknown>(options: RequestOptions): Promise<T> {
  return doRequest<T>(options)
}

export const get = <T = unknown>(
  url: string,
  params?: Record<string, string | number>
) => request<T>({ url, params })

export const post = <T = unknown>(url: string, data?: Record<string, unknown>) =>
  request<T>({ url, method: 'POST', data })
