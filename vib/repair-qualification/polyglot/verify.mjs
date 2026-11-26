import fs from 'node:fs';
const [contractPath,reportPath]=process.argv.slice(2);
const c=JSON.parse(fs.readFileSync(contractPath,'utf8')), r=JSON.parse(fs.readFileSync(reportPath,'utf8'));
const need=new Map(Object.entries(c.cases));
if(r.source!==c.source||r.mode!=='after'||!Array.isArray(r.cases)||r.cases.length!==need.size||r.counts.total!==need.size||r.counts.passed!==need.size||r.counts.failed!==0)throw Error('invalid receipt header');
for(const x of r.cases){const k=x.boundary+'/'+x.case,expected=need.get(k);if(expected===undefined||x.expected!==expected||x.outcome!==expected||x.pass!==true)throw Error('invalid case '+k);need.delete(k);}
if(need.size)throw Error('omitted cases');
