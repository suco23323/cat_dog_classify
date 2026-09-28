/**
 * F3 接口封装:后端 API 统一入口
 *
 * 契约依据:doc/high-level-design.md §4.3/§4.4
 * 约定:
 *  - 所有后端请求必须经本模块的 axios 实例发起(本地经 Vite 代理,线上经 VITE_API_BASE_URL);
 *  - 错误提示统一由本模块的响应拦截器使用 Element Plus 的 ElMessage 弹出,
 *    视图组件不得自行拼请求、也不得重复实现错误提示逻辑。
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'

// ---------------------------------------------------------------------------
// API 地址:
//  - 本地开发缺省保持 '/api',由 Vite 代理到 127.0.0.1:8000;
//  - Vercel 部署时设置 VITE_API_BASE_URL,例如 https://your-space.hf.space/api。
// timeout 120000(120 秒),兼容单张识别与批量任务轮询的耗时场景。
// ---------------------------------------------------------------------------
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/+$/, '')

// 后端返回的 image_url/csv_url 是 /uploads/...、/result/... 这类根路径。
// 跨域部署时必须补上后端 origin,Vercel 前端才能正确加载图片和 CSV。
const BACKEND_ORIGIN = (() => {
  try {
    return new URL(API_BASE_URL).origin
  } catch {
    return ''
  }
})()

export function resolveAssetUrl(path) {
  if (!path) return path
  if (/^(https?:)?\/\//i.test(path) || path.startsWith('data:') || path.startsWith('blob:')) {
    return path
  }
  const normalized = path.startsWith('/') ? path : `/${path}`
  return `${BACKEND_ORIGIN}${normalized}`
}

const request = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
})

// ---------------------------------------------------------------------------
// 响应拦截器:统一错误提示 + 统一 reject
//  - 有响应且非 2xx:取出后端约定的 {"detail": "中文提示"} 文案弹 error;
//  - 无响应(网络错误 / 后端未启动):弹固定中文提示,支撑 TC-13 友好提示需求;
//  - 无论何种错误均 reject,供调用方(await 侧)捕获后终止后续流程。
// ---------------------------------------------------------------------------
request.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // 有响应但状态码非 2xx:优先展示后端返回的 detail 中文文案
      const detail = error.response.data?.detail
      if (typeof detail === 'string' && detail) {
        ElMessage.error(detail)
      } else {
        // detail 缺失(如 blob 响应体)时退回通用提示
        ElMessage.error(`请求失败(${error.response.status}),请稍后重试`)
      }
    } else {
      // 无响应:网络错误或后端未启动
      ElMessage.error('无法连接后端服务,请稍后重试')
    }
    return Promise.reject(error)
  },
)

// ---------------------------------------------------------------------------
// 单张识别:POST /api/classify(multipart file)
// 返回 Promise<单张结果>,结构同 proposal §6 示例
// ---------------------------------------------------------------------------
export function classify(file) {
  const formData = new FormData()
  formData.append('file', file) // 字段名固定为 file
  return request.post('/classify', formData)
}

// ---------------------------------------------------------------------------
// 批量识别提交:POST /api/batch(multipart files[])
// 返回 Promise<{ job_id, total }>,批量结果通过轮询 getJobStatus 获取
// ---------------------------------------------------------------------------
export function submitBatch(files) {
  const formData = new FormData()
  for (const file of files) {
    formData.append('files', file) // 同名多次 append,对应后端 files[] 列表
  }
  return request.post('/batch', formData)
}

// ---------------------------------------------------------------------------
// 批量任务状态轮询:GET /api/batch/status/{job_id}
// 状态机:queued → running → succeeded / failed(见设计 §4.4)
// ---------------------------------------------------------------------------
export function getJobStatus(jobId) {
  return request.get(`/batch/status/${encodeURIComponent(jobId)}`)
}

// ---------------------------------------------------------------------------
// 历史记录分页查询:GET /api/history?page=&page_size=
// 返回 Promise<{ total, page, page_size, items }>
// ---------------------------------------------------------------------------
export function getHistory(page = 1, pageSize = 10) {
  return request.get('/history', {
    params: { page, page_size: pageSize },
  })
}

// ---------------------------------------------------------------------------
// 删除单条历史:DELETE /api/history/{id}
// 返回 Promise<{ ok: true }>
// ---------------------------------------------------------------------------
export function deleteHistory(id) {
  return request.delete(`/history/${encodeURIComponent(id)}`)
}

// ---------------------------------------------------------------------------
// 清空全部历史:DELETE /api/history
// 返回 Promise<{ ok: true, deleted: n }>
// ---------------------------------------------------------------------------
export function clearHistory() {
  return request.delete('/history')
}

// ---------------------------------------------------------------------------
// 导出历史 CSV:GET /api/history/export
// responseType 为 'blob',拿到 Blob 后交给 downloadCsv 触发浏览器下载
// ---------------------------------------------------------------------------
export function exportHistory() {
  return request.get('/history/export', { responseType: 'blob' })
}

// ---------------------------------------------------------------------------
// 健康检查:GET /api/health
// 返回 Promise<{ status: "ok" }>,供视图探测后端是否就绪(TC-13)
// ---------------------------------------------------------------------------
export function health() {
  return request.get('/health')
}

// ---------------------------------------------------------------------------
// CSV 下载封装(供 F5/F6 复用):
// 创建临时 URL → 隐藏 <a download> 触发下载 → 移除节点并释放临时 URL,
// 避免内存泄漏;filename 用于设置下载保存的文件名。
// ---------------------------------------------------------------------------
export function downloadCsv(blob, filename) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url) // 立即释放临时 URL,防止内存泄漏
}
