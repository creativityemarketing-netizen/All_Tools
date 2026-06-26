const form = document.querySelector("#lookup-form");
const input = document.querySelector("#video-id");
const submitButton = form.querySelector('button[type="submit"]');
const submitLabel = submitButton.querySelector("span");
const result = document.querySelector("#result");
const errorBox = document.querySelector("#error");
const copyButton = document.querySelector("#copy-link");
const foundBadge = document.querySelector("#found-badge");

let currentVideoUrl = "";

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
  const hasCreator = Boolean(data.username && data.profile_url);

  foundBadge.innerHTML = data.public_found
    ? "<i></i> Public video found"
    : "<i></i> Date decoded from ID";
  document.querySelector("#result-id").textContent = `ID ${data.video_id}`;
  document.querySelector("#published-at").textContent = formatDate(data.published_at);
  document.querySelector("#video-title").textContent = data.message || data.title || "TikTok publication";
  document.querySelector("#author-name").textContent = hasCreator ? (data.author_name || data.username) : "Account unknown";
  document.querySelector("#username").textContent = hasCreator ? `@${data.username}` : "Not available from ID only";
  document.querySelector("#avatar").textContent = hasCreator ? (data.author_name || data.username)[0].toUpperCase() : "?";

  const thumbnail = document.querySelector("#thumbnail");
  if (data.thumbnail_url) {
    thumbnail.src = data.thumbnail_url;
    thumbnail.alt = data.title ? `Thumbnail for ${data.title}` : "TikTok video thumbnail";
  } else {
    thumbnail.removeAttribute("src");
    thumbnail.alt = "";
  }

  const creatorLink = document.querySelector("#creator-link");
  if (hasCreator) {
    creatorLink.href = data.profile_url;
    creatorLink.classList.remove("disabled");
  } else {
    creatorLink.removeAttribute("href");
    creatorLink.classList.add("disabled");
  }

  const videoLink = document.querySelector("#video-link");
  videoLink.href = data.video_url;

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
  return date.toISOString().slice(0, 19).replace("T", " ") + " UTC";
}
