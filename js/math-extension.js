// Custom marked.js extensions for LaTeX math rendering via KaTeX

const blockMathRule1 = /^\\\[([\s\S]+?)\\\]/;
const blockMathRule2 = /^\$\$([\s\S]+?)\$\$/;
const inlineMathRule1 = /^\\\(([\s\S]+?)\\\)/;
const inlineMathRule2 = /^\$([^$\n]+?)\$/;

const blockMath1 = {
    name: 'blockMath1',
    level: 'block',
    start(src) { return src.indexOf('\\['); },
    tokenizer(src, tokens) {
        const match = blockMathRule1.exec(src);
        if (match) {
            return {
                type: 'blockMath1',
                raw: match[0],
                text: match[1]
            };
        }
    },
    renderer(token) {
        try {
            return katex.renderToString(token.text, { throwOnError: false, displayMode: true });
        } catch (e) {
            return `<div class="error">${e.message}</div>`;
        }
    }
};

const blockMath2 = {
    name: 'blockMath2',
    level: 'block',
    start(src) { return src.indexOf('$$'); },
    tokenizer(src, tokens) {
        const match = blockMathRule2.exec(src);
        if (match) {
            return {
                type: 'blockMath2',
                raw: match[0],
                text: match[1]
            };
        }
    },
    renderer(token) {
        try {
            return katex.renderToString(token.text, { throwOnError: false, displayMode: true });
        } catch (e) {
            return `<div class="error">${e.message}</div>`;
        }
    }
};

const inlineMath1 = {
    name: 'inlineMath1',
    level: 'inline',
    start(src) { return src.indexOf('\\('); },
    tokenizer(src, tokens) {
        const match = inlineMathRule1.exec(src);
        if (match) {
            return {
                type: 'inlineMath1',
                raw: match[0],
                text: match[1]
            };
        }
    },
    renderer(token) {
        try {
            return katex.renderToString(token.text, { throwOnError: false, displayMode: false });
        } catch (e) {
            return `<span class="error">${e.message}</span>`;
        }
    }
};

const inlineMath2 = {
    name: 'inlineMath2',
    level: 'inline',
    start(src) { return src.indexOf('$'); },
    tokenizer(src, tokens) {
        const match = inlineMathRule2.exec(src);
        if (match) {
            return {
                type: 'inlineMath2',
                raw: match[0],
                text: match[1]
            };
        }
    },
    renderer(token) {
        try {
            return katex.renderToString(token.text, { throwOnError: false, displayMode: false });
        } catch (e) {
            return `<span class="error">${e.message}</span>`;
        }
    }
};

marked.use({ extensions: [blockMath1, blockMath2, inlineMath1, inlineMath2] });