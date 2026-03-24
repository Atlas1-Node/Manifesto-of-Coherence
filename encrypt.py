#!/usr/bin/env python3
"""
Encrypts the .page content of index.html with AES-256-GCM + PBKDF2.
Password: Coherence
Writes the result back to index.html.
"""

import os, base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

PASSWORD = b"Coherence"
SALT     = os.urandom(16)
IV       = os.urandom(12)

# ── Derive key ────────────────────────────────────────────────────────────────
kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=SALT, iterations=100000)
key = kdf.derive(PASSWORD)

# ── Read HTML ─────────────────────────────────────────────────────────────────
with open("index.html", "r", encoding="utf-8") as f:
    html = f.read()

# ── Extract .page content (between <div class="page"> and </div><!-- /page -->) ──
PAGE_OPEN  = '<div class="page">'
PAGE_CLOSE = '</div><!-- /page -->'

start = html.index(PAGE_OPEN)  + len(PAGE_OPEN)
end   = html.index(PAGE_CLOSE)
page_content = html[start:end]

# ── Encrypt ───────────────────────────────────────────────────────────────────
aesgcm     = AESGCM(key)
ciphertext = aesgcm.encrypt(IV, page_content.encode("utf-8"), None)
# Layout: salt(16) + iv(12) + ciphertext+tag
blob       = base64.b64encode(SALT + IV + ciphertext).decode("ascii")

# ── Lock screen HTML ──────────────────────────────────────────────────────────
lock_screen = """
<div id="lock-screen">
  <div class="lock-inner">
    <div class="lock-eyebrow">MANIFESTO OF COHERENCE</div>
    <div class="lock-glyph">&#x4D30;</div>
    <div class="lock-subtitle">Constitutional Edition &middot; v9</div>
    <div class="lock-form">
      <input type="password" id="lock-input" placeholder="enter passphrase"
             autocomplete="off" spellcheck="false">
      <button id="lock-submit">ENTER</button>
    </div>
    <div id="lock-error" class="lock-error"></div>
  </div>
</div>
"""

# ── Decryption script ─────────────────────────────────────────────────────────
decrypt_script = f"""<script>
(async function(){{
  'use strict';
  const BLOB = '{blob}';

  async function tryDecrypt(password) {{
    const raw  = Uint8Array.from(atob(BLOB), c => c.charCodeAt(0));
    const salt = raw.slice(0,  16);
    const iv   = raw.slice(16, 28);
    const ct   = raw.slice(28);
    const enc  = new TextEncoder();
    let key;
    try {{
      const km = await crypto.subtle.importKey('raw', enc.encode(password), 'PBKDF2', false, ['deriveKey']);
      key = await crypto.subtle.deriveKey(
        {{ name:'PBKDF2', salt, iterations:100000, hash:'SHA-256' }},
        km, {{ name:'AES-GCM', length:256 }}, false, ['decrypt']
      );
    }} catch {{ return null; }}
    try {{
      const plain = await crypto.subtle.decrypt({{ name:'AES-GCM', iv }}, key, ct);
      return new TextDecoder().decode(plain);
    }} catch {{ return null; }}
  }}

  async function unlock() {{
    const pw   = document.getElementById('lock-input').value;
    const html = await tryDecrypt(pw);
    if (html) {{
      const page = document.querySelector('.page');
      page.innerHTML = html;
      page.style.display = '';
      document.getElementById('lock-screen').style.display = 'none';
      // Re-run reveal observer on injected content
      const els = page.querySelectorAll('.reveal, .section, .divider, .edition-mark');
      const obs = new IntersectionObserver(entries => {{
        entries.forEach(e => {{
          if (e.isIntersecting) {{ e.target.classList.add('visible'); obs.unobserve(e.target); }}
        }});
      }}, {{ threshold: 0.08 }});
      els.forEach(el => obs.observe(el));
    }} else {{
      const inp = document.getElementById('lock-input');
      inp.value = '';
      inp.classList.remove('shake');
      void inp.offsetWidth; // reflow to restart animation
      inp.classList.add('shake');
      document.getElementById('lock-error').textContent = 'Incorrect passphrase.';
    }}
  }}

  document.getElementById('lock-submit').addEventListener('click', unlock);
  document.getElementById('lock-input').addEventListener('keydown', e => {{
    if (e.key === 'Enter') unlock();
  }});
}})();
</script>"""

# ── Lock screen CSS ───────────────────────────────────────────────────────────
lock_css = """
/* ── LOCK SCREEN ── */
#lock-screen {
  position: fixed; inset: 0; z-index: 50;
  display: flex; align-items: center; justify-content: center;
}
.lock-inner {
  text-align: center;
  display: flex; flex-direction: column; align-items: center; gap: 1.2rem;
}
.lock-eyebrow {
  font-family: 'Cinzel', serif; font-size: 0.58rem;
  letter-spacing: 0.42em; color: var(--gold);
  text-transform: uppercase;
}
.lock-glyph {
  font-size: 2.4rem; color: var(--gold); opacity: 0.5;
  letter-spacing: 0.2em;
}
.lock-subtitle {
  font-family: 'Cormorant Garamond', serif;
  font-size: 0.95rem; font-style: italic;
  color: var(--text-dim); letter-spacing: 0.06em;
}
.lock-form {
  display: flex; flex-direction: column; align-items: center; gap: 0.8rem;
  margin-top: 0.6rem;
}
#lock-input {
  background: none;
  border: none;
  border-bottom: 1px solid var(--rule-strong);
  color: var(--text);
  font-family: 'Cormorant Garamond', serif;
  font-size: 1.05rem; font-style: italic;
  letter-spacing: 0.12em;
  text-align: center;
  width: 220px; padding: 0.5rem 0.2rem;
  outline: none;
  transition: border-color 0.3s;
}
#lock-input::placeholder { color: var(--text-dim); opacity: 0.5; }
#lock-input:focus { border-bottom-color: var(--gold); }
#lock-submit {
  background: none;
  border: 1px solid var(--rule-strong);
  color: var(--text-dim);
  font-family: 'Cinzel', serif; font-size: 0.52rem;
  letter-spacing: 0.38em; text-transform: uppercase;
  padding: 0.55rem 1.4rem; cursor: pointer;
  transition: border-color 0.3s, color 0.3s;
}
#lock-submit:hover { border-color: var(--gold); color: var(--gold); }
.lock-error {
  font-family: 'Cormorant Garamond', serif;
  font-size: 0.82rem; font-style: italic;
  color: var(--gold-dim); letter-spacing: 0.08em;
  min-height: 1.2rem;
}
@keyframes shake {
  0%,100% { transform: translateX(0); }
  20%,60%  { transform: translateX(-6px); }
  40%,80%  { transform: translateX(6px); }
}
.shake { animation: shake 0.45s ease; }
"""

# ── Inject lock CSS before </style> ──────────────────────────────────────────
html = html.replace("</style>", lock_css + "\n</style>", 1)

# ── Replace .page content with empty div (hidden) ────────────────────────────
html = html.replace(
    PAGE_OPEN + page_content + PAGE_CLOSE,
    PAGE_OPEN + "\n" + PAGE_CLOSE
)

# ── Remove old reveal observer (we re-run it after unlock) ───────────────────
# Keep it — it won't find any .reveal elements until after unlock, harmless.

# ── Insert lock screen right after <body> tag area (after #bh-bg div) ────────
# Actually insert it just before </body>
html = html.replace("</body>", lock_screen + "\n</body>", 1)

# ── Insert decrypt script just before </body> ─────────────────────────────────
html = html.replace("</body>", decrypt_script + "\n</body>", 1)

# ── Remove axiom guards (galaxy/sun scripts bail without article-zero in DOM) ──
html = html.replace(
    "  const axiom = document.getElementById('article-zero');\n  if (!axiom) return;\n",
    "  const axiom = document.getElementById('article-zero');\n",
    2  # replace both occurrences
)

# ── Write output ──────────────────────────────────────────────────────────────
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print(f"Done. Encrypted {len(page_content)} chars → {len(ciphertext)} bytes ciphertext.")
print(f"Salt: {SALT.hex()}")
print(f"IV:   {IV.hex()}")
