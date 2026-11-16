import { buildApp } from './app.js';
import { loadConfig } from './config.js';
import { createRuntimeServices } from './runtime.js';

try {
  const config = loadConfig();
  const runtime = await createRuntimeServices(config);
  const app = buildApp(config, {
    persistence: runtime.persistence,
    coordination: runtime.coordination,
    approvals: runtime.approvals,
    postgresConfigured: runtime.postgresConfigured,
    redisConfigured: runtime.redisConfigured,
  });
  const shutdown = async () => {
    await app.close();
    await runtime.close();
  };
  process.once('SIGINT', shutdown);
  process.once('SIGTERM', shutdown);
  await app.listen({ host: config.HOST, port: config.PORT });
} catch (error) {
  console.error(error);
  process.exit(1);
}

