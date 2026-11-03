"use strict";


const MANIFEST_URL =
    "./data/dashboard_manifest.json";

const PAGE_SIZE = 25;


let manifestData = null;
let dashboardData = null;
let filteredCases = [];
let currentPage = 1;


/* ============================================================
   BASIC HELPERS
   ============================================================ */

function getElement(id) {
    return document.getElementById(id);
}


function setText(id, value) {
    const element = getElement(id);

    if (element) {
        element.textContent = value;
    }
}


function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll("\"", "&quot;")
        .replaceAll("'", "&#039;");
}


/* ============================================================
   FORMATTING
   ============================================================ */

const numberFormatter = new Intl.NumberFormat(
    "en-US",
    {
        maximumFractionDigits: 0
    }
);


const decimalFormatter = new Intl.NumberFormat(
    "en-US",
    {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }
);


const currencyFormatter = new Intl.NumberFormat(
    "en-SZ",
    {
        style: "currency",
        currency: "SZL",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }
);


function formatNumber(value) {
    return numberFormatter.format(
        Number(value || 0)
    );
}


function formatDecimal(value) {
    return decimalFormatter.format(
        Number(value || 0)
    );
}


function formatCurrency(value) {
    return currencyFormatter.format(
        Number(value || 0)
    );
}


function formatPercent(value) {
    return `${formatDecimal(value)}%`;
}


function formatBytes(value) {
    const bytes = Number(value || 0);

    if (bytes < 1024) {
        return `${formatNumber(bytes)} B`;
    }

    if (bytes < 1048576) {
        return `${formatDecimal(bytes / 1024)} KB`;
    }

    return `${formatDecimal(bytes / 1048576)} MB`;
}


function formatMilliseconds(value) {
    const milliseconds = Number(value || 0);

    if (milliseconds < 1000) {
        return `${formatDecimal(milliseconds)} ms`;
    }

    return `${formatDecimal(milliseconds / 1000)} sec`;
}


/* ============================================================
   LOADING AND ERROR PANELS
   ============================================================ */

function showLoading(message) {
    setText(
        "loadingPanel",
        message
    );

    getElement(
        "loadingPanel"
    ).classList.remove(
        "hidden"
    );

    getElement(
        "errorPanel"
    ).classList.add(
        "hidden"
    );
}


function hideLoading() {
    getElement(
        "loadingPanel"
    ).classList.add(
        "hidden"
    );
}


function showError(error) {
    hideLoading();

    const errorPanel = getElement(
        "errorPanel"
    );

    errorPanel.classList.remove(
        "hidden"
    );

    errorPanel.innerHTML = `
        <strong>Dashboard could not load.</strong>
        <p>${escapeHtml(error.message)}</p>
    `;
}


/* ============================================================
   LOAD THE QUARTER MANIFEST
   ============================================================ */

async function loadManifest() {
    showLoading(
        "Loading available quarters..."
    );

    try {
        const response = await fetch(
            MANIFEST_URL,
            {
                cache: "no-store"
            }
        );

        if (!response.ok) {
            throw new Error(
                `Could not load dashboard manifest. HTTP ${response.status}`
            );
        }

        manifestData = await response.json();

        populateQuarterFilter();

        const defaultQuarter =
            manifestData.metadata.defaultQuarter;

        getElement(
            "quarterFilter"
        ).value = defaultQuarter;

        await loadSelectedQuarter(
            defaultQuarter
        );
    } catch (error) {
        showError(error);
    }
}


/* ============================================================
   QUARTER FILTER
   ============================================================ */

function populateQuarterFilter() {
    const quarterFilter = getElement(
        "quarterFilter"
    );

    quarterFilter.innerHTML = "";

    const quarterRecords = [
        ...(manifestData.quarters || [])
    ];

    quarterRecords.sort(
        (left, right) =>
            right.quarter.localeCompare(
                left.quarter
            )
    );

    for (const quarterRecord of quarterRecords) {
        const option = document.createElement(
            "option"
        );

        option.value = quarterRecord.quarter;

        option.textContent =
            `${quarterRecord.quarter} | `
            + `${formatNumber(quarterRecord.rowsScored)} rows | `
            + `${formatNumber(quarterRecord.potentialCases)} cases`;

        quarterFilter.appendChild(option);
    }
}


async function loadSelectedQuarter(
    yearQuarter
) {
    const quarterRecord = (
        manifestData.quarters || []
    ).find(
        record =>
            record.quarter === yearQuarter
    );

    if (!quarterRecord) {
        showError(
            new Error(
                `Quarter ${yearQuarter} is not in the manifest.`
            )
        );

        return;
    }

    showLoading(
        `Loading ${yearQuarter} results...`
    );

    const totalStart =
        performance.now();

    try {
        const downloadStart =
            performance.now();

        const response = await fetch(
            quarterRecord.dataUrl,
            {
                cache: "no-store"
            }
        );

        const downloadEnd =
            performance.now();

        if (!response.ok) {
            throw new Error(
                `Could not load ${yearQuarter}. HTTP ${response.status}`
            );
        }

        const responseText =
            await response.text();

        const parseStart =
            performance.now();

        dashboardData =
            JSON.parse(responseText);

        const parseEnd =
            performance.now();

        filteredCases = [
            ...(dashboardData.topCases || [])
        ];

        resetCaseFilters(
            false
        );

        const renderStart =
            performance.now();

        renderDashboard();

        const renderEnd =
            performance.now();

        const totalEnd =
            performance.now();

        renderPerformanceMetrics(
            yearQuarter,
            quarterRecord.fileSizeBytes,
            downloadEnd - downloadStart,
            parseEnd - parseStart,
            renderEnd - renderStart,
            totalEnd - totalStart
        );

        hideLoading();

        getElement(
            "dashboardContent"
        ).classList.remove(
            "hidden"
        );
    } catch (error) {
        showError(error);
    }
}


/* ============================================================
   PERFORMANCE OUTPUT
   ============================================================ */

function renderPerformanceMetrics(
    yearQuarter,
    fileSizeBytes,
    downloadMilliseconds,
    parseMilliseconds,
    renderMilliseconds,
    totalMilliseconds
) {
    setText(
        "selectedQuarterText",
        yearQuarter
    );

    setText(
        "jsonSizeText",
        formatBytes(fileSizeBytes)
    );

    setText(
        "downloadTimeText",
        formatMilliseconds(downloadMilliseconds)
    );

    setText(
        "parseTimeText",
        formatMilliseconds(parseMilliseconds)
    );

    setText(
        "renderTimeText",
        formatMilliseconds(renderMilliseconds)
    );

    setText(
        "totalDisplayTimeText",
        formatMilliseconds(totalMilliseconds)
    );
}


/* ============================================================
   MAIN DASHBOARD RENDERING
   ============================================================ */

function renderDashboard() {
    renderMetadata();
    renderKpis();
    populateCaseFilters();
    renderCharts();
    renderTopHSTable();
    renderTopTradersTable();

    currentPage = 1;

    applyFilters();
}


function renderMetadata() {
    const metadata =
        dashboardData.metadata || {};

    setText(
        "generatedAt",
        metadata.generatedAt
            ? `Generated ${metadata.generatedAt}`
            : ""
    );
}


function renderKpis() {
    const kpis =
        dashboardData.kpis || {};

    setText(
        "rowsScoredKpi",
        formatNumber(kpis.rowsScored)
    );

    setText(
        "potentialCasesKpi",
        formatNumber(kpis.potentialCases)
    );

    setText(
        "highRiskKpi",
        formatNumber(kpis.highRiskCases)
    );

    setText(
        "mediumRiskKpi",
        formatNumber(kpis.mediumRiskCases)
    );

    setText(
        "lowRiskKpi",
        formatNumber(kpis.lowRiskCases)
    );

    setText(
        "valueGapKpi",
        formatCurrency(
            kpis.totalPotentialValueGap
        )
    );
}


/* ============================================================
   QUARTER-SPECIFIC CASE FILTERS
   ============================================================ */

function replaceSelectOptions(
    selectId,
    firstLabel,
    values
) {
    const select = getElement(
        selectId
    );

    select.innerHTML = "";

    const firstOption =
        document.createElement(
            "option"
        );

    firstOption.value = "";
    firstOption.textContent = firstLabel;

    select.appendChild(firstOption);

    for (const value of values || []) {
        const option =
            document.createElement(
                "option"
            );

        option.value = value;
        option.textContent = value;

        select.appendChild(option);
    }
}


function populateCaseFilters() {
    const filters =
        dashboardData.filters || {};

    replaceSelectOptions(
        "riskLevelFilter",
        "All risk levels",
        filters.riskLevels
    );

    replaceSelectOptions(
        "benchmarkMethodFilter",
        "All methods",
        filters.benchmarkMethods
    );

    replaceSelectOptions(
        "modelAgreementFilter",
        "All model results",
        filters.modelAgreements
    );

    replaceSelectOptions(
        "hsFilter",
        "All HS codes",
        filters.hsCodes
    );
}


function resetCaseFilters(
    rerender = true
) {
    getElement("searchInput").value = "";
    getElement("riskLevelFilter").value = "";
    getElement("benchmarkMethodFilter").value = "";
    getElement("modelAgreementFilter").value = "";
    getElement("hsFilter").value = "";
    getElement("minimumScoreFilter").value = "0";

    currentPage = 1;

    if (rerender) {
        applyFilters();
    }
}


function applyFilters() {
    if (!dashboardData) {
        return;
    }

    const searchValue =
        getElement("searchInput")
        .value
        .trim()
        .toLowerCase();

    const riskLevel =
        getElement(
            "riskLevelFilter"
        ).value;

    const benchmarkMethod =
        getElement(
            "benchmarkMethodFilter"
        ).value;

    const modelAgreement =
        getElement(
            "modelAgreementFilter"
        ).value;

    const hsCode =
        getElement(
            "hsFilter"
        ).value;

    const minimumScore = Number(
        getElement(
            "minimumScoreFilter"
        ).value || 0
    );

    filteredCases = (
        dashboardData.topCases || []
    ).filter(
        record => {
            const searchableText = [
                record.DashboardTraderTin,
                record.DashboardTraderName,
                record.DashboardHS,
                record.DashboardHSDescription,
                record.DashboardDeclarationReference,
                record.CaseReason
            ]
                .join(" ")
                .toLowerCase();

            return (
                (
                    !searchValue
                    || searchableText.includes(
                        searchValue
                    )
                )
                && (
                    !riskLevel
                    || record.CaseRiskLevel
                        === riskLevel
                )
                && (
                    !benchmarkMethod
                    || record.FinalBenchmarkMethod
                        === benchmarkMethod
                )
                && (
                    !modelAgreement
                    || record.ModelAgreement
                        === modelAgreement
                )
                && (
                    !hsCode
                    || record.DashboardHS
                        === hsCode
                )
                && (
                    Number(
                        record.CaseRiskScore || 0
                    )
                    >= minimumScore
                )
            );
        }
    );

    filteredCases.sort(
        (left, right) =>
            Number(
                right.CaseRiskScore || 0
            )
            - Number(
                left.CaseRiskScore || 0
            )
    );

    renderCasesTable();
}


/* ============================================================
   CHARTS
   ============================================================ */

function renderBarChart(
    elementId,
    records
) {
    const container = getElement(
        elementId
    );

    container.innerHTML = "";

    if (
        !records
        || records.length === 0
    ) {
        container.innerHTML =
            "<p>No data available.</p>";

        return;
    }

    const maximumValue = Math.max(
        ...records.map(
            record =>
                Number(record.value || 0)
        ),
        1
    );

    for (const record of records) {
        const numericValue =
            Number(record.value || 0);

        const percentage =
            (
                numericValue
                / maximumValue
            )
            * 100;

        const row =
            document.createElement(
                "div"
            );

        row.className = "bar-row";

        row.innerHTML = `
            <div class="bar-label">
                ${escapeHtml(record.label)}
            </div>

            <div class="bar-track">
                <div
                    class="bar-fill"
                    style="width: ${Math.max(percentage, 1)}%"
                >
                </div>
            </div>

            <div class="bar-value">
                ${formatNumber(numericValue)}
            </div>
        `;

        container.appendChild(row);
    }
}


function renderCharts() {
    renderBarChart(
        "riskDistributionChart",
        dashboardData.riskDistribution
    );

    renderBarChart(
        "agreementDistributionChart",
        dashboardData.modelAgreementDistribution
    );

    renderBarChart(
        "benchmarkMethodChart",
        dashboardData.benchmarkMethodDistribution
    );
}


/* ============================================================
   POTENTIAL-CASE TABLE
   ============================================================ */

function getTotalPages() {
    return Math.max(
        1,
        Math.ceil(
            filteredCases.length
            / PAGE_SIZE
        )
    );
}


function getRiskClass(riskLevel) {
    if (riskLevel === "High Risk") {
        return "risk-high";
    }

    if (riskLevel === "Medium Risk") {
        return "risk-medium";
    }

    return "risk-low";
}


function renderCasesTable() {
    const tableBody = getElement(
        "casesTableBody"
    );

    tableBody.innerHTML = "";

    const totalPages =
        getTotalPages();

    if (currentPage > totalPages) {
        currentPage = totalPages;
    }

    const startIndex =
        (
            currentPage - 1
        )
        * PAGE_SIZE;

    const pageRows =
        filteredCases.slice(
            startIndex,
            startIndex + PAGE_SIZE
        );

    if (pageRows.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="14">
                    No cases match the selected filters.
                </td>
            </tr>
        `;
    }

    for (const record of pageRows) {
        const row =
            document.createElement(
                "tr"
            );

        row.innerHTML = `
            <td>
                ${formatNumber(record.DashboardRank)}
            </td>

            <td>
                <span class="risk-pill ${getRiskClass(record.CaseRiskLevel)}">
                    ${escapeHtml(record.CaseRiskLevel)}
                </span>
            </td>

            <td>
                ${formatDecimal(record.CaseRiskScore)}
            </td>

            <td>
                ${escapeHtml(record.DashboardTraderName)}
            </td>

            <td>
                ${escapeHtml(record.DashboardTraderTin)}
            </td>

            <td>
                ${escapeHtml(record.DashboardHS)}
            </td>

            <td>
                ${escapeHtml(record.DashboardDeclarationReference)}
            </td>

            <td>
                ${formatCurrency(record.UnitValue)}
            </td>

            <td>
                ${formatCurrency(record.FinalBenchmarkQ1)}
            </td>

            <td>
                ${formatPercent(record.FinalDeviationPercent)}
            </td>

            <td>
                ${formatCurrency(record.PotentialValueGap)}
            </td>

            <td>
                ${escapeHtml(record.FinalBenchmarkMethod)}
            </td>

            <td>
                ${escapeHtml(record.ModelAgreement)}
            </td>

            <td>
                <button
                    class="details-button"
                    type="button"
                    data-case-id="${escapeHtml(record.PreparedDeclarationId)}"
                >
                    View
                </button>
            </td>
        `;

        tableBody.appendChild(row);
    }

    tableBody
        .querySelectorAll(
            ".details-button"
        )
        .forEach(
            button => {
                button.addEventListener(
                    "click",
                    () => {
                        openCaseModal(
                            button.dataset.caseId
                        );
                    }
                );
            }
        );

    setText(
        "caseCountText",
        `${formatNumber(filteredCases.length)} cases shown`
    );

    setText(
        "pageInformation",
        `Page ${currentPage} of ${totalPages}`
    );

    getElement(
        "previousPageButton"
    ).disabled =
        currentPage <= 1;

    getElement(
        "nextPageButton"
    ).disabled =
        currentPage >= totalPages;
}


/* ============================================================
   TOP HS AND TRADERS
   ============================================================ */

function renderTopHSTable() {
    const tableBody = getElement(
        "topHSTableBody"
    );

    tableBody.innerHTML = "";

    for (
        const record
        of dashboardData.topHS || []
    ) {
        const row =
            document.createElement(
                "tr"
            );

        row.innerHTML = `
            <td>${escapeHtml(record.DashboardHS)}</td>
            <td>${escapeHtml(record.DashboardHSDescription)}</td>
            <td>${formatNumber(record.PotentialCases)}</td>
            <td>${formatCurrency(record.TotalPotentialValueGap)}</td>
            <td>${formatDecimal(record.AverageRiskScore)}</td>
        `;

        tableBody.appendChild(row);
    }
}


function renderTopTradersTable() {
    const tableBody = getElement(
        "topTradersTableBody"
    );

    tableBody.innerHTML = "";

    for (
        const record
        of dashboardData.topTraders || []
    ) {
        const row =
            document.createElement(
                "tr"
            );

        row.innerHTML = `
            <td>${escapeHtml(record.DashboardTraderTin)}</td>
            <td>${escapeHtml(record.DashboardTraderName)}</td>
            <td>${formatNumber(record.PotentialCases)}</td>
            <td>${formatNumber(record.UniqueHS)}</td>
            <td>${formatCurrency(record.TotalPotentialValueGap)}</td>
        `;

        tableBody.appendChild(row);
    }
}


/* ============================================================
   CASE DETAILS
   ============================================================ */

function detailRow(label, value) {
    return `
        <div class="detail-row">
            <span>${escapeHtml(label)}</span>
            <strong>${escapeHtml(value)}</strong>
        </div>
    `;
}


function openCaseModal(
    preparedDeclarationId
) {
    const record = (
        dashboardData.topCases || []
    ).find(
        candidate =>
            String(
                candidate.PreparedDeclarationId
            )
            === String(
                preparedDeclarationId
            )
    );

    if (!record) {
        return;
    }

    setText(
        "caseModalTitle",
        record.DashboardDeclarationReference
        || `Case ${record.PreparedDeclarationId}`
    );

    getElement(
        "caseModalContent"
    ).innerHTML = `
        <div class="detail-grid">
            <section class="detail-card">
                <h3>Declaration</h3>

                ${detailRow(
                    "Quarter",
                    record.DashboardQuarter
                )}

                ${detailRow(
                    "Declaration",
                    record.DashboardDeclarationReference
                )}

                ${detailRow(
                    "FOB Value",
                    formatCurrency(record.FOBValue)
                )}

                ${detailRow(
                    "Unit Value",
                    formatCurrency(record.UnitValue)
                )}
            </section>

            <section class="detail-card">
                <h3>Trader and Product</h3>

                ${detailRow(
                    "TIN",
                    record.DashboardTraderTin
                )}

                ${detailRow(
                    "Trader",
                    record.DashboardTraderName
                )}

                ${detailRow(
                    "HS",
                    record.DashboardHS
                )}

                ${detailRow(
                    "Description",
                    record.DashboardHSDescription
                )}
            </section>

            <section class="detail-card">
                <h3>Benchmark Result</h3>

                ${detailRow(
                    "Original Q1",
                    formatCurrency(record.OriginalQ1)
                )}

                ${detailRow(
                    "Cluster Q1",
                    formatCurrency(record.ClusterQ1)
                )}

                ${detailRow(
                    "Final Q1",
                    formatCurrency(record.FinalBenchmarkQ1)
                )}

                ${detailRow(
                    "Method",
                    record.FinalBenchmarkMethod
                )}
            </section>

            <section class="detail-card">
                <h3>Risk Result</h3>

                ${detailRow(
                    "Deviation",
                    formatPercent(record.FinalDeviationPercent)
                )}

                ${detailRow(
                    "Value Gap",
                    formatCurrency(record.PotentialValueGap)
                )}

                ${detailRow(
                    "Risk Score",
                    formatDecimal(record.CaseRiskScore)
                )}

                ${detailRow(
                    "Risk Level",
                    record.CaseRiskLevel
                )}
            </section>

            <section class="detail-card reason-card">
                <h3>Case Explanation</h3>

                <p>
                    ${escapeHtml(record.CaseReason)}
                </p>
            </section>
        </div>
    `;

    getElement(
        "caseModal"
    ).classList.remove(
        "hidden"
    );
}


function closeCaseModal() {
    getElement(
        "caseModal"
    ).classList.add(
        "hidden"
    );
}


/* ============================================================
   EVENTS
   ============================================================ */

function bindEvents() {
    getElement(
        "quarterFilter"
    ).addEventListener(
        "change",
        event => {
            loadSelectedQuarter(
                event.target.value
            );
        }
    );

    const filterIds = [
        "searchInput",
        "riskLevelFilter",
        "benchmarkMethodFilter",
        "modelAgreementFilter",
        "hsFilter",
        "minimumScoreFilter"
    ];

    for (const filterId of filterIds) {
        const element =
            getElement(filterId);

        element.addEventListener(
            element.tagName === "INPUT"
                ? "input"
                : "change",
            () => {
                currentPage = 1;
                applyFilters();
            }
        );
    }

    getElement(
        "resetFiltersButton"
    ).addEventListener(
        "click",
        () => {
            resetCaseFilters(true);
        }
    );

    getElement(
        "previousPageButton"
    ).addEventListener(
        "click",
        () => {
            if (currentPage > 1) {
                currentPage -= 1;
                renderCasesTable();
            }
        }
    );

    getElement(
        "nextPageButton"
    ).addEventListener(
        "click",
        () => {
            if (
                currentPage
                < getTotalPages()
            ) {
                currentPage += 1;
                renderCasesTable();
            }
        }
    );

    getElement(
        "closeModalButton"
    ).addEventListener(
        "click",
        closeCaseModal
    );

    getElement(
        "caseModal"
    )
        .querySelector(
            ".modal-backdrop"
        )
        .addEventListener(
            "click",
            closeCaseModal
        );

    document.addEventListener(
        "keydown",
        event => {
            if (event.key === "Escape") {
                closeCaseModal();
            }
        }
    );
}


/* ============================================================
   START DASHBOARD
   ============================================================ */

document.addEventListener(
    "DOMContentLoaded",
    () => {
        bindEvents();
        loadManifest();
    }
);