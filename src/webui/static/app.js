import { EditorState } from "https://esm.sh/@codemirror/state@6";
import {
  EditorView,
  keymap,
  lineNumbers,
  highlightActiveLineGutter,
  highlightSpecialChars,
  drawSelection,
  dropCursor,
  rectangularSelection,
  crosshairCursor
} from "https://esm.sh/@codemirror/view@6";
import {
  defaultKeymap,
  history,
  historyKeymap,
  indentWithTab
} from "https://esm.sh/@codemirror/commands@6";
import {
  bracketMatching,
  indentOnInput
} from "https://esm.sh/@codemirror/language@6";
import {
  closeBrackets,
  closeBracketsKeymap
} from "https://esm.sh/@codemirror/autocomplete@6";
import { json } from "https://esm.sh/@codemirror/lang-json@6";
import { oneDark } from "https://esm.sh/@codemirror/theme-one-dark@6";

const saveBtn = document.getElementById("saveBtn");
const revertBtn = document.getElementById("revertBtn");
const restartBtn = document.getElementById("restartBtn");
const statusEl = document.getElementById("status");
const editorWrap = document.getElementById("editorWrap");

let currentFile = "config.json";
let original = "";
let view = null;

function setStatus(msg, isError = false) {
  statusEl.textContent = msg || "";
  statusEl.style.color = isError ? "#ffb4aa" : "";
}

function setDirty(dirty) {
  saveBtn.disabled = !dirty;
  revertBtn.disabled = !dirty;
}

function getEditorText() {
  if (!view) return "";
  return view.state.doc.toString();
}

function setEditorText(text) {
  if (!view) return;

  view.dispatch({
    changes: { from: 0, to: view.state.doc.length, insert: text }
  });
}

function isDirty() {
  return getEditorText() !== original;
}

function refreshDirtyUI() {
  setDirty(isDirty());
  setStatus(isDirty() ? "Unsaved changes" : "");
}

function createEditor(initialText) {
  // destroy existing
  if (view) {
    view.destroy();
    view = null;
  }

  const onUpdate = EditorView.updateListener.of((update) => {
    if (update.docChanged) {
      refreshDirtyUI();
    }
  });

  const state = EditorState.create({
    doc: initialText,
    extensions: [
      oneDark,
      lineNumbers(),
      highlightActiveLineGutter(),
      highlightSpecialChars(),
      history(),
      drawSelection(),
      dropCursor(),
      indentOnInput(),
      bracketMatching(),
      closeBrackets(),
      rectangularSelection(),
      crosshairCursor(),
      json(),

      keymap.of([
        indentWithTab,
        ...closeBracketsKeymap,
        ...defaultKeymap,
        ...historyKeymap,
      ]),

      onUpdate,

      // make the editor use the full height of the wrapper
      EditorView.theme({
        "&": { height: "100%" },
        ".cm-scroller": { overflow: "auto" }
      }),
    ],
  });

  view = new EditorView({
    state,
    parent: editorWrap,
  });
}

async function loadFile(name) {
  setStatus(`Loading ${name}...`);
  setDirty(false);

  const res = await fetch(`/api/file/${encodeURIComponent(name)}`);
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    setStatus(data.error || "Load failed", true);
    createEditor("");
    original = "";
    currentFile = name;
    setDirty(false);
    return;
  }

  const content = data.content || "";
  original = content;
  currentFile = name;

  createEditor(content);
  setDirty(false);
  setStatus(`Loaded ${name}`);
}

revertBtn.addEventListener("click", () => {
  setEditorText(original);
  setDirty(false);
  setStatus("Reverted");
});

saveBtn.addEventListener("click", async () => {
  try {
    JSON.parse(getEditorText());
  } catch (e) {
    setStatus(`Invalid JSON: ${e.message}`, true);
    return;
  }

  setStatus("Saving...");
  const res = await fetch(`/api/file/${encodeURIComponent(currentFile)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content: getEditorText() }),
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    setStatus(data.error || "Save failed", true);
    return;
  }

  // reload so editor matches server-normalized formatting
  await loadFile(currentFile);
  setStatus("Saved");
});

restartBtn.addEventListener("click", async () => {
  setStatus("Restarting...");
  const res = await fetch("/api/restart", { method: "POST" });
  const data = await res.json().catch(() => ({}));

  if (!res.ok || !data.ok) {
    setStatus(data.error || "Restart failed", true);
    return;
  }

  setStatus("Restarted");
});

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", async () => {
    const file = tab.dataset.file;
    if (file === currentFile) return;

    if (isDirty()) {
      const ok = confirm("You have unsaved changes. Switch tabs and lose them?");
      if (!ok) return;
    }

    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");

    await loadFile(file);
  });
});

loadFile("config.json");
