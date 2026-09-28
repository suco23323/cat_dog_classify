<template>
  <div class="batch-classify">
    <!-- 降级提示:轮询遇 404(任务不存在/已失效)或页面刷新后本地无 job_id 时展示(TC-16/17) -->
    <el-alert
      v-if="degraded"
      class="mb12"
      title="任务状态已失效,已完成图片结果可在历史记录查看"
      type="warning"
      show-icon
      :closable="false"
    />

    <!-- ① 文件选择区:el-upload 多选 + 隐藏 webkitdirectory 输入框选文件夹,双入口统一列表 -->
    <el-card class="mb12" shadow="never">
      <template #header>
        <span>选择图片(单次最多 500 张,单张不超过 10MB)</span>
      </template>

      <div class="pick-actions">
        <!-- 入口一:el-upload multiple 手动上传模式,仅收集文件不自动上传 -->
        <el-upload
          ref="uploadRef"
          multiple
          accept=".jpg,.jpeg,.png,.bmp"
          :auto-upload="false"
          :show-file-list="false"
          :disabled="busy"
          :on-change="onUploadChange"
        >
          <el-button type="primary" :disabled="busy">多选图片</el-button>
        </el-upload>

        <!-- 入口二:"选择文件夹"按钮触发隐藏的 webkitdirectory 输入框(不支持时降级提示) -->
        <el-button :disabled="busy" @click="onPickFolder">选择文件夹</el-button>
        <input
          ref="folderInputRef"
          type="file"
          class="hidden-input"
          webkitdirectory
          multiple
          @change="onFolderChange"
        />

        <span class="count-text">已选择 {{ selectedFiles.length }} 张图片</span>

        <div class="spacer" />

        <el-button type="primary" :loading="submitting" :disabled="!canSubmit" @click="onSubmit">
          开始批量识别
        </el-button>
        <el-button :disabled="selectedFiles.length === 0 || busy" @click="onClear">清空</el-button>
      </div>

      <!-- 已选文件列表(两种入口收集到的文件统一展示在此) -->
      <el-table :data="fileRows" size="small" max-height="260" empty-text="尚未选择图片">
        <el-table-column type="index" label="序号" width="70" />
        <el-table-column prop="name" label="文件名" min-width="220" show-overflow-tooltip />
        <el-table-column prop="sizeText" label="大小" width="110" />
        <el-table-column label="操作" width="90">
          <template #default="{ $index }">
            <el-button link type="danger" :disabled="busy" @click="onRemove($index)">移除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- ② 进度区:任务 queued/running 期间展示进度条(百分比 + 当前文件名 done/total) -->
    <el-card v-if="isActive" class="mb12" shadow="never">
      <template #header>
        <span>识别进度</span>
      </template>
      <el-progress :percentage="percent" :stroke-width="18" :format="percentFormat" />
      <div class="progress-text">正在识别:{{ currentText }}({{ done }}/{{ total }})</div>
    </el-card>

    <!-- ③ 终态结果区:succeeded → 汇总统计 + CSV 下载 + 结果明细表格 -->
    <el-card v-if="isSucceeded" class="mb12" shadow="never">
      <template #header>
        <span>识别结果</span>
      </template>

      <el-descriptions :column="5" border size="small" class="mb12">
        <el-descriptions-item label="总数">{{ summary.total }}</el-descriptions-item>
        <el-descriptions-item label="成功">{{ summary.success }}</el-descriptions-item>
        <el-descriptions-item label="失败">{{ summary.failed }}</el-descriptions-item>
        <el-descriptions-item label="猫">{{ summary.cat_count }}</el-descriptions-item>
        <el-descriptions-item label="狗">{{ summary.dog_count }}</el-descriptions-item>
      </el-descriptions>

      <div class="mb12">
        <el-button type="primary" @click="onDownloadCsv">下载 CSV</el-button>
      </div>

      <el-table :data="results" size="small" max-height="420" empty-text="暂无结果">
        <el-table-column type="index" label="序号" width="70" />
        <el-table-column prop="filename" label="文件名" min-width="200" show-overflow-tooltip />
        <el-table-column prop="predict_label" label="预测类别" width="110" />
        <el-table-column label="置信度" width="110">
          <template #default="{ row }">{{ format_percent(row.confidence) || '-' }}</template>
        </el-table-column>
        <el-table-column label="备注" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">{{ row.remark || '-' }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
/**
 * F5 批量识别视图
 *
 * 依据:doc/high-level-design.md §3.3(F5)、§4.2(2)、§1.4
 * 流程:双入口选择图片(F7 收集/校验)→ submitBatch 提交拿 {job_id, total}
 *       → setInterval 每 1 秒 getJobStatus 轮询进度(el-progress + 当前文件名)
 *       → 终态 succeeded 展示汇总/结果表/CSV 下载,failed 展示中文错误
 *       → 404 / 页面刷新丢失 job_id 时给出降级提示(进度仅存后端内存,结果已落历史)
 * 约定:只调用 F3 接口封装与 F7 工具;错误提示由 F3 拦截器统一弹出,
 *       本组件仅按 catch 分支做状态降级;组件内部状态管理,不引入 Pinia。
 */
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { submitBatch, getJobStatus, downloadCsv, resolveAssetUrl } from '../api/index.js'
import { is_supported, check_size, collect_folder_files, format_percent } from '../utils/collect.js'

// sessionStorage 键:记录本页面生命周期内"进行中的批量任务 job_id",
// 用于页面刷新后识别"批量被中断"场景并给出降级提示(TC-16)
const BATCH_JOB_KEY = 'catdog_batch_job_id'

// ---------------------------------------------------------------------------
// 文件选择状态(两个入口收集到的 File 统一存入 selectedFiles,作为唯一数据源)
// ---------------------------------------------------------------------------
const selectedFiles = ref([]) // 已选图片 File 数组(提交与列表展示共用)
const folderInputRef = ref(null) // 隐藏的 webkitdirectory 文件夹输入框
const uploadRef = ref(null) // el-upload 实例(清空时同步重置其内部文件列表)
const uploadHandled = new Set() // 已处理的 el-upload 条目 uid,防止 on-change 重复添加

// 浏览器是否支持 webkitdirectory 目录选择:Firefox 等不支持时降级为仅多选(TC-07)
const folderSupported = 'webkitdirectory' in document.createElement('input')

// ---------------------------------------------------------------------------
// 任务状态(组件内部状态;任务状态仅存后端内存,页面刷新即丢失)
// ---------------------------------------------------------------------------
const submitting = ref(false) // 提交请求在途标记(防重复提交)
const jobState = ref(null) // 最近一次 getJobStatus 返回的任务状态快照
const degraded = ref(false) // 降级提示开关:404 / 页面刷新后无 job_id 时置 true
let pollTimer = null // 轮询定时器句柄(setInterval)
let pollInFlight = false // 轮询请求在途标记,上一轮未返回时跳过本轮,避免请求堆积
let disposed = false // 组件卸载标记,卸载后不再更新状态/弹提示
let jobId = null // 当前轮询的任务 id(非响应式,仅轮询闭包使用)

// 任务是否处于进行中(queued/running):期间禁用重复提交与文件入口
const isActive = computed(() => {
  const s = jobState.value && jobState.value.status
  return s === 'queued' || s === 'running'
})
const isSucceeded = computed(() => jobState.value && jobState.value.status === 'succeeded')

// 提交/文件入口的禁用总开关(提交中或任务进行中)
const busy = computed(() => submitting.value || isActive.value)
const canSubmit = computed(() => selectedFiles.value.length > 0 && !busy.value)

// 进度展示:percent 限制在 0~100(接口可能返回浮点,进度条格式化时取整)
const percent = computed(() => {
  const p = Number(jobState.value && jobState.value.percent)
  return Number.isFinite(p) ? Math.min(100, Math.max(0, p)) : 0
})
const done = computed(() => (jobState.value && jobState.value.done) || 0)
const total = computed(() => (jobState.value && jobState.value.total) || 0)
// 当前处理中的文件名;queued 阶段接口可能返回 null,降级显示 '—'
const currentText = computed(() => (jobState.value && jobState.value.current_filename) || '—')

/** 进度条百分比格式化:接口可能返回浮点(如 37.5),取整显示为 38% */
function percentFormat(p) {
  return Math.round(p) + '%'
}

// 终态数据:succeeded 时接口携带 results/summary/csv_url,其余阶段为 null
const results = computed(() => (jobState.value && jobState.value.results) || [])
const summary = computed(() => {
  const s = (jobState.value && jobState.value.summary) || {}
  return {
    total: s.total ?? 0,
    success: s.success ?? 0,
    failed: s.failed ?? 0,
    cat_count: s.cat_count ?? 0,
    dog_count: s.dog_count ?? 0,
  }
})

// 已选文件表格行:文件夹收集的文件展示子目录相对路径(webkitRelativePath)
const fileRows = computed(() =>
  selectedFiles.value.map((f) => ({
    name: f.webkitRelativePath || f.name,
    size: f.size,
    sizeText: (f.size / 1024 / 1024).toFixed(2) + ' MB',
  })),
)

// ---------------------------------------------------------------------------
// 文件收集与校验(复用 F7 is_supported/check_size;前端即时校验,后端权威校验)
// ---------------------------------------------------------------------------

/** 校验并添加单个文件:格式/大小不通过时提示并跳过(设计 §2 约束 10 双重校验前端部分) */
function addFile(file) {
  if (!file) return
  if (!is_supported(file.name)) {
    ElMessage.warning(`「${file.name}」格式不支持,仅支持 jpg/jpeg/png/bmp 图片,已跳过`)
    return
  }
  if (!check_size(file)) {
    ElMessage.warning(`「${file.name}」超过 10MB,已跳过`)
    return
  }
  // 按 文件名+大小+修改时间 去重,避免同一文件经不同入口重复加入
  const duplicated = selectedFiles.value.some(
    (f) => f.name === file.name && f.size === file.size && f.lastModified === file.lastModified,
  )
  if (!duplicated) selectedFiles.value.push(file)
}

/** 入口一:el-upload 多选。on-change 携带完整内部列表,按 uid 去重后逐个校验添加 */
function onUploadChange(uploadFile, uploadFiles) {
  for (const item of uploadFiles) {
    if (uploadHandled.has(item.uid)) continue
    uploadHandled.add(item.uid)
    addFile(item.raw)
  }
}

/** 入口二:点击"选择文件夹"。浏览器不支持 webkitdirectory 时给出降级提示,仅多选可用 */
function onPickFolder() {
  if (!folderSupported) {
    ElMessage.warning('当前浏览器不支持选择文件夹,请使用多选文件')
    return
  }
  if (folderInputRef.value) folderInputRef.value.click()
}

/** 入口二:文件夹输入框 change,复用 F7 collect_folder_files 收集图片 */
function onFolderChange() {
  const input = folderInputRef.value
  if (!input) return
  const images = collect_folder_files(input)
  const rawTotal = input.files ? input.files.length : 0
  if (images.length === 0) {
    if (rawTotal > 0) ElMessage.warning('所选文件夹中未找到支持的图片文件(jpg/jpeg/png/bmp)')
  } else {
    if (rawTotal > images.length) {
      ElMessage.warning(`已跳过 ${rawTotal - images.length} 个非图片文件,仅支持 jpg/jpeg/png/bmp 图片`)
    }
    const oversize = images.filter((f) => !check_size(f)).length
    if (oversize > 0) ElMessage.warning(`已跳过 ${oversize} 个超过 10MB 的文件`)
    images.filter((f) => check_size(f)).forEach((f) => addFile(f))
  }
  // 重置 value,保证再次选择同一文件夹时仍能触发 change
  input.value = ''
}

/** 移除列表中的单个文件 */
function onRemove(index) {
  selectedFiles.value.splice(index, 1)
}

/** 清空已选列表,并同步重置 el-upload 内部文件列表 */
function onClear() {
  selectedFiles.value = []
  if (uploadRef.value) uploadRef.value.clearFiles()
}

// ---------------------------------------------------------------------------
// 提交与轮询(设计 §4.2(2):POST /api/batch → 每 1 秒 GET /api/batch/status/{job_id})
// ---------------------------------------------------------------------------

/** 提交全部已选文件;成功后记录 job_id 并启动轮询;超上限等错误由 F3 拦截器统一提示 */
async function onSubmit() {
  if (!canSubmit.value) return
  submitting.value = true
  try {
    const res = await submitBatch(selectedFiles.value)
    const { job_id, total: fileTotal } = res.data
    // 第一次轮询返回前先按 queued 初始化本地快照,进度区立即显示 0% 与总数
    jobState.value = { status: 'queued', total: fileTotal, done: 0, percent: 0, current_filename: null }
    degraded.value = false
    sessionStorage.setItem(BATCH_JOB_KEY, job_id)
    startPolling(job_id)
  } catch (err) {
    // F3 拦截器已弹出错误提示(如"单次最多识别 500 张图片"),此处仅终止提交流程
  } finally {
    submitting.value = false
  }
}

/** 启动轮询定时器:每 1000ms 查询一次任务状态 */
function startPolling(id) {
  jobId = id
  stopTimer()
  pollTimer = setInterval(pollOnce, 1000)
}

/** 停止并清理轮询定时器(终态、404、组件卸载时调用) */
function stopTimer() {
  if (pollTimer !== null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

/** 移除 sessionStorage 中的 job_id 记录(任务进入终态或已失效时) */
function clearStoredJob() {
  sessionStorage.removeItem(BATCH_JOB_KEY)
}

/** 单次轮询:更新任务快照;终态停轮询;404 降级;其他错误继续轮询等待恢复 */
async function pollOnce() {
  if (disposed || pollInFlight || !jobId) return
  pollInFlight = true
  try {
    const res = await getJobStatus(jobId)
    jobState.value = res.data
    const status = res.data.status
    if (status === 'succeeded' || status === 'failed') {
      // 终态:停止轮询并清理本地任务记录
      stopTimer()
      jobId = null
      clearStoredJob()
      if (status === 'failed') {
        // 整体失败:展示后端 error,缺省时兜底中文提示(设计 §4.4)
        ElMessage.error(res.data.error || '识别失败,请重试')
      }
      // succeeded:results/summary/csv_url 已写入 jobState,由模板渲染结果区
    }
  } catch (err) {
    // 404:任务不存在或已失效(后端重启/任务被清理,TC-17)→ 停止轮询并降级提示;
    // 该 404 同时会触发 F3 拦截器的 detail 弹窗,本分支负责组件状态降级
    if (err && err.response && err.response.status === 404) {
      stopTimer()
      jobId = null
      clearStoredJob()
      jobState.value = null
      degraded.value = true
    }
    // 其他错误(网络抖动/后端未启动):F3 拦截器已统一提示,继续轮询等待恢复
  } finally {
    pollInFlight = false
  }
}

// ---------------------------------------------------------------------------
// CSV 下载(succeeded 后可用):csv_url 形如 /result/xxx.csv,
// 线上通过 resolveAssetUrl 补全后端域名;fetch 取 Blob 后交给 F3 的 downloadCsv 触发下载
// ---------------------------------------------------------------------------
async function onDownloadCsv() {
  const rawCsvUrl = jobState.value && jobState.value.csv_url
  if (!rawCsvUrl) {
    ElMessage.warning('暂无 CSV 文件可下载')
    return
  }
  const csvUrl = resolveAssetUrl(rawCsvUrl)
  try {
    const resp = await fetch(csvUrl)
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const blob = await resp.blob()
    downloadCsv(blob, csvUrl.split('/').pop() || 'batch_result.csv')
  } catch (err) {
    ElMessage.error('CSV 下载失败,请重试')
  }
}

// ---------------------------------------------------------------------------
// 生命周期
// ---------------------------------------------------------------------------
onMounted(() => {
  // 页面刷新后内存中的 job_id 与轮询定时器均已丢失:
  // 若上一页面生命周期存在进行中的批量任务(sessionStorage 有记录),
  // 按 TC-16 给出降级提示(进度不可见,已完成图片结果可在历史记录查看)
  if (sessionStorage.getItem(BATCH_JOB_KEY)) {
    sessionStorage.removeItem(BATCH_JOB_KEY)
    degraded.value = true
  }
})

onBeforeUnmount(() => {
  // 组件卸载:清理轮询定时器,并标记 disposed,避免卸载后仍更新状态(TC-15)
  disposed = true
  stopTimer()
})
</script>

<style scoped>
/* 顶部间距:卡片/提示之间的统一间隔 */
.mb12 {
  margin-bottom: 12px;
}

/* 选择区操作行:双入口按钮 + 数量统计 + 提交/清空 */
.pick-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}

.count-text {
  color: #606266;
  font-size: 13px;
}

/* 占位伸缩,把提交/清空按钮推到行尾 */
.spacer {
  flex: 1;
}

/* 隐藏的文件夹选择输入框(由"选择文件夹"按钮触发 click) */
.hidden-input {
  display: none;
}

/* 进度条下方的当前文件名提示行 */
.progress-text {
  margin-top: 10px;
  color: #606266;
  font-size: 13px;
}
</style>
