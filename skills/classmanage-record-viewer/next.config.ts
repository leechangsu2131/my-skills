import type { NextConfig } from "next";
// 중앙 .env (OneDrive\96. 인증\.env) 로드 — skills/_shared/skill_env.js
// eslint-disable-next-line @typescript-eslint/no-require-imports
require("../_shared/skill_env.js").loadEnv("classmanage-record-viewer");

process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';

const nextConfig: NextConfig = {
  /* config options here */
};

export default nextConfig;
