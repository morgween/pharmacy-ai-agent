export async function POST(req: Request) {
  const payload = await req.json();
  const apiBaseUrl = process.env.API_BASE_URL ?? 'http://localhost:8000';

  const backendResponse = await fetch(`${apiBaseUrl}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  const body = await backendResponse.text();
  return new Response(body, {
    status: backendResponse.status,
    headers: { 'Content-Type': backendResponse.headers.get('Content-Type') ?? 'application/json' },
  });
}
