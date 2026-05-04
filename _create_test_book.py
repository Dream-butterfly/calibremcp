"""Create a minimal test EPUB in the calibre library directory."""
import zipfile
import io
from pathlib import Path

lib_dir = Path(r"E:\A_Books\Calibre书库\轻小说")
# Put in a dedicated folder to keep it organized
test_dir = lib_dir / "_test_book"
test_dir.mkdir(parents=True, exist_ok=True)
out = test_dir / "test_book.epub"

buf = io.BytesIO()
z = zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED)
z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
z.writestr(
    "META-INF/container.xml",
    '<?xml version="1.0"?>\n<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>',
)
z.writestr(
    "content.opf",
    '<?xml version="1.0"?>\n<package version="3.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="book-id"><metadata><dc:title xmlns:dc="http://purl.org/dc/elements/1.1/">测试专用书（请删除）</dc:title><dc:creator xmlns:dc="http://purl.org/dc/elements/1.1/">CherryClaw</dc:creator></metadata><spine><itemref idref="xhtml-001"/></spine><manifest><item id="xhtml-001" href="page001.xhtml" media-type="application/xhtml+xml"/></manifest></package>',
)
z.writestr(
    "page001.xhtml",
    '<?xml version="1.0"?>\n<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Test</title></head><body><p>Test book for MCP CRUD testing - safe to delete.</p></body></html>',
)
z.close()
with open(out, "wb") as f:
    f.write(buf.getvalue())

print(f"OK: {out}")
print(f"Size: {out.stat().st_size} bytes")

# Also copy to project dir (ASCII-friendly path for MCP server)
proj_dir = Path(r"D:\a_code\A_Agents\Calibre_Agent\calibremcp")
proj_out = proj_dir / "test_book_import.epub"
import shutil
shutil.copy2(out, proj_out)
print(f"Copied to: {proj_out}")
print(f"Size: {proj_out.stat().st_size} bytes")
