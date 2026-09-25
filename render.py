#!/usr/bin/env python3
"""Render the parcel drop box to images/.

    sleep 300 | xvfb-run -a FreeCAD -c render.py     (headless)
    FreeCAD -c render.py                             (on a desktop)

FreeCAD's console mode quits as soon as stdin reaches EOF, which can cut
the macro off before it starts - hence the `sleep | ` in the headless
form.

Rebuilds the three documents with build_box.py, then saves one PNG per
view listed in SHOTS.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)
IMG = os.path.join(HERE, "images")
SIZE = (1200, 900)
BG = "White"

# (document, file stem, view)
SHOTS = [
    ("ParcelDropBox",        "parcelbox_iso",        "Isometric"),
    ("ParcelDropBox",        "parcelbox_front",      "Front"),
    ("ParcelDropBox",        "parcelbox_right",      "Right"),
    ("ParcelDropBox",        "parcelbox_bottom",     "Bottom"),
    ("ParcelDropBoxOpen",    "parcelbox_open_iso",   "Isometric"),
    ("ParcelDropBoxOpen",    "parcelbox_open_front", "Front"),
    ("ParcelDropBoxOpen",    "parcelbox_open_back",  "Rear"),
    ("ParcelDropBoxSection", "parcelbox_section",    "Isometric"),
    ("ParcelDropBoxSection", "parcelbox_section_side", "Right"),
]


LOG = open(os.path.join(HERE, "render.log"), "w", buffering=1)


def step(msg):
    LOG.write(msg + "\n")


def main():
    import FreeCAD
    import FreeCADGui
    FreeCADGui.showMainWindow()
    step("gui up")

    os.environ["PDB_NO_SAVE"] = "1"       # geometry only, no file writes
    import build_box                      # builds all three documents
    assert build_box.PARTS

    if not os.path.isdir(IMG):
        os.makedirs(IMG)

    step("documents: %s" % list(FreeCAD.listDocuments()))
    for docname, stem, view in SHOTS:
        step("shot %s / %s" % (docname, stem))
        FreeCAD.setActiveDocument(docname)
        gdoc = FreeCADGui.getDocument(docname)
        views = gdoc.mdiViewsOfType("Gui::View3DInventor")
        step("  views=%d" % len(views))
        v = views[0]
        FreeCADGui.setActiveDocument(docname)
        getattr(v, "view" + view)()
        v.fitAll()
        v.saveImage(os.path.join(IMG, stem + ".png"), SIZE[0], SIZE[1], BG)
        step("  wrote " + stem)


try:
    main()
    _result = "OK"
except Exception:
    import traceback
    _result = traceback.format_exc()
LOG.write(_result + "\n")
LOG.close()
os._exit(0)
