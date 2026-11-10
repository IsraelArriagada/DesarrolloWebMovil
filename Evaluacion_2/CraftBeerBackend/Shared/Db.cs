using Oracle.ManagedDataAccess.Client;
using System.Data;

namespace CraftBeer.Shared;

/// <summary>Acceso a Oracle con consultas parametrizadas y stored procedures.</summary>
public class Db(string connectionString)
{
    public OracleConnection Open()
    {
        var c = new OracleConnection(connectionString);
        c.Open();
        return c;
    }

    public async Task<List<Dictionary<string, object?>>> QueryAsync(string sql, params (string, object?)[] p)
    {
        using var c = Open();
        using var cmd = c.CreateCommand();
        cmd.BindByName = true;
        cmd.CommandText = sql;
        foreach (var (n, v) in p) cmd.Parameters.Add(new OracleParameter(n, v ?? DBNull.Value));
        using var r = await cmd.ExecuteReaderAsync();
        var list = new List<Dictionary<string, object?>>();
        while (await r.ReadAsync())
        {
            var row = new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase);
            for (int i = 0; i < r.FieldCount; i++) row[r.GetName(i)] = r.IsDBNull(i) ? null : r.GetValue(i);
            list.Add(row);
        }
        return list;
    }

    public async Task<int> ExecAsync(string sql, params (string, object?)[] p)
    {
        using var c = Open();
        using var cmd = c.CreateCommand();
        cmd.BindByName = true;
        cmd.CommandText = sql;
        foreach (var (n, v) in p) cmd.Parameters.Add(new OracleParameter(n, v ?? DBNull.Value));
        return await cmd.ExecuteNonQueryAsync();
    }

    /// <summary>Ejecuta un SP. Parámetros OUT: pasar (nombre, OracleDbType, tamaño) en outs; se devuelven por nombre.</summary>
    public async Task<Dictionary<string, string?>> CallAsync(string sp,
        (string, object?)[] ins, (string, OracleDbType, int)[] outs)
    {
        using var c = Open();
        using var cmd = c.CreateCommand();
        cmd.BindByName = true;
        cmd.CommandType = CommandType.StoredProcedure;
        cmd.CommandText = sp;
        foreach (var (n, v) in ins) cmd.Parameters.Add(new OracleParameter(n, v ?? DBNull.Value));
        foreach (var (n, t, s) in outs)
            cmd.Parameters.Add(new OracleParameter(n, t, s, null, ParameterDirection.Output));
        await cmd.ExecuteNonQueryAsync();
        var res = new Dictionary<string, string?>();
        foreach (var (n, _, _) in outs)
        {
            var v = cmd.Parameters[n].Value;
            res[n] = v is Oracle.ManagedDataAccess.Types.INullable { IsNull: true } ? null : v?.ToString();
        }
        return res;
    }
}

public static class Conn
{
    public static string For(string user, string pwdVar) =>
        $"User Id={user};Password={Secrets.Get(pwdVar)};Data Source={Environment.GetEnvironmentVariable("ORACLE_HOST") ?? "oracle"}:1521/XEPDB1;Connection Timeout=15";
}
