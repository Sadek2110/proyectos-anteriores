import { readFile, readdir } from 'node:fs/promises';
import { resolve } from 'node:path';
import { Pool } from 'pg';
import { loadConfig } from '../src/config.js';

const config = loadConfig();
if (!config.DATABASE_URL) throw new Error('DATABASE_URL es obligatoria para ejecutar migraciones.');

const pool = new Pool({
  connectionString: config.DATABASE_URL,
  max: 1,
  connectionTimeoutMillis: config.DATABASE_CONNECTION_TIMEOUT_MS,
  application_name: 'asistente-personal-migrations',
});

try {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS schema_migrations (
      name text PRIMARY KEY,
      applied_at timestamptz NOT NULL DEFAULT now()
    )
  `);

  const directory = resolve(process.cwd(), 'db', 'migrations');
  const files = (await readdir(directory)).filter((file) => file.endsWith('.sql')).sort();

  for (const file of files) {
    const alreadyApplied = await pool.query<{ name: string }>(
      'SELECT name FROM schema_migrations WHERE name = $1',
      [file],
    );
    if (alreadyApplied.rowCount) {
      console.log(`skip ${file}`);
      continue;
    }

    const sql = await readFile(resolve(directory, file), 'utf8');
    const client = await pool.connect();
    try {
      await client.query('BEGIN');
      await client.query(sql);
      await client.query('INSERT INTO schema_migrations (name) VALUES ($1)', [file]);
      await client.query('COMMIT');
      console.log(`applied ${file}`);
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }
} finally {
  await pool.end();
}
