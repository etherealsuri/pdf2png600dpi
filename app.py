import io
import os
import re
import zipfile

import fitz  # PyMuPDF
import streamlit as st

DPI = 600

st.set_page_config(page_title="PDF to 600 DPI PNG Converter", page_icon="📄", layout="centered")

st.title("📄 PDF to 600 DPI High-Resolution Converter")
st.write(
    f"Upload one or multiple PDF files below. The app renders every page at **{DPI} DPI** "
    "and gives you a ZIP file to download."
)

uploaded_files = st.file_uploader("Choose PDF files", type=["pdf"], accept_multiple_files=True)


def safe_name(name: str) -> str:
    base = os.path.splitext(os.path.basename(name))[0]
    return re.sub(r"[^\w.\- ]", "_", base) or "document"


def convert(files) -> tuple[bytes, int]:
    """Render each page and stream it straight into an in-memory ZIP (low memory use)."""
    buffer = io.BytesIO()
    total_pages = 0
    used_names = set()

    # Count pages up front for the progress bar
    docs = [(f, fitz.open(stream=f.getvalue(), filetype="pdf")) for f in files]
    grand_total = sum(len(d) for _, d in docs)
    progress = st.progress(0.0, text="Starting...")

    # PNGs are already compressed, so ZIP_STORED is faster and no larger
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as zf:
        for f, doc in docs:
            folder = safe_name(f.name)
            n = 2
            while folder in used_names:  # avoid collisions between same-named PDFs
                folder = f"{safe_name(f.name)}_{n}"
                n += 1
            used_names.add(folder)

            digits = max(3, len(str(len(doc))))
            for i in range(len(doc)):
                pix = doc.load_page(i).get_pixmap(dpi=DPI, alpha=False)
                pix.set_dpi(DPI, DPI)  # embed 600 DPI metadata in the PNG
                zf.writestr(f"{folder}/page_{i + 1:0{digits}d}_{DPI}dpi.png", pix.tobytes("png"))
                del pix  # free memory before the next page
                total_pages += 1
                progress.progress(total_pages / grand_total, text=f"{folder}: page {i + 1}/{len(doc)}")
            doc.close()

    progress.empty()
    return buffer.getvalue(), total_pages


if uploaded_files and st.button(f"Convert to {DPI} DPI PNGs", type="primary"):
    try:
        zip_bytes, pages = convert(uploaded_files)
        # Keep the result in session_state so it survives the rerun
        # that happens when the download button is clicked.
        st.session_state["result"] = {
            "zip": zip_bytes,
            "msg": f"Converted {len(uploaded_files)} PDF(s), {pages} page(s) at {DPI} DPI.",
        }
    except Exception as e:
        st.session_state.pop("result", None)
        st.error(f"Conversion failed: {e}")

if "result" in st.session_state:
    st.success(st.session_state["result"]["msg"])
    st.download_button(
        label=f"📥 Download All {DPI} DPI Images (ZIP)",
        data=st.session_state["result"]["zip"],
        file_name=f"extracted_{DPI}dpi_images.zip",
        mime="application/zip",
    )
