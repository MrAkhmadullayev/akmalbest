import { NextResponse } from "next/server";

// Docker healthcheck / nginx upstream tekshiruvi uchun yengil endpoint.
// Nginx `/api/` ni backendga yuboradi, shuning uchun bu manzil `/healthz`.
export const dynamic = "force-dynamic";

export function GET() {
  return NextResponse.json({ status: "ok" });
}
