/**
 * QuantumAML Nexus — Centralized API Client Layer
 * Connects to the FastAPI Serving Engine at http://localhost:8000
 */

export const DEFAULT_API_URL = "http://localhost:8000";

/**
 * Executes a fetch request with a strict 5-second timeout and structured error handling.
 */
async function requestWithTimeout(url, options = {}, timeoutMs = 5000) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        ...(options.headers || {}),
      },
    });
    clearTimeout(id);

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status} ${response.statusText}`;
      try {
        const errorJson = await response.json();
        if (response.status === 422) {
          // Schema validation failure
          const details = Array.isArray(errorJson.detail)
            ? errorJson.detail.map((d) => `${d.loc?.join(".") || "field"}: ${d.msg}`).join("; ")
            : JSON.stringify(errorJson.detail);
          errorMessage = `Schema Validation Error (422): ${details}`;
        } else if (response.status === 500) {
          // Inference engine fault
          errorMessage = `Inference Engine Fault (500): ${errorJson.detail || "Internal Server Error"}`;
        } else if (errorJson.detail) {
          errorMessage = `Server Error (${response.status}): ${errorJson.detail}`;
        }
      } catch {
        // Non-JSON response body
        const text = await response.text();
        if (text) errorMessage += ` - ${text.slice(0, 200)}`;
      }

      const err = new Error(errorMessage);
      err.status = response.status;
      throw err;
    }

    return response;
  } catch (error) {
    clearTimeout(id);
    if (error.name === "AbortError") {
      throw new Error(`Request timed out after ${timeoutMs / 1000}s. The serving layer may be under high load.`);
    }
    if (error.message?.includes("Failed to fetch") || error.name === "TypeError") {
      throw new Error(`Unable to connect to QuantumAML backend at ${url}. Verify the server is running on port 8000.`);
    }
    throw error;
  }
}

/**
 * Queries GET /health for engine status and loaded models inventory.
 */
export async function checkHealth(baseUrl = DEFAULT_API_URL) {
  const cleanUrl = baseUrl.replace(/\/+$/, "");
  const res = await requestWithTimeout(`${cleanUrl}/health`, { method: "GET" }, 3000);
  return await res.json();
}

/**
 * Queries GET /metrics and parses Prometheus text format into structured telemetry.
 */
export async function fetchMetrics(baseUrl = DEFAULT_API_URL) {
  const cleanUrl = baseUrl.replace(/\/+$/, "");
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), 4000);

  try {
    const res = await fetch(`${cleanUrl}/metrics`, {
      method: "GET",
      signal: controller.signal,
      headers: { Accept: "text/plain" },
    });
    clearTimeout(id);

    if (!res.ok) {
      throw new Error(`Failed to scrape metrics: HTTP ${res.status}`);
    }

    const text = await res.text();
    return parsePrometheusMetrics(text);
  } catch (err) {
    clearTimeout(id);
    throw err;
  }
}

/**
 * Custom text parser for Prometheus metric lines.
 */
export function parsePrometheusMetrics(text) {
  const result = {
    totalEvaluated: 0,
    totalAnomalies: 0,
    byTier: { LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 },
    byDataset: {},
    latencySum: 0,
    latencyCount: 0,
    rawText: text,
  };

  const lines = text.split("\n");
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;

    // aml_transactions_evaluated_total{dataset_model="...",risk_tier="..."} 123
    if (trimmed.startsWith("aml_transactions_evaluated_total")) {
      const match = trimmed.match(/\{.*dataset_model="([^"]+)".*risk_tier="([^"]+)".*\}\s+([\d.e+-]+)/);
      if (match) {
        const [, dataset, tier, valStr] = match;
        const val = Math.round(parseFloat(valStr) || 0);
        result.totalEvaluated += val;

        const normalizedTier = tier.toUpperCase();
        if (normalizedTier.includes("CRIT")) result.byTier.CRITICAL += val;
        else if (normalizedTier.includes("HIGH")) result.byTier.HIGH += val;
        else if (normalizedTier.includes("ELEV") || normalizedTier.includes("MED")) result.byTier.MEDIUM += val;
        else result.byTier.LOW += val;

        result.byDataset[dataset] = (result.byDataset[dataset] || 0) + val;
      }
    }

    // aml_anomalies_detected_total{dataset_model="..."} 45
    if (trimmed.startsWith("aml_anomalies_detected_total")) {
      const match = trimmed.match(/\{.*dataset_model="([^"]+)".*\}\s+([\d.e+-]+)/);
      if (match) {
        const val = Math.round(parseFloat(match[2]) || 0);
        result.totalAnomalies += val;
      }
    }

    // aml_inference_latency_seconds_sum / count
    if (trimmed.startsWith("aml_inference_latency_seconds_sum")) {
      const match = trimmed.match(/([\d.e+-]+)$/);
      if (match) result.latencySum += parseFloat(match[1]) || 0;
    }
    if (trimmed.startsWith("aml_inference_latency_seconds_count")) {
      const match = trimmed.match(/([\d.e+-]+)$/);
      if (match) result.latencyCount += parseFloat(match[1]) || 0;
    }
  }

  result.avgLatencyMs =
    result.latencyCount > 0 ? (result.latencySum / result.latencyCount) * 1000 : null;

  return result;
}

/**
 * Scores a 7-feature IBM banking transaction via POST /api/v1/score/transaction.
 */
export async function scoreTransaction(payload, baseUrl = DEFAULT_API_URL) {
  const cleanUrl = baseUrl.replace(/\/+$/, "");
  const res = await requestWithTimeout(
    `${cleanUrl}/api/v1/score/transaction`,
    {
      method: "POST",
      body: JSON.stringify({
        transaction_id: String(payload.transaction_id || "").trim(),
        from_bank: String(payload.from_bank || "").trim(),
        to_bank: String(payload.to_bank || "").trim(),
        account_from: String(payload.account_from || "").trim(),
        account_to: String(payload.account_to || "").trim(),
        amount: Number(payload.amount),
        currency: String(payload.currency || "USD").trim(),
        payment_format: String(payload.payment_format || "ACH").trim(),
      }),
    },
    5000
  );
  return await res.json();
}

/**
 * Scores an Elliptic Bitcoin graph node (166 features) via POST /api/v1/score/crypto.
 */
export async function scoreCrypto(payload, baseUrl = DEFAULT_API_URL) {
  const cleanUrl = baseUrl.replace(/\/+$/, "");
  const res = await requestWithTimeout(
    `${cleanUrl}/api/v1/score/crypto`,
    {
      method: "POST",
      body: JSON.stringify({
        node_id: String(payload.node_id || "").trim(),
        features: payload.features.map(Number),
      }),
    },
    5000
  );
  return await res.json();
}

/**
 * Scores a batch of transactions via POST /api/v1/score/batch?dataset={dataset}.
 */
export async function scoreBatch(dataset, items, baseUrl = DEFAULT_API_URL) {
  const cleanUrl = baseUrl.replace(/\/+$/, "");
  const res = await requestWithTimeout(
    `${cleanUrl}/api/v1/score/batch?dataset=${encodeURIComponent(dataset)}`,
    {
      method: "POST",
      body: JSON.stringify(items),
    },
    15000
  );
  return await res.json();
}

// =============================================================================
// SAR Compliance & Case Management API Client
// =============================================================================

/**
 * Lists SAR case records with pagination, status/typology filtering, and keyword search.
 * GET /api/v1/sar/list
 */
export async function listSarCases({
  page = 1,
  pageSize = 20,
  status = null,
  typology = null,
  search = null,
} = {}, baseUrl = DEFAULT_API_URL) {
  const cleanUrl = baseUrl.replace(/\/+$/, "");
  const params = new URLSearchParams();
  params.set("page", String(page));
  params.set("page_size", String(pageSize));
  if (status) params.set("status", status);
  if (typology) params.set("typology", typology);
  if (search) params.set("search", search);

  const res = await requestWithTimeout(
    `${cleanUrl}/api/v1/sar/list?${params.toString()}`,
    { method: "GET" },
    8000
  );
  return await res.json();
}

/**
 * Retrieves a single SAR case dossier by ID.
 * GET /api/v1/sar/{sar_id}
 */
export async function getSarCase(sarId, baseUrl = DEFAULT_API_URL) {
  const cleanUrl = baseUrl.replace(/\/+$/, "");
  const res = await requestWithTimeout(
    `${cleanUrl}/api/v1/sar/${encodeURIComponent(sarId)}`,
    { method: "GET" },
    5000
  );
  return await res.json();
}

/**
 * Manually generates a new SAR case dossier.
 * POST /api/v1/sar/generate
 */
export async function generateSar(payload, baseUrl = DEFAULT_API_URL) {
  const cleanUrl = baseUrl.replace(/\/+$/, "");
  const res = await requestWithTimeout(
    `${cleanUrl}/api/v1/sar/generate`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    8000
  );
  return await res.json();
}

/**
 * Updates the remediation status of a SAR case.
 * PATCH /api/v1/sar/{sar_id}/status
 */
export async function updateSarStatus(sarId, newStatus, analystId, notes = "", baseUrl = DEFAULT_API_URL) {
  const cleanUrl = baseUrl.replace(/\/+$/, "");
  const res = await requestWithTimeout(
    `${cleanUrl}/api/v1/sar/${encodeURIComponent(sarId)}/status`,
    {
      method: "PATCH",
      body: JSON.stringify({
        new_status: newStatus,
        analyst_id: analystId,
        resolution_notes: notes,
      }),
    },
    5000
  );
  return await res.json();
}

/**
 * Exports a SAR case dossier as JSON (FINnet 2.0) or PDF (forensic dossier).
 * GET /api/v1/sar/{sar_id}/export?format=pdf|json
 * Returns a Blob for binary downloads.
 */
export async function exportSar(sarId, format = "pdf", baseUrl = DEFAULT_API_URL) {
  const cleanUrl = baseUrl.replace(/\/+$/, "");
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), 15000);

  try {
    const response = await fetch(
      `${cleanUrl}/api/v1/sar/${encodeURIComponent(sarId)}/export?format=${encodeURIComponent(format)}`,
      {
        method: "GET",
        signal: controller.signal,
      }
    );
    clearTimeout(id);

    if (!response.ok) {
      throw new Error(`Export failed: HTTP ${response.status}`);
    }

    const blob = await response.blob();
    const contentDisp = response.headers.get("content-disposition") || "";
    const filenameMatch = contentDisp.match(/filename="?([^"]+)"?/);
    const filename = filenameMatch
      ? filenameMatch[1]
      : `${sarId}.${format === "json" ? "json" : "pdf"}`;

    return { blob, filename };
  } catch (err) {
    clearTimeout(id);
    if (err.name === "AbortError") {
      throw new Error("Export request timed out.");
    }
    throw err;
  }
}

