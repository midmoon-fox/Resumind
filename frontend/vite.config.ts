import { defineConfig, type ProxyOptions } from 'vite';
import vue from '@vitejs/plugin-vue';
import Components from 'unplugin-vue-components/vite';
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers';
const backend = 'https://localhost:8443';
const proxy: ProxyOptions = {
  target: backend,
  changeOrigin: true,
  secure: false, // Accept the local backend's development certificate in the Vite proxy only.
};

export default defineConfig({
  plugins: [vue(), Components({ resolvers: [ElementPlusResolver()], dts: 'src/components.d.ts' })],
  optimizeDeps: {
    // Auto-imported Element Plus dependencies must be ready before lazy routes open.
    include: [
      'element-plus/es',
      ...[
        'base', 'button', 'cascader', 'checkbox', 'collapse', 'collapse-item',
        'config-provider', 'date-picker', 'dialog', 'input', 'input-number',
        'message', 'message-box', 'option', 'select', 'slider', 'steps', 'step', 'upload',
      ].map((component) => `element-plus/es/components/${component}/style/css`),
    ],
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: { '/api': proxy, '/internal/files': proxy },
  },
});
