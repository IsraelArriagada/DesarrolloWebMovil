using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using BCrypt.Net;
using CraftBeer.Shared;
using Microsoft.IdentityModel.Tokens;
using Oracle.ManagedDataAccess.Client;

var b = WebApplication.CreateBuilder(args);
var db = new Db(Conn.For("clients", "DB_CLIENTS_PWD"));
b.AddCommon(db, [Secrets.Get("SVC_ORDERS_KEY"), Secrets.Get("SVC_PAYMENTS_KEY"), Secrets.Get("SVC_DELIVERY_KEY")]);
var app = b.Build();
app.UseCommon();

// Seed de usuarios de staff (idempotente)
try
{
    foreach (var (mail, rol) in new[] { ("admin@craftbeer.cl", "ADMIN"), ("cajero@craftbeer.cl", "CAJERO"),
                                         ("despacho@craftbeer.cl", "DESPACHO"), ("dueno@craftbeer.cl", "DUENO") })
    {
        var ex = await db.QueryAsync("SELECT 1 X FROM USUARIO WHERE CORREO=:c", ("c", mail));
        if (ex.Count == 0)
            await db.ExecAsync("INSERT INTO USUARIO(CORREO,PASSWORD_HASH,ROL) VALUES(:c,:h,:r)",
                ("c", mail), ("h", BCrypt.Net.BCrypt.HashPassword(Secrets.Get("SEED_ADMIN_PWD"), 12)), ("r", rol));
    }
}
catch (Exception e) { app.Logger.LogWarning("Seed omitido: {m}", e.Message); }

int Age(DateTime nac) { var t = DateTime.Today; var a = t.Year - nac.Year; if (nac.Date > t.AddYears(-a)) a--; return a; }
bool PwdOk(string p) => p.Length >= 8 && p.Any(char.IsDigit) && p.Any(char.IsLetter);

app.MapPost("/auth/login", async (HttpContext ctx, LoginReq r) =>
{
    var rows = await db.QueryAsync("SELECT ID_USUARIO,PASSWORD_HASH,ROL,BLOQUEADO_HASTA,ACTIVO FROM USUARIO WHERE CORREO=:c",
        ("c", r.Correo.ToLower()));
    if (rows.Count == 0) return Results.Json(new { error = "Credenciales inválidas" }, statusCode: 401);
    var u = rows[0];
    if (u["BLOQUEADO_HASTA"] is DateTime bh && bh > DateTime.Now)
        return Results.Json(new { error = "Cuenta bloqueada temporalmente" }, statusCode: 423);
    var ok = Convert.ToInt32(u["ACTIVO"]) == 1 && BCrypt.Net.BCrypt.Verify(r.Password, (string)u["PASSWORD_HASH"]!);
    await db.CallAsync("SP_REGISTRAR_INTENTO_LOGIN", [("p_correo", r.Correo), ("p_ok", ok ? 1 : 0)], []);
    if (!ok) return Results.Json(new { error = "Credenciales inválidas" }, statusCode: 401);
    var uid = Convert.ToInt64(u["ID_USUARIO"]);
    var rol = (string)u["ROL"]!;
    long? cid = null;
    var c = await db.QueryAsync("SELECT ID_CLIENTE FROM CLIENTE WHERE ID_USUARIO=:u", ("u", uid));
    if (c.Count > 0) cid = Convert.ToInt64(c[0]["ID_CLIENTE"]);
    // Para clientes, el "subject" es el ID_CLIENTE (propiedad de recursos); para staff, el ID_USUARIO.
    var sub = rol == "CLIENTE" ? cid!.Value : uid;
    var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(Secrets.Get("JWT_SECRET")));
    var jwt = new JwtSecurityToken("craftbeer", "craftbeer-api",
        [new Claim("sub", sub.ToString()), new Claim("role", rol)],
        expires: DateTime.UtcNow.AddMinutes(30),
        signingCredentials: new SigningCredentials(key, SecurityAlgorithms.HmacSha256));
    return Results.Ok(new { token = new JwtSecurityTokenHandler().WriteToken(jwt), rol, expiraEnMin = 30 });
});

app.MapPost("/clients", async (RegisterReq r) =>
{
    if (!r.AceptaTerminos) return Results.BadRequest(new { error = "Debe aceptar términos" });
    if (!PwdOk(r.Password)) return Results.BadRequest(new { error = "Contraseña mínima 8 caracteres con letras y números" });
    if (string.IsNullOrWhiteSpace(r.Nombre) || !r.Correo.Contains('@')) return Results.BadRequest(new { error = "Datos inválidos" });
    if (Age(r.FechaNacimiento) < 18) return Results.Json(new { error = "Debes ser mayor de 18 años (Ley 19.925)" }, statusCode: 422);
    try
    {
        var o = await db.CallAsync("SP_REGISTRAR_CLIENTE",
            [("p_correo", r.Correo), ("p_hash", BCrypt.Net.BCrypt.HashPassword(r.Password, 12)), ("p_nombre", r.Nombre),
             ("p_tel", r.Telefono), ("p_dir", r.Direccion), ("p_nac", r.FechaNacimiento), ("p_terminos", 1)],
            [("o_id_usuario", OracleDbType.Int64, 0), ("o_id_cliente", OracleDbType.Int64, 0)]);
        return Results.Created($"/clients/{o["o_id_cliente"]}", new { idCliente = long.Parse(o["o_id_cliente"]!) });
    }
    catch (OracleException e) when (e.Message.Contains("CORREO_DUPLICADO")) { return Results.Conflict(new { error = "Correo ya registrado" }); }
    catch (OracleException e) when (e.Message.Contains("MENOR_DE_EDAD")) { return Results.Json(new { error = "Debes ser mayor de 18 años" }, statusCode: 422); }
});

app.MapGet("/clients/me", async (HttpContext ctx) =>
{
    if (ctx.UserId() is not { } id || !ctx.InRole("CLIENTE")) return Results.Unauthorized();
    var r = await db.QueryAsync("SELECT ID_CLIENTE,NOMBRE,TELEFONO,DIRECCION FROM CLIENTE WHERE ID_CLIENTE=:i", ("i", id));
    return r.Count == 0 ? Results.NotFound() : Results.Ok(r[0]);
});

// Propiedad: un CLIENTE solo ve su propio perfil; ADMIN/CAJERO ven cualquiera.
app.MapGet("/clients/{id:long}", async (HttpContext ctx, long id) =>
{
    if (ctx.UserId() is not { } uid) return Results.Unauthorized();
    if (!(ctx.InRole("ADMIN", "CAJERO") || (ctx.InRole("CLIENTE") && uid == id))) return Results.Json(new { error = "Acceso denegado" }, statusCode: 403);
    var r = await db.QueryAsync("SELECT ID_CLIENTE,NOMBRE,TELEFONO,DIRECCION FROM CLIENTE WHERE ID_CLIENTE=:i", ("i", id));
    return r.Count == 0 ? Results.NotFound() : Results.Ok(r[0]);
});

app.MapPut("/clients/{id:long}", async (HttpContext ctx, long id, UpdateReq u) =>
{
    if (ctx.UserId() is not { } uid) return Results.Unauthorized();
    if (!(ctx.InRole("ADMIN") || (ctx.InRole("CLIENTE") && uid == id))) return Results.Json(new { error = "Acceso denegado" }, statusCode: 403);
    await db.ExecAsync("UPDATE CLIENTE SET NOMBRE=:n,TELEFONO=:t,DIRECCION=:d WHERE ID_CLIENTE=:i",
        ("n", u.Nombre), ("t", u.Telefono), ("d", u.Direccion), ("i", id));
    return Results.NoContent();
});

// Interno (solo otros servicios con X-Service-Key): elegibilidad y datos de contacto
app.MapGet("/clients/{id:long}/eligibility", async (HttpContext ctx, long id) =>
{
    if (!ctx.IsInternal()) return Results.Json(new { error = "Acceso denegado" }, statusCode: 403);
    var r = await db.QueryAsync(@"SELECT c.NOMBRE,c.TELEFONO,c.DIRECCION,u.CORREO,u.ACTIVO,
        TRUNC(MONTHS_BETWEEN(TRUNC(SYSDATE),c.FECHA_NACIMIENTO)/12) EDAD FROM CLIENTE c JOIN USUARIO u USING(ID_USUARIO) WHERE c.ID_CLIENTE=:i", ("i", id));
    if (r.Count == 0) return Results.NotFound();
    var x = r[0];
    return Results.Ok(new { elegible = Convert.ToInt32(x["EDAD"]) >= 18 && Convert.ToInt32(x["ACTIVO"]) == 1,
        nombre = x["NOMBRE"], telefono = x["TELEFONO"], direccion = x["DIRECCION"], correo = x["CORREO"] });
});

app.Run();

record LoginReq(string Correo, string Password);
record RegisterReq(string Nombre, string Correo, string Password, string? Telefono, string? Direccion, DateTime FechaNacimiento, bool AceptaTerminos);
record UpdateReq(string Nombre, string? Telefono, string? Direccion);
public partial class Program { }
