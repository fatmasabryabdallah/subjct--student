import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlsplit


UPSTREAM = "https://zatoona-platform.vercel.app"
HOST = "127.0.0.1"
PORT = 8765
REPLACEMENTS = (
    ("Abdallah Mohamed Ali", "Fatma Sabry Abdallah"),
    ("عبدالله محمد علي", "Fatma Sabry Abdallah"),
    ("01285512241", "01285949284"),
    ("201285512241", "201285949284"),
    ("الزتـونة", "الانجاز"),
    ("الزتونه", "الانجاز"),
    ("الزتونة", "الانجاز"),
    ("زتونه", "الانجاز"),
    ("زتونة", "الانجاز"),
    ("Zatoona", "Al-Enjaz"),
    ("ZATOONA", "AL-ENJAZ"),
)
BRANDING_SCRIPT = """
<script>
(() => {
  const replacements = __REPLACEMENTS__;
  const swap = (value) => replacements.reduce(
    (text, [from, to]) => text.split(from).join(to),
    value
  );
  const updateNode = (node) => {
    if (node.nodeType === Node.TEXT_NODE) {
      if (node.parentElement?.closest("a")?.href.includes("magixa.tech")) {
        const link = node.parentElement.closest("a");
        const wrapper = link.closest("li") || link.parentElement;
        if (wrapper) wrapper.remove();
        else link.remove();
        return;
      }
      const updated = swap(node.nodeValue || "");
      if (updated !== node.nodeValue) node.nodeValue = updated;
      return;
    }
    if (node.nodeType !== Node.ELEMENT_NODE) return;
    if (node.matches('a[href*="magixa.tech"]')) {
      const wrapper = node.closest("li") || node.parentElement;
      if (wrapper) wrapper.remove();
      else node.remove();
      return;
    }
    for (const name of ["href", "title", "aria-label", "alt"]) {
      const value = node.getAttribute(name);
      if (value) {
        const updated = swap(value);
        if (updated !== value) node.setAttribute(name, updated);
      }
    }
    for (const child of node.childNodes) updateNode(child);
  };
  window.addEventListener("load", () => {
    updateNode(document.documentElement);
    new MutationObserver((records) => {
      for (const record of records) {
        if (record.type === "attributes") updateNode(record.target);
        else if (record.type === "characterData") updateNode(record.target);
        else for (const node of record.addedNodes) updateNode(node);
      }
    }).observe(document.documentElement, {
      subtree: true,
      childList: true,
      characterData: true,
      attributes: true,
      attributeFilter: ["href", "title", "aria-label", "alt"],
    });
  }, { once: true });
})();
</script>
""".replace("__REPLACEMENTS__", json.dumps(REPLACEMENTS, ensure_ascii=True))
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


class SiteProxy(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        self.forward()

    def do_HEAD(self):
        self.forward()

    def do_POST(self):
        self.forward()

    def do_OPTIONS(self):
        self.forward()

    def forward(self):
        target = UPSTREAM + self.path
        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in HOP_BY_HOP_HEADERS
            and key.lower() not in {"host", "accept-encoding", "content-length"}
        }
        headers["Accept-Encoding"] = "identity"
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        request = Request(target, data=body or None, headers=headers, method=self.command)

        try:
            response = urlopen(request, timeout=30)
        except HTTPError as error:
            response = error
        except (URLError, TimeoutError) as error:
            message = f"Unable to load the reference site: {error}".encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(message)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(message)
            return

        with response:
            payload = response.read()
            content_type = response.headers.get("Content-Type", "")
            if content_type.startswith("text/html"):
                try:
                    text = payload.decode("utf-8")
                except UnicodeDecodeError:
                    pass
                else:
                    if "</body>" in text:
                        text = text.replace("</body>", BRANDING_SCRIPT + "</body>", 1)
                    payload = text.encode("utf-8")

            self.send_response(response.status)
            for key, value in response.headers.items():
                lower_key = key.lower()
                if lower_key in HOP_BY_HOP_HEADERS or lower_key in {
                    "content-length",
                    "content-encoding",
                    "etag",
                    "last-modified",
                    "cache-control",
                    "expires",
                }:
                    continue
                if lower_key == "location":
                    upstream_origin = urlsplit(UPSTREAM)
                    value = value.replace(
                        f"{upstream_origin.scheme}://{upstream_origin.netloc}",
                        f"http://{HOST}:{PORT}",
                    )
                self.send_header(key, value)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(payload)

    def log_message(self, format_string, *args):
        print(f"{self.address_string()} - {format_string % args}")


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), SiteProxy)
    print(f"Al-Enjaz local site: http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping local site proxy.")
    finally:
        server.server_close()
