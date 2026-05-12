using var httpClient = new HttpClient
{
    BaseAddress = new Uri("http://localhost:5000")
};

var temperature = await httpClient.GetStringAsync("/temperature/celsius");

Console.WriteLine(temperature);
