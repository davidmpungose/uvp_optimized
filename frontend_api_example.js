"use strict";

const API_BASE_URL = "http://127.0.0.1:8080/api/v1";

function quarterParameter(selectedQuarters) {
    if (!selectedQuarters || selectedQuarters.length === 0) {
        return "";
    }
    return `quarters=${encodeURIComponent(selectedQuarters.join(","))}`;
}

function withQuery(path, parameters) {
    const query = parameters.filter(Boolean).join("&");
    return query ? `${path}?${query}` : path;
}

async function fetchJson(url) {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) {
        const message = await response.text();
        throw new Error(`HTTP ${response.status}: ${message}`);
    }
    return response.json();
}

async function loadQuarters() {
    return fetchJson(`${API_BASE_URL}/quarters`);
}

async function loadMultiQuarterDashboard(
    selectedQuarters,
    page = 1,
    pageSize = 25,
    caseFilters = {}
) {
    const quarters = quarterParameter(selectedQuarters);
    const caseQuery = [
        quarters,
        `page=${page}`,
        `page_size=${pageSize}`,
        caseFilters.riskLevel
            ? `risk_level=${encodeURIComponent(caseFilters.riskLevel)}`
            : "",
        caseFilters.minimumScore != null
            ? `minimum_score=${encodeURIComponent(caseFilters.minimumScore)}`
            : "",
        caseFilters.search
            ? `search=${encodeURIComponent(caseFilters.search)}`
            : "",
    ];

    const [summary, distributions, cases, topHS, topTraders] =
        await Promise.all([
            fetchJson(withQuery(`${API_BASE_URL}/dashboard/summary`, [quarters])),
            fetchJson(withQuery(`${API_BASE_URL}/dashboard/distributions`, [quarters])),
            fetchJson(withQuery(`${API_BASE_URL}/cases`, caseQuery)),
            fetchJson(withQuery(`${API_BASE_URL}/top-hs`, [quarters, "limit=15"])),
            fetchJson(withQuery(`${API_BASE_URL}/top-traders`, [quarters, "limit=15"])),
        ]);

    return { summary, distributions, cases, topHS, topTraders };
}

async function loadTraderHistory(
    traderTin,
    selectedQuarters,
    page = 1,
    pageSize = 25
) {
    const quarters = quarterParameter(selectedQuarters);
    return fetchJson(
        withQuery(
            `${API_BASE_URL}/traders/${encodeURIComponent(traderTin)}/history`,
            [quarters, `page=${page}`, `page_size=${pageSize}`]
        )
    );
}
