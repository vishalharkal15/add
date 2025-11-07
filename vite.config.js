import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import fs from 'fs';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0', // allow access via LAN IP
    port: 5173,
    // Only use HTTPS if certificates exist (for local dev)
    https: fs.existsSync(path.resolve(__dirname, '{Yout IP}-key.pem')) && 
           fs.existsSync(path.resolve(__dirname, '{Yout IP}.pem'))
      ? {
          key: fs.readFileSync(path.resolve(__dirname, '{Yout IP}-key.pem')),
          cert: fs.readFileSync(path.resolve(__dirname, '{Yout IP}.pem'))
        }
      : false
  }
});
