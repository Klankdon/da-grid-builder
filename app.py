import base64
import io
import os
import zipfile
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from PIL import Image

app = FastAPI(title="DA Grid Builder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure local output directory exists inside container
OUTPUT_DIR = "output_slices"
os.makedirs(OUTPUT_DIR, exist_ok=True)


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
  return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>DA Grid Builder</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-900 text-white min-h-screen p-6">
        <h1 class="text-2xl font-bold mb-6 text-pink-500">DA Clue-tober Grid Builder</h1>
        
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <!-- Sidebar Controls -->
            <div class="bg-slate-800 p-5 rounded-xl space-y-4">
                <div id="drop-zone" class="border-2 border-dashed border-pink-500/50 p-6 rounded-lg text-center cursor-pointer hover:bg-slate-700/50 transition">
                    <span class="font-bold text-pink-400 block">Click or Drop Master Canvas</span>
                    <span class="text-xs text-slate-400 block mt-1">PNG, JPG, WEBP</span>
                    <input type="file" id="file-input" accept="image/*" class="hidden">
                </div>

                <div>
                    <label class="block text-xs font-mono text-slate-400 uppercase">Target URL</label>
                    <input type="text" id="target-url" value="https://www.deviantart.com/deviantai" class="w-full bg-slate-700 border border-slate-600 p-2 rounded mt-1 text-white text-sm">
                </div>

                <div>
                    <label class="block text-xs font-mono text-slate-400 uppercase">Grid Slices</label>
                    <select id="num-slices" class="w-full bg-slate-700 border border-slate-600 p-2 rounded mt-1 text-white text-sm">
                        <option value="3" selected>3 Slices (Left, Target, Right)</option>
                        <option value="5">5 Slices Grid</option>
                        <option value="9">9 Slices Grid</option>
                    </select>
                </div>

                <div id="coords-info" class="hidden bg-slate-900 p-3 rounded font-mono text-xs space-y-1 border border-slate-700">
                    <div class="text-pink-400 font-bold">Bounding Box Coordinates:</div>
                    <div id="box-dimensions">0 x 0 px</div>
                </div>

                <button id="btn-slice" disabled class="w-full bg-pink-600 hover:bg-pink-700 disabled:opacity-40 p-3 rounded font-bold transition">
                    Generate Slices & HTML
                </button>

                <div id="output-area" class="hidden space-y-3">
                    <a id="download-zip" href="#" download class="block text-center w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-2 rounded text-sm transition">
                        Download All Slices (.ZIP)
                    </a>
                    <div>
                        <label class="block text-xs font-mono text-slate-400 uppercase mb-1">Sta.sh Journal HTML Markup</label>
                        <textarea id="html-output" readonly class="w-full h-32 bg-slate-950 p-2 text-xs font-mono text-pink-300 rounded border border-slate-800"></textarea>
                    </div>
                </div>
            </div>

            <!-- Canvas Viewport -->
            <div class="col-span-2 bg-slate-800 p-4 rounded-xl flex items-center justify-center min-h-[500px]">
                <div id="canvas-wrapper" class="relative hidden select-none cursor-crosshair">
                    <img id="canvas-img" class="max-h-[75vh] w-auto rounded border border-slate-700" draggable="false">
                    <svg id="svg-overlay" class="absolute top-0 left-0 w-full h-full pointer-events-none"></svg>
                </div>
                <p id="placeholder-text" class="text-slate-500">Drop an artwork canvas on the left to begin drawing selection boxes.</p>
            </div>
        </div>

        <script>
            let selectedFile = null;
            let imgElement = document.getElementById('canvas-img');
            let wrapper = document.getElementById('canvas-wrapper');
            let svgOverlay = document.getElementById('svg-overlay');
            let isDragging = false;
            let startX = 0, startY = 0, currentX = 0, currentY = 0;
            let coords = null;

            // File Drop
            const dropZone = document.getElementById('drop-zone');
            const fileInput = document.getElementById('file-input');
            dropZone.onclick = () => fileInput.click();
            fileInput.onchange = (e) => loadFile(e.target.files[0]);

            dropZone.ondragover = (e) => { e.preventDefault(); dropZone.classList.add('bg-slate-700'); };
            dropZone.ondragleave = () => dropZone.classList.remove('bg-slate-700');
            dropZone.ondrop = (e) => {
                e.preventDefault();
                dropZone.classList.remove('bg-slate-700');
                if (e.dataTransfer.files.length) loadFile(e.dataTransfer.files[0]);
            };

            function loadFile(file) {
                if (!file) return;
                selectedFile = file;
                const reader = new FileReader();
                reader.onload = (e) => {
                    imgElement.src = e.target.result;
                    imgElement.onload = () => {
                        document.getElementById('placeholder-text').classList.add('hidden');
                        wrapper.classList.remove('hidden');
                        svgOverlay.setAttribute('viewBox', `0 0 ${imgElement.naturalWidth} ${imgElement.naturalHeight}`);
                    };
                };
                reader.readAsDataURL(file);
            }

            // Mouse Drag Coordinates
            wrapper.onmousedown = (e) => {
                const rect = imgElement.getBoundingClientRect();
                const scaleX = imgElement.naturalWidth / rect.width;
                const scaleY = imgElement.naturalHeight / rect.height;

                isDragging = true;
                startX = (e.clientX - rect.left) * scaleX;
                startY = (e.clientY - rect.top) * scaleY;
                currentX = startX;
                currentY = startY;
            };

            wrapper.onmousemove = (e) => {
                if (!isDragging) return;
                const rect = imgElement.getBoundingClientRect();
                const scaleX = imgElement.naturalWidth / rect.width;
                const scaleY = imgElement.naturalHeight / rect.height;

                currentX = Math.max(0, Math.min((e.clientX - rect.left) * scaleX, imgElement.naturalWidth));
                currentY = Math.max(0, Math.min((e.clientY - rect.top) * scaleY, imgElement.naturalHeight));

                coords = {
                    xmin: Math.round(Math.min(startX, currentX)),
                    ymin: Math.round(Math.min(startY, currentY)),
                    xmax: Math.round(Math.max(startX, currentX)),
                    ymax: Math.round(Math.max(startY, currentY)),
                    w: Math.round(Math.abs(currentX - startX)),
                    h: Math.round(Math.abs(currentY - startY))
                };

                updateSVG();
            };

            wrapper.onmouseup = () => { isDragging = false; };

            function updateSVG() {
                if (!coords) return;
                svgOverlay.innerHTML = `
                    <rect x="${coords.xmin}" y="${coords.ymin}" width="${coords.w}" height="${coords.h}" fill="rgba(236, 72, 153, 0.35)" stroke="#ec4899" stroke-width="4" />
                    <text x="${coords.xmin + 8}" y="${Math.max(coords.ymin + 28, 28)}" fill="#ffffff" font-size="20" font-weight="bold">${coords.w}x${coords.h}px</text>
                `;
                document.getElementById('coords-info').classList.remove('hidden');
                document.getElementById('box-dimensions').innerText = `${coords.w} x ${coords.h} px (X: ${coords.xmin} - ${coords.xmax})`;
                document.getElementById('btn-slice').disabled = false;
            }

            // API Submission
            document.getElementById('btn-slice').onclick = async () => {
                if (!selectedFile || !coords) return;
                const formData = new FormData();
                formData.append('file', selectedFile);
                formData.append('xmin', coords.xmin);
                formData.append('ymin', coords.ymin);
                formData.append('xmax', coords.xmax);
                formData.append('ymax', coords.ymax);
                formData.append('num_slices', document.getElementById('num-slices').value);
                formData.append('target_url', document.getElementById('target-url').value);

                const res = await fetch('/api/slice', { method: 'POST', body: formData });
                const data = await res.json();

                document.getElementById('output-area').classList.remove('hidden');
                document.getElementById('html-output').value = data.html_code;
                document.getElementById('download-zip').href = `/download/${data.zip_filename}`;
            };
        </script>
    </body>
    </html>
    """


@app.post("/api/slice")
async def slice_image(
    file: UploadFile = File(...),
    xmin: int = Form(...),
    ymin: int = Form(...),
    xmax: int = Form(...),
    ymax: int = Form(...),
    num_slices: int = Form(3),
    target_url: str = Form("https://www.deviantart.com/deviantai/posts"),
):
  content = await file.read()
  img = Image.open(io.BytesIO(content))
  width, height = img.size

  x1, x2 = min(xmin, xmax), max(xmin, xmax)
  y1, y2 = min(ymin, ymax), max(ymin, ymax)

  # Clear old files in output directory
  for f in os.listdir(OUTPUT_DIR):
    file_path = os.path.join(OUTPUT_DIR, f)
    if os.path.isfile(file_path):
      os.remove(file_path)

  generated_files = []

  # --- 9 SLICES (3x3 GRID) ---
  if num_slices == 9:
    # Row 1 (Top)
    r1c1 = img.crop((0, 0, x1, y1))
    r1c2 = img.crop((x1, 0, x2, y1))
    r1c3 = img.crop((x2, 0, width, y1))

    # Row 2 (Middle - Target is Center)
    r2c1 = img.crop((0, y1, x1, y2))
    target = img.crop((x1, y1, x2, y2))
    r2c3 = img.crop((x2, y1, width, y2))

    # Row 3 (Bottom)
    r3c1 = img.crop((0, y2, x1, height))
    r3c2 = img.crop((x1, y2, x2, height))
    r3c3 = img.crop((x2, y2, width, height))

    slices = {
        "tile_r1_c1.png": r1c1,
        "tile_r1_c2.png": r1c2,
        "tile_r1_c3.png": r1c3,
        "tile_r2_c1.png": r2c1,
        "item_interactive.png": target,
        "tile_r2_c3.png": r2c3,
        "tile_r3_c1.png": r3c1,
        "tile_r3_c2.png": r3c2,
        "tile_r3_c3.png": r3c3,
    }

    for fname, tile in slices.items():
      p = os.path.join(OUTPUT_DIR, fname)
      tile.save(p)
      generated_files.append((p, fname))

    html_code = f"""<div style="display: flex; flex-direction: column; gap: 0px; line-height: 0; width: 100%; margin: 0 auto;">
  <div style="display: flex; gap: 0px; align-items: flex-end;">
    <img src="https://backend.deviantart.com/stash/tile_r1_c1.png" style="display: block; border: none; margin: 0;" alt="Tile R1C1">
    <img src="https://backend.deviantart.com/stash/tile_r1_c2.png" style="display: block; border: none; margin: 0;" alt="Tile R1C2">
    <img src="https://backend.deviantart.com/stash/tile_r1_c3.png" style="display: block; border: none; margin: 0;" alt="Tile R1C3">
  </div>
  <div style="display: flex; gap: 0px; align-items: flex-end;">
    <img src="https://backend.deviantart.com/stash/tile_r2_c1.png" style="display: block; border: none; margin: 0;" alt="Tile R2C1">
    <a href="{target_url}" target="_blank" style="display: block; margin: 0; padding: 0;">
      <img src="https://backend.deviantart.com/stash/item_interactive.png" style="display: block; border: none; margin: 0;" alt="Interactive Object">
    </a>
    <img src="https://backend.deviantart.com/stash/tile_r2_c3.png" style="display: block; border: none; margin: 0;" alt="Tile R2C3">
  </div>
  <div style="display: flex; gap: 0px; align-items: flex-end;">
    <img src="https://backend.deviantart.com/stash/tile_r3_c1.png" style="display: block; border: none; margin: 0;" alt="Tile R3C1">
    <img src="https://backend.deviantart.com/stash/tile_r3_c2.png" style="display: block; border: none; margin: 0;" alt="Tile R3C2">
    <img src="https://backend.deviantart.com/stash/tile_r3_c3.png" style="display: block; border: none; margin: 0;" alt="Tile R3C3">
  </div>
</div>"""

  # --- 5 SLICES (HORIZONTAL + TOP/BOTTOM BOUNDS) ---
  elif num_slices == 5:
    top_strip = img.crop((0, 0, width, y1))
    left = img.crop((0, y1, x1, y2))
    target = img.crop((x1, y1, x2, y2))
    right = img.crop((x2, y1, width, y2))
    bottom_strip = img.crop((0, y2, width, height))

    slices = {
        "strip_top.png": top_strip,
        "tile_left.png": left,
        "item_interactive.png": target,
        "tile_right.png": right,
        "strip_bottom.png": bottom_strip,
    }

    for fname, tile in slices.items():
      p = os.path.join(OUTPUT_DIR, fname)
      tile.save(p)
      generated_files.append((p, fname))

    html_code = f"""<table style="border-collapse: collapse; border-spacing: 0; margin: 0 auto; padding: 0; line-height: 0; border: none;">
  <tr style="margin: 0; padding: 0;">
    <td style="padding: 0; margin: 0; line-height: 0;"><img src="https://backend.deviantart.com/stash/tile_r1_c1.png" style="display: block; border: none; margin: 0; padding: 0;" alt="R1C1"></td>
    <td style="padding: 0; margin: 0; line-height: 0;"><img src="https://backend.deviantart.com/stash/tile_r1_c2.png" style="display: block; border: none; margin: 0; padding: 0;" alt="R1C2"></td>
    <td style="padding: 0; margin: 0; line-height: 0;"><img src="https://backend.deviantart.com/stash/tile_r1_c3.png" style="display: block; border: none; margin: 0; padding: 0;" alt="R1C3"></td>
  </tr>
  <tr style="margin: 0; padding: 0;">
    <td style="padding: 0; margin: 0; line-height: 0;"><img src="https://backend.deviantart.com/stash/tile_r2_c1.png" style="display: block; border: none; margin: 0; padding: 0;" alt="R2C1"></td>
    <td style="padding: 0; margin: 0; line-height: 0;">
      <a href="{target_url}" target="_blank" style="display: block; text-decoration: none; border: none; margin: 0; padding: 0;">
        <img src="https://backend.deviantart.com/stash/item_interactive.png" style="display: block; border: none; margin: 0; padding: 0;" alt="Target Object">
      </a>
    </td>
    <td style="padding: 0; margin: 0; line-height: 0;"><img src="https://backend.deviantart.com/stash/tile_r2_c3.png" style="display: block; border: none; margin: 0; padding: 0;" alt="R2C3"></td>
  </tr>
  <tr style="margin: 0; padding: 0;">
    <td style="padding: 0; margin: 0; line-height: 0;"><img src="https://backend.deviantart.com/stash/tile_r3_c1.png" style="display: block; border: none; margin: 0; padding: 0;" alt="R3C1"></td>
    <td style="padding: 0; margin: 0; line-height: 0;"><img src="https://backend.deviantart.com/stash/tile_r3_c2.png" style="display: block; border: none; margin: 0; padding: 0;" alt="R3C2"></td>
    <td style="padding: 0; margin: 0; line-height: 0;"><img src="https://backend.deviantart.com/stash/tile_r3_c3.png" style="display: block; border: none; margin: 0; padding: 0;" alt="R3C3"></td>
  </tr>
</table>"""

  # --- DEFAULT 3 SLICES (FULL HEIGHT STRIPS) ---
  else:
    left = img.crop((0, 0, x1, height))
    target = img.crop((x1, 0, x2, height))
    right = img.crop((x2, 0, width, height))

    slices = {
        "shelf_left.png": left,
        "item_interactive.png": target,
        "shelf_right.png": right,
    }

    for fname, tile in slices.items():
      p = os.path.join(OUTPUT_DIR, fname)
      tile.save(p)
      generated_files.append((p, fname))

    html_code = f"""<div style="display: flex; gap: 0px; align-items: flex-end; line-height: 0;">
  <img src="https://backend.deviantart.com/stash/shelf_left.png" style="display: block; border: none; margin: 0;" alt="Shelf Left">
  <a href="{target_url}" target="_blank" style="display: block; margin: 0; padding: 0;">
    <img src="https://backend.deviantart.com/stash/item_interactive.png" style="display: block; border: none; margin: 0;" alt="Interactive Object">
  </a>
  <img src="https://backend.deviantart.com/stash/shelf_right.png" style="display: block; border: none; margin: 0;" alt="Shelf Right">
</div>"""

  # Package output into downloadable ZIP
  zip_filename = f"cluetober_{num_slices}slices.zip"
  zip_path = os.path.join(OUTPUT_DIR, zip_filename)
  with zipfile.ZipFile(zip_path, "w") as zipf:
    for full_path, arc_name in generated_files:
      zipf.write(full_path, arcname=arc_name)

  return {
      "status": "success",
      "num_slices": num_slices,
      "zip_filename": zip_filename,
      "html_code": html_code,
  }

@app.get("/download/{filename}")
async def download_file(filename: str):
  file_path = os.path.join(OUTPUT_DIR, filename)
  if os.path.exists(file_path):
    return FileResponse(file_path, media_type="application/zip", filename=filename)
  return {"error": "File not found"}


if __name__ == "__main__":
  import uvicorn

  uvicorn.run(app, host="0.0.0.0", port=8080)