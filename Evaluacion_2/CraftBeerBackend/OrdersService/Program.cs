using System.Net.Http.Json;
using CraftBeer.Shared;
using Oracle.ManagedDataAccess.Client;

var b = WebApplication.CreateBuilder(args);
var db = new Db(Conn.For("orders", "DB_ORDERS_PWD"));
b.AddCommon(db, [Secrets.Get("SVC_PAYMENTS_KEY"), Secrets.Get("SVC_DELIVERY_KEY"), Secrets.Get("SVC_GRAPHQL_KEY")]);
var app = b.Build();
app.UseCommon();

var invUrl = Environment.GetEnvironmentVariable("INVENTORY_URL") ?? "http://inventory:8080";
var cliUrl = Environment.GetEnvironmentVariable("CLIENTS_URL") ?? "http://clients:8080";
var myKey = Secrets.Get("SVC_ORDERS_KEY");
var http = app.Services.GetRequiredService<IHttpClientFactory>();

HttpRequestMessage Req(HttpMethod m, string url, HttpContext ctx, object? body = null)
{
    var r = new HttpRequestMessage(m, url);
    r.Headers.Add("X-Service-Key", myKey);
    r.Headers.Add("X-Correlation-Id", ctx.Items["X-Correlation-Id"]?.ToString());
    if (body != null) r.Content = JsonContent.Create(body);
    return r;
}

bool Owns(HttpContext ctx, long idCliente) =>
    ctx.InRole("ADMIN", "CAJERO", "DUENO") || (ctx.InRole("CLIENTE") && ctx.UserId() == idCliente);

app.MapPost("/orders", async (HttpContext ctx, CreateOrder o) =>
{
    if (!ctx.InRole("CLIENTE") || ctx.UserId() is not { } cid) return Results.Json(new { error = "Acceso denegado" }, statusCode: 403);
    if (o.Items is null || o.Items.Length == 0 || o.Items.Any(i => i.Cantidad <= 0 || i.Cantidad > 50))
        return Results.BadRequest(new { error = "Items inválidos" });
    if (string.IsNullOrWhiteSpace(o.Direccion)) return Results.BadRequest(new { error = "Dirección requerida" });
    if (!o.ConfirmaMayorEdad) return Results.Json(new { error = "Debes confirmar mayoría de edad" }, statusCode: 422);

    var client = http.CreateClient();
    HttpResponseMessage er;
    try { er = await client.SendAsync(Req(HttpMethod.Get, $"{cliUrl}/clients/{cid}/eligibility", ctx)); }
    catch { return Results.Json(new { error = "Servicio de clientes no disponible" }, statusCode: 503); }
    if (!er.IsSuccessStatusCode) return Results.Json(new { error = "Cliente no válido" }, statusCode: 422);
    var el = await er.Content.ReadFromJsonAsync<Elig>();
    if (el is null || !el.Elegible) return Results.Json(new { error = "Cliente no elegible (edad/estado)" }, statusCode: 422);

    var reference = "PED-" + Guid.NewGuid().ToString("N")[..12].ToUpper();
    HttpResponseMessage rr;
    try { rr = await client.SendAsync(Req(HttpMethod.Post, $"{invUrl}/stock/reservations", ctx, new { Ref = reference, o.Items })); }
    catch { return Results.Json(new { error = "Inventario no disponible, reintente" }, statusCode: 503); }
    if (rr.StatusCode == System.Net.HttpStatusCode.Conflict)
        return Results.Conflict(await rr.Content.ReadFromJsonAsync<object>());
    if (!rr.IsSuccessStatusCode) return Results.Json(new { error = "Error de inventario" }, statusCode: 502);
    var res = await rr.Content.ReadFromJsonAsync<ReserveRes>();
    // Precios SIEMPRE desde inventario; el frontend no define montos.
    var subtotal = res!.Items.Sum(i => i.PrecioUnitario * i.Cantidad);
    var km = Math.Clamp(o.DistanciaKm ?? 0, 0, 100);
    try
    {
        var oc = await db.CallAsync("SP_CREAR_PEDIDO",
            [("p_ref", reference), ("p_cliente", cid), ("p_dir", o.Direccion), ("p_km", km), ("p_subtotal", subtotal)],
            [("o_id", OracleDbType.Int64, 0), ("o_envio", OracleDbType.Int64, 0), ("o_total", OracleDbType.Int64, 0)]);
        var id = long.Parse(oc["o_id"]!);
        foreach (var i in res.Items)
            await db.ExecAsync("INSERT INTO DETALLE_PEDIDO(ID_PEDIDO,ID_PRODUCTO,NOMBRE_PRODUCTO,PRECIO_UNITARIO,CANTIDAD) VALUES(:p,:i,:n,:pr,:c)",
                ("p", id), ("i", i.IdProducto), ("n", i.Nombre), ("pr", i.PrecioUnitario), ("c", i.Cantidad));
        return Results.Created($"/orders/{id}", new { id, referencia = reference, subtotal, costoEnvio = long.Parse(oc["o_envio"]!), total = long.Parse(oc["o_total"]!), estado = "PENDIENTE_PAGO" });
    }
    catch (Exception e)
    {
        app.Logger.LogError(e, "Fallo al crear pedido {ref}; liberando reserva", reference);
        try { await client.SendAsync(Req(HttpMethod.Delete, $"{invUrl}/stock/reservations/{reference}", ctx)); } catch { }
        return Results.Json(new { error = "No se pudo crear el pedido" }, statusCode: 500);
    }
});

async Task<object?> Load(long id)
{
    var h = await db.QueryAsync("SELECT * FROM PEDIDO WHERE ID_PEDIDO=:i", ("i", id));
    if (h.Count == 0) return null;
    var d = await db.QueryAsync("SELECT ID_PRODUCTO,NOMBRE_PRODUCTO,PRECIO_UNITARIO,CANTIDAD FROM DETALLE_PEDIDO WHERE ID_PEDIDO=:i", ("i", id));
    var x = h[0];
    return new
    {
        id, referencia = x["REF"], idCliente = Convert.ToInt64(x["ID_CLIENTE"]), estado = x["ESTADO"],
        subtotal = Convert.ToInt64(x["SUBTOTAL"]), costoEnvio = Convert.ToInt64(x["COSTO_ENVIO"]), total = Convert.ToInt64(x["TOTAL"]),
        direccion = x["DIRECCION_ENTREGA"], creado = x["CREADO"],
        items = d.Select(r => new { idProducto = Convert.ToInt64(r["ID_PRODUCTO"]), nombre = r["NOMBRE_PRODUCTO"],
            precioUnitario = Convert.ToInt64(r["PRECIO_UNITARIO"]), cantidad = Convert.ToInt32(r["CANTIDAD"]) })
    };
}

app.MapGet("/orders/me", async (HttpContext ctx, int? page, int? size) =>
{
    if (!ctx.InRole("CLIENTE") || ctx.UserId() is not { } cid) return Results.Json(new { error = "Acceso denegado" }, statusCode: 403);
    var s = Math.Clamp(size ?? 20, 1, 50); var p = Math.Max(1, page ?? 1);
    var rows = await db.QueryAsync("SELECT ID_PEDIDO,REF,ESTADO,TOTAL,CREADO FROM PEDIDO WHERE ID_CLIENTE=:c ORDER BY CREADO DESC OFFSET :o ROWS FETCH NEXT :s ROWS ONLY",
        ("c", cid), ("o", (p - 1) * s), ("s", s));
    return Results.Ok(rows.Select(r => new { id = Convert.ToInt64(r["ID_PEDIDO"]), referencia = r["REF"], estado = r["ESTADO"], total = Convert.ToInt64(r["TOTAL"]), creado = r["CREADO"] }));
});

app.MapGet("/orders/{id:long}", async (HttpContext ctx, long id) =>
{
    if (ctx.UserId() is null && !ctx.IsInternal()) return Results.Unauthorized();
    var o = await Load(id);
    if (o is null) return Results.NotFound();
    var owner = (long)o.GetType().GetProperty("idCliente")!.GetValue(o)!;
    // Bypass solo para llamadas servicio-a-servicio SIN usuario; el GraphQL reenvía el usuario y se valida propiedad.
    if (!(ctx.IsInternal() && ctx.UserId() is null) && !Owns(ctx, owner)) return Results.NotFound(); // no revelar existencia
    return Results.Ok(o);
});

app.MapPatch("/orders/{id:long}/cancel", async (HttpContext ctx, long id, CancelReq c) =>
{
    if (string.IsNullOrWhiteSpace(c.Motivo)) return Results.BadRequest(new { error = "Motivo requerido" });
    var h = await db.QueryAsync("SELECT ID_CLIENTE FROM PEDIDO WHERE ID_PEDIDO=:i", ("i", id));
    if (h.Count == 0 || !Owns(ctx, Convert.ToInt64(h[0]["ID_CLIENTE"]))) return Results.NotFound();
    try
    {
        var o = await db.CallAsync("SP_ANULAR_PEDIDO", [("p_id", id), ("p_motivo", c.Motivo)], [("o_ref", OracleDbType.Varchar2, 40)]);
        try { await http.CreateClient().SendAsync(Req(HttpMethod.Delete, $"{invUrl}/stock/reservations/{o["o_ref"]}", ctx)); }
        catch (Exception e) { app.Logger.LogWarning("Reserva {r} no liberada ahora; el job la recuperará: {m}", o["o_ref"], e.Message); }
        return Results.Ok(new { id, estado = "ANULADO" });
    }
    catch (OracleException e) when (e.Message.Contains("ESTADO_NO_ANULABLE")) { return Results.Conflict(new { error = "El pedido no puede anularse en su estado actual" }); }
});

// Interno: otros servicios cambian estado (transiciones válidas)
var allowed = new Dictionary<string, string[]>
{
    ["PENDIENTE_PAGO"] = ["PAGADO"], ["PAGADO"] = ["EN_PREPARACION", "EN_DESPACHO"],
    ["EN_PREPARACION"] = ["EN_DESPACHO"], ["EN_DESPACHO"] = ["ENTREGADO"]
};
app.MapPatch("/orders/{id:long}/status", async (HttpContext ctx, long id, StatusReq s) =>
{
    if (!ctx.IsInternal()) return Results.Json(new { error = "Acceso denegado" }, statusCode: 403);
    var h = await db.QueryAsync("SELECT ESTADO FROM PEDIDO WHERE ID_PEDIDO=:i", ("i", id));
    if (h.Count == 0) return Results.NotFound();
    var cur = (string)h[0]["ESTADO"]!;
    if (cur == s.Estado) return Results.Ok(new { id, estado = cur }); // idempotente
    if (!allowed.TryGetValue(cur, out var nx) || !nx.Contains(s.Estado))
        return Results.Conflict(new { error = $"Transición {cur}->{s.Estado} no permitida" });
    await db.ExecAsync("UPDATE PEDIDO SET ESTADO=:e WHERE ID_PEDIDO=:i", ("e", s.Estado), ("i", id));
    return Results.Ok(new { id, estado = s.Estado });
});

app.Run();

record Item(long IdProducto, int Cantidad);
record CreateOrder(Item[] Items, string Direccion, double? DistanciaKm, bool ConfirmaMayorEdad);
record CancelReq(string Motivo);
record StatusReq(string Estado);
record Elig(bool Elegible, string? Nombre, string? Telefono, string? Direccion, string? Correo);
record ResItem(long IdProducto, string Nombre, long PrecioUnitario, int Cantidad);
record ReserveRes(string Reserva, ResItem[] Items);
public partial class Program { }
