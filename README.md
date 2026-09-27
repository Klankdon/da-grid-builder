# da-grid-builder

A desktop and containerized canvas slicer built with NiceGUI and Pillow for generating interactive image grids, custom image maps, and Sta.sh-ready HTML layouts for DeviantArt journals and community events.

## Features
- **Point-and-Click Coordinate Selection:** Upload your master canvas and click top-left / bottom-right points directly on the preview to select your target bounding box.
- **Automated Image Slicing:** Uses Pillow to cleanly cut the canvas into interactive sections.
- **Sta.sh-Ready HTML Export:** Automatically generates pre-formatted zero-margin flexbox/table markup for DeviantArt journals.

## Quick Start (Local)

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
python app.py

docker build -t da-grid-builder .


docker run -p 8080:8080 da-grid-builder


Workflow for Community Events
Drop your event banner or artwork into the uploader.

Click the two opposite corners of the target element (e.g., a book spine or object).

Input your destination URL (e.g., @deviantai or event journal link).

Click Generate Slices & HTML.

Upload the resulting PNG slices to DA Sta.sh and paste the generated HTML block into your journal.

---

### 3. `.gitignore`
Prevents accidental commits of temporary uploads, slice caches, PyInstaller build artifacts, or environment files:

```gitignore
# Byte-compiled / optimized files
__pycache__/
*.py[cod]
*$py.class

# Output Slices & User Uploads
*.png
*.jpg
*.jpeg
*.webp
*.zip
shelf_left.png
item_interactive.png
shelf_right.png

# Environments
venv/
env/
ENV/

# PyInstaller / Build Artifacts
build/
dist/
*.spec

# IDEs
.vscode/
.idea/

