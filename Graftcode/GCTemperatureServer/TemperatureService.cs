namespace GCTemperatureServer;

public class TemperatureService
{
    public string GetTemperatureCelsius()
    {
        return $"{Random.Shared.Next(-20, 41)}'C";
    }
}
