<!--
  F2 整体布局(App.vue)

  职责(doc/tasks/app.md 任务 1~3;doc/high-level-design.md §3.3(F2)、§4.2(4)、§6):
    1. 三页签布局:el-tabs 三个页签——单张识别(F4)/批量识别(F5)/历史记录(F6),
       页首标题"猫狗分类识别";
    2. 后端就绪探测:页面挂载(onMounted)时调用 F3 health();失败时顶部显示
       el-alert"后端服务暂不可用,请稍后重试"(提供"重试"按钮再次探测,
       不阻塞页面操作),成功则隐藏(TC-13);
    3. 历史页签刷新联动:切换到"历史记录"页签时,经模板 ref 调用 F6 暴露的
       reload() 回到第一页重新加载(不采用 v-if 重挂载,避免批量识别进行中
       切页签丢失轮询进度;F6 自身的 onMounted 负责首次挂载加载)。

  依赖:F3(frontend/src/api/index.js)的 health;三个视图组件为默认导出,
       History.vue 额外 defineExpose({ reload })。
  约定:只做布局与就绪探测,不包含业务逻辑;组件内部状态,不引入 Pinia;
        错误提示统一由 F3 拦截器弹出,此处仅维护 alert 的显隐状态。
-->
<template>
  <div class="app-root">
    <!-- 白底卡片容器:最大宽度居中,承载标题 / 健康提示 / 三页签 -->
    <div class="app-container">
      <!-- 页首标题 -->
      <header class="app-header">
        <h1 class="app-title">猫狗分类识别</h1>
      </header>

      <!--
        后端就绪探测提示:仅在探测失败时显示;
        "重试"按钮再次调 F3 health(),成功后隐藏提示(TC-13);
        v-if 仅控制提示条,不影响下方页签与页面操作。
      -->
      <el-alert
        v-if="backendDown"
        class="health-alert"
        title="后端服务暂不可用,请稍后重试"
        type="warning"
        show-icon
        :closable="false"
      >
        <el-button size="small" :loading="checking" @click="checkHealth">
          重试
        </el-button>
      </el-alert>

      <!-- 三页签:单张识别 / 批量识别 / 历史记录 -->
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="单张识别" name="single">
          <SingleClassify />
        </el-tab-pane>
        <el-tab-pane label="批量识别" name="batch">
          <BatchClassify />
        </el-tab-pane>
        <el-tab-pane label="历史记录" name="history">
          <History ref="historyRef" />
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
/**
 * F2 整体布局:三页签 / 后端就绪探测 / 历史页签刷新联动。
 *
 * 契约依据:
 *  - doc/tasks/app.md 任务 1~3;
 *  - doc/high-level-design.md §3.3(F2)、§4.2(4) 启动流程、§6(后端未启动提示);
 *  - F3 health() 成功返回 { status: "ok" },失败统一由拦截器弹中文提示并 reject。
 */
import { ref, onMounted } from 'vue'
import { health } from './api/index.js'
import SingleClassify from './views/SingleClassify.vue'
import BatchClassify from './views/BatchClassify.vue'
import History from './views/History.vue'

const activeTab = ref('single') // 当前页签名,默认停在"单张识别"
const backendDown = ref(false) // 后端就绪状态:true 表示探测失败,显示警告条
const checking = ref(false) // 探测进行中(重试按钮 loading,防重复点击)
const historyRef = ref(null) // History(F6)组件实例,供页签切换时调用其 reload()

/** 后端就绪探测:调 F3 health(),失败显示警告条、成功隐藏(TC-13)。 */
async function checkHealth() {
  checking.value = true
  try {
    await health()
    backendDown.value = false // 探测成功,隐藏提示
  } catch (error) {
    // 失败提示已由 F3 拦截器统一弹出,此处仅维持警告条显示
    backendDown.value = true
  } finally {
    checking.value = false
  }
}

/** 页签切换(activeName 实际变化时触发):切到"历史记录"时通知 F6 刷新第一页。 */
function handleTabChange(name) {
  if (name === 'history') {
    // F6 经 defineExpose 暴露 reload():回到第一页并重新加载(最新记录在前)
    historyRef.value?.reload()
  }
}

// 页面挂载时探测后端就绪状态(§4.2(4) 启动流程:进入页面即探测 /api/health)
onMounted(checkHealth)
</script>

<style scoped>
/* 页面底色与整体留白 */
.app-root {
  min-height: 100vh;
  box-sizing: border-box;
  padding: 24px 16px 40px;
  background: #f5f7fa;
}

/* 白底卡片容器:最大宽度居中,阴影轻量 */
.app-container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 20px 24px 24px;
  background: #ffffff;
  border-radius: 10px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

/* 页首标题:居中、主色深灰 */
.app-header {
  margin-bottom: 8px;
  text-align: center;
}

.app-title {
  margin: 0;
  font-size: 26px;
  font-weight: 600;
  color: #303133;
}

/* 后端未就绪警告条:与页签间留出间距 */
.health-alert {
  margin-bottom: 12px;
}
</style>
