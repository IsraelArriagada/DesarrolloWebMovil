using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using CraftBeer.Shared;
using Oracle.ManagedDataAccess.Client;

var b = WebApplication.CreateBuilder(args);
var db = new Db(Conn.For("payments", "DB_PAYMENTS_PWD"));
b.AddCommon(db, [Secrets.Get("SVC_GRAPHQL_KEY")]); // PaymentsService
var app = b.Build();
app.UseCommon();

var ordersUrl = Environment.GetEnvironmentVariable("ORDERS_URL") ?? "http://orders:8080";
var invUrl = Environment.GetEnvironmentVariable("INVENTORY_URL") ?? "http://inventory:8080";
var delUrl = Environment.GetEnvironmentVariable("DELIVERY_URL") ?? "http://delivery:8080";
var notUrl = Environment.GetEnvironmentVariable("NOTIFICATIONS_URL") ?? "http://notifications:8080";
var cliUrl = Environment.GetEnvironmentVariable("CLIENTS_URL") ?? "http://clients:8080";
var myKey = Secrets.Get("SVC_PAYMENTS_KEY");
var webhookSecret = Secrets.Get("WEBHOOK_SECRET");
var http = app.Services.GetRequiredService<IHttpClientFactory>();
var json = new JsonSerializerOptions(JsonSerializerDefaults.Web);

HttpRequestMessage Req(HttpMethod m, string url, HttpContext ctx, object? body = null)
{
    var r = new HttpRequestMessage(m, url);
    r.Headers.Add("X-Service-Key", myKey);
    if (ctx.Items["X-Correlation-Id"] is string cid) r.Headers.Add("X-Correlation-Id", cid);
    if (body != null) r.Content = JsonContent.Create(body);
    return r;
}

// Adaptador del proveedor de pago. "fake" = modo de prueba sin red externa.
// Para Servipag/Webpay real se reemplaza esta función (misma firma) sin tocar el resto.
Task<string> CreateCheckout(string provider, long orderId, long amount) =>
    Task.FromResult(provider == "fake" ? $"fake-checkout-{orderId}-{amount}" : throw new NotSupportedException(provider));

static string Hmac(string secret, string body)
{
    using var h = new HMACSHA256(Encoding.UTF8.GetBytes(secret));
    return Convert.ToHexString(h.ComputeHash(Encoding.UTF8.GetBytes(body))).ToLower();
}

app.MapPost("/payments", async (HttpContext ctx, PayReq p) =>
{
    if (!ctx.InRole("CLIENTE") || ctx.UserId() is not { } cid) return Results.Json(new { error = "Acceso denegado" }, statusCode: 403);
    HttpResponseMessage r;
    try { r = await http.CreateClient().SendAsync(Req(HttpMethod.Get, $"{ordersUrl}/orders/{p.IdPedido}", ctx)); }
    catch { return Results.Json(new { error = "Pedidos no disponible" }, statusCode: 503); }
    if (!r.IsSuccessStatusCode) return Results.NotFound();
    var o = (await r.Content.ReadFromJsonAsync<OrderDto>(json))!;
    if (o.IdCliente != cid) return Results.NotFound();
    if (o.Estado != "PENDIENTE_PAGO") return Results.Conflict(new { error = "Pedido no está pendiente de pago" });
    // El monto lo define el servidor (total del pedido), nunca el frontend.
    var checkout = await CreateCheckout(Environment.GetEnvironmentVariable("PAYMENT_PROVIDER") ?? "fake", o.Id, o.Total);
    await db.ExecAsync("INSERT INTO PAGO(ID_PEDIDO,REF_PEDIDO,MONTO,METODO) VALUES(:p,:r,:m,:me)",
        ("p", o.Id), ("r", o.Referencia), ("m", o.Total), ("me", p.Metodo ?? "SERVIPAG"));
    return Results.Ok(new { idPedido = o.Id, monto = o.Total, checkoutId = checkout });
});

// Webhook del proveedor: firma HMAC, idempotente, monto verificado contra el pedido.
app.MapPost("/payments/webhook", async (HttpContext ctx) =>
{
    using var sr = new StreamReader(ctx.Request.Body);
    var body = await sr.ReadToEndAsync();
    var sig = ctx.Request.Headers["X-Signature"].FirstOrDefault() ?? "";
    var expected = Hmac(webhookSecret, body);
    if (!CryptographicOperations.FixedTimeEquals(Encoding.UTF8.GetBytes(sig), Encoding.UTF8.GetBytes(expected)))
        return Results.Json(new { error = "Firma inválida" }, statusCode: 401);
    var w = JsonSerializer.Deserialize<Webhook>(body, json)!;
    if (w.Status != "APPROVED") return Results.Ok(new { ignorado = true });

    var cl = http.CreateClient();
    var r = await cl.SendAsync(Req(HttpMethod.Get, $"{ordersUrl}/orders/{w.OrderId}", ctx));
    if (!r.IsSuccessStatusCode) return Results.NotFound();
    var o = (await r.Content.ReadFromJsonAsync<OrderDto>(json))!;
    if (w.Amount != o.Total) return Results.Json(new { error = "Monto no coincide" }, statusCode: 422);
    if (o.Estado == "ANULADO") return Results.Conflict(new { error = "Pedido anulado" });

    var detalle = JsonSerializer.Serialize(new { o.Referencia, o.Items, o.Subtotal, o.CostoEnvio, o.Total });
    var res = await db.CallAsync("SP_CONFIRMAR_PAGO",
        [("p_pedido", o.Id), ("p_ref", o.Referencia), ("p_monto", o.Total), ("p_metodo", "SERVIPAG"), ("p_tx", w.TxId),
         ("p_cliente", o.IdCliente), ("p_detalle", detalle)],
        [("o_dup", OracleDbType.Int32, 0), ("o_boleta", OracleDbType.Varchar2, 20)]);
    if (res["o_dup"] == "1") return Results.Ok(new { duplicado = true, boleta = res["o_boleta"] });

    // Efectos secundarios: el pago ya está confirmado; fallos aquí no revierten (se loguean y reintentan por cola/outbox).
    async Task Try(string what, Func<Task<HttpResponseMessage>> f)
    {
        try { var x = await f(); if (!x.IsSuccessStatusCode) app.Logger.LogWarning("{w} falló: {s}", what, x.StatusCode); }
        catch (Exception e) { app.Logger.LogWarning("{w} no disponible: {m}", what, e.Message); }
    }
    await Try("orders.status", () => cl.SendAsync(Req(HttpMethod.Patch, $"{ordersUrl}/orders/{o.Id}/status", ctx, new { Estado = "PAGADO" })));
    await Try("inventory.confirm", () => cl.SendAsync(Req(HttpMethod.Post, $"{invUrl}/stock/reservations/{o.Referencia}/confirm", ctx)));
    string? correo = null, tel = null;
    try
    {
        var e = await cl.SendAsync(Req(HttpMethod.Get, $"{cliUrl}/clients/{o.IdCliente}/eligibility", ctx));
        var el = await e.Content.ReadFromJsonAsync<Elig>(json); correo = el?.Correo; tel = el?.Telefono;
    }
    catch { }
    await Try("delivery.create", () => cl.SendAsync(Req(HttpMethod.Post, $"{delUrl}/dispatch-orders", ctx,
        new { IdPedido = o.Id, IdCliente = o.IdCliente, Direccion = o.Direccion, Telefono = tel })));
    if (correo != null)
        await Try("notifications", () => cl.SendAsync(Req(HttpMethod.Post, $"{notUrl}/notifications", ctx,
            new { Tipo = "BOLETA", Destinatario = correo, Asunto = $"Boleta {res["o_boleta"]}", Cuerpo = $"Pago recibido por ${o.Total}. Pedido {o.Referencia}." })));
    return Results.Ok(new { confirmado = true, boleta = res["o_boleta"] });
});

app.MapGet("/receipts/{orderId:long}", async (HttpContext ctx, long orderId) =>
{
    if (ctx.UserId() is null) return Results.Unauthorized();
    var r = await db.QueryAsync("SELECT NUMERO,ID_CLIENTE,TOTAL,DETALLE_JSON,EMITIDA FROM BOLETA WHERE ID_PEDIDO=:i", ("i", orderId));
    if (r.Count == 0) return Results.NotFound();
    var owner = Convert.ToInt64(r[0]["ID_CLIENTE"]);
    if (!(ctx.InRole("ADMIN", "CAJERO", "DUENO") || (ctx.InRole("CLIENTE") && ctx.UserId() == owner))) return Results.NotFound();
    return Results.Ok(new { numero = r[0]["NUMERO"], total = Convert.ToInt64(r[0]["TOTAL"]), emitida = r[0]["EMITIDA"],
        detalle = JsonSerializer.Deserialize<JsonElement>(r[0]["DETALLE_JSON"]!.ToString()!) });
});

app.MapPost("/receipts/{orderId:long}/resend", async (HttpContext ctx, long orderId) =>
{
    if (!ctx.InRole("ADMIN", "CAJERO")) return Results.Json(new { error = "Acceso denegado" }, statusCode: 403);
    var r = await db.QueryAsync("SELECT NUMERO,ID_CLIENTE,TOTAL FROM BOLETA WHERE ID_PEDIDO=:i", ("i", orderId));
    if (r.Count == 0) return Results.NotFound();
    var cl = http.CreateClient();
    var e = await cl.SendAsync(Req(HttpMethod.Get, $"{cliUrl}/clients/{r[0]["ID_CLIENTE"]}/eligibility", ctx));
    var el = await e.Content.ReadFromJsonAsync<Elig>(json);
    await cl.SendAsync(Req(HttpMethod.Post, $"{notUrl}/notifications", ctx,
        new { Tipo = "BOLETA", Destinatario = el!.Correo, Asunto = $"Boleta {r[0]["NUMERO"]} (reenvío)", Cuerpo = $"Total ${r[0]["TOTAL"]}" }));
    return Results.Accepted();
});

app.MapGet("/reports/sales", async (HttpContext ctx, DateTime? desde, DateTime? hasta) =>
{
    if (!ctx.InRole("ADMIN", "DUENO")) return Results.Json(new { error = "Acceso denegado" }, statusCode: 403);
    var d = desde ?? DateTime.Today.AddDays(-30); var h = hasta ?? DateTime.Today;
    if (h < d || (h - d).TotalDays > 366) return Results.BadRequest(new { error = "Rango inválido" });
    var rows = await db.QueryAsync("SELECT TRUNC(FECHA) DIA, COUNT(*) CANTIDAD, SUM(TOTAL) TOTAL FROM VENTA WHERE FECHA>=:d AND FECHA<:h+1 GROUP BY TRUNC(FECHA) ORDER BY 1",
        ("d", d), ("h", h));
    return Results.Ok(rows.Select(x => new { dia = x["DIA"], cantidad = Convert.ToInt32(x["CANTIDAD"]), total = Convert.ToInt64(x["TOTAL"]) }));
});

app.Run();

record PayReq(long IdPedido, string? Metodo);
record Webhook(long OrderId, string TxId, long Amount, string Status);
record OItem(long IdProducto, string Nombre, long PrecioUnitario, int Cantidad);
record OrderDto(long Id, string Referencia, long IdCliente, string Estado, long Subtotal, long CostoEnvio, long Total, string Direccion, OItem[] Items);
record Elig(bool Elegible, string? Correo, string? Telefono);
public partial class Program { }
