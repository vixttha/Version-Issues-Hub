import java.nio.file.*;import java.nio.charset.StandardCharsets;import java.util.*;
public class Verify {
 public static void main(String[] args)throws Exception{
  var c=Files.readAllLines(Path.of(args[0]),StandardCharsets.UTF_8);var r=Files.readAllLines(Path.of(args[1]),StandardCharsets.UTF_8);
  Map<String,String> expected=new HashMap<>();
  for(String line:c.subList(1,c.size())){var f=line.split("\\t",-1);if(f.length!=2||expected.put(f[0],f[1])!=null)throw new IllegalArgumentException("bad contract");}
  int n=expected.size();if(!r.get(0).equals(c.get(0)+"\tafter\t"+n+"\t"+n+"\t0")||r.size()!=n+1)throw new IllegalArgumentException("bad header");
  for(String line:r.subList(1,r.size())){var f=line.split("\\t",-1);if(f.length!=4)throw new IllegalArgumentException("bad row");var want=expected.remove(f[0]);if(want==null||!want.equals(f[1])||!want.equals(f[2])||!f[3].equals("true"))throw new IllegalArgumentException("bad case "+f[0]);}
  if(!expected.isEmpty())throw new IllegalArgumentException("missing rows");
 }
}
