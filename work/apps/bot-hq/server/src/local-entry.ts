// OPENBOT-OS: the installed default launcher. No provider/autonomous modules imported.
import { serve } from '@hono/node-server';
import { createLocalApp } from './local-app.js';
import { env } from './env.js';

const app = createLocalApp();
const server = serve({ fetch: app.fetch, hostname: '0.0.0.0', port: env.port }, info => {
  console.log(`[OpenBot HQ] local-only interface on port ${info.port}; ALL providers, schedulers, MCP, computer/shell and voice disabled.`);
});
const stop = () => server.close(() => process.exit(0));
process.on('SIGTERM', stop);
process.on('SIGINT', stop);
