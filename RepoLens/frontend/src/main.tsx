import React,{useRef,useState}from"react";
import{createRoot}from"react-dom/client";
import cytoscape from"cytoscape";
import"./style.css";
const API=location.hostname==="localhost"?"http://localhost:8000":"";

function App(){
 const[path,setPath]=useState("/repo");
 const[job,setJob]=useState<any>();
 const[repo,setRepo]=useState<string>();
 const[overview,setOverview]=useState<any>();
 const[q,setQ]=useState("authenticate");
 const[results,setResults]=useState<any[]>([]);
 const[impact,setImpact]=useState<any>();
 const[architecture,setArchitecture]=useState<any>();
 const[hotspots,setHotspots]=useState<any[]>([]);
 const[contributors,setContributors]=useState<any[]>([]);
 const graphRef=useRef<HTMLDivElement>(null);

 async function start(url:string,body?:any){
  const r=await fetch(API+url,{method:"POST",headers:{"content-type":"application/json"},body:body?JSON.stringify(body):undefined});
  const j=await r.json(); poll(j.job_id);
 }
 function poll(id:string){
  const timer=setInterval(async()=>{
   const j=await(await fetch(API+"/api/jobs/"+id)).json();
   setJob(j);
   if(j.status==="complete"){
    clearInterval(timer); setRepo(j.repository_id); load(j.repository_id);
   }
   if(j.status==="failed")clearInterval(timer);
  },500);
 }
 async function load(id:string){
  const [o,g,a,h,c]=await Promise.all([
   fetch(`${API}/api/repositories/${id}/overview`).then(r=>r.json()),
   fetch(`${API}/api/repositories/${id}/graph?limit=1500`).then(r=>r.json()),
   fetch(`${API}/api/repositories/${id}/architecture`).then(r=>r.json()),
   fetch(`${API}/api/repositories/${id}/git/hotspots`).then(r=>r.json()),
   fetch(`${API}/api/repositories/${id}/git/contributors`).then(r=>r.json())
  ]);
  setOverview(o);setArchitecture(a);setHotspots(h);setContributors(c);
  if(graphRef.current){
   cytoscape({container:graphRef.current,
    elements:[...g.nodes.map((n:any)=>({data:n})),...g.edges.map((e:any,i:number)=>({data:{id:"e"+i,source:e.source,target:e.target,label:e.kind}}))],
    style:[
     {selector:"node",style:{label:"data(label)","font-size":8,"background-color":"#5de4c7",color:"#dfe7ff"}},
     {selector:'node[type="file"]',style:{shape:"round-rectangle","background-color":"#7aa2f7"}},
     {selector:"edge",style:{width:1,"line-color":"#39445f","target-arrow-color":"#39445f","target-arrow-shape":"triangle","curve-style":"bezier"}}
    ],layout:{name:"cose",animate:false}});
  }
 }
 async function search(){
  if(repo)setResults(await fetch(`${API}/api/repositories/${repo}/search?q=${encodeURIComponent(q)}`).then(r=>r.json()));
 }
 async function analyze(id:string){
  if(repo)setImpact(await fetch(`${API}/api/repositories/${repo}/impact?node=${encodeURIComponent(id)}`).then(r=>r.json()));
 }
 return <main>
  <header><div><b>REPOLENS</b><span>GRAPH-FIRST REPOSITORY INTELLIGENCE</span></div><i>LOCAL ANALYSIS · NO CODE UPLOAD</i></header>
  <section className="hero"><h1>Understand a codebase<br/>before you change it.</h1>
   <p>Index symbols, imports, calls, inheritance, cycles, Git history, and change impact with graph-backed evidence.</p>
   <div className="index"><input value={path} onChange={e=>setPath(e.target.value)}/><button onClick={()=>start("/api/repositories/index",{path})}>INDEX</button>{repo&&<button onClick={()=>start(`/api/repositories/${repo}/reindex`)}>INCREMENTAL REINDEX</button>}</div>
   {job&&<small>{job.status.toUpperCase()} · {job.progress||0}% · {job.changes?`${job.changes.reindexed} files reindexed`:""} {job.error||""}</small>}
  </section>
  {overview&&<>
   <section className="metrics">{Object.entries(overview.metrics).filter(([k])=>!["languages","edge_types"].includes(k)).map(([k,v]:any)=><article key={k}><strong>{v}</strong><span>{k}</span></article>)}</section>
   <section className="grid">
    <div className="panel graph"><h2>Dependency Graph</h2><div ref={graphRef}/></div>
    <div className="panel"><h2>Symbol Search</h2><div className="search"><input value={q} onChange={e=>setQ(e.target.value)}/><button onClick={search}>SEARCH</button></div>{results.map(r=><button key={r.id} className="result" onClick={()=>analyze(r.id)}><b>{r.name}</b><span>{r.kind} · {r.file}:{r.line}</span></button>)}</div>
    <div className="panel impact"><h2>Impact Radius</h2>{impact?<><div className="risk">{impact.risk_score}<span>RISK</span></div><p>{impact.affected_nodes.length} downstream nodes across {impact.affected_files.length} files</p><h3>Recommended tests</h3>{impact.recommended_tests.length?impact.recommended_tests.map((x:string)=><code key={x}>{x}</code>):<small>No connected tests found.</small>}</>:<p>Select a symbol to compute impact.</p>}</div>
    <div className="panel"><h2>Architecture Health</h2><p>{architecture?.cycles?.length||0} cycles · {architecture?.inheritance?.length||0} inheritance edges</p>{architecture?.hotspots?.slice(0,8).map((x:any)=><div className="lang" key={x.file}><span>{x.file}</span><b>{x.coupling}</b></div>)}</div>
    <div className="panel"><h2>Git Hotspots</h2>{hotspots.slice(0,10).map((x:any)=><div className="lang" key={x.file}><span>{x.file}</span><b>{x.changes}</b></div>)}</div>
    <div className="panel"><h2>Contributors</h2>{contributors.slice(0,10).map((x:any)=><div className="lang" key={x.author}><span>{x.author}</span><b>{x.commits}</b></div>)}</div>
   </section>
  </>}
 </main>
}
createRoot(document.getElementById("root")!).render(<App/>);
