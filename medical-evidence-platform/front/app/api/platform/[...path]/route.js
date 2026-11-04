const allowed=new Set(['v1/patients','v1/assistant/tools','v1/assistant/ask','v1/documents/import','v1/documents/list','v1/documents/ocr','v1/documents/reviews','v1/documents/review-queue','v1/documents/search','v1/queries/creatinine-latest-two','v1/ingestion/lab-records']);
async function forward(request,context){
 const {path}=await context.params;const route=path.join('/');
 if(!allowed.has(route)&&!/^v1\/assistant\/answers\/[a-zA-Z0-9_-]+$/.test(route)&&!/^v1\/documents\/reviews\/[a-zA-Z0-9_-]+$/.test(route)&&!/^v1\/documents\/[a-zA-Z0-9_-]+\/pages\/[0-9]+$/.test(route)&&!/^v1\/evidence\/[a-zA-Z0-9_-]+$/.test(route))return Response.json({detail:'Unsupported endpoint'},{status:404});
 try{
 const upstream=await fetch(`${process.env.BACKEND_URL||'http://127.0.0.1:8000'}/${route}`,{method:request.method,headers:{'Content-Type':'application/json','Authorization':request.headers.get('Authorization')||''},body:request.method==='POST'?await request.text():undefined,cache:'no-store',signal:AbortSignal.timeout(route==='v1/documents/ocr'?150000:route==='v1/assistant/ask'?100000:15000)});
 return new Response(await upstream.arrayBuffer(),{status:upstream.status,headers:{'Content-Type':upstream.headers.get('content-type')||'application/json','Cache-Control':'no-store'}});
 }catch{return Response.json({detail:'后端连接失败，请确认 API 服务已启动'},{status:502})}
}
export const GET=forward;export const POST=forward;
