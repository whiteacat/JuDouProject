// 带 token 的统一请求封装
import { BASE_URL } from './config'

interface RequestOptions {
  url: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: Record<string, unknown>
  params?: Record<string, string | number>
  auth?: boolean
}

function buildUrl(url: string, params?: Record<string, string | number>): string {
  if (!params) return url
  const qs = Object.keys(params)
    .map((k) => `${encodeURIComponent(k)}=${encodeURIComponent(String(params[k]))}`)
    .join('&')
  return qs ? `${url}?${qs}` : url
}

export function request<T = unknown>(options: RequestOptions): Promise<T> {
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
        } else {
          reject(res)
        }
      },
      fail(err) {
        reject(err)
      }
    })
  })
}

export const get = <T = unknown>(
  url: string,
  params?: Record<string, string | number>
) => request<T>({ url, params })

export const post = <T = unknown>(url: string, data?: Record<string, unknown>) =>
  request<T>({ url, method: 'POST', data })
