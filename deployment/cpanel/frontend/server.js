const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const { URL } = require("node:url");

const publicRoot = path.join(__dirname, "frontend");
const port = Number(process.env.PORT || 3000);

const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".webmanifest": "application/manifest+json",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
};

function sendFile(request, response, filePath) {
  const extension = path.extname(filePath).toLowerCase();
  const headers = {
    "Content-Type": contentTypes[extension] || "application/octet-stream",
    "X-Content-Type-Options": "nosniff",
  };

  if (filePath.includes(`${path.sep}assets${path.sep}`)) {
    headers["Cache-Control"] = "public, max-age=31536000, immutable";
  } else if (extension === ".html") {
    headers["Cache-Control"] = "no-cache";
  } else {
    headers["Cache-Control"] = "public, max-age=2592000";
  }

  response.writeHead(200, headers);
  if (request.method === "HEAD") return response.end();
  fs.createReadStream(filePath).on("error", () => {
    if (!response.headersSent) response.writeHead(500);
    response.end();
  }).pipe(response);
}

const server = http.createServer((request, response) => {
  if (!request.url || !["GET", "HEAD"].includes(request.method || "")) {
    response.writeHead(405, { Allow: "GET, HEAD" });
    return response.end();
  }

  let pathname;
  try {
    pathname = decodeURIComponent(new URL(request.url, "http://localhost").pathname);
  } catch {
    response.writeHead(400);
    return response.end();
  }

  const relativePath = pathname.replace(/^\/+/, "");
  const candidate = path.resolve(publicRoot, relativePath);
  if (candidate !== publicRoot && !candidate.startsWith(`${publicRoot}${path.sep}`)) {
    response.writeHead(403);
    return response.end();
  }

  fs.stat(candidate, (error, stats) => {
    if (!error && stats.isFile()) return sendFile(request, response, candidate);
    if (path.extname(pathname)) {
      response.writeHead(404);
      return response.end();
    }
    return sendFile(request, response, path.join(publicRoot, "index.html"));
  });
});

server.listen(port, "0.0.0.0", () => {
  console.log(`Salovina frontend listening on port ${port}`);
});
