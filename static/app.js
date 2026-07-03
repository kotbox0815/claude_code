async function loadFacets() {
  const res = await fetch("/api/facets");
  const data = await res.json();
  const clusterSel = document.getElementById("cluster");
  const vswitchSel = document.getElementById("vswitch");
  for (const c of data.clusters) {
    const opt = document.createElement("option");
    opt.value = c;
    opt.textContent = c;
    clusterSel.appendChild(opt);
  }
  for (const v of data.vswitches) {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = v;
    vswitchSel.appendChild(opt);
  }
}

function buildParams() {
  const params = new URLSearchParams();
  const q = document.getElementById("q").value.trim();
  const host = document.getElementById("host").value.trim();
  const cluster = document.getElementById("cluster").value;
  const vswitch = document.getElementById("vswitch").value;
  const deviceId = document.getElementById("device_id").value.trim();
  const urlReportId = new URLSearchParams(window.location.search).get("report_id");

  if (q) params.set("q", q);
  if (host) params.set("host", host);
  if (cluster) params.set("cluster", cluster);
  if (vswitch) params.set("vswitch", vswitch);
  if (deviceId) params.set("device_id", deviceId);
  if (urlReportId) params.set("report_id", urlReportId);
  return params;
}

async function runSearch() {
  const params = buildParams();
  const res = await fetch("/api/entries?" + params.toString());
  const data = await res.json();

  document.getElementById("result-count").textContent = `${data.total} Treffer`;

  const tbody = document.querySelector("#result-table tbody");
  tbody.innerHTML = "";
  for (const e of data.items) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="host-link" data-host="${e.host}">${e.host}</td>
      <td>${e.cluster}</td>
      <td>${e.vswitch}</td>
      <td>${e.pnic}</td>
      <td>${e.speed}</td>
      <td>${e.mac}</td>
      <td>${e.device_id}</td>
      <td>${e.port_id}</td>
    `;
    tbody.appendChild(tr);
  }

  document.querySelectorAll(".host-link").forEach((td) => {
    td.addEventListener("click", () => {
      document.getElementById("host").value = td.dataset.host;
      runSearch();
    });
  });
}

document.getElementById("search-btn").addEventListener("click", runSearch);
document.getElementById("reset-btn").addEventListener("click", () => {
  document.getElementById("q").value = "";
  document.getElementById("host").value = "";
  document.getElementById("cluster").value = "";
  document.getElementById("vswitch").value = "";
  document.getElementById("device_id").value = "";
  history.replaceState(null, "", "/");
  runSearch();
});
document.getElementById("q").addEventListener("keydown", (e) => {
  if (e.key === "Enter") runSearch();
});

loadFacets().then(runSearch);
