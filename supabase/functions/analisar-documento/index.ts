// Retired unsafe legacy endpoint. All processing goes through the authenticated Flask gateway.
// Deploy this replacement to retire an existing function; source changes alone do not affect production.
Deno.serve((_request: Request) => new Response(JSON.stringify({error: "Endpoint legado desativado. Utilize o gateway autenticado."}), {
  status: 410,
  headers: {"Content-Type": "application/json", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
}));
