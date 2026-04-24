/** @type {import('next').NextConfig} */
const nextConfig = {
  // Required for production Docker image (see frontend1/Dockerfile.prod)
  output: "standalone",
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
}

export default nextConfig
