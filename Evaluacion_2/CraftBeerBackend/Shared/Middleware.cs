using Microsoft.Extensions.Logging;
using System.Security.Claims;
using Microsoft.AspNetCore.Http;

namespace CraftBeer.Shared;

/// <summary>Propaga/crea X-Correlation-Id y lo escribe en los logs.</summary>
public class CorrelationMiddleware(RequestDelegate next, Microsoft.Extensions.Logging.ILogger<CorrelationMiddleware> log)
{
    public const string Header = "X-Correlation-Id";
    public async Task Invoke(HttpContext ctx)
    {
        var id = ctx.Request.Headers[Header].FirstOrDefault() ?? Guid.NewGuid().ToString("N");
        ctx.Items[Header] = id;
        ctx.Response.Headers[Header] = id;
        using (log.BeginScope(new Dictionary<string, object> { ["correlationId"] = id }))
        {
            log.LogInformation("{Method} {Path} cid={Cid}", ctx.Request.Method, ctx.Request.Path, id);
            await next(ctx);
        }
    }
}

/// <summary>
/// Rechaza peticiones que no vengan del Gateway (X-Gateway-Token) o de otro servicio (X-Service-Key).
/// Construye el ClaimsPrincipal desde X-User-Id / X-User-Role inyectados por el Gateway.
/// </summary>
public class GatewayTrustMiddleware(RequestDelegate next)
{
    public static string[] ServiceKeys = [];
    public async Task Invoke(HttpContext ctx)
    {
        var path = ctx.Request.Path.Value ?? "";
        if (path.StartsWith("/health")) { await next(ctx); return; }

        var gw = ctx.Request.Headers["X-Gateway-Token"].FirstOrDefault();
        var sk = ctx.Request.Headers["X-Service-Key"].FirstOrDefault();
        var okGw = gw != null && gw == Secrets.Get("GATEWAY_INTERNAL_TOKEN");
        var okSvc = sk != null && ServiceKeys.Contains(sk);
        if (!okGw && !okSvc)
        {
            ctx.Response.StatusCode = 403;
            await ctx.Response.WriteAsJsonAsync(new { error = "Acceso directo no permitido" });
            return;
        }
        ctx.Items["IsInternal"] = okSvc;
        var uid = ctx.Request.Headers["X-User-Id"].FirstOrDefault();
        var role = ctx.Request.Headers["X-User-Role"].FirstOrDefault();
        if (!string.IsNullOrEmpty(uid) && !string.IsNullOrEmpty(role))
        {
            var id = new ClaimsIdentity(
                [new Claim(ClaimTypes.NameIdentifier, uid), new Claim(ClaimTypes.Role, role)], "gateway");
            ctx.User = new ClaimsPrincipal(id);
        }
        await next(ctx);
    }
}

public static class Ext
{
    public static bool IsInternal(this HttpContext c) => c.Items["IsInternal"] as bool? ?? false;
    public static long? UserId(this HttpContext c) =>
        long.TryParse(c.User.FindFirstValue(ClaimTypes.NameIdentifier), out var v) ? v : null;
    public static string? Role(this HttpContext c) => c.User.FindFirstValue(ClaimTypes.Role);
    public static bool InRole(this HttpContext c, params string[] roles) =>
        c.Role() is { } r && roles.Contains(r);
}
