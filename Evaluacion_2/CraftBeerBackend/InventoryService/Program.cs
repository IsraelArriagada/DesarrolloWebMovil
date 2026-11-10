using CraftBeer.Shared;
using Oracle.ManagedDataAccess.Client;

var b = WebApplication.CreateBuilder(args);
var db = new Db(Conn.For("inventory", "DB_INVENTORY_PWD"));
b.AddCommon(db, [Secrets.Get("SVC_ORDERS_KEY"), Secrets.Get("SVC_PAYMENTS_KEY"), Secrets.Get("SVC_GRAPHQL_KEY")]);
var app = b.Build();
app.UseCommon();

static object Map(Dictionary<string, object?> r) => new
{
    id = Convert.ToInt64(r["ID_PRODUCTO"]), nombre = r["NOMBRE"], categoria = r["CATEGORIA"],
    precio = Convert.ToInt64(r["PRECIO"]), stock = Convert.ToInt64(r["STOCK"]), disponible = Convert.ToInt32(r["DISPONIBLE"]) == 1
};

app.MapGet("/products", async (string? categoria, int? page, int? size) =>
{
    var p = Math.Max(1, page ?? 1); var s = Math.Clamp(size ?? 20, 1, 50);
    var rows = await db.QueryAsync(@"SELECT * FROM PRODUCTO WHERE (:c IS NULL OR CATEGORIA=:c)
        ORDER BY ID_PRODUCTO OFFSET :o ROWS FETCH NEXT :s ROWS ONLY",
        ("c", categoria), ("o", (p - 1) * s), ("s", s));
    return Results.Ok(rows.Select(Map));
});

app.MapGet("/products/{id:long}", async (long id) =>
{
    var r = await db.QueryAsync("SELECT * FROM PRODUCTO WHERE ID_PRODUCTO=:i", ("i", id));
    return r.Count == 0 ? Results.NotFound() : Results.Ok(Map(r[0]));
});

// Batch lookup (usado por el GraphQL Gateway para evitar N+1)
app.MapPost("/products/batch", async (long[] ids) =>
{
    if (ids.Length == 0 || ids.Length > 50) return Results.BadRequest(new { error = "1..50 ids" });
    var list = string.Join(",", ids.Select(i => (long)i));   // enteros tipados, sin concatenar texto del usuario
    var rows = await db.QueryAsync($"SELECT * FROM PRODUCTO WHERE ID_PRODUCTO IN ({list})");
    return Results.Ok(rows.Select(Map));
});

app.MapPost("/products", async (HttpContext ctx, ProdReq p) =>
{
    if (!ctx.InRole("ADMIN")) return Results.Json(new { error = "Acceso denegado" }, statusCode: 403);
    if (p.Precio <= 0 || p.Stock < 0) return Results.BadRequest(new { error = "Precio/stock inválido" });
    await db.ExecAsync("INSERT INTO PRODUCTO VALUES(:i,:n,:c,:p,:s,1)", ("i", p.Id), ("n", p.Nombre), ("c", p.Categoria), ("p", p.Precio), ("s", p.Stock));
    return Results.Created($"/products/{p.Id}", new { p.Id });
});

app.MapPut("/products/{id:long}", async (HttpContext ctx, long id, ProdReq p) =>
{
    if (!ctx.InRole("ADMIN")) return Results.Json(new { error = "Acceso denegado" }, statusCode: 403);
    if (p.Precio <= 0 || p.Stock < 0) return Results.BadRequest(new { error = "Precio/stock inválido" });
    var n = await db.ExecAsync("UPDATE PRODUCTO SET NOMBRE=:n,CATEGORIA=:c,PRECIO=:p,STOCK=:s WHERE ID_PRODUCTO=:i",
        ("n", p.Nombre), ("c", p.Categoria), ("p", p.Precio), ("s", p.Stock), ("i", id));
    return n == 0 ? Results.NotFound() : Results.NoContent();
});

app.MapPatch("/products/{id:long}/availability", async (HttpContext ctx, long id, AvailReq a) =>
{
    if (!ctx.InRole("ADMIN")) return Results.Json(new { error = "Acceso denegado" }, statusCode: 403);
    var n = await db.ExecAsync("UPDATE PRODUCTO SET DISPONIBLE=:d WHERE ID_PRODUCTO=:i", ("d", a.Disponible ? 1 : 0), ("i", id));
    return n == 0 ? Results.NotFound() : Results.NoContent();
});

// ---- Interno: reservas de stock (solo con X-Service-Key) ----
app.MapPost("/stock/reservations", async (HttpContext ctx, ReserveReq r) =>
{
    if (!ctx.IsInternal()) return Results.Json(new { error = "Acceso denegado" }, statusCode: 403);
    if (r.Items.Length == 0 || r.Items.Any(i => i.Cantidad <= 0)) return Results.BadRequest(new { error = "Items inválidos" });
    var ids = string.Join(",", r.Items.Select(i => i.IdProducto));
    var cs = string.Join(",", r.Items.Select(i => i.Cantidad));
    var o = await db.CallAsync("SP_RESERVAR_STOCK", [("p_ref", r.Ref), ("p_ids", ids), ("p_cants", cs)],
        [("o_error", OracleDbType.Varchar2, 200)]);
    if (!string.IsNullOrEmpty(o["o_error"])) return Results.Conflict(new { error = o["o_error"] });
    var prods = await db.QueryAsync($"SELECT * FROM PRODUCTO WHERE ID_PRODUCTO IN ({ids})");
    var items = r.Items.Select(i =>
    {
        var p = prods.First(x => Convert.ToInt64(x["ID_PRODUCTO"]) == i.IdProducto);
        return new { idProducto = i.IdProducto, nombre = p["NOMBRE"], precioUnitario = Convert.ToInt64(p["PRECIO"]), cantidad = i.Cantidad };
    });
    return Results.Ok(new { reserva = r.Ref, items });
});

app.MapDelete("/stock/reservations/{reference}", async (HttpContext ctx, string reference) =>
{
    if (!ctx.IsInternal()) return Results.Json(new { error = "Acceso denegado" }, statusCode: 403);
    await db.CallAsync("SP_LIBERAR_RESERVA", [("p_ref", reference)], []);
    return Results.NoContent();
});

app.MapPost("/stock/reservations/{reference}/confirm", async (HttpContext ctx, string reference) =>
{
    if (!ctx.IsInternal()) return Results.Json(new { error = "Acceso denegado" }, statusCode: 403);
    await db.CallAsync("SP_CONFIRMAR_RESERVA", [("p_ref", reference)], []);
    return Results.NoContent();
});

app.Run();

record ProdReq(long Id, string Nombre, string Categoria, long Precio, long Stock);
record AvailReq(bool Disponible);
record Item(long IdProducto, int Cantidad);
record ReserveReq(string Ref, Item[] Items);
public partial class Program { }
