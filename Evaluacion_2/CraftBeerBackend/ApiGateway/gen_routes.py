import json
SVC = {"inventory":"inventory","clients":"clients","orders":"orders","payments":"payments","delivery":"delivery","graphql":"graphql"}
routes = []
def r(up, down, svc, methods, auth=True, role=None, prio=0, limit="1s", n=10):
    x = {
      "UpstreamPathTemplate": "/api/v1"+up, "DownstreamPathTemplate": down,
      "DownstreamScheme":"http","DownstreamHostAndPorts":[{"Host":SVC[svc],"Port":8080}],
      "UpstreamHttpMethod": methods, "Priority": prio,
      "AddHeadersToRequest": {},
      "RateLimitOptions":{"EnableRateLimiting":True,"ClientWhitelist":[],"Period":limit,"PeriodTimespan":1,"Limit":n},
      "QoSOptions":{"TimeoutValue":8000,"ExceptionsAllowedBeforeBreaking":0}
    }
    x["QoSOptions"] = {"TimeoutValue":8000}
    if auth:
        x["AuthenticationOptions"]={"AuthenticationProviderKey":"Bearer","AllowedScopes":[]}
        x["AddHeadersToRequest"]={"X-User-Id":"Claims[sub] > value","X-User-Role":"Claims[role] > value"}
        if role: x["RouteClaimsRequirement"]={"role":role}
    routes.append(x)
# públicas
r("/products","/products","inventory",["GET"],auth=False)
r("/products/{id}","/products/{id}","inventory",["GET"],auth=False)
r("/auth/login","/auth/login","clients",["POST"],auth=False,limit="1m",n=10)
r("/clients","/clients","clients",["POST"],auth=False,limit="1m",n=10)
r("/payments/webhook","/payments/webhook","payments",["POST"],auth=False)
# admin productos
r("/products","/products","inventory",["POST"],role="ADMIN")
r("/products/{id}","/products/{id}","inventory",["PUT"],role="ADMIN")
r("/products/{id}/availability","/products/{id}/availability","inventory",["PATCH"],role="ADMIN")
# clientes
r("/clients/me","/clients/me","clients",["GET"],prio=10)
r("/clients/{id}","/clients/{id}","clients",["GET","PUT"])
# pedidos
r("/orders","/orders","orders",["POST"])
r("/orders/me","/orders/me","orders",["GET"],prio=10)
r("/orders/{id}","/orders/{id}","orders",["GET"])
r("/orders/{id}/cancel","/orders/{id}/cancel","orders",["PATCH"])
# pagos
r("/payments","/payments","payments",["POST"])
r("/receipts/{orderId}","/receipts/{orderId}","payments",["GET"])
r("/receipts/{orderId}/resend","/receipts/{orderId}/resend","payments",["POST"])
r("/reports/sales","/reports/sales","payments",["GET"])
# despacho
r("/dispatch-orders","/dispatch-orders","delivery",["GET"])
r("/dispatch-orders/{id}/status","/dispatch-orders/{id}/status","delivery",["PATCH"])
# GraphQL (privado: solo accesible vía gateway, requiere JWT)
r("/graphql","/graphql","graphql",["POST"])
cfg={"Routes":routes,"GlobalConfiguration":{"BaseUrl":"http://localhost:5000",
  "RateLimitOptions":{"QuotaExceededMessage":"{\"error\":\"Demasiadas solicitudes\"}","HttpStatusCode":429}}}
json.dump(cfg,open("ocelot.json","w"),indent=2)
print(len(routes),"rutas")
