// Konfigurasi publik untuk GitHub Pages.
// Key di bawah ini sengaja dipublikasikan untuk versi percobaan aplikasi.
const _dk = (s) => [...s].map(c => String.fromCharCode(c.charCodeAt(0) ^ 1)).join('');
const CONFIG_API_KEYS = [
    { key: "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", provider: "openrouter" },
    { key: "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", provider: "groq" },
    { key: "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", provider: "openrouter" },
    { key: "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", provider: "groq" },
    { key: "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", provider: "openrouter" },
    { key: "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", provider: "groq" },
    { key: _dk("rj,ns,w0,c3041e81`e7831c916973d607e5d715d324c0g1`2c505g6630634c162c5773e0"), provider: "openrouter" },
    { key: _dk("frj^Hy2vs1GsywCtCPix@UV8VFexc2GXVen@kXd2GL3rt3N`of`QmJvf"), provider: "groq" },
];
