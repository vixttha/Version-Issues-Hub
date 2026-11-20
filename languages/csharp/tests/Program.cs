using System;
using System.Text.Json;

static bool IsSupported(string value)
{
    using var document = JsonDocument.Parse(value);
    return document.RootElement.TryGetProperty("version", out var version)
        && version.ValueKind == JsonValueKind.Number
        && version.TryGetInt32(out var number)
        && number == 1;
}

if (!IsSupported("{\"version\":1}") || IsSupported("{\"version\":2}") || IsSupported("{}"))
    throw new InvalidOperationException("JSON version contract mismatch");
