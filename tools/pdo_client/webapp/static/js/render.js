// Safe rendering of registry text: a minimal Markdown renderer for card READMEs
// and a Rego highlighter for their rules. Everything is HTML-escaped before any
// markup is added.
//
//   window.render.escape(text)    -> HTML-escaped text
//   window.render.markdown(src)   -> HTML
//   window.render.rego(src)       -> highlighted HTML (for <code class="rego-code">)

(function () {
    function escapeHtml(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function renderInline(text) {
        // Inline code spans are set aside so the emphasis and link passes leave
        // their contents alone.
        var codes = [];
        text = text.replace(/`([^`]+)`/g, function (_, c) {
            codes.push(c);
            return '\u0000' + (codes.length - 1) + '\u0000';
        });
        text = text.replace(
            /\[([^\]]+)\]\(([^)\s]+)\)/g,
            '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
        );
        text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        text = text.replace(/(^|[^*])\*(?!\s)([^*]+?)\*/g, '$1<em>$2</em>');
        text = text.replace(/\u0000(\d+)\u0000/g, function (_, n) {
            return '<code>' + codes[n] + '</code>';
        });
        return text;
    }

    function markdown(src) {
        var lines = String(src).replace(/\r\n?/g, '\n').split('\n');
        var html = '';
        var i = 0;
        var isBlockStart = function (l) {
            return /^\s*$/.test(l) || /^#{1,6}\s+/.test(l) || /^```/.test(l) ||
                /^>\s?/.test(l) || /^\s*[-*+]\s+/.test(l) ||
                /^\s*\d+\.\s+/.test(l) || /^(-{3,}|\*{3,}|_{3,})\s*$/.test(l) ||
                /^\|/.test(l);
        };
        function list(pattern, tag) {
            var items = [];
            while (i < lines.length && pattern.test(lines[i])) {
                items.push(lines[i].replace(pattern, ''));
                i++;
            }
            return '<' + tag + '>' + items.map(function (it) {
                return '<li>' + renderInline(escapeHtml(it)) + '</li>';
            }).join('') + '</' + tag + '>';
        }
        function cells(line) {
            return line.replace(/^\||\|$/g, '').split('|').map(function (c) { return c.trim(); });
        }
        while (i < lines.length) {
            var line = lines[i];
            if (/^```/.test(line)) {
                var buf = [];
                i++;
                while (i < lines.length && !/^```/.test(lines[i])) { buf.push(lines[i]); i++; }
                i++;
                html += '<pre class="md-code"><code>' + escapeHtml(buf.join('\n')) + '</code></pre>';
                continue;
            }
            var heading = /^(#{1,6})\s+(.*)$/.exec(line);
            if (heading) {
                var level = heading[1].length;
                html += '<h' + level + '>' + renderInline(escapeHtml(heading[2])) + '</h' + level + '>';
                i++;
                continue;
            }
            if (/^(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) { html += '<hr>'; i++; continue; }
            if (/^\|/.test(line)) {
                var head = cells(line);
                i++;
                if (i < lines.length && /^\|?\s*:?-{3,}/.test(lines[i])) { i++; }
                var body = [];
                while (i < lines.length && /^\|/.test(lines[i])) { body.push(cells(lines[i])); i++; }
                html += '<table class="data-table"><thead><tr>' + head.map(function (c) {
                    return '<th>' + renderInline(escapeHtml(c)) + '</th>';
                }).join('') + '</tr></thead><tbody>' + body.map(function (row) {
                    return '<tr>' + row.map(function (c) {
                        return '<td>' + renderInline(escapeHtml(c)) + '</td>';
                    }).join('') + '</tr>';
                }).join('') + '</tbody></table>';
                continue;
            }
            if (/^>\s?/.test(line)) {
                var quote = [];
                while (i < lines.length && /^>\s?/.test(lines[i])) {
                    quote.push(lines[i].replace(/^>\s?/, ''));
                    i++;
                }
                html += '<blockquote>' + markdown(quote.join('\n')) + '</blockquote>';
                continue;
            }
            if (/^\s*[-*+]\s+/.test(line)) { html += list(/^\s*[-*+]\s+/, 'ul'); continue; }
            if (/^\s*\d+\.\s+/.test(line)) { html += list(/^\s*\d+\.\s+/, 'ol'); continue; }
            if (/^\s*$/.test(line)) { i++; continue; }
            var para = [];
            while (i < lines.length && !isBlockStart(lines[i])) { para.push(lines[i]); i++; }
            html += '<p>' + renderInline(escapeHtml(para.join('\n'))) + '</p>';
        }
        return html;
    }

    var REGO_KEYWORDS = {
        package: 1, import: 1, default: 1, some: 1, every: 1, in: 1, if: 1,
        else: 1, not: 1, with: 1, as: 1, contains: 1, null: 1, true: 1, false: 1
    };
    var REGO_BUILTINS = {
        count: 1, array: 1, concat: 1, object: 1, sprintf: 1, json: 1, split: 1,
        sort: 1, sum: 1, max: 1, min: 1, upper: 1, lower: 1, trim: 1, walk: 1,
        startswith: 1, endswith: 1, to_number: 1, is_string: 1, is_number: 1, time: 1
    };

    function rego(src) {
        var re = /(#[^\n]*)|("(?:\\.|[^"\\])*")|(\b\d+(?:\.\d+)?\b)|([A-Za-z_][A-Za-z0-9_]*)|(:=|==|!=|<=|>=|[=<>+\-*/])|([\s\S])/g;
        var out = '';
        var m;
        while ((m = re.exec(src)) !== null) {
            if (m[1]) {
                out += '<span class="tok-comment">' + escapeHtml(m[1]) + '</span>';
            } else if (m[2]) {
                out += '<span class="tok-string">' + escapeHtml(m[2]) + '</span>';
            } else if (m[3]) {
                out += '<span class="tok-number">' + escapeHtml(m[3]) + '</span>';
            } else if (m[4]) {
                if (REGO_KEYWORDS[m[4]]) {
                    out += '<span class="tok-keyword">' + m[4] + '</span>';
                } else if (REGO_BUILTINS[m[4]]) {
                    out += '<span class="tok-fn">' + m[4] + '</span>';
                } else {
                    out += escapeHtml(m[4]);
                }
            } else if (m[5]) {
                out += '<span class="tok-op">' + escapeHtml(m[5]) + '</span>';
            } else {
                out += escapeHtml(m[6]);
            }
        }
        return out;
    }

    // A card's README and rule, in the shared #card-detail-modal.
    function showCard(title, readme, source) {
        var modal = document.getElementById('card-detail-modal');
        if (!modal) return;
        document.getElementById('card-detail-title').textContent = title;
        document.getElementById('card-detail-readme').innerHTML = readme
            ? markdown(readme)
            : '<p class="md-empty">No description provided.</p>';
        document.getElementById('card-detail-rego').innerHTML = rego(source);
        selectTab(modal, 'readme');
        modal.classList.remove('hidden');
        modal.querySelector('.modal').scrollTop = 0;
    }

    function selectTab(modal, name) {
        modal.querySelectorAll('[data-card-tab]').forEach(function (b) {
            b.classList.toggle('active', b.dataset.cardTab === name);
        });
        modal.querySelectorAll('[data-card-panel]').forEach(function (p) {
            p.classList.toggle('active', p.dataset.cardPanel === name);
        });
    }

    document.addEventListener('click', function (e) {
        var tab = e.target.closest('[data-card-tab]');
        if (tab) selectTab(tab.closest('.modal-backdrop'), tab.dataset.cardTab);
    });

    window.render = { escape: escapeHtml, markdown: markdown, rego: rego, showCard: showCard };
})();
