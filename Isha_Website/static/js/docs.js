(function() {
    "use strict";

    // ── Sidebar toggle (mobile) ────────────────────────
    const sidebar = document.getElementById("docs-sidebar");
    const sidebarToggle = document.getElementById("docs-sidebar-toggle");
    if (sidebar && sidebarToggle) {
        sidebarToggle.addEventListener("click", () => {
            sidebar.classList.toggle("open");
        });
        // Close on link click (mobile)
        sidebar.querySelectorAll(".sidebar-link").forEach(link => {
            link.addEventListener("click", () => sidebar.classList.remove("open"));
        });
    }

    // ── Active sidebar link on scroll ──────────────────
    const sidebarLinks = document.querySelectorAll(".sidebar-link[href^='#']");
    const sections = [];
    sidebarLinks.forEach(link => {
        const id = link.getAttribute("href").substring(1);
        const el = document.getElementById(id);
        if (el) sections.push({ el, link });
    });

    let prevActive = null;
    function updateActive() {
        let current = sections[0];
        for (const s of sections) {
            if (s.el.getBoundingClientRect().top <= 120) current = s;
        }
        sidebarLinks.forEach(l => l.classList.remove("active"));
        if (current) {
            current.link.classList.add("active");
            // Auto-scroll sidebar to keep active link visible
            if (current.link !== prevActive && sidebar) {
                prevActive = current.link;
                current.link.scrollIntoView({
                    block: "nearest",
                    behavior: "smooth"
                });
            }
        }
    }
    window.addEventListener("scroll", updateActive, { passive: true });
    updateActive();

    // ── Search filter ──────────────────────────────────
    const searchInput = document.getElementById("docs-search");
    if (searchInput) {
        searchInput.addEventListener("input", () => {
            const q = searchInput.value.toLowerCase();
            sidebarLinks.forEach(link => {
                const text = link.textContent.toLowerCase();
                link.style.display = text.includes(q) || q === "" ? "" : "none";
            });
        });
    }

    // ── Syntax Highlighting ────────────────────────────
    // Lightweight Python/shell/config highlighter
    function highlightCode(text) {
        // HTML-decode entities for processing, then re-encode after
        var decoded = text
            .replace(/&amp;/g, "&")
            .replace(/&lt;/g, "<")
            .replace(/&gt;/g, ">")
            .replace(/&quot;/g, '"')
            .replace(/&#123;/g, "{")
            .replace(/&#125;/g, "}");

        var tokens = [];
        var i = 0;
        var len = decoded.length;

        while (i < len) {
            var ch = decoded[i];
            var rest = decoded.substring(i);

            // Comments: # to end of line (but not inside strings)
            if (ch === "#") {
                var end = decoded.indexOf("\n", i);
                if (end === -1) end = len;
                tokens.push({ type: "comment", value: decoded.substring(i, end) });
                i = end;
                continue;
            }

            // Triple-quoted strings
            if (rest.startsWith('"""') || rest.startsWith("'''")) {
                var q3 = rest.substring(0, 3);
                var close = decoded.indexOf(q3, i + 3);
                if (close === -1) close = len - 3;
                tokens.push({ type: "string", value: decoded.substring(i, close + 3) });
                i = close + 3;
                continue;
            }

            // Strings: single or double quoted
            if (ch === '"' || ch === "'") {
                var quote = ch;
                var j = i + 1;
                while (j < len && decoded[j] !== quote) {
                    if (decoded[j] === "\\") j++;
                    j++;
                }
                tokens.push({ type: "string", value: decoded.substring(i, j + 1) });
                i = j + 1;
                continue;
            }

            // Numbers
            if (/[0-9]/.test(ch) && (i === 0 || /[\s=(:,\[{+\-*/<>!]/.test(decoded[i - 1]))) {
                var numMatch = rest.match(/^[0-9]+\.?[0-9]*/);
                if (numMatch) {
                    tokens.push({ type: "number", value: numMatch[0] });
                    i += numMatch[0].length;
                    continue;
                }
            }

            // Decorators: @word
            if (ch === "@" && (i === 0 || decoded[i - 1] === "\n")) {
                var decMatch = rest.match(/^@[\w.]+/);
                if (decMatch) {
                    tokens.push({ type: "decorator", value: decMatch[0] });
                    i += decMatch[0].length;
                    continue;
                }
            }

            // Words (keywords, builtins, identifiers)
            if (/[a-zA-Z_]/.test(ch)) {
                var wordMatch = rest.match(/^[a-zA-Z_]\w*/);
                if (wordMatch) {
                    var word = wordMatch[0];
                    var keywords = [
                        "import", "from", "as", "def", "async", "await", "class",
                        "return", "if", "elif", "else", "for", "while", "in",
                        "try", "except", "finally", "raise", "with", "yield",
                        "not", "and", "or", "is", "None", "True", "False",
                        "pass", "break", "continue", "lambda", "del", "global",
                        "nonlocal", "assert"
                    ];
                    var builtins = [
                        "print", "len", "range", "int", "str", "float", "bool",
                        "list", "dict", "set", "tuple", "type", "isinstance",
                        "super", "self", "cls", "Exception", "ValueError",
                        "TypeError", "KeyError", "AttributeError"
                    ];
                    // Check if this is a function call (followed by `(`)
                    var afterWord = decoded.substring(i + word.length).trimStart();
                    var isCall = afterWord.length > 0 && afterWord[0] === "(";

                    if (keywords.indexOf(word) !== -1) {
                        tokens.push({ type: "keyword", value: word });
                    } else if (builtins.indexOf(word) !== -1) {
                        tokens.push({ type: "builtin", value: word });
                    } else if (isCall) {
                        tokens.push({ type: "function", value: word });
                    } else {
                        tokens.push({ type: "plain", value: word });
                    }
                    i += word.length;
                    continue;
                }
            }

            // Operators
            if ("=!<>+-*/%|&^~".indexOf(ch) !== -1) {
                var opMatch = rest.match(/^([=!<>]=|[+\-*/%|&^~=<>]+)/);
                if (opMatch) {
                    tokens.push({ type: "operator", value: opMatch[0] });
                    i += opMatch[0].length;
                    continue;
                }
            }

            // Punctuation
            if ("()[]{}:,.".indexOf(ch) !== -1) {
                tokens.push({ type: "punctuation", value: ch });
                i++;
                continue;
            }

            // Everything else (whitespace, etc.)
            tokens.push({ type: "plain", value: ch });
            i++;
        }

        // Convert tokens back to HTML
        var html = "";
        for (var t = 0; t < tokens.length; t++) {
            var tok = tokens[t];
            var escaped = tok.value
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;");
            if (tok.type === "plain" || tok.type === "punctuation") {
                html += escaped;
            } else {
                html += '<span class="sh-' + tok.type + '">' + escaped + '</span>';
            }
        }
        return html;
    }

    // Apply highlighting to all <pre><code> blocks in docs
    document.querySelectorAll(".docs-content pre code").forEach(function(block) {
        block.innerHTML = highlightCode(block.innerHTML);
    });
})();
