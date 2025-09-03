export function authHeaders(token) {
  const h = { "Content-Type": "application/json" };
  if (token) h["Authorization"] = `Bearer ${token}`;
  return h;
}

export function pick(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}
