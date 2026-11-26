export function verify(contract: unknown, receipt: unknown): void {
  function object(value: unknown): Record<string,unknown> {if(typeof value!=='object'||value===null||Array.isArray(value))throw Error('expected object');return value as Record<string,unknown>;}
  const c=object(contract),r=object(receipt),counts=object(r.counts),expected=object(c.cases);
  const ids=Object.keys(expected);if(r.source!==c.source||r.mode!=='after'||!Array.isArray(r.cases)||r.cases.length!==ids.length||counts.total!==ids.length||counts.passed!==ids.length||counts.failed!==0)throw Error('bad header');
  const seen=new Set<string>();
  for(const row of r.cases as unknown[]){const x=object(row);if(typeof x.boundary!=='string'||typeof x.case!=='string')throw Error('bad id');const id=x.boundary+'/'+x.case;
    if(!Object.prototype.hasOwnProperty.call(expected,id)||seen.has(id)||x.expected!==expected[id]||x.outcome!==expected[id]||x.pass!==true)throw Error('bad assertion '+id);seen.add(id);}
  if(seen.size!==ids.length)throw Error('incomplete');
}
