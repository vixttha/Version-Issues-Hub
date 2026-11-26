using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Text.Json;
using var c=JsonDocument.Parse(File.ReadAllText(args[0]));
using var r=JsonDocument.Parse(File.ReadAllText(args[1]));
var root=r.RootElement;var contract=c.RootElement;
var cases=contract.GetProperty("cases").EnumerateObject().ToDictionary(p=>p.Name,p=>p.Value.GetString());
var counts=root.GetProperty("counts");var rows=root.GetProperty("cases");
if(root.GetProperty("source").GetString()!=contract.GetProperty("source").GetString()||root.GetProperty("mode").GetString()!="after"||counts.GetProperty("total").GetInt32()!=cases.Count||counts.GetProperty("passed").GetInt32()!=cases.Count||counts.GetProperty("failed").GetInt32()!=0||rows.GetArrayLength()!=cases.Count)throw new Exception("bad header");
foreach(var row in rows.EnumerateArray()){
 var id=row.GetProperty("boundary").GetString()+"/"+row.GetProperty("case").GetString();
 if(!cases.Remove(id,out var expected)||row.GetProperty("expected").GetString()!=expected||row.GetProperty("outcome").GetString()!=expected||row.GetProperty("pass").ValueKind!=JsonValueKind.True)throw new Exception("bad case "+id);
}
if(cases.Count!=0)throw new Exception("missing cases");
