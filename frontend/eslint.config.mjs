import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  {
    rules: {
      // O'zbek tilida apostrof — bu harf ("o'", "g'", "to'lash"). Har bir
      // matndagi ' ni &apos; ga aylantirish kodni o'qib bo'lmas holga
      // keltiradi, xavfsizlikka esa hech qanday ta'siri yo'q (JSX matni
      // baribir escape qilinadi).
      "react/no-unescaped-entities": "off",

      // MVP bosqichi: API javoblari va xato handlerlarida `any` ko'p.
      // Bu build'ni to'xtatadigan xato emas — `types/` dagi interfeyslarga
      // asta-sekin o'tkaziladi, shuning uchun ogohlantirish darajasida.
      "@typescript-eslint/no-explicit-any": "warn",

      // React Compiler'ning yangi qoidasi. Bizdagi ikkita holat —
      // hidratsiya uchun `mounted` bayrog'i va boshlang'ich `loadUser()` —
      // ikkalasi ham standart pattern. Ko'rinib tursin, lekin CI'ni
      // yiqitmasin. `react-hooks/refs` esa ATAYLAB error bo'lib qoladi,
      // chunki u haqiqiy correctness xatosini ushlaydi.
      "react-hooks/set-state-in-effect": "warn",
    },
  },
]);

export default eslintConfig;
