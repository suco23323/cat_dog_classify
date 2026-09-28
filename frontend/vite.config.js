import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Vite 工程配置:端口 5173,开发期将后端接口与静态资源代理到 FastAPI(8000)
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    // 前端只经同源代理访问后端,后端无需配置 CORS
    proxy: {
      // 业务接口
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      // 上传图片(历史缩略图)
      '/uploads': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      // CSV 结果文件(批量结果 / 历史导出)
      '/result': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
