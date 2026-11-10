using CraftBeer.Shared;
using GraphQLGateway;
using HotChocolate.Execution.Configuration;

var b = WebApplication.CreateBuilder(args);
GatewayTrustMiddleware.ServiceKeys = []; // solo acepta tráfico del API Gateway (X-Gateway-Token)
b.Services.AddHttpClient("orders", c => c.BaseAddress = new Uri(Environment.GetEnvironmentVariable("ORDERS_URL") ?? "http://orders:8080"));
b.Services.AddHttpClient("inventory", c => c.BaseAddress = new Uri(Environment.GetEnvironmentVariable("INVENTORY_URL") ?? "http://inventory:8080"));
b.Services.AddHttpContextAccessor();
b.Services.AddSingleton<GraphQLGateway.Upstream>();
b.Services.AddHealthChecks();
b.Services.AddAuthorization();
b.Services
    .AddGraphQLServer()
    .AddAuthorization()
    .AddQueryType<Query>()
    .AddType<ResumenPedidoType>()
    .AddType<ItemPedidoExt>()
    .AddType<ProductoExt>()
    .AddDataLoader<ProductoByIdDataLoader>()
    .AddMaxExecutionDepthRule(5)                                   // límite de profundidad
    .ModifyRequestOptions(o =>
    {
        o.Complexity.Enable = true;                                // límite de costo/complejidad
        o.Complexity.MaximumAllowed = 150;
        o.ExecutionTimeout = TimeSpan.FromSeconds(10);
    })
    .SetPagingOptions(new HotChocolate.Types.Pagination.PagingOptions { MaxPageSize = 20, DefaultPageSize = 10, IncludeTotalCount = true })
    .ModifyOptions(o => o.EnableOneOf = false)
    .AllowIntrospection(b.Environment.IsDevelopment());
var app = b.Build();
app.UseMiddleware<CorrelationMiddleware>();
app.UseMiddleware<GatewayTrustMiddleware>();
app.UseAuthorization();
app.MapHealthChecks("/health");
app.MapGraphQL("/graphql");
app.Run();
public partial class Program { }
