"""
Inline HTML for the Syntharia web UI.

Returns the complete single-page application as a string so it can be
served directly from the Cloudflare Worker without a static-assets binding.
"""


def get_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Syntharia — Creative AI Studio</title>

  <!-- abcjs for rendering ABC music notation -->
  <script src="https://cdn.jsdelivr.net/npm/abcjs@6.3.0/dist/abcjs-basic-min.js"></script>

  <style>
    /* ------------------------------------------------------------------ */
    /* Base & reset                                                         */
    /* ------------------------------------------------------------------ */
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg:         #0f0f1a;
      --surface:    #1a1a2e;
      --surface2:   #16213e;
      --border:     #2d2d4e;
      --accent1:    #7c3aed;
      --accent2:    #2563eb;
      --accent3:    #db2777;
      --text:       #e2e8f0;
      --text-muted: #94a3b8;
      --success:    #10b981;
      --error:      #ef4444;
      --radius:     12px;
      --radius-sm:  6px;
      --shadow:     0 4px 24px rgba(0,0,0,.45);
      --transition: .2s ease;
    }

    html { scroll-behavior: smooth; }

    body {
      font-family: 'Segoe UI', system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      line-height: 1.6;
    }

    /* ------------------------------------------------------------------ */
    /* Header                                                               */
    /* ------------------------------------------------------------------ */
    header {
      background: linear-gradient(135deg, #1e0533 0%, #0c1445 50%, #0d2137 100%);
      border-bottom: 1px solid var(--border);
      padding: 2rem 1.5rem 1.5rem;
      text-align: center;
    }

    .logo {
      display: inline-flex;
      align-items: center;
      gap: .6rem;
      margin-bottom: .5rem;
    }

    .logo-icon {
      width: 44px; height: 44px;
      background: linear-gradient(135deg, var(--accent1), var(--accent2));
      border-radius: 10px;
      display: flex; align-items: center; justify-content: center;
      font-size: 22px;
    }

    .logo h1 { font-size: 2.2rem; font-weight: 800; letter-spacing: -.5px; }
    .logo h1 span { background: linear-gradient(90deg, #a78bfa, #60a5fa, #f472b6);
                    -webkit-background-clip: text; -webkit-text-fill-color: transparent; }

    header p { color: var(--text-muted); font-size: .95rem; margin-top: .25rem; }

    /* ------------------------------------------------------------------ */
    /* Navigation tabs                                                      */
    /* ------------------------------------------------------------------ */
    nav {
      display: flex;
      gap: .5rem;
      justify-content: center;
      flex-wrap: wrap;
      padding: 1.25rem 1rem;
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      position: sticky; top: 0; z-index: 100;
    }

    .tab-btn {
      padding: .55rem 1.25rem;
      border: 1px solid var(--border);
      background: transparent;
      color: var(--text-muted);
      border-radius: 99px;
      cursor: pointer;
      font-size: .88rem;
      font-weight: 500;
      transition: var(--transition);
      display: flex; align-items: center; gap: .4rem;
    }

    .tab-btn:hover { border-color: var(--accent1); color: var(--text); }

    .tab-btn.active {
      background: linear-gradient(135deg, var(--accent1), var(--accent2));
      border-color: transparent;
      color: #fff;
    }

    /* ------------------------------------------------------------------ */
    /* Main layout                                                          */
    /* ------------------------------------------------------------------ */
    main {
      max-width: 960px;
      margin: 2rem auto;
      padding: 0 1rem;
    }

    .tab-panel { display: none; animation: fadeIn .25s ease; }
    .tab-panel.active { display: block; }

    @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; } }

    /* ------------------------------------------------------------------ */
    /* Cards                                                                */
    /* ------------------------------------------------------------------ */
    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.75rem;
      box-shadow: var(--shadow);
    }

    .card + .card { margin-top: 1.25rem; }

    .card-title {
      font-size: 1.15rem;
      font-weight: 700;
      margin-bottom: 1.25rem;
      display: flex; align-items: center; gap: .5rem;
    }

    .card-title .icon {
      width: 32px; height: 32px;
      background: linear-gradient(135deg, var(--accent1)44, var(--accent2)44);
      border-radius: 8px;
      display: flex; align-items: center; justify-content: center;
      font-size: 16px;
    }

    /* ------------------------------------------------------------------ */
    /* Form controls                                                        */
    /* ------------------------------------------------------------------ */
    .field { margin-bottom: 1rem; }

    label {
      display: block;
      font-size: .82rem;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: .05em;
      margin-bottom: .4rem;
    }

    input[type=text],
    textarea,
    select {
      width: 100%;
      background: var(--surface2);
      border: 1px solid var(--border);
      color: var(--text);
      padding: .65rem .9rem;
      border-radius: var(--radius-sm);
      font-size: .93rem;
      font-family: inherit;
      transition: border-color var(--transition);
      resize: vertical;
    }

    input[type=text]:focus,
    textarea:focus,
    select:focus {
      outline: none;
      border-color: var(--accent1);
      box-shadow: 0 0 0 3px rgba(124,58,237,.18);
    }

    textarea { min-height: 80px; }

    .row { display: flex; gap: .75rem; flex-wrap: wrap; }
    .row .field { flex: 1; min-width: 140px; }

    /* Range / slider */
    input[type=range] {
      width: 100%; accent-color: var(--accent1);
    }

    .range-row {
      display: flex; align-items: center; gap: .75rem;
    }

    .range-row input { flex: 1; }

    .range-val {
      min-width: 2.5rem; text-align: right;
      font-size: .85rem; color: var(--text-muted);
    }

    /* File input */
    .file-label {
      display: flex; align-items: center; justify-content: center;
      gap: .6rem; padding: 1.5rem;
      border: 2px dashed var(--border);
      border-radius: var(--radius-sm);
      cursor: pointer; color: var(--text-muted);
      transition: var(--transition);
      text-align: center;
    }

    .file-label:hover { border-color: var(--accent1); color: var(--text); }
    .file-label input { display: none; }

    /* ------------------------------------------------------------------ */
    /* Buttons                                                              */
    /* ------------------------------------------------------------------ */
    .btn {
      padding: .7rem 1.6rem;
      border: none; border-radius: var(--radius-sm);
      font-size: .93rem; font-weight: 600;
      cursor: pointer; transition: var(--transition);
      display: inline-flex; align-items: center; gap: .45rem;
    }

    .btn-primary {
      background: linear-gradient(135deg, var(--accent1), var(--accent2));
      color: #fff;
    }

    .btn-primary:hover { filter: brightness(1.12); transform: translateY(-1px); }
    .btn-primary:disabled { opacity: .55; cursor: not-allowed; transform: none; }

    .btn-secondary {
      background: var(--surface2); border: 1px solid var(--border); color: var(--text);
    }

    .btn-secondary:hover { border-color: var(--accent1); }

    /* ------------------------------------------------------------------ */
    /* Output area                                                          */
    /* ------------------------------------------------------------------ */
    .output-card { display: none; }
    .output-card.visible { display: block; }

    .output-img {
      max-width: 100%; border-radius: var(--radius-sm);
      display: block; margin: 0 auto;
    }

    .poem-text {
      white-space: pre-wrap;
      font-family: 'Georgia', serif;
      font-size: 1.05rem;
      line-height: 1.9;
      color: var(--text);
      background: var(--surface2);
      padding: 1.25rem;
      border-radius: var(--radius-sm);
      border-left: 3px solid var(--accent1);
    }

    .poem-title {
      font-size: 1.25rem; font-weight: 700;
      margin-bottom: .75rem;
      background: linear-gradient(90deg, #a78bfa, #f472b6);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }

    .notes {
      margin-top: 1rem; padding: .75rem;
      background: var(--surface2); border-radius: var(--radius-sm);
      color: var(--text-muted); font-size: .88rem;
      border-left: 3px solid var(--accent2);
    }

    .chord-list {
      display: flex; flex-wrap: wrap; gap: .45rem; margin: .75rem 0;
    }

    .chord-badge {
      background: linear-gradient(135deg, var(--accent1)33, var(--accent2)33);
      border: 1px solid var(--accent1)66;
      color: #a78bfa; border-radius: 99px;
      padding: .25rem .75rem; font-size: .85rem; font-weight: 600;
    }

    .music-meta {
      display: flex; gap: 1.5rem; flex-wrap: wrap;
      margin: .75rem 0; font-size: .88rem; color: var(--text-muted);
    }

    .music-meta span strong { color: var(--text); }

    #abc-render { margin-top: .75rem; }
    #abc-render svg { max-width: 100%; }

    /* ------------------------------------------------------------------ */
    /* Spinner / status                                                     */
    /* ------------------------------------------------------------------ */
    .spinner {
      width: 22px; height: 22px;
      border: 3px solid rgba(255,255,255,.15);
      border-top-color: #fff;
      border-radius: 50%;
      animation: spin .7s linear infinite;
    }

    @keyframes spin { to { transform: rotate(360deg); } }

    .status-msg {
      padding: .65rem 1rem; border-radius: var(--radius-sm);
      font-size: .88rem; margin-top: .75rem;
    }

    .status-msg.error {
      background: rgba(239,68,68,.12); border: 1px solid rgba(239,68,68,.35);
      color: #fca5a5;
    }

    .status-msg.success {
      background: rgba(16,185,129,.12); border: 1px solid rgba(16,185,129,.35);
      color: #6ee7b7;
    }

    /* ------------------------------------------------------------------ */
    /* Action row                                                           */
    /* ------------------------------------------------------------------ */
    .action-row {
      display: flex; align-items: center; gap: 1rem;
      margin-top: 1.25rem; flex-wrap: wrap;
    }

    /* ------------------------------------------------------------------ */
    /* Download link                                                        */
    /* ------------------------------------------------------------------ */
    .dl-link {
      color: var(--accent2); font-size: .85rem;
      text-decoration: none; display: inline-flex; align-items: center; gap: .3rem;
    }

    .dl-link:hover { text-decoration: underline; }

    /* ------------------------------------------------------------------ */
    /* Footer                                                               */
    /* ------------------------------------------------------------------ */
    footer {
      text-align: center; padding: 2rem;
      color: var(--text-muted); font-size: .82rem;
      border-top: 1px solid var(--border); margin-top: 3rem;
    }

    footer a { color: var(--accent1); text-decoration: none; }

    /* ------------------------------------------------------------------ */
    /* Responsive                                                           */
    /* ------------------------------------------------------------------ */
    @media (max-width: 600px) {
      .logo h1 { font-size: 1.7rem; }
      .row { flex-direction: column; }
    }
  </style>
</head>
<body>

<!-- ===== Header ===== -->
<header>
  <div class="logo">
    <div class="logo-icon">✦</div>
    <h1><span>Syntharia</span></h1>
  </div>
  <p>A creative AI studio — generate art, music &amp; poetry with Cloudflare AI</p>
</header>

<!-- ===== Navigation ===== -->
<nav id="nav">
  <button class="tab-btn active" data-tab="art">🎨 Art</button>
  <button class="tab-btn" data-tab="music">🎵 Music</button>
  <button class="tab-btn" data-tab="poetry">📝 Poetry</button>
  <button class="tab-btn" data-tab="style">🖼️ Style Transfer</button>
  <button class="tab-btn" data-tab="refine">✨ Refine</button>
</nav>

<!-- ===== Main ===== -->
<main>

  <!-- ── Art ─────────────────────────────────────────────── -->
  <section id="tab-art" class="tab-panel active">
    <div class="card">
      <div class="card-title"><div class="icon">🎨</div>Image Generation</div>

      <div class="field">
        <label>Describe your image</label>
        <textarea id="art-prompt" rows="3" placeholder="A surreal landscape with floating islands, crystal clear waterfalls and twin moons…"></textarea>
      </div>

      <div class="row">
        <div class="field">
          <label>Style</label>
          <select id="art-style">
            <option value="">— none —</option>
            <option value="photorealistic">Photorealistic</option>
            <option value="artistic">Oil Painting</option>
            <option value="abstract">Abstract</option>
            <option value="digital">Digital Art</option>
            <option value="watercolor">Watercolor</option>
            <option value="sketch">Pencil Sketch</option>
          </select>
        </div>
        <div class="field">
          <label>Quality Steps (1–20)</label>
          <div class="range-row">
            <input type="range" id="art-steps" min="1" max="20" value="8"
                   oninput="document.getElementById('art-steps-val').textContent=this.value" />
            <span class="range-val" id="art-steps-val">8</span>
          </div>
        </div>
      </div>

      <div class="field">
        <label>Negative Prompt (optional)</label>
        <input type="text" id="art-negative" placeholder="blurry, low quality, text, watermark…" />
      </div>

      <div class="action-row">
        <button class="btn btn-primary" id="art-btn" onclick="generateArt()">
          <span>🎨</span> Generate
        </button>
        <div id="art-spinner" style="display:none"><div class="spinner"></div></div>
        <div id="art-status"></div>
      </div>
    </div>

    <div class="card output-card" id="art-output">
      <div class="card-title"><div class="icon">🖼️</div>Result</div>
      <img class="output-img" id="art-result-img" src="" alt="Generated image" />
      <div style="margin-top:.75rem; display:flex; gap:1rem; align-items:center;">
        <a class="dl-link" id="art-dl" href="#" download="syntharia-art.png">⬇ Download PNG</a>
        <button class="btn btn-secondary" onclick="sendToRefine('art')">✨ Refine this</button>
      </div>
    </div>
  </section>

  <!-- ── Music ────────────────────────────────────────────── -->
  <section id="tab-music" class="tab-panel">
    <div class="card">
      <div class="card-title"><div class="icon">🎵</div>Music Composition</div>

      <div class="field">
        <label>Describe the music</label>
        <textarea id="music-prompt" rows="3" placeholder="A melancholic piano piece evoking rain on a quiet Sunday morning…"></textarea>
      </div>

      <div class="row">
        <div class="field">
          <label>Genre</label>
          <select id="music-genre">
            <option value="classical">Classical</option>
            <option value="jazz">Jazz</option>
            <option value="electronic">Electronic</option>
            <option value="ambient">Ambient</option>
            <option value="folk">Folk</option>
            <option value="cinematic">Cinematic</option>
          </select>
        </div>
        <div class="field">
          <label>Target Tempo (BPM)</label>
          <input type="text" id="music-tempo" placeholder="e.g. 90" />
        </div>
      </div>

      <div class="action-row">
        <button class="btn btn-primary" id="music-btn" onclick="composeMusic()">
          <span>🎵</span> Compose
        </button>
        <div id="music-spinner" style="display:none"><div class="spinner"></div></div>
        <div id="music-status"></div>
      </div>
    </div>

    <div class="card output-card" id="music-output">
      <div class="card-title"><div class="icon">🎼</div>Composition</div>
      <div id="music-title-out" class="poem-title" style="-webkit-text-fill-color:unset;background:none;color:#a78bfa;"></div>
      <div class="music-meta" id="music-meta-out"></div>
      <div class="chord-list" id="music-chords-out"></div>
      <div id="abc-render"></div>
      <div class="notes" id="music-notes-out"></div>
      <div style="margin-top:.75rem; display:flex; gap:1rem;">
        <button class="btn btn-secondary" onclick="sendToRefine('music')">✨ Refine this</button>
        <button class="btn btn-secondary" onclick="copyAbc()">📋 Copy ABC notation</button>
      </div>
    </div>
  </section>

  <!-- ── Poetry ───────────────────────────────────────────── -->
  <section id="tab-poetry" class="tab-panel">
    <div class="card">
      <div class="card-title"><div class="icon">📝</div>Poetry Generator</div>

      <div class="field">
        <label>Theme / Subject</label>
        <textarea id="poetry-prompt" rows="3" placeholder="The passage of time observed through the changing of seasons…"></textarea>
      </div>

      <div class="row">
        <div class="field">
          <label>Poetic Form</label>
          <select id="poetry-form">
            <option value="free">Free Verse</option>
            <option value="sonnet">Sonnet</option>
            <option value="haiku">Haiku</option>
            <option value="ballad">Ballad</option>
            <option value="ode">Ode</option>
            <option value="limerick">Limerick</option>
          </select>
        </div>
        <div class="field">
          <label>Tone</label>
          <select id="poetry-tone">
            <option value="">— any —</option>
            <option value="romantic">Romantic</option>
            <option value="melancholic">Melancholic</option>
            <option value="joyful">Joyful</option>
            <option value="philosophical">Philosophical</option>
            <option value="mysterious">Mysterious</option>
            <option value="hopeful">Hopeful</option>
          </select>
        </div>
      </div>

      <div class="action-row">
        <button class="btn btn-primary" id="poetry-btn" onclick="generatePoetry()">
          <span>📝</span> Write Poem
        </button>
        <div id="poetry-spinner" style="display:none"><div class="spinner"></div></div>
        <div id="poetry-status"></div>
      </div>
    </div>

    <div class="card output-card" id="poetry-output">
      <div class="card-title"><div class="icon">✍️</div>Your Poem</div>
      <div class="poem-title" id="poetry-title-out"></div>
      <div class="poem-text" id="poetry-poem-out"></div>
      <div class="notes" id="poetry-notes-out"></div>
      <div style="margin-top:.75rem; display:flex; gap:1rem;">
        <button class="btn btn-secondary" onclick="sendToRefine('poetry')">✨ Refine this</button>
        <button class="btn btn-secondary" onclick="copyPoem()">📋 Copy poem</button>
      </div>
    </div>
  </section>

  <!-- ── Style Transfer ───────────────────────────────────── -->
  <section id="tab-style" class="tab-panel">
    <div class="card">
      <div class="card-title"><div class="icon">🖼️</div>Style Transfer</div>

      <div class="field">
        <label>Source Image</label>
        <label class="file-label" id="style-file-label">
          <span id="style-file-name">📁 Click to choose an image (PNG / JPEG)</span>
          <input type="file" id="style-file" accept="image/png,image/jpeg,image/webp"
                 onchange="previewStyleImage(this)" />
        </label>
        <img id="style-preview" src="" alt="" style="display:none; max-width:100%; margin-top:.75rem; border-radius:6px;" />
      </div>

      <div class="row">
        <div class="field">
          <label>Style Preset</label>
          <select id="style-preset">
            <option value="">— custom only —</option>
            <option value="van_gogh">Van Gogh</option>
            <option value="monet">Monet</option>
            <option value="picasso">Picasso</option>
            <option value="anime">Anime</option>
            <option value="watercolor">Watercolor</option>
            <option value="cyberpunk">Cyberpunk</option>
            <option value="oil_painting">Oil Painting</option>
            <option value="sketch">Sketch</option>
          </select>
        </div>
        <div class="field">
          <label>Custom Style Description</label>
          <input type="text" id="style-custom" placeholder="dreamy impressionist, soft pastel…" />
        </div>
      </div>

      <div class="field">
        <label>Style Strength</label>
        <div class="range-row">
          <input type="range" id="style-strength" min="1" max="100" value="60"
                 oninput="document.getElementById('style-strength-val').textContent=(this.value/100).toFixed(2)" />
          <span class="range-val" id="style-strength-val">0.60</span>
        </div>
      </div>

      <div class="action-row">
        <button class="btn btn-primary" id="style-btn" onclick="applyStyle()">
          <span>🖼️</span> Apply Style
        </button>
        <div id="style-spinner" style="display:none"><div class="spinner"></div></div>
        <div id="style-status"></div>
      </div>
    </div>

    <div class="card output-card" id="style-output">
      <div class="card-title"><div class="icon">✦</div>Styled Result</div>
      <img class="output-img" id="style-result-img" src="" alt="Styled image" />
      <div style="margin-top:.75rem; display:flex; gap:1rem;">
        <a class="dl-link" id="style-dl" href="#" download="syntharia-styled.png">⬇ Download PNG</a>
        <button class="btn btn-secondary" onclick="sendToRefine('art-image')">✨ Refine this</button>
      </div>
    </div>
  </section>

  <!-- ── Refine ────────────────────────────────────────────── -->
  <section id="tab-refine" class="tab-panel">
    <div class="card">
      <div class="card-title"><div class="icon">✨</div>Iterative Refinement</div>
      <p style="color:var(--text-muted);font-size:.88rem;margin-bottom:1.25rem;">
        Take any previous creation and evolve it with a natural-language instruction.
      </p>

      <div class="field">
        <label>Content Type</label>
        <select id="refine-type" onchange="toggleRefineFields()">
          <option value="art">Art (re-generate from refined prompt)</option>
          <option value="art-image">Art (style-transfer existing image)</option>
          <option value="music">Music</option>
          <option value="poetry">Poetry</option>
        </select>
      </div>

      <div class="field">
        <label>Refinement Instruction</label>
        <textarea id="refine-instruction" rows="2"
          placeholder="Make it more dramatic with stormy clouds and deeper shadows…"></textarea>
      </div>

      <!-- Art fields -->
      <div id="refine-art-fields">
        <div class="field">
          <label>Original Prompt</label>
          <input type="text" id="refine-art-prompt" placeholder="Original image description…" />
        </div>
        <div class="field">
          <label>Style</label>
          <select id="refine-art-style">
            <option value="">— none —</option>
            <option value="photorealistic">Photorealistic</option>
            <option value="artistic">Oil Painting</option>
            <option value="abstract">Abstract</option>
            <option value="digital">Digital Art</option>
            <option value="watercolor">Watercolor</option>
            <option value="sketch">Pencil Sketch</option>
          </select>
        </div>
      </div>

      <!-- Art-image fields -->
      <div id="refine-art-image-fields" style="display:none">
        <div class="field">
          <label>Image to Refine</label>
          <label class="file-label">
            <span id="refine-img-name">📁 Choose image</span>
            <input type="file" id="refine-img-file" accept="image/*"
                   onchange="previewRefineImage(this)" />
          </label>
          <img id="refine-img-preview" src="" alt="" style="display:none;max-width:100%;margin-top:.75rem;border-radius:6px;" />
        </div>
      </div>

      <!-- Music fields -->
      <div id="refine-music-fields" style="display:none">
        <div class="field">
          <label>Original Music Prompt</label>
          <input type="text" id="refine-music-prompt" placeholder="Original description…" />
        </div>
        <div class="field">
          <label>ABC Notation (paste previous output)</label>
          <textarea id="refine-abc" rows="4" placeholder="X:1&#10;T:Title&#10;…"></textarea>
        </div>
        <div class="row">
          <div class="field">
            <label>Genre</label>
            <select id="refine-music-genre">
              <option value="classical">Classical</option>
              <option value="jazz">Jazz</option>
              <option value="electronic">Electronic</option>
              <option value="ambient">Ambient</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Poetry fields -->
      <div id="refine-poetry-fields" style="display:none">
        <div class="field">
          <label>Original Prompt</label>
          <input type="text" id="refine-poetry-prompt" placeholder="Original theme…" />
        </div>
        <div class="field">
          <label>Previous Poem (paste to refine)</label>
          <textarea id="refine-poem" rows="5" placeholder="Paste previous poem here…"></textarea>
        </div>
        <div class="row">
          <div class="field">
            <label>Form</label>
            <select id="refine-poetry-form">
              <option value="free">Free Verse</option>
              <option value="sonnet">Sonnet</option>
              <option value="haiku">Haiku</option>
              <option value="ballad">Ballad</option>
            </select>
          </div>
          <div class="field">
            <label>Tone</label>
            <select id="refine-poetry-tone">
              <option value="">— any —</option>
              <option value="romantic">Romantic</option>
              <option value="melancholic">Melancholic</option>
              <option value="joyful">Joyful</option>
              <option value="philosophical">Philosophical</option>
            </select>
          </div>
        </div>
      </div>

      <div class="action-row">
        <button class="btn btn-primary" id="refine-btn" onclick="refineContent()">
          <span>✨</span> Refine
        </button>
        <div id="refine-spinner" style="display:none"><div class="spinner"></div></div>
        <div id="refine-status"></div>
      </div>
    </div>

    <div class="card output-card" id="refine-output">
      <div class="card-title"><div class="icon">✦</div>Refined Result</div>
      <div id="refine-result"></div>
    </div>
  </section>

</main>

<footer>
  Built with <a href="https://developers.cloudflare.com/workers/languages/python/" target="_blank">Cloudflare Python Workers</a>
  &amp; <a href="https://developers.cloudflare.com/workers-ai/" target="_blank">Workers AI</a> ·
  <strong style="color:var(--text)">Syntharia</strong> Creative Studio
</footer>

<script>
/* ================================================================
   State
================================================================ */
const state = {
  lastArt:    null,   // { prompt, style, imgSrc }
  lastMusic:  null,   // { prompt, genre, abc, chords }
  lastPoetry: null,   // { prompt, form, tone, title, poem }
  lastStyled: null,   // { imgB64 }
};

/* ================================================================
   Tab navigation
================================================================ */
document.getElementById('nav').addEventListener('click', e => {
  const btn = e.target.closest('.tab-btn');
  if (!btn) return;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
});

/* ================================================================
   Helpers
================================================================ */
function setLoading(prefix, loading) {
  document.getElementById(prefix + '-btn').disabled = loading;
  document.getElementById(prefix + '-spinner').style.display = loading ? 'flex' : 'none';
}

function setStatus(prefix, msg, type = 'error') {
  const el = document.getElementById(prefix + '-status');
  el.innerHTML = msg ? `<div class="status-msg ${type}">${msg}</div>` : '';
}

function showOutput(prefix) {
  document.getElementById(prefix + '-output').classList.add('visible');
}

function imgToB64(file) {
  return new Promise((res, rej) => {
    const r = new FileReader();
    r.onload = e => res(e.target.result.split(',')[1]);
    r.onerror = rej;
    r.readAsDataURL(file);
  });
}

async function postJSON(path, body) {
  const r = await fetch(path, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
  return r;
}

/* ================================================================
   Art generation
================================================================ */
async function generateArt() {
  const prompt = document.getElementById('art-prompt').value.trim();
  if (!prompt) { setStatus('art', 'Please enter a prompt.'); return; }
  setLoading('art', true); setStatus('art', '');

  try {
    const r = await postJSON('/api/art/generate', {
      prompt,
      style: document.getElementById('art-style').value,
      num_steps: parseInt(document.getElementById('art-steps').value),
      negative_prompt: document.getElementById('art-negative').value.trim(),
    });

    if (!r.ok) {
      const e = await r.json().catch(() => ({ error: r.statusText }));
      throw new Error(e.error || r.statusText);
    }

    const blob = await r.blob();
    const src = URL.createObjectURL(blob);
    document.getElementById('art-result-img').src = src;
    document.getElementById('art-dl').href = src;
    showOutput('art');
    state.lastArt = { prompt, style: document.getElementById('art-style').value, imgSrc: src };
    setStatus('art', '✅ Image generated successfully!', 'success');
  } catch (err) {
    setStatus('art', '❌ ' + err.message);
  } finally {
    setLoading('art', false);
  }
}

/* ================================================================
   Music composition
================================================================ */
async function composeMusic() {
  const prompt = document.getElementById('music-prompt').value.trim();
  if (!prompt) { setStatus('music', 'Please enter a prompt.'); return; }
  setLoading('music', true); setStatus('music', '');

  try {
    const r = await postJSON('/api/music/compose', {
      prompt,
      genre: document.getElementById('music-genre').value,
      tempo: document.getElementById('music-tempo').value || undefined,
    });
    const json = await r.json();
    if (!r.ok || !json.success) throw new Error(json.error || 'Composition failed');

    const d = json.data;
    document.getElementById('music-title-out').textContent = d.title || 'Untitled Composition';

    // Meta
    const meta = document.getElementById('music-meta-out');
    meta.innerHTML = [
      d.tempo ? `<span><strong>Tempo:</strong> ${d.tempo} BPM</span>` : '',
      d.time_signature ? `<span><strong>Time:</strong> ${d.time_signature}</span>` : '',
      d.key ? `<span><strong>Key:</strong> ${d.key}</span>` : '',
      `<span><strong>Genre:</strong> ${json.genre}</span>`,
    ].filter(Boolean).join('');

    // Chords
    const chordsEl = document.getElementById('music-chords-out');
    if (Array.isArray(d.chords) && d.chords.length) {
      chordsEl.innerHTML = d.chords.map(c => `<span class="chord-badge">${c}</span>`).join('');
    }

    // ABC notation
    if (d.abc_notation) {
      ABCJS.renderAbc('abc-render', d.abc_notation, {
        responsive: 'resize',
        paddingtop: 0, paddingbottom: 10,
      });
    }

    document.getElementById('music-notes-out').textContent = d.style_notes || '';
    showOutput('music');

    state.lastMusic = {
      prompt, genre: json.genre,
      abc: d.abc_notation || '',
      chords: d.chords || [],
    };

    setStatus('music', '✅ Composition complete!', 'success');
  } catch (err) {
    setStatus('music', '❌ ' + err.message);
  } finally {
    setLoading('music', false);
  }
}

function copyAbc() {
  const abc = state.lastMusic && state.lastMusic.abc;
  if (abc) navigator.clipboard.writeText(abc).then(() => alert('ABC notation copied!'));
}

/* ================================================================
   Poetry generation
================================================================ */
async function generatePoetry() {
  const prompt = document.getElementById('poetry-prompt').value.trim();
  if (!prompt) { setStatus('poetry', 'Please enter a theme or prompt.'); return; }
  setLoading('poetry', true); setStatus('poetry', '');

  try {
    const r = await postJSON('/api/poetry/generate', {
      prompt,
      form: document.getElementById('poetry-form').value,
      tone: document.getElementById('poetry-tone').value,
    });
    const json = await r.json();
    if (!r.ok || !json.success) throw new Error(json.error || 'Poetry generation failed');

    const d = json.data;
    document.getElementById('poetry-title-out').textContent = d.title || 'Untitled';
    document.getElementById('poetry-poem-out').textContent = d.poem || d.raw || '';
    document.getElementById('poetry-notes-out').textContent = d.notes || '';
    showOutput('poetry');

    state.lastPoetry = {
      prompt, form: json.form, tone: json.tone,
      title: d.title, poem: d.poem || d.raw || '',
    };

    setStatus('poetry', '✅ Poem generated!', 'success');
  } catch (err) {
    setStatus('poetry', '❌ ' + err.message);
  } finally {
    setLoading('poetry', false);
  }
}

function copyPoem() {
  const poem = state.lastPoetry && state.lastPoetry.poem;
  if (poem) navigator.clipboard.writeText(poem).then(() => alert('Poem copied!'));
}

/* ================================================================
   Style transfer
================================================================ */
function previewStyleImage(input) {
  const file = input.files[0];
  if (!file) return;
  document.getElementById('style-file-name').textContent = '✅ ' + file.name;
  const url = URL.createObjectURL(file);
  const preview = document.getElementById('style-preview');
  preview.src = url;
  preview.style.display = 'block';
}

async function applyStyle() {
  const file = document.getElementById('style-file').files[0];
  if (!file) { setStatus('style', 'Please select a source image.'); return; }

  const preset = document.getElementById('style-preset').value;
  const custom = document.getElementById('style-custom').value.trim();
  if (!preset && !custom) { setStatus('style', 'Please choose a style preset or enter a custom style.'); return; }

  setLoading('style', true); setStatus('style', '');

  try {
    const b64 = await imgToB64(file);
    const strength = parseInt(document.getElementById('style-strength').value) / 100;

    const r = await postJSON('/api/art/style-transfer', {
      image: b64,
      style_preset: preset,
      style_prompt: custom,
      strength,
      num_steps: 10,
    });

    if (!r.ok) {
      const e = await r.json().catch(() => ({ error: r.statusText }));
      throw new Error(e.error || r.statusText);
    }

    const blob = await r.blob();
    const src = URL.createObjectURL(blob);
    document.getElementById('style-result-img').src = src;
    document.getElementById('style-dl').href = src;
    showOutput('style');

    state.lastStyled = { imgB64: b64 };
    setStatus('style', '✅ Style applied!', 'success');
  } catch (err) {
    setStatus('style', '❌ ' + err.message);
  } finally {
    setLoading('style', false);
  }
}

/* ================================================================
   Refine
================================================================ */
function toggleRefineFields() {
  const type = document.getElementById('refine-type').value;
  document.getElementById('refine-art-fields').style.display       = type === 'art' ? '' : 'none';
  document.getElementById('refine-art-image-fields').style.display = type === 'art-image' ? '' : 'none';
  document.getElementById('refine-music-fields').style.display     = type === 'music' ? '' : 'none';
  document.getElementById('refine-poetry-fields').style.display    = type === 'poetry' ? '' : 'none';
}

function previewRefineImage(input) {
  const file = input.files[0];
  if (!file) return;
  document.getElementById('refine-img-name').textContent = '✅ ' + file.name;
  const url = URL.createObjectURL(file);
  const p = document.getElementById('refine-img-preview');
  p.src = url; p.style.display = 'block';
}

function sendToRefine(type) {
  // Switch to Refine tab
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelector('[data-tab="refine"]').classList.add('active');
  document.getElementById('tab-refine').classList.add('active');

  const sel = document.getElementById('refine-type');

  if (type === 'art' && state.lastArt) {
    sel.value = 'art';
    document.getElementById('refine-art-prompt').value = state.lastArt.prompt;
    document.getElementById('refine-art-style').value  = state.lastArt.style || '';
  } else if (type === 'art-image' && state.lastStyled) {
    sel.value = 'art-image';
  } else if (type === 'music' && state.lastMusic) {
    sel.value = 'music';
    document.getElementById('refine-music-prompt').value = state.lastMusic.prompt;
    document.getElementById('refine-abc').value          = state.lastMusic.abc;
    document.getElementById('refine-music-genre').value  = state.lastMusic.genre;
  } else if (type === 'poetry' && state.lastPoetry) {
    sel.value = 'poetry';
    document.getElementById('refine-poetry-prompt').value = state.lastPoetry.prompt;
    document.getElementById('refine-poem').value          = state.lastPoetry.poem;
    document.getElementById('refine-poetry-form').value   = state.lastPoetry.form;
    document.getElementById('refine-poetry-tone').value   = state.lastPoetry.tone || '';
  }
  toggleRefineFields();
}

async function refineContent() {
  const instruction = document.getElementById('refine-instruction').value.trim();
  if (!instruction) { setStatus('refine', 'Please enter a refinement instruction.'); return; }

  const type = document.getElementById('refine-type').value;
  setLoading('refine', true); setStatus('refine', '');

  try {
    let body = { instruction };
    let contentType, endpoint;

    if (type === 'art') {
      contentType = 'art';
      body = {
        ...body, content_type: 'art',
        prompt: document.getElementById('refine-art-prompt').value.trim(),
        style:  document.getElementById('refine-art-style').value,
      };
    } else if (type === 'art-image') {
      const file = document.getElementById('refine-img-file').files[0];
      if (!file) throw new Error('Please select an image to refine.');
      const b64 = await imgToB64(file);
      contentType = 'art';
      body = { ...body, content_type: 'art', image: b64 };
    } else if (type === 'music') {
      contentType = 'music';
      body = {
        ...body, content_type: 'music',
        prompt:       document.getElementById('refine-music-prompt').value.trim(),
        abc_notation: document.getElementById('refine-abc').value.trim(),
        genre:        document.getElementById('refine-music-genre').value,
      };
    } else {
      contentType = 'poetry';
      body = {
        ...body, content_type: 'poetry',
        prompt: document.getElementById('refine-poetry-prompt').value.trim(),
        poem:   document.getElementById('refine-poem').value.trim(),
        form:   document.getElementById('refine-poetry-form').value,
        tone:   document.getElementById('refine-poetry-tone').value,
      };
    }

    const r = await postJSON('/api/refine', body);
    const resultEl = document.getElementById('refine-result');

    if (contentType === 'art') {
      if (!r.ok) {
        const e = await r.json().catch(() => ({ error: r.statusText }));
        throw new Error(e.error || r.statusText);
      }
      const blob = await r.blob();
      const src = URL.createObjectURL(blob);
      resultEl.innerHTML = `
        <img class="output-img" src="${src}" alt="Refined image" />
        <div style="margin-top:.75rem">
          <a class="dl-link" href="${src}" download="syntharia-refined.png">⬇ Download PNG</a>
        </div>`;
    } else {
      const json = await r.json();
      if (!r.ok || !json.success) throw new Error(json.error || 'Refinement failed');
      const d = json.data;

      if (contentType === 'music') {
        resultEl.innerHTML = `
          <div class="poem-title" style="color:#a78bfa">${d.title || 'Refined Composition'}</div>
          <div class="notes">${d.style_notes || ''}</div>
          <div id="abc-render-refine"></div>`;
        if (d.abc_notation) {
          ABCJS.renderAbc('abc-render-refine', d.abc_notation, { responsive: 'resize' });
        }
      } else {
        resultEl.innerHTML = `
          <div class="poem-title">${d.title || 'Refined Poem'}</div>
          <div class="poem-text">${(d.poem || d.raw || '').replace(/\\n/g, '<br>')}</div>
          <div class="notes">${d.notes || ''}</div>`;
      }
    }

    showOutput('refine');
    setStatus('refine', '✅ Refinement complete!', 'success');
  } catch (err) {
    setStatus('refine', '❌ ' + err.message);
  } finally {
    setLoading('refine', false);
  }
}
</script>
</body>
</html>"""
