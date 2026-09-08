#!/usr/bin/env python3
"""Parametric sheet-metal delivery drop box for FreeCAD.

Run inside FreeCAD (GUI Python console or `freecadcmd build_box.py`).
Creates document "DeliveryBox" (closed state) and "DeliveryBoxOpen"
(bottom door + top lid swung open).

Design intent:
- Couriers drop packages in through the OPEN TOP.
- Owner retrieves packages through a LOCKABLE BOTTOM DOOR
  (rear-hinged, hasp + padlock on the front bottom edge).

All dimensions in millimetres.
"""
import FreeCAD as App
import Part
from FreeCAD import Vector

# ---------------- parameters ----------------
t = 2          # sheet thickness
W, D, H = 700, 500, 800   # outer width(x), depth(y), height(z)
# y=0 is FRONT, y=D is BACK, z=0 is BOTTOM


def box(x1, y1, z1, x2, y2, z2):
    return Part.makeBox(x2 - x1, y2 - y1, z2 - z1, Vector(x1, y1, z1))


def add(doc, name, shape, rgb):
    o = doc.addObject("Part::Feature", name)
    o.Shape = shape
    o.ViewObject.ShapeColor = rgb
    return o


def build_closed(doc):
    walls = [
        box(0, 0, 0, W, t, H),        # front
        box(0, D - t, 0, W, D, H),    # back
        box(0, t, 0, t, D - t, H),    # left
        box(W - t, t, 0, W, D - t, H),# right
    ]
    flanges = [
        box(0, -20, H - t, W, 0, H),     # front flange
        box(0, D, H - t, W, D + 20, H),  # back flange
        box(-20, 0, H - t, 0, D, H),     # left flange
        box(W, 0, H - t, W + 20, D, H),  # right flange
    ]
    ribs = [
        box(-t, -t, 0, t, t, H),
        box(W - t, -t, 0, W + t, t, H),
        box(-t, D - t, 0, t, D + t, H),
        box(W - t, D - t, 0, W + t, D + t, H),
    ]
    body = walls[0]
    for s in walls[1:] + flanges + ribs:
        body = body.fuse(s)
    try:
        body = body.removeSplitter()
    except Exception:
        pass
    add(doc, "Body", body, (0.55, 0.57, 0.60))

    # top rain-cover lid (hinged on rear edge)
    lid = box(-20, -20, H, W + 20, D + 20, H + t)
    add(doc, "TopLid", lid, (0.85, 0.45, 0.10))

    lid_hinge = box(100, D + 18, H, 200, D + 22, H + 10)
    lid_hinge = lid_hinge.fuse(box(500, D + 18, H, 600, D + 22, H + 10))
    lid_hinge = lid_hinge.fuse(
        Part.makeCylinder(3, 600, Vector(50, D + 20, H + 5), Vector(1, 0, 0)))
    add(doc, "LidHinge", lid_hinge, (0.18, 0.18, 0.20))

    latch = box(330, -20, H - t, 370, -16, H)
    latch = latch.fuse(box(344, -19, H, 356, -15, H + 10))
    latch = latch.fuse(box(344, -23, H + 6, 356, -15, H + 10))
    add(doc, "LidLatch", latch, (0.18, 0.18, 0.20))

    # bottom door (hinged on rear edge, pull tab on front edge)
    door = box(0, 0, -t, W, D, 0)
    door = door.fuse(box(60, -25, -t, 120, 0, t))
    add(doc, "BottomDoor", door, (0.15, 0.35, 0.60))

    dh = box(100, D - t, -t, 200, D + t, 12)
    dh = dh.fuse(box(500, D - t, -t, 600, D + t, 12))
    dh = dh.fuse(Part.makeCylinder(4, 600, Vector(50, D, -1), Vector(1, 0, 0)))
    add(doc, "DoorHinge", dh, (0.18, 0.18, 0.20))

    # hasp + padlock on the front bottom edge
    hasp = box(325, -22, -t, 375, 0, t)
    hasp = hasp.cut(Part.makeCylinder(4, 30, Vector(350, -25, -1), Vector(0, 1, 0)))
    add(doc, "Hasp", hasp, (0.18, 0.18, 0.20))

    lock_body = box(336, -16, -30, 364, -6, -8)
    free_leg = box(348, -13, -8, 352, -9, 10)
    fixed_leg = box(356, -13, -8, 360, -9, 0)
    top_bend = box(348, -13, 6, 360, -9, 10)
    shackle = free_leg.fuse(fixed_leg).fuse(top_bend)
    add(doc, "Padlock", lock_body.fuse(shackle), (0.75, 0.62, 0.12))

    doc.recompute()
    return doc


def build_open(src):
    doc = App.newDocument("DeliveryBoxOpen")
    colors = {
        "Body": (0.55, 0.57, 0.60),
        "TopLid": (0.85, 0.45, 0.10),
        "LidHinge": (0.18, 0.18, 0.20),
        "LidLatch": (0.18, 0.18, 0.20),
        "BottomDoor": (0.15, 0.35, 0.60),
        "DoorHinge": (0.18, 0.18, 0.20),
        "Hasp": (0.18, 0.18, 0.20),
        "Padlock": (0.75, 0.62, 0.12),
    }

    def rotated(shape, center, angle_deg):
        s = shape.copy()
        s.rotate(Vector(*center), Vector(1, 0, 0), angle_deg)
        return s

    # door group swings UP 90 deg about the rear bottom edge
    for n in ["BottomDoor", "DoorHinge", "Hasp", "Padlock"]:
        add(doc, n, rotated(src.getObject(n).Shape, (0, D, 0), -90), colors[n])
    # lid group stands up at the back
    for n in ["TopLid", "LidHinge", "LidLatch"]:
        add(doc, n, rotated(src.getObject(n).Shape, (0, D + 20, H + 5), -90), colors[n])
    add(doc, "Body", src.Body.Shape, colors["Body"])
    doc.recompute()
    return doc


def main():
    for d in list(App.listDocuments()):
        App.closeDocument(d)
    doc = App.newDocument("DeliveryBox")
    build_closed(doc)
    build_open(doc)
    doc.saveAs("/home/isklv/DeliveryBox.FCStd")
    import Part as _P
    _P.export([doc.getObject(n) for n in
               ["Body", "TopLid", "LidHinge", "LidLatch",
                "BottomDoor", "DoorHinge", "Hasp", "Padlock"]],
              "/home/isklv/DeliveryBox.step")
    print("Done: DeliveryBox + DeliveryBoxOpen")


if __name__ == "__main__":
    main()
