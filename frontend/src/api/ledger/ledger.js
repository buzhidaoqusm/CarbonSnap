import { apiRequest } from "../http.js";

export async function fetchLedgerSummary(token) {
  return apiRequest("/api/ledger/summary", { token });
}

export async function fetchLedgerGamification(token) {
  return apiRequest("/api/ledger/gamification", { token });
}

export async function fetchLedgerWeeklyLeaderboard(token) {
  return apiRequest("/api/ledger/leaderboard/weekly", { token });
}

export async function fetchLedgerTransactions({ page = 1, perPage = 20, token }) {
  const params = new URLSearchParams({
    page: String(page),
    per_page: String(perPage),
  });
  return apiRequest(`/api/ledger/transactions?${params.toString()}`, { token });
}

export async function fetchLedgerRecords({ page = 1, perPage = 20, token }) {
  const params = new URLSearchParams({
    page: String(page),
    per_page: String(perPage),
  });
  return apiRequest(`/api/ledger/records?${params.toString()}`, { token });
}
