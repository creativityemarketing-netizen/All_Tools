const form = document.querySelector("#exportForm");
const statusEl = document.querySelector("#status");
const button = document.querySelector("#submitButton");
const channelInput = document.querySelector("#channelUrl");
const limitInput = document.querySelector("#limit");
const preview = document.querySelector("#channelPreview");
const avatar = document.querySelector("#channelAvatar");
const channelTitle = document.querySelector("#channelTitle");
const channelHandle = document.querySelector("#channelHandle");
const channelDescription = document.querySelector("#channelDescription");
const progressPanel = document.querySelector("#progressPanel");
const progressLabel = document.querySelector("#progressLabel");
const progressPercent = document.querySelector("#progressPercent");
const progressFill = document.querySelector("#progressFill");

let previewTimer;
let lastPreviewUrl = "";

function setStatus(message, type = "") {
  statusEl.textContent = message;
  statusEl.className = `status ${type}`.trim();
}

function setProgress(percent, message) {
  const safePercent = Math.max(0, Math.min(100, Number(percent) || 0));
  progressPanel.hidden = false;
  progressFill.style.width = `${safePercent}%`;
  progressPercent.textContent = `${safePercent}%`;
  progressLabel.textContent = message || "Working";
}

function renderPreview(data) {
  channelTitle.textContent = data.title || "YouTube channel";
  channelHandle.textContent = [data.handle, data.channelId].filter(Boolean).join("  ");
  channelDescription.textContent = data.description || "Public YouTube channel";
  avatar.src = data.thumbnail || "";
  avatar.alt = data.title || "Channel image";
  avatar.classList.toggle("is-empty", !data.thumbnail);
  preview.hidden = false;
}

async function loadPreview(force = false) {
  const channelUrl = channelInput.value.trim();
  if (!channelUrl || (!force && channelUrl === lastPreviewUrl)) return;
  lastPreviewUrl = channelUrl;
  setStatus("Checking channel...");

  const response = await fetch("preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ channelUrl }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || "Could not load channel preview.");
  }
  renderPreview(await response.json());
  setStatus("Channel found. Starting export will show progress here.", "success");
}

function schedulePreview() {
  clearTimeout(previewTimer);
  const value = channelInput.value.trim();
  if (!value || value.length < 12) return;
  previewTimer = setTimeout(() => {
    loadPreview().catch((error) => setStatus(error.message, "error"));
  }, 700);
}

async function startExport() {
  const payload = {
    channelUrl: channelInput.value,
    limit: limitInput.value,
  };

  const response = await fetch("export/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || "Export failed.");
  }
  return (await response.json()).jobId;
}

async function pollJob(jobId) {
  while (true) {
    const response = await fetch(`export/status?id=${encodeURIComponent(jobId)}`);
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Could not read export progress.");
    }
    const job = await response.json();
    setProgress(job.percent, job.message);

    if (job.status === "error") throw new Error(job.error || job.message || "Export failed.");
    if (job.status === "done") {
      const link = document.createElement("a");
      link.href = `export/download?id=${encodeURIComponent(jobId)}`;
      link.download = job.filename || "youtube-channel.xlsx";
      document.body.appendChild(link);
      link.click();
      link.remove();
      setStatus("Excel file downloaded.", "success");
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 1200));
  }
}

channelInput.addEventListener("input", schedulePreview);
channelInput.addEventListener("blur", () => {
  loadPreview().catch((error) => setStatus(error.message, "error"));
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  button.disabled = true;
  progressPanel.hidden = true;
  setProgress(0, "Preparing");

  try {
    await loadPreview(true);
    setProgress(2, "Starting export");
    setStatus("Fetching public YouTube data. Empty limit means all content and can take a long time.");
    const jobId = await startExport();
    await pollJob(jobId);
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    button.disabled = false;
  }
});

