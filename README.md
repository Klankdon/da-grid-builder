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
