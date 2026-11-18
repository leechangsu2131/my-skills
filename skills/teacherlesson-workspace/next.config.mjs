// 중앙 .env (OneDrive\96. 인증\.env) 로드 — skills/_shared/skill_env.js
import { createRequire } from 'module';
createRequire(import.meta.url)('../_shared/skill_env.js').loadEnv('teacherlesson-workspace');

process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Config options go here
};

export default nextConfig;
