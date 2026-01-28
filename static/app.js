const $ = (sel, el=document) => el.querySelector(sel);
const $$ = (sel, el=document) => Array.from(el.querySelectorAll(sel));

const table = $("#task-table");
const tbody = $("#task-body");
const projId = table?.dataset.project;

$("#q")?.addEventListener("input", (e)=>{
  const q = e.target.value.trim().toLowerCase();
  $$(".data-row", tbody).forEach(tr=>{
    const text = tr.innerText.toLowerCase();
    tr.style.display = text.includes(q) ? "" : "none";
  });
  updateGroupCounts();
});

document.querySelector('[data-action="toggle-groups"]')?.addEventListener("click", ()=>{
  $$(".group-row", tbody).forEach(gr=>{
    let next = gr.nextElementSibling;
    const hide = !(next && next.style.display === "none");
    while(next && !next.classList.contains("group-row")){
      next.style.display = hide ? "none" : "";
      next = next.nextElementSibling;
    }
  });
});

tbody?.addEventListener("change", async (e)=>{
  const t = e.target;
  if(!t.classList.contains("cell-edit")) return;

  const tr = t.closest("tr");
  let id = tr.dataset.id;

  if(!id){
    const payload = collectRow(tr);
    const res = await fetch(`/tasks/create`,{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body: JSON.stringify({ project_id: Number(projId), ...payload })
    });
    const data = await res.json();
    tr.dataset.id = data.id;
    id = data.id;
  }

  const name = t.dataset.name;
  const body = {};
  body[name] = t.value;
  await fetch(`/tasks/${id}/update-json`,{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body: JSON.stringify(body)
  });
});

function collectRow(tr){
  return {
    cat1: $(".c1", tr)?.innerText.trim(),
    cat2: $(".c2", tr)?.innerText.trim(),
    dept_from: $(".c3", tr)?.innerText.trim(),
    dept_to: $(".c4", tr)?.innerText.trim(),
    due_date: $('input[data-name="due_date"]', tr)?.value || null,
    status: $('select[data-name="status"]', tr)?.value || "Not Started",
    reason: $('input[data-name="reason"]', tr)?.value || ""
  }
}

function insertRow(direction){
  const tpl = $("#row-template").content.firstElementChild.cloneNode(true);
  const sel = document.getSelection();
  let anchor = sel?.anchorNode?.closest?.("tr.data-row");
  if(!anchor) anchor = $$(".data-row", tbody).pop();

  const g = anchor?.dataset.group || "";
  $(".c1", tpl).innerText = g;
  $(".c2", tpl).innerText = "";
  $(".c3", tpl).innerText = anchor?.querySelector(".c3")?.innerText || "";
  $(".c4", tpl).innerText = anchor?.querySelector(".c4")?.innerText || "";

  if(direction === "above") tbody.insertBefore(tpl, anchor);
  else tbody.insertBefore(tpl, anchor.nextSibling);

  updateGroupCounts();
  $('input[data-name="due_date"]', tpl)?.focus();
}

$("#add-row-below")?.addEventListener("click", ()=>insertRow("below"));
$("#add-row-above")?.addEventListener("click", ()=>insertRow("above"));

function updateGroupCounts(){
  const groups = {};
  $$(".data-row", tbody).forEach(tr=>{
    if(tr.style.display==="none") return;
    groups[tr.dataset.group] = (groups[tr.dataset.group]||0)+1;
  });
  $$(".group-row", tbody).forEach(gr=>{
    const key = gr.dataset.group;
    $(".group-count", gr).textContent = `(${groups[key]||0})`;
  });
}
updateGroupCounts();

document.addEventListener('htmx:afterRequest', (e)=>{
  if(e.detail.successful){
  }
});

async function saveField(tid, key, val){
  try{
    const r = await fetch(`/tasks/${tid}/update-json`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({[key]: val})
    });
    if(!r.ok) console.warn('save failed', await r.text());
  }catch(e){ console.error(e); }
}

async function openProjectDelays(pid){
  const res = await fetch(`/projects/${pid}/delays.json`);
  if(!res.ok) return alert(`Load error: ${res.status}`);
  const data = await res.json();

  const modal = document.getElementById("delay-modal");
  const list = modal.querySelector(".delay-list");
  const title = modal.querySelector(".modal-head strong");
  list.innerHTML = "";

  title.textContent = `지연 중 (${data.project.code}) – ${data.count}건`;

  for(const it of data.items){
    const li = document.createElement("li");
    li.className = "delay-item";
    li.innerHTML = `
      <div class="tit">
        <span class="cat1">${it.cat1 || "-"}</span>
        <span class="sep">›</span>
        <span class="cat2">${it.cat2 || "-"}</span>
      </div>
      <div class="meta">
        <span class="muted">FROM: ${it.dept_from || "-"}</span>
        <span class="muted">TO: ${it.dept_to || "-"}</span>
        <span class="muted">Due: ${it.due_date || "-"}</span>
        <span class="muted">지연: ${it.late_days ?? "-"}일</span>
        <span class="muted">사유: ${it.reason || ""}</span>
      </div>
    `;
    list.appendChild(li);
  }

  modal.classList.add("open");
}

function closeDelayModal(){
  document.getElementById("delay-modal").classList.remove("open");
}

window.openProjectDelays = openProjectDelays;
window.closeDelayModal = closeDelayModal;

document.addEventListener('change', async (e) => {
  const fileInput = e.target;
  if (!fileInput.classList.contains('js-file')) return;
  
  const tid = fileInput.dataset.tid;
  const files = Array.from(fileInput.files);
  
  if (files.length === 0) return;
  
  const formData = new FormData();
  files.forEach(file => {
    formData.append('attachments', file);
  });
  
  try {
    const response = await fetch(`/tasks/${tid}/upload`, {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      const error = await response.json();
      console.error('Upload error:', error);
      alert(`Upload failed: ${error.detail || 'Unknown error'}`);
      return;
    }
    
    const data = await response.json();
    console.log('Upload successful:', data);
    
    location.reload();
  } catch (error) {
    console.error('Upload error:', error);
    alert(`Upload failed: ${error.message}`);
  }
});
