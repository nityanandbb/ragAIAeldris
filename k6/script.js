import http from "k6/http";
import { check, sleep } from "k6";
import { authHeaders, pick } from "./helpers.js";

const BASE = __ENV.API_BASE_URL || "http://52.221.197.158:8000";
const TOKEN = __ENV.RAG_API_TOKEN || "";
const P95 = Number(__ENV.K6_P95_MS || 1200);

export const options = {
  stages: [
    { duration: "15s", target: 10 },
    { duration: "45s", target: 50 },
    { duration: "1m", target: Number(__ENV.K6_VUS || 100) },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: [`p(95)<${P95}`],
  },
};

export function setup() {
  const seed = {
    docs: [
      {
        id: "k6-1",
        text: "Use Authorization: Bearer <token>. The OpenAPI spec is at /openapi.json.",
      },
      { id: "k6-2", text: "The capital of India is New Delhi." },
      {
        id: "k6-3",
        text: "RAG retrieves passages (contexts) and grounds answers in them.",
      },
    ],
  };
  const res = http.post(`${BASE}/ingest`, JSON.stringify(seed), {
    headers: authHeaders(TOKEN),
    timeout: "30s",
  });
  check(res, { "seed ingest ok": (r) => [200, 201, 202].includes(r.status) });
}

const questions = [
  "Where is the OpenAPI spec URL?",
  "How do I authenticate to this API?",
  "What is the capital of India?",
  "What does a RAG system do?",
];

export default function () {
  const q = pick(questions);
  const res = http.post(`${BASE}/query`, JSON.stringify({ question: q }), {
    headers: authHeaders(TOKEN),
    timeout: "30s",
  });
  check(res, {
    "status 200": (r) => r.status === 200,
    "answer present": (r) => {
      try {
        return typeof r.json().answer === "string";
      } catch {
        return false;
      }
    },
    "contexts array": (r) => {
      try {
        return Array.isArray(r.json().contexts);
      } catch {
        return false;
      }
    },
  });
  sleep(1);
}
