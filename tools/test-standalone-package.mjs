// Isolated package regression for VIB #80. Standard Node/Git only.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { copyFileSync, cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, renameSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
const root=resolve(dirname(fileURLToPath(import.meta.url)),"..");
const source="041e187dc1d383082c1a4805e6d4743eec97e535", project="vixttha/Version-Issues-Hub", version="v0.0.0.37";
const retained=join(root,"archives","candidates",source,"45994489992-1");
const pins=[
  ["shard-0001","340d395271b0e45c7fedf1e8a4efb6c794eceaa1b862c4722d6fb7e58fb6e149",32],
  ["shard-0002","fc63c09e0e9b993330acece28bff33b05aae39408a38cc9594637f0339eadca9",6],
];
const receipt=JSON.parse(readFileSync(join(retained,"candidate-receipt.json"),"utf8"));
assert.equal(receipt.source,source); assert.equal(receipt.version,version); assert.equal(receipt.status,"candidate_only");
assert.equal(receipt.runner_id,"45994489992"); assert.equal(receipt.runner_attempt,"1");
assert.equal(receipt.veraphify_source,"13996f0a57e038bb9a2d61339d6c49448075f715");
assert.equal(receipt.shards.length,2);
const checkout=resolve(process.argv[2] ?? "standalone-source");
const git=spawnSync("git",["-C",checkout,"rev-parse","HEAD"],{encoding:"utf8",timeout:15000});
assert.equal(git.status,0,git.stderr); assert.equal(git.stdout.trim(),source);
const work=mkdtempSync(join(tmpdir(),"vib standalone package "));
const pack=join(work,"runtime"), cwd=join(work,"unrelated cwd"), archives=join(work,"archive copy");
const files=["veraphifiy.mjs","lib/inspect-evidence.mjs","lib/code-graph.mjs","lib/handoff-profile.json","lib/LYDITE-LICENSE","LICENSE"];
const hash=b=>createHash("sha256").update(b).digest("hex");
const invoke=(args,expected=null)=>{
  const env={...process.env}; delete env.NODE_PATH; delete env.NODE_OPTIONS;
  const p=spawnSync(process.execPath,[join(pack,"veraphifiy.mjs"),...args],{cwd,env,encoding:"utf8",timeout:45000,maxBuffer:16*1024*1024,windowsHide:true});
  assert.ifError(p.error); assert.equal(p.signal,null);
  if(expected!==null){assert.notEqual(p.status,0,"Unexpected success: "+args.join(" "));assert.match(p.stderr,expected);assert.equal(p.stdout.trim(),"");return;}
  assert.equal(p.status,0,p.stderr); return p.stdout.trim();
};
const cli=(command,archive,...args)=>[command,"--archive",archive,"--project",project,"--version",version,"--source",source,...args];
function withMissing(file,fn){
  const original=join(pack,file), moved=original+".missing";renameSync(original,moved);
  try{fn();}finally{renameSync(moved,original);}
}
try{
  mkdirSync(cwd,{recursive:true});mkdirSync(archives,{recursive:true});
  for(const file of files){const dest=join(pack,file);mkdirSync(dirname(dest),{recursive:true});copyFileSync(join(root,file),dest);assert.deepEqual(readFileSync(dest),readFileSync(join(root,file)));}
  assert.deepEqual(readdirSync(pack).sort(),["LICENSE","lib","veraphifiy.mjs"]);
  assert.equal(existsSync(join(pack,"test-vault")),false);
  assert.match(invoke(["--help"]),/code-verify\/code-graph/);assert.equal(invoke(["--version"]),"v0.0.9");
  for(const [dir,digest,count] of pins){
    const shard=receipt.shards.find(x=>x.directory===dir);
    assert.equal(shard.archive_sha256,digest);assert.equal(shard.features.length,count);
    const original=join(retained,dir,"archive"), dest=join(archives,dir);
    cpSync(original,dest,{recursive:true});const entries=readdirSync(dest);assert.equal(entries.length,1);
    const file=join(dest,entries[0]), raw=readFileSync(file);assert.equal(hash(raw),digest);
    const result=JSON.parse(invoke(cli("verify",dest,"--archive-sha256",digest)));
    assert.equal(result.source,source);assert.equal(result.archive_sha256,digest);assert.equal(result.version,version);
    for(const id of shard.features){
      const lookup=JSON.parse(invoke(cli("lookup",dest,"--archive-sha256",digest,"--feature","feature:"+id)));
      assert.deepEqual(lookup,receipt.lookups[id]);
    }
    const wrongSource=cli("verify",dest,"--archive-sha256",digest);wrongSource[wrongSource.indexOf("--source")+1]="0".repeat(40);
    invoke(wrongSource,/Archive source commit mismatch/);
    invoke(cli("verify",dest,"--archive-sha256","0".repeat(64)),/Archive SHA-256 mismatch/);
    invoke(cli("verify",dest,"--source",source),/may only be specified once/);
    const missing=cli("verify",dest);missing[missing.indexOf("--version")+1]="v0.0.0.999999";
    invoke(missing,/Project version is not archived/);
    invoke(cli("lookup",dest,"--archive-sha256",digest,"--feature","feature:not-present"),/Feature is not present/);
    writeFileSync(file,Buffer.concat([raw,Buffer.from(" ")]));
    invoke(cli("verify",dest,"--archive-sha256",digest),/Archive SHA-256 mismatch/);
    writeFileSync(file,raw);
    assert.deepEqual(readFileSync(file),raw);assert.deepEqual(readFileSync(join(original,entries[0])),raw);
    // Replay actual archived producer bytes against an independently pinned Git checkout.
    const payload=JSON.parse(raw.toString("utf8")), evidence=join(work,dir+" evidence"), fresh=join(work,dir+" fresh archive");
    mkdirSync(evidence);for(const name of ["graph","receipt"])writeFileSync(join(evidence,name+".json"),Buffer.from(payload[name],"base64"));
    const args=cli("import",fresh,"--checkout",checkout,"--evidence",evidence);
    assert.equal(JSON.parse(invoke(args)).archive_sha256,digest);
    assert.equal(JSON.parse(invoke(args)).archive_sha256,digest);
    assert.deepEqual(readdirSync(fresh),entries);assert.deepEqual(readFileSync(join(fresh,entries[0])),raw);
    // Malformed producer evidence must not create a new archive.
    const broken=join(work,dir+" rejected archive");writeFileSync(join(evidence,"receipt.json"),"{");
    invoke(cli("import",broken,"--checkout",checkout,"--evidence",evidence),/Invalid JSON/);
    assert.equal(existsSync(broken),false);
  }
  // Native development graph retrieval must also work with the isolated package.
  const devArgs=["code-verify","--archive",join(root,"archives"),"--project",project,"--version","v0.0.0.43","--scope","development","--source","0147d51eb7965034848ea623be55676149a74895","--graph-sha256","c3a87f26b3a61ba746305382c98cb582fb03da128d87cbf59c2b3d004a4766ab"];
  const dev=JSON.parse(invoke(devArgs));assert.equal(dev.finalized,false);assert.equal(dev.nodes,1150);assert.equal(dev.edges,3683);
  withMissing("lib/inspect-evidence.mjs",()=>invoke(["--help"],/ERR_MODULE_NOT_FOUND/));
  withMissing("lib/code-graph.mjs",()=>invoke(["--help"],/ERR_MODULE_NOT_FOUND/));
  withMissing("lib/handoff-profile.json",()=>invoke(["--help"],/ENOENT/));
  const profile=join(pack,"lib/handoff-profile.json"), originalProfile=readFileSync(profile);
  try{writeFileSync(profile,"{");invoke(["--help"],/SyntaxError/);}finally{writeFileSync(profile,originalProfile);}
  assert.equal(invoke(["--version"]),"v0.0.9");
  console.log(JSON.stringify({status:"passed",platform:process.platform,source,shards:2,lookups:38,development_source:dev.source,missing_dependencies:3,malformed_profile:1}));
}finally{rmSync(work,{recursive:true,force:true});}
