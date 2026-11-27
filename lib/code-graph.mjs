// Native VIB raw graph retrieval, separate from feature evidence format.
import { lstatSync, realpathSync } from "node:fs";
import { join, resolve, relative } from "node:path";
import { parseEvidenceObject, readBytes, sha256 } from "./inspect-evidence.mjs";
const PROJECT="vixttha/version-issues-hub";
const SHA=/^[a-f0-9]{40}$/;
const HASH=/^[a-f0-9]{64}$/;
function read(root,path,max) {
  const file=join(root,path);
  if (!lstatSync(file).isFile() || relative(root,realpathSync(file))!==path) throw new Error("Invalid archive file");
  return readBytes(file,max);
}
export function codeGraph(command, opts) {
  if (opts.scope==="development") {
    if(opts.project?.toLowerCase()!==PROJECT || !/^v0\.0\.0\.[1-9][0-9]{0,8}$/.test(opts.version??"") ||
       !SHA.test(opts.source??"") || !HASH.test(opts["graph-sha256"]??"")) throw new Error("Invalid development graph identity");
    const root=realpathSync(resolve(opts.archive)), base=join("development-code-graphs",opts.version,opts.source);
    const receipt=parseEvidenceObject(read(root,join(base,"receipt.json"),128*1024),"receipt.json");
    const keys=["repository","version","issue","branch","source","tree","canonical","schema","source_kind","production_integrated","historical_test_claim","finalized","graphify_version","mode","nodes","edges","graph_sha256","run","attempt"];
    if(Object.keys(receipt).length!==keys.length || keys.some(k=>!Object.hasOwn(receipt,k)) ||
       receipt.repository?.toLowerCase()!==PROJECT || receipt.version!==opts.version || receipt.source!==opts.source ||
       receipt.branch!=="plan/checkpoint-"+opts.version || !Number.isSafeInteger(receipt.issue) || receipt.issue<1 ||
       !SHA.test(receipt.tree??"") || !SHA.test(receipt.canonical??"") || receipt.schema!==1 ||
       receipt.source_kind!=="development_snapshot" || receipt.finalized!==false || receipt.production_integrated!==false ||
       receipt.historical_test_claim!==false || receipt.graphify_version!=="0.9.109" || receipt.mode!=="code-only AST" ||
       receipt.graph_sha256!==opts["graph-sha256"] || ![receipt.run,receipt.attempt].every(x=>typeof x==="string" && /^[1-9][0-9]*$/.test(x)) ||
       !Number.isSafeInteger(receipt.nodes) || receipt.nodes<1 || !Number.isSafeInteger(receipt.edges) || receipt.edges<0)
      throw new Error("Development receipt identity mismatch");
    const raw=read(root,join(base,"graph.json"),8*1024*1024);
    if(sha256(raw)!==receipt.graph_sha256) throw new Error("Graph SHA-256 mismatch");
    const graph=parseEvidenceObject(raw,"graph.json");
    if(!Array.isArray(graph.nodes)||!Array.isArray(graph.links)) throw new Error("Graph structure mismatch");
    const ids=new Set(graph.nodes.map(n=>n?.id));
    if(graph.built_at_commit!==receipt.source || graph.nodes.length!==receipt.nodes || ids.size!==receipt.nodes ||
       [...ids].some(id=>typeof id!=="string"||!id) || graph.links.length!==receipt.edges ||
       graph.links.some(e=>!ids.has(e?.source)||!ids.has(e?.target))) throw new Error("Graph structure mismatch");
    return command==="code-graph"?{receipt,graph}:receipt;
  }
  if (opts.scope==="engineering") {
    const extension = ["v0.0.0.41","v0.0.0.42"].includes(opts.version) ||
      (opts.version==="v0.0.0.40" && opts.source==="43ef2b660aae5ccee00009e900509158f0137d0f");
    const versions=extension?["v0.0.0.40","v0.0.0.41","v0.0.0.42"]:["v0.0.0.37","v0.0.0.38","v0.0.0.39","v0.0.0.40"], issues=extension?[86,92,94]:[53,82,84,86];
    if(opts.project?.toLowerCase()!==PROJECT || !versions.includes(opts.version) ||
       !SHA.test(opts.source??"") || !HASH.test(opts["graph-sha256"]??"")) throw new Error("Invalid engineering graph identity");
    const root=realpathSync(resolve(opts.archive)), base=extension?"engineering-code-graphs-40-42":"engineering-code-graphs";
    const index=parseEvidenceObject(read(root,join(base,"index.json"),2*1024*1024),"index.json");
    if(index.repository?.toLowerCase()!==PROJECT || index.schema!==1 || index.failures.length!==0 ||
       index.results.length!==versions.length || index.results.some((r,i)=>r.version!==versions[i] || r.issue!==issues[i]))
      throw new Error("Incomplete engineering graph inventory");
    const item=index.results[versions.indexOf(opts.version)];
    const receipt=parseEvidenceObject(read(root,join(base,opts.version,"receipt.json"),128*1024),"receipt.json");
    if(JSON.stringify(item)!==JSON.stringify(receipt) || receipt.source!==opts.source ||
       receipt.graph_sha256!==opts["graph-sha256"] || !SHA.test(receipt.tree??"") ||
       receipt.source_kind!=="actual_engineering_merge" || receipt.historical_test_claim!==false ||
       receipt.production_integrated!==false || receipt.mode!=="code-only AST" ||
       receipt.graphify_version!=="0.9.109" ||
       receipt.disposition!==(opts.version==="v0.0.0.37"?"experimental_engineering_merge":"engineering_complete_production_deferred"))
      throw new Error("Engineering receipt identity mismatch");
    const raw=read(root,join(base,opts.version,"graph.json"),8*1024*1024);
    if(sha256(raw)!==receipt.graph_sha256) throw new Error("Graph SHA-256 mismatch");
    const graph=parseEvidenceObject(raw,"graph.json"), ids=new Set(graph.nodes.map(n=>n.id));
    if(graph.built_at_commit!==receipt.source || graph.nodes.length!==receipt.nodes || graph.nodes.length!==ids.size ||
       graph.links.length!==receipt.edges || graph.links.some(e=>!ids.has(e.source)||!ids.has(e.target))) throw new Error("Graph structure mismatch");
    return command==="code-graph"?{receipt,graph}:receipt;
  }
  if (opts.scope==="candidate") {
    if (opts.project?.toLowerCase()!==PROJECT || opts.version!=="v0.0.0.37" ||
        !SHA.test(opts.source??"") || !HASH.test(opts["graph-sha256"]??"")) throw new Error("Invalid candidate identity");
    const root=realpathSync(resolve(opts.archive));
    const base=join("candidate-code-graphs",opts.version,opts.source);
    const receipt=parseEvidenceObject(read(root,join(base,"receipt.json"),128*1024),"receipt.json");
    if(receipt.version!==opts.version || receipt.issue!==53 || receipt.repository?.toLowerCase()!==PROJECT ||
       receipt.source!==opts.source || receipt.graph_sha256!==opts["graph-sha256"] ||
       receipt.graphify_version!=="0.9.109" || receipt.source_kind!=="unmerged_engineering_candidate" ||
       receipt.historical_test_claim!==false || receipt.mode!=="code-only AST") throw new Error("Candidate receipt identity mismatch");
    const raw=read(root,join(base,"graph.json"),8*1024*1024);
    if(sha256(raw)!==receipt.graph_sha256) throw new Error("Graph SHA-256 mismatch");
    const graph=parseEvidenceObject(raw,"graph.json");
    const ids=new Set(graph.nodes.map(n=>n.id));
    if(graph.built_at_commit!==receipt.source || graph.nodes.length!==receipt.nodes || graph.nodes.length!==ids.size ||
       graph.links.length!==receipt.edges || graph.links.some(e=>!ids.has(e.source)||!ids.has(e.target))) throw new Error("Graph structure mismatch");
    return command==="code-graph"?{receipt,graph}:receipt;
  }
  if (opts.project?.toLowerCase()!==PROJECT || !/^v0\.0\.0\.(?:[1-9]|[12][0-9]|3[0-6])$/.test(opts.version??"")) throw new Error("Unsupported VIB graph identity");
  if (!["fix","cumulative"].includes(opts.scope)) throw new Error("Specify --scope fix or cumulative");
  if (!SHA.test(opts.source??"") || !HASH.test(opts["graph-sha256"]??"")) throw new Error("Require independently recorded --source and --graph-sha256");
  const root=realpathSync(resolve(opts.archive));
  const base=opts.scope==="fix"?"code-graphs":"cumulative-code-graphs";
  const index=parseEvidenceObject(read(root,join(base,"index.json"),2*1024*1024),"index.json");
  if(index.repository.toLowerCase()!==PROJECT || index.failures.length!==0 || index.results.length!==36 ||
    index.results.some((r,i)=>r.version!==`v0.0.0.${i+1}`) || new Set(index.results.map(r=>r.issue)).size!==36) throw new Error("Incomplete or duplicate graph inventory");
  const item=index.results.find(r=>r.version===opts.version);
  const receipt=parseEvidenceObject(read(root,join(base,opts.version,"receipt.json"),128*1024),"receipt.json");
  if(JSON.stringify(item)!==JSON.stringify(receipt) || receipt.source!==opts.source || receipt.graph_sha256!==opts["graph-sha256"] ||
    receipt.graphify_version!=="0.9.109" || receipt.reconstructed!==true || receipt.historical_test_claim!==false ||
    (opts.scope==="cumulative" && receipt.source_kind!=="reconstructed_cumulative_engineering_prefix") ||
    (opts.scope==="fix" && !["historical_engineering_fix","operational_preflight_revision"].includes(receipt.source_kind))) throw new Error("Graph receipt identity or digest pin mismatch");
  const raw=read(root,join(base,opts.version,"graph.json"),8*1024*1024);
  if(sha256(raw)!==receipt.graph_sha256) throw new Error("Graph SHA-256 mismatch");
  const graph=parseEvidenceObject(raw,"graph.json");
  const ids=new Set(graph.nodes.map(n=>n.id));
  if(graph.built_at_commit!==receipt.source || graph.nodes.length!==receipt.nodes || graph.nodes.length!==ids.size ||
    graph.links.length!==receipt.edges || graph.links.some(e=>!ids.has(e.source)||!ids.has(e.target))) throw new Error("Graph structure mismatch");
  return command==="code-graph"?{receipt,graph}:receipt;
}
