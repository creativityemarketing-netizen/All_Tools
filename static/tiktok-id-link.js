const form = document.querySelector("#lookup-form");
const input = document.querySelector("#video-id");
const submitButton = form.querySelector('button[type="submit"]');
const submitLabel = submitButton.querySelector("span");
const result = document.querySelector("#result");
const errorBox = document.querySelector("#error");
const copyButton = document.querySelector("#copy-link");

let currentVideoUrl = "";

document.querySelector(".example").addEventListener("click", () => {
  input.value = document.querySelector(".example").dataset.id;
  input.focus();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setLoading(true);
  errorBox.hidden = true;
  result.hidden = true;

  try {
    const response = await fetch("/api/tiktok-id-lookup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: input.value }),
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "The lookup failed.");
    }

    showResult(data);
  } catch (error) {
    errorBox.textContent = error.message;
    errorBox.hidden = false;
  } finally {
    setLoading(false);
  }
});

copyButton.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(currentVideoUrl);
    copyButton.querySelector("span").textContent = "Copied";
    window.setTimeout(() => {
      copyButton.querySelector("span").textContent = "Copy link";
    }, 1800);
  } catch {
    errorBox.textContent = "Could not copy automatically. Open the publication and copy its address.";
    errorBox.hidden = false;
  }
});

function showResult(data) {
  currentVideoUrl = data.video_url;
  document.querySelector("#result-id").textContent = `ID ${data.video_id}`;
  document.querySelector("#published-at").textContent = formatDate(data.published_at);
  document.querySelector("#video-title").textContent = data.title || "TikTok publication";
  document.querySelector("#author-name").textContent = data.author_name || data.username;
  document.querySelector("#username").textContent = data.username ? `@${data.username}` : "Public profile";
  document.querySelector("#avatar").textContent = (data.author_name || data.username || "?")[0].toUpperCase();

  const thumbnail = document.querySelector("#thumbnail");
  thumbnail.src = data.thumbnail_url || "";
  thumbnail.alt = data.title ? `Thumbnail for ${data.title}` : "TikTok video thumbnail";

  const creatorLink = document.querySelector("#creator-link");
  creatorLink.href = data.profile_url || data.video_url;

  document.querySelector("#video-link").href = data.video_url;
  result.hidden = false;
  result.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function setLoading(loading) {
  submitButton.disabled = loading;
  submitLabel.textContent = loading ? "Finding..." : "Find links";
}

function formatDate(value) {
  if (!value) {
    return "Unknown date";
  }

  const date = new Date(value);
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}
