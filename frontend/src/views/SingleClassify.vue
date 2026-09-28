<!--
  F4 单张识别视图 SingleClassify.vue
  设计依据:doc/high-level-design.md §3.3(F4)、§4.2(1)
  职责:
  1. el-upload(拖拽、手动模式、仅图片)选择图片,只保留最近一次选择的单个文件,el-image 本地预览;
  2. 点击"开始识别"先前端校验(未选图 / 格式 / 大小,F7 工具),不符则本地提示且不发请求;
  3. 校验通过后调用 F3 classify(file),按钮 loading 防重复点击,失败提示由 F3 拦截器统一弹出;
  4. 结果区:预测类别大字 + 置信度百分比 + 猫/狗双 el-progress 概率对比条(高者 success 绿色突出,低者 info 灰色弱化)。
  约定:组件内部状态即可,不引入 Pinia;不自行拼请求地址、不重复实现后端错误提示。
-->
<template>
  <div class="single-classify">
    <!-- 任务 1:上传与预览区 -->
    <el-row :gutter="24">
      <el-col :xs="24" :md="12">
        <!--
          手动上传模式:drag、auto-upload=false、accept 限定图片类型;
          limit=1 保证只保留一个文件,再次选择经 on-exceed 替换为最新文件
        -->
        <el-upload
          ref="uploadRef"
          class="classify-upload"
          drag
          :auto-upload="false"
          :limit="1"
          accept=".jpg,.jpeg,.png,.bmp,image/jpeg,image/png,image/bmp"
          :show-file-list="false"
          :on-change="handleFileChange"
          :on-exceed="handleExceed"
        >
          <div class="upload-tip">
            <div class="upload-icon">🖼️</div>
            <div class="upload-main">将图片拖到此处,或点击选择图片</div>
            <div class="upload-sub">仅支持 jpg / jpeg / png / bmp,单张不超过 10MB</div>
          </div>
        </el-upload>
        <div v-if="selectedFile" class="file-info">
          已选择:{{ selectedFile.name }}({{ formatSize(selectedFile.size) }}),再次选择将替换
        </div>
      </el-col>
      <el-col :xs="24" :md="12">
        <div class="preview-box">
          <el-image v-if="previewUrl" :src="previewUrl" fit="contain" class="preview-image" />
          <span v-else class="preview-placeholder">暂无预览,请先选择图片</span>
        </div>
      </el-col>
    </el-row>

    <!-- 任务 2/3:识别按钮(loading + 禁用,防重复点击) -->
    <div class="action-row">
      <el-button
        type="primary"
        size="large"
        :loading="recognizing"
        :disabled="recognizing"
        @click="handleClassify"
      >
        {{ recognizing ? '识别中,请稍候…' : '开始识别' }}
      </el-button>
    </div>

    <!-- 任务 4:结果区 -->
    <el-card v-if="result" class="result-card" shadow="never">
      <template #header><span>识别结果</span></template>
      <div class="result-main">
        <div class="predict-label">{{ result.predict_label }}</div>
        <div class="confidence">置信度:{{ format_percent(result.confidence) || '-' }}</div>
      </div>
      <!--
        概率对比条:prob*100 转百分比;高概率侧 status=success(绿色),
        低概率侧 status='info'(el-progress 无 info 状态,配合 --el-color-info 灰色令牌实现 info 语义);
        默认插槽提供百分比文本,避免 status 生效时默认文本被图标替换
      -->
      <div class="prob-row">
        <span class="prob-name">猫</span>
        <el-progress
          class="prob-bar"
          :percentage="catPercent"
          :status="catIsHigh ? 'success' : 'info'"
          :color="catIsHigh ? undefined : 'var(--el-color-info)'"
          :stroke-width="16"
        >
          <span class="prob-text">{{ format_percent(result.probs?.cat) || '-' }}</span>
        </el-progress>
      </div>
      <div class="prob-row">
        <span class="prob-name">狗</span>
        <el-progress
          class="prob-bar"
          :percentage="dogPercent"
          :status="catIsHigh ? 'info' : 'success'"
          :color="catIsHigh ? 'var(--el-color-info)' : undefined"
          :stroke-width="16"
        >
          <span class="prob-text">{{ format_percent(result.probs?.dog) || '-' }}</span>
        </el-progress>
      </div>
      <div class="result-meta">文件名:{{ result.filename }}</div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { classify } from '../api/index.js'
import { is_supported, check_size, format_percent } from '../utils/collect.js'

// ---------------------------------------------------------------------------
// 上传与预览状态:只保留最近一次选择的单个文件
// ---------------------------------------------------------------------------
const uploadRef = ref(null)    // el-upload 组件实例(超出 limit 时手动替换文件)
const selectedFile = ref(null) // 当前选中的图片文件(File)
const previewUrl = ref('')     // 本地预览地址(blob: URL)

// 选择新文件:替换旧文件并刷新预览(仅记录最近一次选择)
const handleFileChange = (uploadFile) => {
  if (!uploadFile || !uploadFile.raw) return
  setSelectedFile(uploadFile.raw)
}

// 超出 limit(1)再次选择:清空旧文件,把新选择的文件重新放入;
// handleStart 会触发 on-change,复用 handleFileChange 更新状态
const handleExceed = (files) => {
  if (!files || files.length === 0) return
  uploadRef.value?.clearFiles()
  uploadRef.value?.handleStart(files[0])
}

// 记录当前文件并更新预览;释放旧的 blob URL,避免内存泄漏
const setSelectedFile = (file) => {
  selectedFile.value = file
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = URL.createObjectURL(file)
}

onBeforeUnmount(() => {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
})

// ---------------------------------------------------------------------------
// 识别流程:前端校验 → F3 classify → 结果渲染
// ---------------------------------------------------------------------------
const recognizing = ref(false) // 识别中标记:按钮 loading + 防重复点击
const result = ref(null)       // 单张识别结果(字段与 classify 响应一致)

const handleClassify = async () => {
  if (recognizing.value) return // 防重复点击(与按钮 disabled 双保险)

  // 校验 1:未选图 → 本地提示,不发请求(TC-04)
  if (!selectedFile.value) {
    ElMessage('请先上传图片')
    return
  }

  // 校验 2:格式/大小不符 → 本地提示,不发请求(TC-03);判断逻辑复用 F7 工具
  if (!is_supported(selectedFile.value.name) || !check_size(selectedFile.value)) {
    ElMessage('仅支持 jpg/jpeg/png/bmp 图片,单张不超过 10MB')
    return
  }

  const file = selectedFile.value
  recognizing.value = true
  try {
    const { data } = await classify(file)
    // 识别期间若用户已更换图片,丢弃本次过期结果,保证结果与当前预览一致(TC-05)
    result.value = selectedFile.value === file ? data : null
  } catch {
    // 失败提示已由 F3 拦截器统一弹出;清除旧结果,避免与当前预览不符造成误读
    result.value = null
  } finally {
    recognizing.value = false
  }
}

// ---------------------------------------------------------------------------
// 结果区派生数据:概率 → 百分比(prob*100)与高/低概率侧样式
// ---------------------------------------------------------------------------
// 概率(0~1)→ 百分比(0~100,保留 1 位小数);非法值退化为 0
const toPercent = (p) => {
  const n = Number(p)
  return Number.isFinite(n) ? Number((n * 100).toFixed(1)) : 0
}
const catPercent = computed(() => toPercent(result.value?.probs?.cat))
const dogPercent = computed(() => toPercent(result.value?.probs?.dog))
// 高概率侧用 success(绿)突出;概率相等时猫侧视为高侧(两者视觉一致,无歧义)
const catIsHigh = computed(() => catPercent.value >= dogPercent.value)

// 文件大小 → 可读文本(仅本地展示用)
const formatSize = (bytes) => {
  if (typeof bytes !== 'number' || !Number.isFinite(bytes)) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
</script>

<style scoped>
.single-classify {
  max-width: 1000px;
  margin: 0 auto;
  padding: 8px 0;
}

/* 上传区:与预览区同高,内部提示居中 */
.classify-upload {
  width: 100%;
}
.classify-upload :deep(.el-upload) {
  width: 100%;
}
.classify-upload :deep(.el-upload-dragger) {
  width: 100%;
  height: 300px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.upload-tip {
  text-align: center;
}
.upload-icon {
  font-size: 40px;
  line-height: 1;
  margin-bottom: 12px;
}
.upload-main {
  font-size: 15px;
  color: #303133;
  margin-bottom: 6px;
}
.upload-sub {
  font-size: 12px;
  color: #909399;
}
.file-info {
  margin-top: 10px;
  font-size: 13px;
  color: #606266;
}

/* 预览区:与上传区同高 */
.preview-box {
  height: 300px;
  border: 1px dashed #dcdfe6;
  border-radius: 6px;
  background: #fafafa;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.preview-image {
  width: 100%;
  height: 100%;
}
.preview-placeholder {
  color: #909399;
  font-size: 14px;
}

/* 操作行 */
.action-row {
  margin: 24px 0 8px;
  text-align: center;
}

/* 结果区 */
.result-card {
  margin-top: 8px;
}
.result-main {
  text-align: center;
  margin-bottom: 20px;
}
.predict-label {
  font-size: 44px;
  font-weight: 700;
  line-height: 1.2;
  color: #409eff;
}
.confidence {
  margin-top: 8px;
  font-size: 15px;
  color: #606266;
}

/* 猫/狗概率对比条 */
.prob-row {
  display: flex;
  align-items: center;
  margin-bottom: 14px;
}
.prob-name {
  width: 36px;
  font-size: 14px;
  color: #303133;
}
.prob-bar {
  flex: 1;
}
.prob-text {
  font-size: 13px;
  color: #606266;
}
.result-meta {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
  text-align: center;
}
</style>
