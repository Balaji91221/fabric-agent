/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The browser never sees the agent API key. All calls go through the route
  // handlers in app/api, which add the key server-side.
  env: {},
};
export default nextConfig;
