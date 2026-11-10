using CraftBeer.Shared;
using Oracle.ManagedDataAccess.Client;

var b = WebApplication.CreateBuilder(args);
var db = new Db(Conn.For("notifications", "DB_NOTIFICATIONS_PWD"));
b.AddCommon(db, [Secrets.Get("SVC_ORDERS_KEY"), Secrets.Get("SVC_PAYMENTS_KEY"), Secrets.Get("SVC_DELIVERY_KEY")]);
b.Services.AddHostedService<MailWorker>();
var app = b.Build();
app.UseCommon();

app.MapPost("/notifications", async (HttpContext ctx, NewNotif n) =>
{
    if (!ctx.IsInternal()) return Results.Json(new { error = "Acceso denegado" }, statusCode: 403);
    if (!n.Destinatario.Contains('@')) return Results.BadRequest(new { error = "Destinatario inválido" });
    var o = await db.CallAsync("SP_ENCOLAR_NOTIFICACION",
        [("p_tipo", n.Tipo), ("p_dest", n.Destinatario), ("p_asunto", n.Asunto), ("p_cuerpo", n.Cuerpo)],
        [("o_id", OracleDbType.Int64, 0)]);
    return Results.Accepted(null, new { id = long.Parse(o["o_id"]!) });
});

app.Run();

record NewNotif(string Tipo, string Destinatario, string Asunto, string Cuerpo);

/// <summary>Worker: toma NOTIFICACION_COLA pendientes y las envía con el adaptador de correo.
/// MAIL_PROVIDER=fake solo registra en log (modo prueba, sin red). Reintenta hasta 3 veces.</summary>
class MailWorker(Db db, ILogger<MailWorker> log) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            try
            {
                var rows = await db.QueryAsync("SELECT ID_NOTIF,DESTINATARIO,ASUNTO FROM NOTIFICACION_COLA WHERE ESTADO='PENDIENTE' FETCH FIRST 10 ROWS ONLY");
                foreach (var r in rows)
                {
                    var ok = Send((string)r["DESTINATARIO"]!, (string?)r["ASUNTO"]);
                    await db.CallAsync("SP_MARCAR_ENVIADA", [("p_id", Convert.ToInt64(r["ID_NOTIF"])), ("p_ok", ok ? 1 : 0)], []);
                }
            }
            catch (Exception e) { log.LogWarning("Worker: {m}", e.Message); }
            await Task.Delay(TimeSpan.FromSeconds(5), ct);
        }
    }
    bool Send(string to, string? subject)
    {
        if ((Environment.GetEnvironmentVariable("MAIL_PROVIDER") ?? "fake") == "fake")
        { log.LogInformation("[MAIL-FAKE] to={to} subject={s}", to, subject); return true; }
        return false; // proveedor real: implementar adaptador SMTP aquí
    }
}
public partial class Program { }
