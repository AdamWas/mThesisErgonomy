using Grpc.Net.Client;
using TemperatureGrpc;

using var channel = GrpcChannel.ForAddress("http://localhost:5001");
var client = new TemperatureService.TemperatureServiceClient(channel);

var temperature = await client.GetTemperatureCelsiusAsync(new TemperatureRequest());

Console.WriteLine(temperature.Value);
