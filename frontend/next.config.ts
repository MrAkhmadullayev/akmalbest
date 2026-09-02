import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /**
   * Docker uchun: kerakli node_modules'ni o'zi trace qilib `.next/standalone`
   * ichiga yig'adi. Natijada image ~1GB emas, ~200MB bo'ladi.
   */
  output: "standalone",

  // Server versiyasini oshkor qilmaymiz
  poweredByHeader: false,

  // Nginx ham gzip qiladi; ikki marta siqish shart emas
  compress: false,

  reactStrictMode: true,

  // Next 16 build vaqtida ESLint ishlatmaydi — lint CI'da alohida bosqich.
  // TypeScript xatolari esa build'ni TO'XTATISHI kerak: buzuq tiplar bilan
  // prod'ga chiqmaymiz.
  typescript: { ignoreBuildErrors: false },

  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
