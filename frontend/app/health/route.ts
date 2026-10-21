export const dynamic = 'force-dynamic';

export function GET() {
  return Response.json({ status: 'healthy' }, { headers: { 'Cache-Control': 'no-store' } });
}
