<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Instagram Date Finder</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <main class="shell">
    <header class="hero">
      <div class="mark">IG</div>
      <h1>Instagram Date Finder</h1>
      <p>Search the fixed private database by Instagram link, shortcode, or post ID.</p>
    </header>

    <section class="card">
      <label for="query">Post link, shortcode, or Post ID</label>
      <div class="search-row">
        <input id="query" type="text" autocomplete="off" spellcheck="false" placeholder="https://www.instagram.com/p/... or 3818230543192566459_36116147692">
        <button id="search-btn" type="button">Search</button>
      </div>
      <p id="db-status" class="db-status">Loading database status...</p>
      <div id="result" class="result" hidden></div>
    </section>
  </main>

  <script>
    const $ = (id) => document.getElementById(id);

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
      }[char]));
    }

    async function loadStats() {
      try {
        const response = await fetch("api.php?action=stats");
        const data = await response.json();
        if (data.ok) {
          $("db-status").textContent = `${data.info.rows.toLocaleString()} posts loaded from the private database`;
        } else {
          $("db-status").textContent = data.error || "Database status unavailable";
        }
      } catch {
        $("db-status").textContent = "Database status unavailable";
      }
    }

    function inputLooksLikeLink(value) {
      return /instagram\.com\/(p|reel|reels|tv)\//i.test(value);
    }

    function renderConvertedValue(query, data) {
      if (inputLooksLikeLink(query)) {
        const id = data._numeric_id || data.numeric_id || "";
        return id ? `<p class="converted"><span>Post ID</span><strong>${escapeHtml(id)}</strong></p>` : "";
      }
      const url = data._url || data.generated_url || data["Post URL"] || "";
      return url ? `<p class="converted"><span>Instagram link</span><a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${escapeHtml(url)}</a></p>` : "";
    }

    function renderExact(query, data) {
      const date = data._date_formatted || data["Published At"] || "Date unavailable";
      return `
        <div class="box success">
          <div class="badge">Exact date</div>
          <h2>${escapeHtml(date)}</h2>
          ${renderConvertedValue(query, data)}
        </div>`;
    }

    function renderRange(query, data) {
      return `
        <div class="box warning">
          <div class="badge">Estimated range</div>
          <h2>${escapeHtml(data.range_label)}</h2>
          ${renderConvertedValue(query, data)}
        </div>`;
    }

    function renderError(message, hint) {
      return `
        <div class="box error">
          <div class="badge">Not found</div>
          <h2>${escapeHtml(message)}</h2>
          ${hint ? `<p>${escapeHtml(hint)}</p>` : ""}
        </div>`;
    }

    async function search() {
      const query = $("query").value.trim();
      if (!query) {
        $("result").hidden = false;
        $("result").innerHTML = renderError("Enter a post link, shortcode, or Post ID.");
        return;
      }

      $("search-btn").disabled = true;
      $("search-btn").textContent = "Searching...";
      try {
        const response = await fetch("api.php?action=search", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({query})
        });
        const raw = await response.text();
        let data;
        try {
          data = JSON.parse(raw);
        } catch {
          throw new Error(raw ? raw.slice(0, 300) : "The API returned an empty response.");
        }
        $("result").hidden = false;
        if (!data.ok) {
          $("result").innerHTML = renderError(data.error || "Search failed.", data.hint || "");
        } else if (data.match === "exact") {
          $("result").innerHTML = renderExact(query, data.data);
        } else {
          $("result").innerHTML = renderRange(query, data.data);
        }
      } catch (error) {
        $("result").hidden = false;
        $("result").innerHTML = renderError("Server error. Please try again.");
      } finally {
        $("search-btn").disabled = false;
        $("search-btn").textContent = "Search";
      }
    }

    $("search-btn").addEventListener("click", search);
    $("query").addEventListener("keydown", (event) => {
      if (event.key === "Enter") search();
    });
    loadStats();
  </script>
</body>
</html>
