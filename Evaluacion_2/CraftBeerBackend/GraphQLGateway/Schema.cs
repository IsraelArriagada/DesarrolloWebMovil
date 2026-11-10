using System.Net.Http.Json;
using System.Text.Json;
using CraftBeer.Shared;
using HotChocolate.Authorization;
using HotChocolate.Types;

namespace GraphQLGateway;

public record Producto(long Id, string Nombre, string Categoria, long Precio, long Stock, bool Disponible);
public record ItemPedido(long IdProducto, string Nombre, long PrecioUnitario, int Cantidad);
public record Pedido(long Id, string Referencia, long IdCliente, string Estado, long Subtotal, long CostoEnvio, long Total, string Direccion, ItemPedido[] Items);

/// <summary>Cliente HTTP hacia los servicios; reenvía identidad del usuario y correlation-id (NO usa bypass interno).</summary>
public class Upstream(IHttpClientFactory f, IHttpContextAccessor acc)
{
    public HttpRequestMessage Req(HttpMethod m, string client, string url, object? body = null)
    {
        var ctx = acc.HttpContext!;
        var r = new HttpRequestMessage(m, url);
        r.Headers.Add("X-Service-Key", Secrets.Get("SVC_GRAPHQL_KEY"));
        r.Headers.Add("X-Gateway-Token", Secrets.Get("GATEWAY_INTERNAL_TOKEN"));
        if (ctx.UserId() is { } id) r.Headers.Add("X-User-Id", id.ToString());
        if (ctx.Role() is { } role) r.Headers.Add("X-User-Role", role);
        if (ctx.Items["X-Correlation-Id"] is string cid) r.Headers.Add("X-Correlation-Id", cid);
        if (body != null) r.Content = JsonContent.Create(body);
        return r;
    }
    public HttpClient Client(string n) => f.CreateClient(n);
    public static readonly JsonSerializerOptions J = new(JsonSerializerDefaults.Web);
}

public class Query
{
    /// <summary>Catálogo paginado (público dentro del GraphQL autenticado).</summary>
    [Authorize]
    [UsePaging(MaxPageSize = 20, IncludeTotalCount = true)]
    [GraphQLComplexity(2)]
    public async Task<IEnumerable<Producto>> Catalogo(string? categoria, [Service] Upstream up)
    {
        var url = "/products?size=50" + (categoria != null ? "&categoria=" + Uri.EscapeDataString(categoria) : "");
        var res = await up.Client("inventory").SendAsync(up.Req(HttpMethod.Get, "inventory", url));
        res.EnsureSuccessStatusCode();
        return (await res.Content.ReadFromJsonAsync<List<Producto>>(Upstream.J))!;
    }

    /// <summary>Resumen de pedido: agrega Orders + Inventory. Solo el dueño o staff (la propiedad la valida Orders).</summary>
    [Authorize]
    [GraphQLComplexity(10)]
    public async Task<Pedido?> ResumenPedido(long id, [Service] Upstream up)
    {
        var res = await up.Client("orders").SendAsync(up.Req(HttpMethod.Get, "orders", $"/orders/{id}"));
        if (res.StatusCode == System.Net.HttpStatusCode.NotFound) return null; // no revela existencia
        res.EnsureSuccessStatusCode();
        return await res.Content.ReadFromJsonAsync<Pedido>(Upstream.J);
    }
}

public class ResumenPedidoType : ObjectType<Pedido>
{
    protected override void Configure(IObjectTypeDescriptor<Pedido> d)
    {
        // Autorización por campo: solo staff ve el id de cliente
        d.Field(x => x.IdCliente).Authorize(roles: ["ADMIN", "CAJERO", "DUENO"]);
        d.Field(x => x.Items).Type<ListType<ObjectType<ItemPedido>>>();
    }
}

[ExtendObjectType(typeof(ItemPedido))]
public class ItemPedidoExt
{
    /// <summary>Datos vivos del producto desde Inventory, con DataLoader (1 llamada batch para N ítems).</summary>
    [GraphQLComplexity(5)]
    public Task<Producto> Producto([Parent] ItemPedido item, ProductoByIdDataLoader loader) => loader.LoadAsync(item.IdProducto);
}

[ExtendObjectType(typeof(Producto))]
public class ProductoExt
{
    // El stock exacto solo lo ven roles internos (autorización por campo)
    [Authorize(Roles = ["ADMIN", "CAJERO", "DUENO"])]
    public long StockInterno([Parent] Producto p) => p.Stock;
}

public class ProductoByIdDataLoader(Upstream up, IBatchScheduler s, DataLoaderOptions o)
    : BatchDataLoader<long, Producto>(s, o)
{
    protected override async Task<IReadOnlyDictionary<long, Producto>> LoadBatchAsync(IReadOnlyList<long> keys, CancellationToken ct)
    {
        var res = await up.Client("inventory").SendAsync(up.Req(HttpMethod.Post, "inventory", "/products/batch", keys.Distinct().ToArray()), ct);
        res.EnsureSuccessStatusCode();
        var list = (await res.Content.ReadFromJsonAsync<List<Producto>>(Upstream.J, ct))!;
        return list.ToDictionary(p => p.Id);
    }
}
