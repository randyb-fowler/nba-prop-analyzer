const form = document.getElementById("prop-form");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");
const statSelect = document.getElementById("stat");
const oppSelect = document.getElementById("opponent");
const seasonSelect = document.getElementById("season");

// --- Populate dropdowns on load ------------------------------------------

async function loadStats() {
  try {
    const res = await fetch("/api/stats");
    const data = await res.json();
    statSelect.innerHTML = data.stats.map((s) => `<option value="${s}">${s}</option>`).join("");
  } catch {
    statSelect.innerHTML = `<option value="PTS">PTS</option>`;
  }
}

async function loadTeams() {
  try {
    const res = await fetch("/api/teams");
    const data = await res.json();
    oppSelect.innerHTML =
      `<option value="">Any</option>` +
      data.teams.map((t) => `<option value="${t.abbr}">${t.abbr} — ${t.name}</option>`).join("");
  } catch {
    /* keep the default "Any" option */
  }
}

async function loadSeasons() {
  try {
    const res = await fetch("/api/seasons");
    const data = await res.json();
    seasonSelect.innerHTML = data.seasons
      .map((s) => `<option value="${s}" ${s === data.default ? "selected" : ""}>${s}</option>`)
      .join("");
  } catch {
    seasonSelect.innerHTML = `<option value="2024-25">2024-25</option>`;
  }
}

loadStats();
loadTeams();
loadSeasons();

// --- Player autocomplete (shared helper for both inputs) ------------------

function wireAutocomplete(inputId, listId) {
  const input = document.getElementById(inputId);
  const list = document.getElementById(listId);
  let debounce;
  input.addEventListener("input", () => {
    clearTimeout(debounce);
    const q = input.value.trim();
    if (q.length < 2) return;
    debounce = setTimeout(async () => {
      try {
        const res = await fetch(`/api/players?q=${encodeURIComponent(q)}`);
        const data = await res.json();
        list.innerHTML = data.players.map((p) => `<option value="${p.name}"></option>`).join("");
      } catch {
        /* ignore */
      }
    }, 200);
  });
}

wireAutocomplete("player", "player-list");
wireAutocomplete("player-b", "player-list-b");

// --- Submit --------------------------------------------------------------

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const player = document.getElementById("player").value.trim();
  const playerB = document.getElementById("player-b").value.trim();
  const stat = statSelect.value;
  const line = document.getElementById("line").value;
  const over = document.getElementById("over").value;
  const opponent = oppSelect.value;
  const season = seasonSelect.value;

  resultsEl.classList.add("hidden");
  statusEl.className = "status";
  statusEl.textContent = playerB
    ? "Comparing two players… (live NBA data, ~8s)"
    : "Crunching the numbers… (live NBA data, ~5s)";

  try {
    if (playerB) {
      const params = new URLSearchParams({ player_a: player, player_b: playerB, stat, line, over, season });
      const res = await fetch(`/api/compare?${params}`);
      if (!res.ok) throw new Error((await res.json()).detail || "Request failed");
      const data = await res.json();
      await renderCompare(data);
    } else {
      const params = new URLSearchParams({ player, stat, line, over, season });
      if (opponent) params.set("opponent", opponent);
      const res = await fetch(`/api/analyze?${params}`);
      if (!res.ok) throw new Error((await res.json()).detail || "Request failed");
      const data = await res.json();
      await renderSingle(data);
    }
    statusEl.textContent = "";
  } catch (err) {
    statusEl.className = "status error";
    statusEl.textContent = err.message;
  }
});

// --- Rendering helpers ----------------------------------------------------

function rateClass(rate) {
  if (rate >= 60) return "good";
  if (rate <= 40) return "bad";
  return "";
}

function statCard(label, s) {
  return `
    <div class="stat-card">
      <div class="k">${label}</div>
      <div class="v ${rateClass(s.rate)}">${s.rate}%</div>
      <div class="d">${s.hits}/${s.games} · avg ${s.avg}</div>
    </div>`;
}

function summaryCards(d) {
  const sum = d.summary;
  const cards = [
    statCard("Last 5", sum.last5),
    statCard("Last 10", sum.last10),
    statCard("Season", sum.season),
    statCard("Home", sum.home),
    statCard("Away", sum.away),
  ];
  if (d.opponent_split && d.opponent_split.games > 0) {
    cards.push(statCard(`vs ${d.opponent_split.opponent}`, d.opponent_split));
  }
  return `<div class="cards">${cards.join("")}</div>`;
}

function gameLogTable(d) {
  const dir = d.over ? "Over" : "Under";
  const rows = d.game_log
    .map((g) => {
      const loc = g.is_home ? "vs" : "@";
      return `
        <tr>
          <td>${g.date}</td>
          <td>${loc} ${g.opponent}</td>
          <td class="venue">${g.arena}, ${g.city}</td>
          <td class="num">${g.min}</td>
          <td class="num">${g.value}</td>
          <td class="num"><span class="pill ${g.hit ? "hit" : "miss"}">${g.hit ? "HIT" : "MISS"}</span></td>
        </tr>`;
    })
    .join("");
  return `
    <table>
      <thead>
        <tr>
          <th>Date</th><th>Opp</th><th>Venue</th>
          <th class="num">Min</th><th class="num">${d.stat}</th><th class="num">${dir} ${d.line}</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function injuriesBlock(inj) {
  if (!inj || !inj.available) {
    return `<div class="injury-note">Injury report unavailable right now.</div>`;
  }
  if (inj.items.length === 0) {
    return `<div class="injury-note">No reported injuries for ${inj.team}.</div>`;
  }
  const rows = inj.items
    .map(
      (i) => `
      <tr>
        <td>${i.player}${i.pos ? ` <span class="muted">(${i.pos})</span>` : ""}</td>
        <td><span class="pill miss">${i.status}</span></td>
        <td>${i.detail || "—"}</td>
        <td class="muted">${i.return_date || ""}</td>
      </tr>`
    )
    .join("");
  return `
    <table class="injury-table">
      <thead><tr><th>Player</th><th>Status</th><th>Detail</th><th>Return</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

async function fetchInjuries(teamAbbr) {
  try {
    const res = await fetch(`/api/injuries?team=${encodeURIComponent(teamAbbr)}`);
    return await res.json();
  } catch {
    return { available: false, team: teamAbbr, items: [] };
  }
}

async function renderSingle(d) {
  const dir = d.over ? "Over" : "Under";
  const inj = await fetchInjuries(d.team);

  resultsEl.innerHTML = `
    <div class="result-head">
      <div>
        <h2>${d.player} <span class="muted">${d.team}</span></h2>
        <div class="sub">${d.season} · ${dir} ${d.line} ${d.stat} · season avg ${d.summary.season.avg} (${d.margin >= 0 ? "+" : ""}${d.margin} vs line)</div>
      </div>
      <span class="lean ${d.lean}">${d.lean}</span>
    </div>

    ${summaryCards(d)}

    <div class="section-title">High ${d.high} · Median ${d.median} · Low ${d.low}</div>

    <div class="section-title">🏥 ${d.team} Injury Report</div>
    ${injuriesBlock(inj)}

    <div class="section-title">Game Log (${d.game_log.length} games)</div>
    ${gameLogTable(d)}`;

  resultsEl.classList.remove("hidden");
}

function comparePanel(d) {
  return `
    <div class="compare-col">
      <div class="result-head">
        <div>
          <h2>${d.player} <span class="muted">${d.team}</span></h2>
          <div class="sub">season avg ${d.summary.season.avg} (${d.margin >= 0 ? "+" : ""}${d.margin})</div>
        </div>
        <span class="lean ${d.lean}">${d.lean}</span>
      </div>
      ${summaryCards(d)}
    </div>`;
}

async function renderCompare(data) {
  const a = data.a, b = data.b;
  const dir = a.over ? "Over" : "Under";

  // Winner highlight on season hit rate.
  const aWins = a.summary.season.rate >= b.summary.season.rate;

  resultsEl.innerHTML = `
    <div class="section-title">${a.season} · ${dir} ${a.line} ${a.stat} — head to head</div>
    <div class="compare ${aWins ? "a-wins" : "b-wins"}">
      ${comparePanel(a)}
      ${comparePanel(b)}
    </div>
    <div class="section-title">${a.player} — Game Log</div>
    ${gameLogTable(a)}
    <div class="section-title">${b.player} — Game Log</div>
    ${gameLogTable(b)}`;

  resultsEl.classList.remove("hidden");
}
