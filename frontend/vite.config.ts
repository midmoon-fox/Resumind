import { defineConfig, loadEnv, type ProxyOptions } from 'vite';
import vue from '@vitejs/plugin-vue';
import Components from 'unplugin-vue-components/vite';
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers';
function backendProxy(mode: string) {
  const { RESUMIND_DEV_BACKEND_URL } = loadEnv(mode, process.cwd(), 'RESUMIND_DEV_');
  const proxy: ProxyOptions = {
    target: RESUMIND_DEV_BACKEND_URL || 'https://localhost:8443',
    changeOrigin: true,
    secure: false, // Accept the local backend's development certificate in the Vite proxy only.
  };
  return { '/api': proxy, '/internal/files': proxy };
}

export default defineConfig(({ mode }) => ({
  base: process.env.VITE_BASE_PATH || '/',
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
    proxy: backendProxy(mode),
  },
}));
