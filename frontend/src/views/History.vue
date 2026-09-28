<!--
  F6 历史记录视图(History.vue)

  职责(doc/tasks/history.md 任务 1~5;doc/high-level-design.md §3.3 F6、§4.2(3)、§5.4):
    1. 分页列表:el-table + el-image 缩略图(原图 + 固定小尺寸)+ el-pagination(默认每页 10 条);
    2. 删除单条:el-popconfirm 二次确认后调 F3 deleteHistory(id),成功后刷新当前页,
       删空当前页时回退上一页;
    3. 清空全部:el-popconfirm 二次确认后调 F3 clearHistory(),成功后列表为空;
    4. 导出 CSV:调 F3 exportHistory() 后 downloadCsv 下载(history_YYYYmmdd_HHMMSS.csv),
       历史为空时展示后端返回的中文提示("暂无历史记录可导出");
    5. 空状态与页签刷新:无数据显示 el-empty;每次组件挂载 / 重新激活(进入页签)重新加载第一页。

  依赖:F3(frontend/src/api/index.js)的 getHistory / deleteHistory / clearHistory /
        exportHistory / downloadCsv。错误提示统一由 F3 拦截器弹出,本组件仅在
        blob 错误体无法被拦截器解析时兜底展示。
  说明:不引入 Pinia,全部为组件内部状态;缩略图直接加载后端返回的 image_url(原图),
        由前端按固定小尺寸缩放显示;删除/清空会连带删除后端 uploads/ 图片文件,前端只调用接口。
-->
<template>
  <div class="history-container">
    <!-- 顶部操作栏:导出历史 / 清空全部 -->
    <div class="toolbar">
      <el-button type="primary" :disabled="loading" @click="handleExport">
        导出历史
      </el-button>
      <el-popconfirm
        title="确定清空全部历史记录吗?此操作不可恢复。"
        confirm-button-text="清空"
        cancel-button-text="取消"
        width="280"
        @confirm="handleClear"
      >
        <template #reference>
          <el-button type="danger" :disabled="loading || total === 0">
            清空全部
          </el-button>
        </template>
      </el-popconfirm>
    </div>

    <!-- 空状态:无数据时展示 el-empty -->
    <el-empty
      v-if="!loading && total === 0"
      description="暂无历史记录,快去识别一张图片吧"
    />

    <!-- 历史记录列表(记录按时间倒序,最新在前) -->
    <el-table v-else v-loading="loading" :data="items" stripe style="width: 100%">
      <el-table-column label="缩略图" width="110" align="center">
        <template #default="{ row }">
          <!-- 原图加载 + 固定小尺寸预览,点击可放大查看 -->
          <el-image
            class="thumbnail"
            :src="resolveAssetUrl(row.image_url)"
            :preview-src-list="[resolveAssetUrl(row.image_url)]"
            preview-teleported
            fit="cover"
            lazy
          >
            <template #error>
              <div class="image-error">图片缺失</div>
            </template>
          </el-image>
        </template>
      </el-table-column>
      <el-table-column
        prop="filename"
        label="文件名"
        min-width="180"
        show-overflow-tooltip
      />
      <el-table-column label="预测类别" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="labelTagType(row.predict_label)" disable-transitions>
            {{ row.predict_label }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="置信度" width="110" align="center">
        <template #default="{ row }">
          {{ formatConfidence(row.confidence) }}
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="识别时间" width="180" />
      <el-table-column label="操作" width="90" align="center" fixed="right">
        <template #default="{ row }">
          <el-popconfirm
            title="确定删除这条记录吗?"
            confirm-button-text="删除"
            cancel-button-text="取消"
            width="220"
            @confirm="handleDelete(row)"
          >
            <template #reference>
              <el-button type="danger" link size="small">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页:默认每页 10 条,与列表联动刷新 -->
    <div v-if="total > 0" class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        background
      />
    </div>
  </div>
</template>

<script setup>
/**
 * F6 历史记录视图:分页列表 / 删除单条 / 清空全部 / 导出 CSV / 空状态与页签刷新。
 *
 * 契约依据:
 *  - doc/tasks/history.md 任务 1~5;
 *  - doc/high-level-design.md §3.3(F6)、§4.2(3)、§5.4、§6(历史为空导出提示);
 *  - F3 getHistory 返回 { total, page, page_size, items },items 元素字段:
 *    id / filename / predict_label / confidence(0~1) / probs / image_url / created_at。
 */
import { ref, watch, onMounted, onActivated } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getHistory,
  deleteHistory,
  clearHistory,
  exportHistory,
  downloadCsv,
  resolveAssetUrl,
} from '../api/index.js'

// ------------------------------ 列表与分页状态 ------------------------------
const items = ref([]) // 当前页记录列表(后端按时间倒序返回)
const total = ref(0) // 历史记录总数
const page = ref(1) // 当前页码(从 1 开始)
const pageSize = ref(10) // 每页条数,默认 10
const loading = ref(false) // 列表加载中

let loadSeq = 0 // 请求序号,丢弃过期响应,避免快速翻页时旧结果覆盖新结果

// ------------------------------ 数据加载 ------------------------------
/** 按当前 page / pageSize 加载历史记录(后端倒序,最新在前)。 */
async function loadHistory() {
  const seq = ++loadSeq
  loading.value = true
  try {
    const res = await getHistory(page.value, pageSize.value)
    if (seq !== loadSeq) return // 已有更新的请求,丢弃本次过期结果
    const data = res.data
    total.value = data.total ?? 0
    items.value = data.items ?? []
    // 数据减少后当前页可能超出总页数(如后端数据被清空),回退到最后一页
    const maxPage = Math.max(1, Math.ceil(total.value / pageSize.value))
    if (page.value > maxPage) page.value = maxPage // 由 watch(page) 触发重新加载
  } catch (error) {
    // 失败提示已由 F3 拦截器统一弹出,此处仅清空展示避免残留旧数据
    if (seq !== loadSeq) return
    items.value = []
    total.value = 0
  } finally {
    if (seq === loadSeq) loading.value = false
  }
}

/** 回到第一页并重新加载(进入页签刷新用)。 */
function reloadFirstPage() {
  if (page.value !== 1) {
    page.value = 1 // 由 watch(page) 触发加载
  } else {
    loadHistory()
  }
}

// ------------------------------ 分页联动 ------------------------------
// 页码变化统一重新加载:覆盖用户翻页、删空当前页回退上一页、清空后回到第一页等场景
watch(page, () => {
  loadHistory()
})

// 每页条数变化:回到第一页重新加载(本就在第一页时页码不变,需手动加载)
watch(pageSize, () => {
  if (page.value !== 1) {
    page.value = 1
  } else {
    loadHistory()
  }
})

// ------------------------------ 删除 / 清空 ------------------------------
/** 删除单条(el-popconfirm 确认后回调):成功后刷新当前页,删空当前页则回退上一页。 */
async function handleDelete(row) {
  try {
    await deleteHistory(row.id)
    ElMessage.success('删除成功')
    if (items.value.length === 1 && page.value > 1) {
      page.value -= 1 // 删空当前页,回退上一页(由 watch(page) 触发加载)
    } else {
      await loadHistory()
    }
  } catch (error) {
    // 失败提示已由 F3 拦截器统一弹出
  }
}

/** 清空全部(el-popconfirm 确认后回调):成功后回到第一页,列表为空。 */
async function handleClear() {
  try {
    await clearHistory()
    ElMessage.success('已清空全部历史记录')
    reloadFirstPage()
  } catch (error) {
    // 失败提示已由 F3 拦截器统一弹出
  }
}

// ------------------------------ 导出 CSV ------------------------------
/** 从响应 blob 中解析后端约定的 JSON 错误体 {"detail": "中文提示"}。 */
async function readBlobDetail(blob) {
  if (!blob || typeof blob.text !== 'function') return ''
  try {
    const text = await blob.text()
    const parsed = JSON.parse(text)
    return typeof parsed?.detail === 'string' && parsed.detail ? parsed.detail : ''
  } catch {
    return '' // 非 JSON(正常 CSV 内容),忽略
  }
}

/** 生成 history_YYYYmmdd_HHMMSS.csv 风格文件名。 */
function buildCsvFilename(date = new Date()) {
  const pad2 = (n) => String(n).padStart(2, '0')
  const stamp =
    `${date.getFullYear()}${pad2(date.getMonth() + 1)}${pad2(date.getDate())}` +
    `_${pad2(date.getHours())}${pad2(date.getMinutes())}${pad2(date.getSeconds())}`
  return `history_${stamp}.csv`
}

/** 导出历史:调 F3 exportHistory 后 downloadCsv 下载;历史为空时展示后端中文提示。 */
async function handleExport() {
  try {
    const res = await exportHistory()
    const blob = res.data
    // 后端在历史为空时可能返回 JSON 提示体(而非 CSV),识别后展示提示且不触发下载
    const detail = await readBlobDetail(blob)
    if (detail) {
      ElMessage.error(detail)
      return
    }
    downloadCsv(blob, buildCsvFilename())
    ElMessage.success('历史记录已导出')
  } catch (error) {
    // 请求失败时 F3 拦截器已弹提示;若后端以 blob 形式返回错误体,
    // 拦截器无法解析 detail,此处兜底解析并展示后端中文提示
    const detail = await readBlobDetail(error?.response?.data)
    if (detail) ElMessage.error(detail)
  }
}

// ------------------------------ 展示格式化 ------------------------------
/** 置信度(0~1)转百分比字符串,保留 1 位小数,如 0.924 → '92.4%'。 */
function formatConfidence(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) return '-'
  return `${(value * 100).toFixed(1)}%`
}

/** 预测类别对应的 el-tag 颜色:猫 → 绿,狗 → 橙,其余灰。 */
function labelTagType(label) {
  if (label === '猫') return 'success'
  if (label === '狗') return 'warning'
  return 'info'
}

// ------------------------------ 页签刷新 ------------------------------
// 每次进入本页签重新加载第一页:
//  - 首次挂载(onMounted)加载第一页;
//  - 若 F2 以 <keep-alive> 包裹页签,切回本页签时 onActivated 再次加载第一页;
//  - 若 F2 使用 el-tabs 默认渲染(无 keep-alive),切换页签不会触发上述钩子,
//    请 F2 通过模板 ref 调用 reload()(defineExpose 已暴露)实现页签切换刷新。
onMounted(reloadFirstPage)
onActivated(reloadFirstPage)

// 供 F2(父组件)在切换页签时调用:回到第一页并重新加载
defineExpose({ reload: reloadFirstPage })
</script>

<style scoped>
.history-container {
  padding: 16px;
  min-height: 400px;
}

.toolbar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

/* 缩略图:原图按固定小尺寸(64×64)缩放显示 */
.thumbnail {
  display: block;
  width: 64px;
  height: 64px;
  border-radius: 4px;
}

/* el-image 加载失败占位(图片文件已被删除等场景) */
.image-error {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  color: #909399;
  font-size: 12px;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
