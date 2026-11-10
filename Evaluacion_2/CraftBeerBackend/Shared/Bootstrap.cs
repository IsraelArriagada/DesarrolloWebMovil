using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Diagnostics.HealthChecks;

namespace CraftBeer.Shared;

public static class Bootstrap
{
    public static void AddCommon(this WebApplicationBuilder b, Db db, string[] allowedServiceKeys)
    {
        GatewayTrustMiddleware.ServiceKeys = allowedServiceKeys;
        b.Services.AddSingleton(db);
        b.Services.AddHttpClient();
        b.Services.AddHealthChecks().AddCheck("oracle", () =>
        {
            try { db.Open().Dispose(); return HealthCheckResult.Healthy(); }
            catch (Exception e) { return HealthCheckResult.Unhealthy(e.Message); }
        });
    }

    public static void UseCommon(this WebApplication app)
    {
        app.UseMiddleware<CorrelationMiddleware>();
        app.UseMiddleware<GatewayTrustMiddleware>();
        app.MapHealthChecks("/health");
    }
}
