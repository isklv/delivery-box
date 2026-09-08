#!/usr/bin/env python3
"""Parametric sheet-metal parcel drop box for FreeCAD (matches the
3FlexHome 'Large Parcel Drop Box — Top Access' style).

Run inside FreeCAD (GUI Python console or `freecadcmd build_box.py`).
Creates "ParcelDropBox" (closed) and "ParcelDropBoxOpen" (top flap +
bottom door swung up).

Design intent:
- Couriers drop parcels in through a HINGED TOP FLAP (top access).
- Owner retrieves parcels through a LOCKABLE BOTTOM DOOR
  (rear-hinged, hasp + padlock on the front bottom edge).
- Box sits on 4 feet so the floor is above ground (weatherproof).

All dimensions in millimetres.
"""
import FreeCAD as App
import Part
from FreeCAD import Vector

# ---------------- parameters ----------------
t    = 2       # steel sheet thickness
W    = 410     # width  (x)
D    = 350     # depth  (y); y=0 front, y=D back
FEET = 40      # foot height (lifts box off ground)
BH   = 950     # body wall height
top  = FEET + BH   # 990 -> top of body / flap line


def box(x1, y1, z1, x2, y2, z2):
    return Part.makeBox(x2 - x1, y2 - y1, z2 - z1, Vector(x1, y1, z1))


def add(doc, name, shape, rgb):
    o = doc.addObject("Part::Feature", name)
    o.Shape = shape
    o.ViewObject.ShapeColor = rgb
    return o


GREY, DARK, STEEL = (0.42, 0.44, 0.47), (0.16, 0.17, 0.19), (0.60, 0.62, 0.65)


def build_closed(doc):
    # ---- FEET (4, lift off ground, butt against floor underside) ----
    feet = box(15, 15, 0, 75, 75, FEET - 3)
    for cx, cy in [(W - 75, D - 75), (W - 75, 15), (15, D - 75)]:
        feet = feet.fuse(box(cx, cy, 0, cx + 60, cy + 60, FEET - 3))
    add(doc, "Feet", feet, DARK)

    # ---- BODY (4 walls + top rim, open top & bottom) ----
    walls = [
        box(0, 0, FEET, W, t, top),          # front
        box(0, D - t, FEET, W, D, top),      # back
        box(0, t, FEET, t, D - t, top),      # left
        box(W - t, t, FEET, W, D - t, top),  # right
    ]
    rim = box(0, 0, top, W, D, top + t)
    rim = rim.cut(box(t, t, top - t, W - t, D - t, top + t + 1))
    ribs = [
        box(-t, -t, FEET, t, t, top),
        box(W - t, -t, FEET, W + t, t, top),
        box(-t, D - t, FEET, t, D + t, top),
        box(W - t, D - t, FEET, W + t, D + t, top),
    ]
    body = walls[0]
    for s in walls[1:] + ribs + [rim]:
        body = body.fuse(s)
    try:
        body = body.removeSplitter()
    except Exception:
        pass
    add(doc, "Body", body, GREY)

    # ---- TOP FLAP (top access, hinged on rear edge) ----
    flap = box(-18, -18, top + t, W + 18, D + 18, top + t + 3)
    flap = flap.fuse(box(60, 40, top + t + 3, W - 60, D - 40, top + t + 6))
    add(doc, "TopFlap", flap, GREY)

    fh = box(70, D + 16, top + t, 150, D + 20, top + t + 12)
    fh = fh.fuse(box(260, D + 16, top + t, 340, D + 20, top + t + 12))
    fh = fh.fuse(Part.makeCylinder(4, 270, Vector(70, D + 18, top + t + 6), Vector(1, 0, 0)))
    add(doc, "FlapHinge", fh, DARK)

    fl = box(185, -18, top + t, 225, -14, top + t + 3)
    fl = fl.fuse(box(196, -15, top + t + 3, 214, -11, top + t + 16))
    fl = fl.fuse(box(196, -19, top + t + 12, 214, -11, top + t + 16))
    add(doc, "FlapLatch", fl, DARK)

    # ---- BOTTOM DOOR (floor, lockable, hinged rear, drainage holes) ----
    door = box(0, 0, FEET - 3, W, D, FEET)
    door = door.fuse(box(150, -22, FEET - 3, 260, 0, FEET + 2))   # pull handle
    for hx in (60, W - 60):
        for hy in (60, D - 60):
            door = door.cut(Part.makeCylinder(4, 8, Vector(hx, hy, FEET - 4), Vector(0, 0, 1)))
    add(doc, "BottomDoor", door, STEEL)

    dh = box(70, D - t, FEET - 3, 150, D + t, FEET + 12)
    dh = dh.fuse(box(260, D - t, FEET - 3, 340, D + t, FEET + 12))
    dh = dh.fuse(Part.makeCylinder(4, 270, Vector(70, D, FEET + 2), Vector(1, 0, 0)))
    add(doc, "DoorHinge", dh, DARK)

    # ---- HASP + PADLOCK (front bottom edge) ----
    hasp = box(180, -24, FEET - 3, 230, 0, FEET)
    hasp = hasp.cut(Part.makeCylinder(4, 30, Vector(205, -27, FEET - 1), Vector(0, 1, 0)))
    add(doc, "Hasp", hasp, DARK)

    lock_body = box(190, -15, FEET - 34, 220, -5, FEET - 8)
    free_leg = box(200, -12, FEET - 8, 204, -8, FEET + 8)
    fixed_leg = box(212, -12, FEET - 8, 216, -8, FEET)
    top_bend = box(200, -12, FEET + 4, 216, -8, FEET + 8)
    shackle = free_leg.fuse(fixed_leg).fuse(top_bend)
    add(doc, "Padlock", lock_body.fuse(shackle), (0.72, 0.58, 0.10))

    doc.recompute()
    return doc


def build_open(src):
    doc = App.newDocument("ParcelDropBoxOpen")
    colors = {o.Name: o.ViewObject.ShapeColor for o in src.Objects}

    def rot(s, c, a):
        r = s.copy()
        r.rotate(Vector(*c), Vector(1, 0, 0), a)
        return r

    def add(n, s):
        o = doc.addObject("Part::Feature", n)
        o.Shape = s
        o.ViewObject.ShapeColor = colors[n]
        return o

    # top flap up about rear top edge
    for n in ["TopFlap", "FlapHinge", "FlapLatch"]:
        add(n, rot(src.getObject(n).Shape, (0, D + 18, top + t + 1.5), -90))
    # bottom door up about rear bottom edge
    for n in ["BottomDoor", "DoorHinge", "Hasp", "Padlock"]:
        add(n, rot(src.getObject(n).Shape, (0, D, FEET - 3), -90))
    add("Body", src.Body.Shape)
    add("Feet", src.Feet.Shape)
    doc.recompute()
    return doc


def main():
    for d in list(App.listDocuments()):
        App.closeDocument(d)
    doc = App.newDocument("ParcelDropBox")
    build_closed(doc)
    build_open(doc)
    doc.saveAs("/home/isklv/ParcelDropBox.FCStd")
    import Part as _P
    _P.export([doc.getObject(n) for n in
               ["Feet", "Body", "TopFlap", "FlapHinge", "FlapLatch",
                "BottomDoor", "DoorHinge", "Hasp", "Padlock"]],
              "/home/isklv/ParcelDropBox.step")
    print("Done: ParcelDropBox + ParcelDropBoxOpen")


if __name__ == "__main__":
    main()
