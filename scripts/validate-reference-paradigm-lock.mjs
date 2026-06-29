#!/usr/bin/env node
import { spawnSync } from 'node:child_process';

const args = ['-m', 'validator.reference_paradigm_lock', ...process.argv.slice(2)];
const command = process.env.PYTHON || 'python';
const result = spawnSync(command, args, { stdio: 'inherit' });
process.exit(result.status ?? 1);
