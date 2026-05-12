var builder = WebApplication.CreateBuilder(args);

builder.WebHost.UseUrls("http://localhost:5000");

var app = builder.Build();

app.MapGet("/temperature/celsius", () => $"{Random.Shared.Next(-20, 41)}'C");

app.Run();
