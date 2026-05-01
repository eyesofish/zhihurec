const state = {
  lastFeedRequestId: null,
  lastSearchQueryKey: null,
};

const el = (id) => document.getElementById(id);

function apiBase() {
  return el("apiBase").value.replace(/\/+$/, "");
}

function userId() {
  return Number(el("userId").value || 7248);
}

function setStatus(message, isError = false) {
  const status = el("status");
  status.textContent = message;
  status.classList.toggle("error", isError);
}

function showDebug(label, data) {
  el("debugJson").textContent = JSON.stringify({ label, data }, null, 2);
}

async function requestJson(path, options = {}) {
  const response = await fetch(`${apiBase()}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    const error = new Error(data.detail || `HTTP ${response.status}`);
    error.payload = data;
    throw error;
  }
  return data;
}

function topicsHtml(topics = []) {
  return topics.map((topic) => `<span class="pill">${topic.display_name || `Topic ${topic.topic_id}`}</span>`).join("");
}

function scoresHtml(scores = {}) {
  return Object.entries(scores)
    .map(([key, value]) => `<span class="pill">${key}: ${Number(value).toFixed(4)}</span>`)
    .join("");
}

function renderFeed(data) {
  state.lastFeedRequestId = data.request_id;
  const target = el("feedResults");
  if (!data.items || data.items.length === 0) {
    target.className = "results empty";
    target.textContent = "No feed results.";
    return;
  }
  target.className = "results";
  target.innerHTML = data.items
    .map(
      (item) => `
        <article class="result-item">
          <h2 class="result-title">${item.question_title}</h2>
          <p class="result-summary">${item.answer_summary}</p>
          <div class="meta">
            <span class="pill">answer ${item.answer_id}</span>
            <span class="pill">${item.author.display_name}</span>
            <span class="pill">${item.is_fallback ? "fallback" : "primary"}</span>
          </div>
          <div class="topics">${topicsHtml(item.topics)}</div>
          <div class="scoreline">${scoresHtml(item.scores)}</div>
          <div class="meta"><span class="pill">${item.recall_sources.join("+")}</span></div>
          <p class="result-summary">${item.selected_reason}</p>
          <div class="actions">
            <button class="secondary" data-feed-click="${item.answer_id}">Record Feed Click</button>
          </div>
        </article>
      `,
    )
    .join("");
  target.querySelectorAll("[data-feed-click]").forEach((button) => {
    button.addEventListener("click", () => recordRecommendationClick(Number(button.dataset.feedClick), data.request_id));
  });
}

function renderSearch(data) {
  state.lastSearchQueryKey = data.query_key;
  const target = el("searchResults");
  if (!data.items || data.items.length === 0) {
    target.className = "results empty";
    target.textContent = "No search results.";
    return;
  }
  target.className = "results";
  target.innerHTML = data.items
    .map(
      (item) => `
        <article class="result-item">
          <h2 class="result-title">${item.question_title}</h2>
          <p class="result-summary">${item.answer_summary}</p>
          <div class="meta">
            <span class="pill">answer ${item.answer_id}</span>
            <span class="pill">question ${item.question_id}</span>
          </div>
          <div class="topics">${topicsHtml(item.topics)}</div>
          <div class="scoreline">${scoresHtml(item.scores)}</div>
          <div class="actions">
            <button class="secondary" data-search-click="${item.answer_id}">Record Search Click</button>
          </div>
        </article>
      `,
    )
    .join("");
  target.querySelectorAll("[data-search-click]").forEach((button) => {
    button.addEventListener("click", () => recordSearchResultClick(Number(button.dataset.searchClick), data.query_key));
  });
}

function renderProfile(data) {
  const target = el("profileSummary");
  target.className = "profile-summary";
  const topics = (data.topic_weights || [])
    .map((topic) => `<li>Topic ${topic.topic_id}: ${Number(topic.weight).toFixed(6)}</li>`)
    .join("");
  const queries = (data.recent_queries || [])
    .map((query) => `<li>${query.query_key} @ ${query.query_ts}</li>`)
    .join("");
  const clicks = (data.recent_clicked_answers || [])
    .map((click) => `<li>answer ${click.answer_id} @ ${click.click_ts}</li>`)
    .join("");
  target.innerHTML = `
    <div class="metric-grid">
      <div class="metric"><span>User</span><strong>${data.user_id}</strong></div>
      <div class="metric"><span>Behavior</span><strong>${Number(data.behavior_score).toFixed(2)}</strong></div>
      <div class="metric"><span>Seed</span><strong>${data.cold_start_seed_key}</strong></div>
      <div class="metric"><span>Vector Keys</span><strong>${data.vector_summary.vector_key_count}</strong></div>
    </div>
    <ul class="list">${topics || "<li>No topics</li>"}</ul>
    <ul class="list">${queries || "<li>No recent queries</li>"}</ul>
    <ul class="list">${clicks || "<li>No recent clicks</li>"}</ul>
  `;
}

async function loadFeed() {
  try {
    setStatus("Loading feed...");
    const data = await requestJson(`/feed?user_id=${userId()}&page_size=10&debug=true`);
    renderFeed(data);
    showDebug("feed", data);
    setStatus("Feed loaded.");
  } catch (error) {
    showDebug("feed_error", error.payload || String(error));
    setStatus(error.message, true);
  }
}

async function loadProfile() {
  try {
    setStatus("Loading profile...");
    const data = await requestJson(`/debug/profile?user_id=${userId()}`);
    renderProfile(data);
    showDebug("profile", data);
    setStatus("Profile loaded.");
  } catch (error) {
    showDebug("profile_error", error.payload || String(error));
    setStatus(error.message, true);
  }
}

async function runSearch() {
  const queryKey = el("queryKey").value.trim();
  if (!queryKey) {
    setStatus("Query key is required.", true);
    return;
  }
  try {
    setStatus("Running search...");
    const data = await requestJson("/search", {
      method: "POST",
      body: JSON.stringify({
        user_id: userId(),
        query_key: queryKey,
        query_text: `Query ${queryKey}`,
        page_size: 10,
        debug: true,
      }),
    });
    renderSearch(data);
    showDebug("search", data);
    setStatus("Search loaded.");
  } catch (error) {
    showDebug("search_error", error.payload || String(error));
    setStatus(error.message, true);
  }
}

async function recordRecommendationClick(answerId, requestId) {
  try {
    setStatus("Recording feed click...");
    const data = await requestJson("/event/recommendation_click", {
      method: "POST",
      body: JSON.stringify({
        user_id: userId(),
        answer_id: answerId,
        request_id: requestId || state.lastFeedRequestId,
        debug: true,
      }),
    });
    showDebug("recommendation_click", data);
    await Promise.all([loadProfile(), loadFeed()]);
    setStatus("Feed click recorded.");
  } catch (error) {
    showDebug("recommendation_click_error", error.payload || String(error));
    setStatus(error.message, true);
  }
}

async function recordSearchResultClick(answerId, queryKey) {
  try {
    setStatus("Recording search click...");
    const data = await requestJson("/event/search_result_click", {
      method: "POST",
      body: JSON.stringify({
        user_id: userId(),
        answer_id: answerId,
        query_key: queryKey || state.lastSearchQueryKey,
        request_id: `search-${Date.now()}`,
        debug: true,
      }),
    });
    showDebug("search_result_click", data);
    await Promise.all([loadProfile(), loadFeed()]);
    setStatus("Search click recorded.");
  } catch (error) {
    showDebug("search_result_click_error", error.payload || String(error));
    setStatus(error.message, true);
  }
}

el("refreshFeed").addEventListener("click", loadFeed);
el("refreshProfile").addEventListener("click", loadProfile);
el("runSearch").addEventListener("click", runSearch);

window.loadFeed = loadFeed;
window.loadProfile = loadProfile;
window.runSearch = runSearch;
window.recordRecommendationClick = recordRecommendationClick;
window.recordSearchResultClick = recordSearchResultClick;
