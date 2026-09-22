// Custom marked.js extensions for LaTeX math rendering via KaTeX

function normalizeMath(text) {
    if (!text) return "";
    
    // Convert \[ ... \] to $$ ... $$
    text = text.replace(/\\\[([\s\S]*?)\\\]/g, (match, eq) => '\n\n$$\n' + eq.trim() + '\n$$\n\n');

    // Convert \( ... \) to $ ... $
    text = text.replace(/\\\(([\s\S]*?)\\\)/g, (match, eq) => '$' + eq.trim() + '$');

    // Convert standalone [ ... ] containing LaTeX commands to $$ ... $$
    text = text.replace(/(^|\n)\s*\[\s*\n([\s\S]*?\\[a-zA-Z][\s\S]*?)\n\s*\]\s*($|\n)/g, (match, pre, eq, post) => {
        return pre + '\n\n$$\n' + eq.trim() + '\n$$\n\n' + post;
    });

    // Convert ( \command ... ) containing LaTeX to $ \command ... $ when not preceded by $
    text = text.replace(/(^|[^$])\(\s*(\\[a-zA-Z][^$\n]*?)\s*\)(?=[^$]|$)/g, (match, pre, eq) => {
        return pre + '$' + eq.trim() + '$';
    });

    return text;
}

// Inline-level display math: works even inside paragraphs without blank lines
const displayMath1 = {
    name: 'displayMath1',
    level: 'inline',
    start(src) { return src.indexOf('\\['); },
    tokenizer(src) {
        const match = /^\\\[([\s\S]+?)\\\]/.exec(src);
        if (match) {
            return { type: 'displayMath1', raw: match[0], text: match[1].trim() };
        }
    },
    renderer(token) {
        try {
            return katex.renderToString(token.text, { displayMode: true, throwOnError: false });
        } catch (e) {
            return `<div class="katex-error">${token.text}</div>`;
        }
    }
};

const displayMath2 = {
    name: 'displayMath2',
    level: 'inline',
    start(src) { return src.indexOf('$$'); },
    tokenizer(src) {
        const match = /^\$\$([\s\S]+?)\$\$/.exec(src);
        if (match) {
            return { type: 'displayMath2', raw: match[0], text: match[1].trim() };
        }
    },
    renderer(token) {
        try {
            return katex.renderToString(token.text, { displayMode: true, throwOnError: false });
        } catch (e) {
            return `<div class="katex-error">${token.text}</div>`;
        }
    }
};

const bracketBlockMath = {
    name: 'bracketBlockMath',
    level: 'inline',
    start(src) { return src.indexOf('['); },
    tokenizer(src) {
        const match = /^\[\s*\n([\s\S]*?\\[a-zA-Z][\s\S]*?)\n\s*\]/.exec(src);
        if (match) {
            return { type: 'bracketBlockMath', raw: match[0], text: match[1].trim() };
        }
    },
    renderer(token) {
        try {
            return katex.renderToString(token.text, { displayMode: true, throwOnError: false });
        } catch (e) {
            return `<div class="katex-error">${token.text}</div>`;
        }
    }
};

const inlineMath1 = {
    name: 'inlineMath1',
    level: 'inline',
    start(src) { return src.indexOf('\\('); },
    tokenizer(src) {
        const match = /^\\\(([\s\S]+?)\\\)/.exec(src);
        if (match) {
            return { type: 'inlineMath1', raw: match[0], text: match[1].trim() };
        }
    },
    renderer(token) {
        try {
            return katex.renderToString(token.text, { displayMode: false, throwOnError: false });
        } catch (e) {
            return `<span class="katex-error">${token.text}</span>`;
        }
    }
};

const inlineMath2 = {
    name: 'inlineMath2',
    level: 'inline',
    start(src) { return src.indexOf('$'); },
    tokenizer(src) {
        const match = /^\$([^$\n]+?)\$/.exec(src);
        if (match) {
            return { type: 'inlineMath2', raw: match[0], text: match[1].trim() };
        }
    },
    renderer(token) {
        try {
            return katex.renderToString(token.text, { displayMode: false, throwOnError: false });
        } catch (e) {
            return `<span class="katex-error">${token.text}</span>`;
        }
    }
};

if (typeof marked !== 'undefined' && marked.use) {
    marked.use({ extensions: [displayMath1, displayMath2, bracketBlockMath, inlineMath1, inlineMath2] });
}