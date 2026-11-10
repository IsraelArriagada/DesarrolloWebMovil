namespace CraftBeer.Shared;

/// <summary>Resuelve secretos por referencia (variable de entorno). Nunca hay valores en el código.</summary>
public static class Secrets
{
    public static string Get(string name, bool required = true)
    {
        var v = Environment.GetEnvironmentVariable(name);
        if (string.IsNullOrWhiteSpace(v) && required)
            throw new InvalidOperationException($"Secreto '{name}' no configurado");
        return v ?? "";
    }
}
