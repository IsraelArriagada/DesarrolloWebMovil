using System.Text;
using CraftBeer.Shared;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;
using Ocelot.DependencyInjection;
using Ocelot.Middleware;

var b = WebApplication.CreateBuilder(args);
b.Configuration.AddJsonFile("ocelot.json", optional: false, reloadOnChange: false);
b.Services.AddOcelot(b.Configuration);
b.Services.AddHealthChecks();
b.Services.AddCors(o => o.AddDefaultPolicy(p => p
    .WithOrigins((Environment.GetEnvironmentVariable("CORS_ORIGINS") ?? "http://localhost:5500,http://127.0.0.1:5500").Split(','))
    .AllowAnyHeader().AllowAnyMethod()));
b.Services.AddAuthentication().AddJwtBearer("Bearer", o =>
{
    o.MapInboundClaims = false; // conserva claims "sub" y "role"
    o.TokenValidationParameters = new TokenValidationParameters
    {
        ValidateIssuer = true, ValidIssuer = "craftbeer",
        ValidateAudience = true, ValidAudience = "craftbeer-api",
        ValidateLifetime = true, ClockSkew = TimeSpan.FromSeconds(10),
        ValidateIssuerSigningKey = true,
        IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(Secrets.Get("JWT_SECRET"))),
        RoleClaimType = "role", NameClaimType = "sub"
    };
});
var app = b.Build();
var internalToken = Secrets.Get("GATEWAY_INTERNAL_TOKEN");
var log = app.Logger;

app.UseCors();
app.Map("/health", hb => hb.Run(c => c.Response.WriteAsync("Healthy")));

app.Use(async (ctx, next) =>
{
    // Correlation-id de extremo a extremo
    var cid = ctx.Request.Headers["X-Correlation-Id"].FirstOrDefault() ?? Guid.NewGuid().ToString("N");
    ctx.Request.Headers["X-Correlation-Id"] = cid;
    ctx.Response.Headers["X-Correlation-Id"] = cid;
    // Elimina cualquier cabecera de identidad/servicio enviada por el cliente (anti-suplantación)
    foreach (var h in new[] { "X-User-Id", "X-User-Role", "X-Gateway-Token", "X-Service-Key" })
        ctx.Request.Headers.Remove(h);
    // El Gateway se identifica ante los servicios
    ctx.Request.Headers["X-Gateway-Token"] = internalToken;
    log.LogInformation("GW {m} {p} cid={c}", ctx.Request.Method, ctx.Request.Path, cid);
    await next();
});

await app.UseOcelot();
app.Run();
public partial class Program { }
