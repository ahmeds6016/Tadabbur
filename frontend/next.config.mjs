/** @type {import('next').NextConfig} */
const nextConfig = {
  // Ensure service worker can be served with correct headers
  async headers() {
    return [
      {
        source: '/sw.js',
        headers: [
          {
            key: 'Service-Worker-Allowed',
            value: '/',
          },
        ],
      },
    ];
  },
};

export default nextConfig;
