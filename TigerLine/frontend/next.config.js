/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Enable static export for PythonAnywhere deployment
  output: 'export',
  // Disable image optimization for static export
  images: {
    unoptimized: true,
  },
  // Remove rewrites() - not needed for static export
  // API calls will go directly to PythonAnywhere backend URL via environment variable
};

module.exports = nextConfig;

