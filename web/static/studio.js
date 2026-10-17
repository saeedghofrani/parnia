"use strict";
const $ = id => document.getElementById(id);
const form = $("studio-form");
let mode = "text", uploaded = null, preview = null, timer = null, animationTimer = null;
let requestVersion = 0, controller = null;
const status = (text, error = false) => { $("status").textContent = text; $("status").classList.toggle("error", error); };
function options(output = "preview") {
  return { mode, text: $("text").value, font: $("font").value, theme: $("theme").value,
    character: $("character").value, message: $("message").value, scale: +$("scale").value,
    color: $("color").value, background: $("background").value, foreground: $("foreground").value,
    animation: $("animation").value, border: $("border").value, padding: +$("padding").value,
    alignment: $("alignment").value, delay: +$("delay").value, width: +$("width").value,
    brightness: +$("brightness").value, contrast: +$("contrast").value, ramp: $("ramp").value,
    invert: $("invert").checked, edges: $("edges").checked, mirror: $("mirror").checked, output };
}
function payload(output) {
  const data = new FormData(); data.append("options", JSON.stringify(options(output)));
  if (mode === "image" && uploaded) data.append("image", uploaded);
  return data;
}
function rgb(x, y, width, height, palette) {
  const t = x / Math.max(1, width - 1);
  if (palette === "none") return preview.foreground;
  if (palette === "neon") return "rgb(90,255,190)";
  if (palette === "rainbow") return `hsl(${(x / Math.max(1, width) + y / Math.max(1, height) * .12) * 360} 100% 60%)`;
  const endpoints = { gradient: [[255,90,160],[75,200,255]], ocean: [[60,110,255],[60,255,210]], sunset: [[255,100,70],[205,90,255]] };
  const [a,b] = endpoints[palette] || endpoints.gradient;
  return `rgb(${a.map((v,i) => Math.round(v+(b[i]-v)*t)).join(",")})`;
}
function draw(art) {
  if (!preview) return;
  const canvas = $("canvas"), w = Math.max(1, preview.width)*10+48, h = preview.height*18+48;
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  // Cap bitmap memory while retaining readable previews of large text.
  const renderRatio = Math.min(ratio, Math.sqrt(8000000 / (w*h)));
  canvas.width = Math.ceil(w*renderRatio); canvas.height = Math.ceil(h*renderRatio);
  const fit = Math.min(1, Math.max(200, $("stage").clientWidth-48)/w);
  canvas.style.width = `${w*fit*+$("zoom").value}px`;
  canvas.style.height = `${h*fit*+$("zoom").value}px`;
  const ctx = canvas.getContext("2d"); ctx.scale(renderRatio, renderRatio);
  ctx.fillStyle = preview.background; ctx.fillRect(0,0,w,h);
  $("stage").style.background = preview.background;
  ctx.font = '14px Consolas, "DejaVu Sans Mono", monospace'; ctx.textBaseline = "top";
  const rows = art.split("\n");
  rows.forEach((row,y) => Array.from(row).forEach((char,x) => {
    if (char === " ") return;
    ctx.fillStyle = rgb(x,y,preview.width,preview.height,preview.color);
    ctx.shadowBlur = preview.color === "neon" ? 7 : 0; ctx.shadowColor = ctx.fillStyle;
    ctx.fillText(char,24+x*10,24+y*18);
  }));
}
function stopAnimation() { clearTimeout(animationTimer); animationTimer = null; }
function replay() {
  stopAnimation(); if (!preview) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { draw(preview.art); return; }
  let frame = 0; const tick = () => { draw(preview.frames[frame]); frame++;
    if (frame < preview.frames.length) animationTimer = setTimeout(tick, preview.delay*1000); };
  tick();
}
function setMode(next) {
  mode = next; requestVersion++; controller?.abort(); stopAnimation();
  ["text","image"].forEach(item => { const active = item === mode;
    $(`${item}-panel`).hidden = !active; $(`${item}-tab`).classList.toggle("active", active);
    $(`${item}-tab`).setAttribute("aria-selected", String(active)); $(`${item}-tab`).tabIndex = active ? 0 : -1; });
  schedule();
}
function updateLabels() {
  $("scale-value").value = $("scale").value+"×"; $("width-value").value = $("width").value;
  ["brightness","contrast"].forEach(id => $(id+"-value").value = (+$(id).value).toFixed(1));
  $("delay-value").value = Math.round(+$("delay").value*1000)+" ms";
  $("zoom-value").value = Math.round(+$("zoom").value*100)+"%";
}
function schedule() { clearTimeout(timer); updateLabels(); timer = setTimeout(generate, 350); }
async function generate() {
  clearTimeout(timer); controller?.abort(); stopAnimation();
  const version = ++requestVersion;
  if (mode === "image" && !uploaded) { preview = null; $("canvas").hidden = true;
    $("empty-state").hidden = false; $("dimensions").textContent = "Choose a photo";
    $("accessible-art").textContent = ""; status("Drop a photo or choose one to get started."); return; }
  controller = new AbortController(); status("Creating your character art…");
  try {
    const response = await fetch("/api/render", {method:"POST", body:payload("preview"), signal:controller.signal});
    const result = await response.json(); if (version !== requestVersion) return;
    if (!response.ok) throw new Error(result.error || "Could not create art.");
    preview = result; $("canvas").hidden = false; $("empty-state").hidden = true;
    $("dimensions").textContent = `${result.width} columns × ${result.height} rows`;
    $("accessible-art").textContent = result.art;
    status("Looking good. Your art is ready to download."); replay();
  } catch (error) { if (error.name !== "AbortError" && version === requestVersion) status(error.message, true); }
}
async function download(type, button) {
  if (mode === "image" && !uploaded) { status("Choose a photo first.", true); return; }
  button.disabled = true; status(`Preparing your ${type.toUpperCase()}…`);
  try {
    const response = await fetch("/api/render", {method:"POST", body:payload(type)});
    if (!response.ok) { const result = await response.json(); throw new Error(result.error || "Download failed."); }
    const url = URL.createObjectURL(await response.blob()), link = document.createElement("a");
    link.href = url; link.download = `parnia.${type}`; document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000); status(`Your ${type.toUpperCase()} is ready. Check your downloads.`);
  } catch (error) { status(error.message, true); } finally { button.disabled = false; }
}
function chooseFile(file) {
  if (!file) return;
  if (file.size > 8*1024*1024) { status("Choose a photo smaller than 8 MB.", true); return; }
  uploaded = file; $("upload-name").textContent = file.name; schedule();
}
form.addEventListener("submit", event => { event.preventDefault(); generate(); });
form.addEventListener("input", event => { if (event.target.id !== "image") schedule(); });
$("text-tab").addEventListener("click", () => setMode("text")); $("image-tab").addEventListener("click", () => setMode("image"));
document.querySelector(".mode-tabs").addEventListener("keydown", event => {
  if (["ArrowLeft","ArrowRight","Home","End"].includes(event.key)) { event.preventDefault();
    setMode(event.key === "Home" ? "text" : event.key === "End" ? "image" : mode === "text" ? "image" : "text");
    $(mode+"-tab").focus(); }
});
$("image").addEventListener("change", event => chooseFile(event.target.files[0]));
$("drop-zone").addEventListener("dragover", event => { event.preventDefault(); $("drop-zone").classList.add("dragging"); });
$("drop-zone").addEventListener("dragleave", () => $("drop-zone").classList.remove("dragging"));
$("drop-zone").addEventListener("drop", event => { event.preventDefault(); $("drop-zone").classList.remove("dragging"); chooseFile(event.dataTransfer.files[0]); });
$("replay").addEventListener("click", replay);
$("copy").addEventListener("click", async () => {
  if (!preview) return;
  try { await navigator.clipboard.writeText(preview.art); status("Character art copied to your clipboard."); }
  catch { status("Clipboard access is unavailable. Download TXT instead.", true); }
});
$("zoom").addEventListener("input", () => { updateLabels(); stopAnimation(); if (preview) draw(preview.art); });
window.addEventListener("resize", () => { stopAnimation(); if (preview) draw(preview.art); });
document.querySelectorAll("[data-download]").forEach(button => button.addEventListener("click", () => download(button.dataset.download, button)));
$("reset").addEventListener("click", () => { form.reset(); uploaded = null; preview = null;
  $("upload-name").textContent = "Choose or drop an image"; $("zoom").value = "1"; setMode("text"); });
document.querySelectorAll("[data-preset]").forEach(button => button.addEventListener("click", () => {
  form.reset(); const name = button.dataset.preset;
  const values = name === "neon" ? {theme:"binary",color:"neon",animation:"pixels"} :
    name === "love" ? {theme:"hearts",color:"sunset",font:"rounded",animation:"typewriter"} :
    {color:"none",background:"#faf7f0",foreground:"#342e3d",border:"single"};
  Object.entries(values).forEach(([id,value]) => $(id).value=value); setMode("text");
}));
updateLabels(); generate();
