'use strict';
const $ = id => document.getElementById(id);
const key = 'clipview.history.v1';
const bytes = text => new TextEncoder().encode(text).length;
let clips = [], selected = null, mode = 'all', category = null, timer, editing = null;
let lastRaw = null, invalidStorage = false;

function toast(message) {
  $('toast').textContent = message;
  $('toast').style.display = 'block';
  clearTimeout(timer);
  timer = setTimeout(() => $('toast').style.display = 'none', 4500);
}
function warn(message) {
  $('storage-warning').hidden = false;
  $('storage-warning').textContent = message;
}
function validate(rows) {
  if (!Array.isArray(rows) || rows.length > 2000) throw Error('A backup can contain at most 2,000 snippets.');
  const seen = new Set();
  return rows.map(row => {
    if (!row || typeof row.body !== 'string' || !row.body.trim() || bytes(row.body) > 100000)
      throw Error('Each snippet must contain text and fit within 100 KB.');
    if (typeof row.category !== 'string' || !row.category.trim() || Array.from(row.category).length > 80)
      throw Error('Each category must contain 1–80 characters.');
    if (typeof row.pinned !== 'boolean' || typeof row.copied !== 'number' || !Number.isFinite(row.copied) || row.copied < 0 || row.copied > 253402214400)
      throw Error('Invalid pin or copy date.');
    if (seen.has(row.body)) throw Error('Backup contains duplicate snippet text.');
    seen.add(row.body);
    return {body: row.body, category: row.category.trim(), pinned: row.pinned, copied: row.copied};
  });
}
function load() {
  try {
    lastRaw = localStorage.getItem(key);
    const data = JSON.parse(lastRaw || '[]');
    if (!Array.isArray(data)) throw Error('Invalid saved history.');
    const clean = validate(data.map(c => ({...c, copied: c.copied / 1000})));
    invalidStorage = false;
    clips = clean.map((c, i) => ({...c, copied:c.copied*1000, id: typeof data[i].id === 'string' ? data[i].id : crypto.randomUUID()}));
  } catch {
    invalidStorage = true;
    warn('Saved history could not be read. It has not been overwritten. Clear history to reset, or use another browser.');
  }
}
load();
try { document.body.classList.toggle('light', localStorage.getItem('clipview.theme') === 'light'); } catch { /* History errors are reported separately. */ }

function commit(change, allowReset = false) {
  const before = structuredClone(clips), oldSelected = selected;
  try {
    if(invalidStorage && !allowReset)throw Error('Saved history is unreadable. Clear history explicitly before making changes.');
    if (localStorage.getItem(key) !== lastRaw) throw Error('History changed in another tab. Reload before editing.');
    change();
    const raw = JSON.stringify(clips);
    localStorage.setItem(key, raw);
    lastRaw = raw; invalidStorage = false;
    $('storage-warning').hidden = true;
    render();
    return true;
  } catch (error) {
    clips = before; selected = oldSelected;
    if (error.name === 'QuotaExceededError' || error.name === 'SecurityError')
      warn('Changes were not saved. Browser storage is full or unavailable. Export your history before clearing space.');
    toast(error.message || 'Changes were not saved.');
    render();
    return false;
  }
}
function current() { return clips.find(c => c.id === selected); }
function add(body) {
  if (!body.trim() || bytes(body) > 100000) throw Error('Enter text up to 100 KB.');
  let c = clips.find(c => c.body === body);
  if (c) c.copied = Date.now();
  else {
    if (clips.length >= 2000) throw Error('History is full. Delete some snippets first.');
    c = {id:crypto.randomUUID(),body,category:'Unsorted',pinned:false,copied:Date.now()};
    clips.push(c);
  }
  selected = c.id;
}
function resetFilters() { category = null; mode = 'all'; $('search').value = ''; }
function render() {
  const q = $('search').value.toLocaleLowerCase();
  const direction = $('sort').value === 'oldest' ? 1 : -1;
  $('sort-label').textContent = direction === 1 ? 'OLDEST FIRST' : 'RECENT FIRST';
  const rows = clips.filter(c => (mode !== 'pins' || c.pinned) && (!category || c.category === category) && c.body.toLocaleLowerCase().includes(q))
    .sort((a,b) => Number(b.pinned)-Number(a.pinned) || direction*(a.copied-b.copied));
  if (!rows.some(c => c.id === selected)) selected = rows[0]?.id || null;
  $('total').textContent = clips.length;
  $('count').textContent = rows.length + ' snippets';
  $('view-title').textContent = category || (mode === 'pins' ? 'Pinned snippets' : 'All snippets');
  $('all').classList.toggle('active', mode === 'all' && !category);
  $('pins').classList.toggle('active', mode === 'pins');
  $('categories').replaceChildren();
  [...new Set(clips.map(c => c.category))].sort().forEach(name => {
    const b = document.createElement('button');
    b.textContent = '◷  ' + name;
    b.classList.toggle('active', category === name);
    b.onclick = () => { category = name; mode = 'all'; render(); };
    $('categories').append(b);
  });
  $('list').replaceChildren();
  if (!rows.length) {
    const p = document.createElement('p');
    p.textContent = q ? 'No matches. Try a different search.' : 'Nothing here yet. Add a snippet to get started.';
    $('list').append(p);
  }
  rows.forEach(c => {
    const b = document.createElement('button');
    b.className = 'card' + (selected === c.id ? ' active' : '');
    b.setAttribute('aria-pressed', String(selected === c.id));
    const p = document.createElement('p'); p.textContent = c.body.slice(0,135);
    const tags = document.createElement('div'); tags.className = 'tags';
    const tag = document.createElement('span'); tag.className = 'tag'; tag.textContent = c.category;
    const date = document.createElement('span');
    date.textContent = (c.pinned ? '★ · ' : '') + new Date(c.copied).toLocaleDateString(undefined,{month:'short',day:'numeric'});
    tags.append(tag,date); b.append(p,tags);
    b.onclick = () => { selected = c.id; render(); };
    $('list').append(b);
  });
  const c = current();
  $('empty').hidden = !!c; $('selected').hidden = !c;
  if (c) {
    $('body').textContent = c.body; $('category').value = c.category;
    $('date').textContent = 'Copied ' + new Date(c.copied).toLocaleString();
    $('pin').textContent = c.pinned ? '★ Pinned' : '☆ Pin';
    $('pin').setAttribute('aria-pressed', String(c.pinned));
    $('measure').textContent = `${Array.from(c.body).length} characters · ${c.body.split('\n').length} lines`;
  }
}
$('all').onclick = () => { mode='all'; category=null; render(); };
$('pins').onclick = () => { mode='pins'; category=null; render(); };
$('search').oninput = render;
$('sort').onchange = render;
$('add').onclick = () => { editing=null; $('text').value=''; $('dialog-title').textContent='Keep something useful.'; $('dialog').showModal(); $('text').focus(); };
$('edit').onclick = () => { const c=current(); if(c){editing=c.id;$('text').value=c.body;$('dialog-title').textContent='Edit your snippet.';$('dialog').showModal();} };
$('cancel').onclick = () => $('dialog').close();
$('form').onsubmit = e => {
  e.preventDefault();
  const body=$('text').value;
  if (commit(() => {
    if(editing){
      if(!body.trim() || bytes(body)>100000) throw Error('Enter text up to 100 KB.');
      if(clips.some(c=>c.id!==editing && c.body===body)) throw Error('That text is already saved.');
      const c=clips.find(c=>c.id===editing); if(!c) throw Error('Snippet no longer exists.'); c.body=body;
    } else add(body);
    resetFilters();
  })) { $('dialog').close(); $('text').value=''; }
};
$('pin').onclick = () => { if(current())commit(()=>{current().pinned=!current().pinned;}); };
$('save').onclick = () => {
  const name=$('category').value.trim()||'Unsorted';
  if(current() && commit(()=>{
    if(Array.from(name).length>80)throw Error('Category must be 80 characters or fewer.');
    current().category=name; category=null;
  }))toast('Category saved.');
};
$('copy').onclick = async () => {
  const c=current();if(!c)return;
  try { await navigator.clipboard.writeText(c.body);toast('Copied. Ready to paste.'); }
  catch { toast('Clipboard access denied. Select the text and copy it manually.'); }
};
$('delete').onclick = () => { if(current()&&confirm('Delete this snippet?'))commit(()=>{clips=clips.filter(c=>c.id!==selected);}); };
$('clear').onclick = () => { $('include-pins').checked=false; $('clear-dialog').showModal(); };
$('confirm-clear').onclick = () => {
  if(commit(()=>{clips=$('include-pins').checked?[]:clips.filter(c=>c.pinned);resetFilters();}, true)){
    $('clear-dialog').close();toast('History cleared. Your system clipboard is unchanged.');
  }
};
$('theme').onclick = () => {
  document.body.classList.toggle('light');
  try {localStorage.setItem('clipview.theme',document.body.classList.contains('light')?'light':'dark');}
  catch {toast('Theme changed for this session only.');}
};
$('export').onclick = () => {
  try {
    const rows=validate(clips.map(c=>({...c,copied:c.copied/1000})));
    const raw=JSON.stringify({format:'clipview',version:1,clips:rows},null,2);
    if(bytes(raw)>10000000)throw Error('Backup exceeds 10 MB. Export a smaller collection.');
    const url=URL.createObjectURL(new Blob([raw],{type:'application/json'}));
    const a=document.createElement('a');a.href=url;a.download='clipview-backup.json';a.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);toast('Plain-text backup downloaded. Keep it private.');
  }catch(error){toast(error.message);}
};
$('import').onclick = () => $('import-file').click();
$('import-file').onchange = async () => {
  try {
    const file=$('import-file').files[0];if(!file)return;
    if(file.size>10000000)throw Error('Backup exceeds 10 MB.');
    const doc=JSON.parse(await file.text());
    if(!doc||doc.format!=='clipview'||doc.version!==1)throw Error('Unsupported backup format or version.');
    const rows=validate(doc.clips);
    if(!confirm(`Merge ${rows.length} snippets? Existing text and categories will be kept.`))return;
    let added=0;
    if(commit(()=>{
      rows.forEach(row=>{if(!clips.some(c=>c.body===row.body)){clips.push({...row,id:crypto.randomUUID(),copied:row.copied*1000});added++;}});
      if(clips.length>2000)throw Error('Import exceeds the 2,000-snippet limit. Nothing was imported.');
      resetFilters();
    }))toast(`Imported ${added}; skipped ${rows.length-added} duplicates.`);
  }catch(error){toast('Import failed: '+error.message);}
  finally{$('import-file').value='';}
};
$('load').onclick = () => {
  if(commit(()=>{
    ['git status --short','Hi! I’ll send the updated notes this afternoon.','SELECT title, created_at\nFROM notes\nORDER BY created_at DESC;','def greet(name):\n    return f"Hello, {name}!"','Read chapter 4 and revise the lab notes.'].forEach(add);
    resetFilters();
  }))toast('Five examples added. Search for SELECT to recover the third.');
};
window.addEventListener('storage',e=>{if(e.key===key){load();render();toast('History updated from another tab.');}});
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key==='k'){e.preventDefault();$('search').focus();}});
render();
