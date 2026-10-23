"""Build a single offline HTML preview using the actual exported STL meshes."""
import base64
import gzip
import json
import math
from pathlib import Path

import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix, translation_matrix
from design import assembly_parameters

ROOT = Path(__file__).resolve().parents[1]
design = assembly_parameters()
side, back = design["side"], design["back"]
mount = (
    translation_matrix([0, design["card_y"], design["lift"]])
    @ rotation_matrix(-back, [1, 0, 0])
    @ rotation_matrix(-side, [0, 1, 0])
    @ rotation_matrix(math.pi / 2, [1, 0, 0])
)


def geometry(name, transform):
    mesh = trimesh.load_mesh(ROOT / "output" / f"{name}.stl")
    mesh.apply_transform(transform)
    vertices = mesh.triangles.reshape(-1, 3)
    normals = np.repeat(mesh.face_normals, 3, axis=0)
    return np.hstack([vertices, normals]).round(5).reshape(-1).tolist()


payload = {
    "assembly": [
        geometry("base", np.eye(4)),
        geometry("card", mount),
    ],
    "parts": [
        geometry("base", translation_matrix([-40, -30, 0])),
        geometry("card", translation_matrix([45, 35, 0])),
    ],
}
image = base64.b64encode((ROOT / "output" / "assembled.png").read_bytes()).decode()
assembly_height = max(max(values[2::6]) for values in payload["assembly"])
mesh_archive = base64.b64encode(gzip.compress(
    json.dumps(payload, separators=(",", ":")).encode(), mtime=0
)).decode()
template = r'''<!doctype html>
<html lang="ja"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nikko ポーカートロフィー | プレビュー</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#101820;color:#f4f1e9;font:16px/1.7 system-ui,sans-serif}
main{max-width:980px;margin:auto;padding:24px 18px}h1{font-size:25px;margin:0 0 6px}
p{margin:8px 0;color:#c6cdd3}.tabs{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0}
button{font:inherit;border:1px solid #53606d;background:#202c38;color:#fff;border-radius:8px;padding:9px 16px;cursor:pointer}
button[aria-pressed=true]{background:#d5b16d;border-color:#d5b16d;color:#151a20}
.stage{position:relative;width:100%;height:min(76vh,760px);min-height:320px;background:#17222d;border:1px solid #35414b;border-radius:14px;overflow:hidden}
img,canvas{width:100%;height:100%;object-fit:contain;display:block}canvas{touch-action:none;cursor:grab}
[hidden]{display:none!important}small{display:block;color:#aab6bf;margin-top:14px}#status{min-height:28px}
</style>
<main>
<h1>Nikko ポーカートロフィー</h1>
<p>幅100 × 奥行70 × 高さ__HEIGHT__ mm ／ カードと台座を別々に印刷</p>
<div class="tabs">
<button data-mode="image" aria-pressed="true">完成画像</button>
<button data-mode="assembly" aria-pressed="false">回して見る</button>
<button data-mode="parts" aria-pressed="false">部品ごと</button>
<button id="reset">角度を戻す</button>
</div>
<div class="stage">
<img id="photo" alt="金色の台座にアイボリーのスペードのAが斜めに差し込まれたNikkoトロフィー" src="data:image/png;base64,__IMAGE__">
<canvas id="view" hidden aria-label="ドラッグして回転できるトロフィーの3Dモデル"></canvas>
</div>
<p id="status" aria-live="polite">実際の印刷用STLから作成した完成イメージです。実物写真ではありません。</p>
<small>「回して見る」ではドラッグで回転、ホイールまたは2本指で拡大縮小できます。画像と3Dデータはこのファイル内に含まれ、外部への通信はありません。</small>
</main>
<script>
'use strict';
const meshArchive="__MESHES__";
let meshes,initTask,requestId=0;
const canvas=document.querySelector('#view'),photo=document.querySelector('#photo'),status=document.querySelector('#status');
let gl,program,buffers,mode='image',yaw=.48,pitch=.36,zoom=__ZOOM__,ready=false;
function shader(type,source){const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;}
async function init(){
 const compressed=Uint8Array.from(atob(meshArchive),c=>c.charCodeAt(0));
 const decoded=new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip'));
 meshes=JSON.parse(await new Response(decoded).text());
 gl=canvas.getContext('webgl',{antialias:true,alpha:false});if(!gl)throw Error('WebGL unavailable');
 program=gl.createProgram();
 gl.attachShader(program,shader(gl.VERTEX_SHADER,`attribute vec3 aPosition;attribute vec3 aNormal;
 uniform vec3 uTarget,uRight,uUp,uEye;uniform float uScale,uAspect;varying vec3 vNormal;
 void main(){vec3 q=aPosition-uTarget;gl_Position=vec4(dot(q,uRight)/(uScale*uAspect),dot(q,uUp)/uScale,-dot(q,uEye)/500.0,1.0);vNormal=aNormal;}`));
 gl.attachShader(program,shader(gl.FRAGMENT_SHADER,`precision mediump float;varying vec3 vNormal;uniform vec3 uColor;
 void main(){vec3 n=normalize(vNormal);float key=max(dot(n,normalize(vec3(-0.5,-0.8,1.0))),0.0);
 float fill=max(dot(n,normalize(vec3(1.0,0.2,0.5))),0.0);float light=0.30+0.58*key+0.18*fill;
 gl_FragColor=vec4(uColor*light,1.0);}`));
 gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));
 gl.useProgram(program);gl.enable(gl.DEPTH_TEST);gl.enable(gl.CULL_FACE);
 buffers={};for(const key of ['assembly','parts'])buffers[key]=meshes[key].map(values=>{const b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(values),gl.STATIC_DRAW);return {buffer:b,count:values.length/6};});
 ready=true;
}
function uniform3(name,values){gl.uniform3fv(gl.getUniformLocation(program,name),values);}
function draw(){
 if(mode==='image'||!ready)return;
 const r=canvas.getBoundingClientRect(),dpr=Math.min(devicePixelRatio||1,2);
 const width=Math.round(r.width*dpr),height=Math.round(r.height*dpr);
 if(canvas.width!==width||canvas.height!==height){canvas.width=width;canvas.height=height;}
 gl.viewport(0,0,width,height);gl.clearColor(.09,.135,.18,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
 const s=Math.sin(yaw),c=Math.cos(yaw),sp=Math.sin(pitch),cp=Math.cos(pitch);
 uniform3('uRight',[c,s,0]);uniform3('uUp',[-s*sp,c*sp,cp]);uniform3('uEye',[s*cp,-c*cp,sp]);
 uniform3('uTarget',mode==='assembly'?[0,0,__CENTER__]:[0,0,4]);
 gl.uniform1f(gl.getUniformLocation(program,'uScale'),zoom);gl.uniform1f(gl.getUniformLocation(program,'uAspect'),width/height);
 const pos=gl.getAttribLocation(program,'aPosition'),normal=gl.getAttribLocation(program,'aNormal');
 buffers[mode].forEach((item,index)=>{gl.bindBuffer(gl.ARRAY_BUFFER,item.buffer);gl.enableVertexAttribArray(pos);gl.vertexAttribPointer(pos,3,gl.FLOAT,false,24,0);gl.enableVertexAttribArray(normal);gl.vertexAttribPointer(normal,3,gl.FLOAT,false,24,12);uniform3('uColor',index===0?[.83,.61,.28]:[.94,.92,.84]);gl.drawArrays(gl.TRIANGLES,0,item.count);});
}
function reset(){yaw=.48;pitch=mode==='parts'?.95:.36;zoom=mode==='parts'?145:__ZOOM__;draw();}
async function setMode(next){
 const request=++requestId;
 if(next!=='image'&&!ready){status.textContent='モデルを読み込んでいます…';try{initTask??=init();await initTask;}catch(error){initTask=null;status.textContent='3Dモデルを読み込めませんでした。「完成画像」でデザインを確認できます。';return;}}
 if(request!==requestId)return;
 mode=next;photo.hidden=mode!=='image';canvas.hidden=mode==='image';
 document.querySelectorAll('[data-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.mode===mode)));
 status.textContent=mode==='image'?'実際の印刷用STLから作成した完成イメージです。実物写真ではありません。':'ドラッグで回転 ／ ホイール・2本指で拡大縮小';reset();
}
document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>setMode(b.dataset.mode));
document.querySelector('#reset').onclick=reset;window.addEventListener('resize',draw);
canvas.addEventListener('wheel',e=>{e.preventDefault();zoom=Math.max(35,Math.min(260,zoom*Math.exp(e.deltaY*.001)));draw();},{passive:false});
const pointers=new Map();let lastDistance=0;
canvas.addEventListener('pointerdown',e=>{canvas.setPointerCapture(e.pointerId);pointers.set(e.pointerId,[e.clientX,e.clientY]);lastDistance=0;});
canvas.addEventListener('pointermove',e=>{
 if(!pointers.has(e.pointerId))return;const prev=pointers.get(e.pointerId);pointers.set(e.pointerId,[e.clientX,e.clientY]);
 if(pointers.size===1){yaw-=(e.clientX-prev[0])*.009;pitch=Math.max(-1.4,Math.min(1.4,pitch+(e.clientY-prev[1])*.009));}
 else{const [a,b]=[...pointers.values()],dist=Math.hypot(a[0]-b[0],a[1]-b[1]);if(lastDistance>0)zoom=Math.max(35,Math.min(260,zoom*lastDistance/Math.max(dist,1)));lastDistance=dist;}
 draw();
});
for(const event of ['pointerup','pointercancel','lostpointercapture'])canvas.addEventListener(event,e=>{pointers.delete(e.pointerId);lastDistance=0;});
</script></html>'''
html = template.replace("__IMAGE__", image).replace(
    "__MESHES__", mesh_archive
).replace("__HEIGHT__", str(round(assembly_height))).replace(
    "__CENTER__", str(round(assembly_height / 2, 3))
).replace("__ZOOM__", str(round(assembly_height * 0.76, 3)))
destination = ROOT / "output" / "nikko_preview.html"
destination.write_text(html)
print(destination, destination.stat().st_size, "bytes")
