using Grpc.Core;
using Microsoft.AspNetCore.Server.Kestrel.Core;
using TemperatureGrpc;

var builder = WebApplication.CreateBuilder(args);

builder.WebHost.ConfigureKestrel(options =>
{
    options.ListenLocalhost(5001, listenOptions =>
    {
        listenOptions.Protocols = HttpProtocols.Http2;
    });
});

builder.Services.AddGrpc();

var app = builder.Build();

app.MapGrpcService<TemperatureServiceImplementation>();

app.Run();

public sealed class TemperatureServiceImplementation : TemperatureService.TemperatureServiceBase
{
    public override Task<TemperatureReply> GetTemperatureCelsius(TemperatureRequest request, ServerCallContext context)
    {
        return Task.FromResult(new TemperatureReply
        {
            Value = $"{Random.Shared.Next(-20, 41)}'C"
        });
    }
}
