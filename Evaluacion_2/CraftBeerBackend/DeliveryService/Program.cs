using System.Net.Http.Json;
using CraftBeer.Shared;
using Oracle.ManagedDataAccess.Client;

var b = WebApplication.CreateBuilder(args);
var db = new Db(Conn.For("delivery", "DB_DELIVERY_PWD"));
b.AddCommon(db, [Secrets.Get("SVC_PAYMENTS_KEY")]);
var app = b.Build();
app.UseCommon();

var ordersUrl = Environment.GetEnvironmentVariable("ORDERS_URL") ?? "http://orders:8080";
var myKey = Secrets.Get("SVC_DELIVERY_KEY");
var http = app.Services.GetRequiredService<IHttpClientFactory>();

// Creación interna (desde Pagos, tras confirmar pago). Idempotente por ID_PEDIDO.
app.MapPost("/dispatch-orders", async (HttpContext ctx, NewDispatch d) =>
{
    if (!ctx.IsInternal()) return Results.Json(new { error = "Acceso denegado" }, statusCode: 403);
    var o = await db.CallAsync("SP_CREAR_ORDEN_DESPACHO",
        [("p_pedido", d.IdPedido), ("p_cli", d.IdCliente), ("p_dir", d.Direccion), ("p_tel", d.Telefono)],
        [("o_id", OracleDbType.Int64, 0)]);
    return Results.Ok(new { id = long.Parse(o["o_id"]!) });
});

app.MapGet("/dispatch-orders", async (HttpContext ctx, string? estado, int? page, int? size) =>
{
    if (!ctx.InRole("ADMIN", "DESPACHO")) return Results.Json(new { error = "Acceso denegado" }, statusCode: 403);
    var s = Math.Clamp(size ?? 20, 1, 50); var p = Math.Max(1, page ?? 1);
    var rows = await db.QueryAsync(@"SELECT ID_ORDEN,ID_PEDIDO,DIRECCION,TELEFONO,ESTADO,EDAD_VERIFICADA FROM ORDEN_DESPACHO
        WHERE (:e IS NULL OR ESTADO=:e) ORDER BY CREADO OFFSET :o ROWS FETCH NEXT :s ROWS ONLY",
        ("e", estado), ("o", (p - 1) * s), ("s", s));
    return Results.Ok(rows.Select(r => new { id = Convert.ToInt64(r["ID_ORDEN"]), idPedido = Convert.ToInt64(r["ID_PEDIDO"]),
        direccion = r["DIRECCION"], telefono = r["TELEFONO"], estado = r["ESTADO"], edadVerificada = Convert.ToInt32(r["EDAD_VERIFICADA"]) == 1 }));
});

var transitions = new Dictionary<string, string[]>
{
    ["PENDIENTE"] = ["EN_PREPARACION"], ["EN_PREPARACION"] = ["EN_RUTA"], ["EN_RUTA"] = ["ENTREGADO", "FALLIDO"]
};
app.MapPatch("/dispatch-orders/{id:long}/status", async (HttpContext ctx, long id, DStatus s) =>
{
    if (!ctx.InRole("ADMIN", "DESPACHO")) return Results.Json(new { error = "Acceso denegado" }, statusCode: 403);
    var r = await db.QueryAsync("SELECT ID_PEDIDO,ESTADO FROM ORDEN_DESPACHO WHERE ID_ORDEN=:i", ("i", id));
    if (r.Count == 0) return Results.NotFound();
    var cur = (string)r[0]["ESTADO"]!;
    if (!transitions.TryGetValue(cur, out var nx) || !nx.Contains(s.Estado))
        return Results.Conflict(new { error = $"Transición {cur}->{s.Estado} no permitida" });
    // Ley 19.925: entrega solo con verificación de edad por cédula
    if (s.Estado == "ENTREGADO" && s.EdadVerificada != true)
        return Results.Json(new { error = "Debe verificar la edad (cédula) antes de entregar" }, statusCode: 422);
    await db.ExecAsync("UPDATE ORDEN_DESPACHO SET ESTADO=:e, EDAD_VERIFICADA=CASE WHEN :ev=1 THEN 1 ELSE EDAD_VERIFICADA END, ACTUALIZADO=SYSTIMESTAMP WHERE ID_ORDEN=:i",
        ("e", s.Estado), ("ev", s.EdadVerificada == true ? 1 : 0), ("i", id));
    var mapped = s.Estado switch { "EN_RUTA" => "EN_DESPACHO", "ENTREGADO" => "ENTREGADO", _ => null };
    if (mapped != null)
    {
        try
        {
            var req = new HttpRequestMessage(HttpMethod.Patch, $"{ordersUrl}/orders/{r[0]["ID_PEDIDO"]}/status") { Content = JsonContent.Create(new { Estado = mapped }) };
            req.Headers.Add("X-Service-Key", myKey);
            await http.CreateClient().SendAsync(req);
        }
        catch (Exception e) { app.Logger.LogWarning("Orders no disponible al sincronizar estado: {m}", e.Message); }
    }
    return Results.Ok(new { id, estado = s.Estado });
});

app.Run();

record NewDispatch(long IdPedido, long IdCliente, string Direccion, string? Telefono);
record DStatus(string Estado, bool? EdadVerificada);
public partial class Program { }
