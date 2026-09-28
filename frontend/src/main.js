import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import App from './App.vue'

// 应用入口:创建应用、注册 Element Plus(中文 locale)并挂载根组件
const app = createApp(App)
app.use(ElementPlus, { locale: zhCn })
app.mount('#app')
