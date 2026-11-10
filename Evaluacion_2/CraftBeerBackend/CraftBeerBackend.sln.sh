#!/bin/bash
# Genera la solución .sln (opcional, para abrir en Visual Studio): bash CraftBeerBackend.sln.sh
dotnet new sln -n CraftBeerBackend
for p in Shared/CraftBeer.Shared ApiGateway/ApiGateway GraphQLGateway/GraphQLGateway InventoryService/InventoryService ClientsService/ClientsService OrdersService/OrdersService PaymentsService/PaymentsService DeliveryService/DeliveryService NotificationsService/NotificationsService; do dotnet sln add $p.csproj; done
