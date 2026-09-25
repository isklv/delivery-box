#!/usr/bin/env python3
"""Parametric sheet-metal parcel drop box for FreeCAD, hardened against
parcel theft ("fishing").

Run inside FreeCAD (GUI Python console or `FreeCADCmd build_box.py`).
Creates three documents:

  ParcelDropBox         - closed / armed (rest state)
  ParcelDropBoxOpen     - flap back, trap tripped, retrieval door swung
  ParcelDropBoxSection  - closed box cut on the X mid-plane (internals)

Security concept
----------------
1. TOP ACCESS + ONE-WAY TRAP.  A courier drops the parcel through the top
   flap onto a spring-returned trap door 170 mm below the rim.  The trap
   rotates DOWNWARD ONLY (stop ledges block it from above), so anything
   can go in and nothing can come back out: a hand, a hook or a wire loop
   cannot drag a parcel up through it.
2. DEPTH.  Parcels rest ~780 mm below the trap, out of arm's reach.
3. THROAT COLLAR.  A returned flange at the rim stiffens the opening and
   leaves no edge for a pry bar.
4. NO EXPOSED PADLOCK.  The front retrieval door is an inset pan in a
   rebated frame, held by a concealed cam lock that lifts one bar into
   four keeps - no hasp, no shackle, nothing to cut or lever.
5. ANTI-LIFT DOG BOLTS.  Fixed pins on the door hinge edge engage keeps
   in the frame, so grinding the hinges off still does not free the door.
6. ANCHORING.  The floor is welded in and carries four M12 ground-anchor
   holes over bosses in the plinth; they can only be reached with the
   door open.  Two rear brackets take wall or post bolts.

All dimensions in millimetres.
"""
import os

import FreeCAD as App
import Part
from FreeCAD import Vector

# ---------------- parameters ----------------
t     = 2       # steel sheet thickness (walls, flap)
tp    = 3       # thicker sheet (plinth, door, trap)
W     = 410     # width  (x)
D     = 350     # depth  (y); y=0 front, y=D back
PL    = 40      # plinth height (lifts the box off the ground)
BH    = 950     # body wall height
top   = PL + BH        # 990 -> top of body / flap line

COLL  = 25      # throat collar flange width
COLLH = 40      # throat collar return depth

TRAP_Z = 820    # top face of the closed trap door
TRAP_A = 62     # trap swing angle shown in the open document (deg)

FLR_Z  = 37     # underside of the welded floor plate (top face at PL)

OPX0, OPX1 = 35, 375    # retrieval door opening in the front wall (x)
OPZ0, OPZ1 = 100, 770   # ... and in z
KEEPS = (150, 340, 530, 720)          # locking-lug stations (z)
DOGS = (200, 435, 670)                # dog-bolt stations (z)
ANCHORS = [(33, 33), (W - 33, 33), (33, D - 33), (W - 33, D - 33)]

OUT = os.path.dirname(os.path.abspath(__file__)) or "."

GREY, DARK, STEEL = (0.42, 0.44, 0.47), (0.16, 0.17, 0.19), (0.60, 0.62, 0.65)
BRASS, RED = (0.72, 0.58, 0.10), (0.55, 0.17, 0.15)


# ---------------- helpers ----------------
def box(x1, y1, z1, x2, y2, z2):
    return Part.makeBox(x2 - x1, y2 - y1, z2 - z1, Vector(x1, y1, z1))


def cyl(r, h, base, direction=(0, 0, 1)):
    return Part.makeCylinder(r, h, Vector(*base), Vector(*direction))


def rod_x(r, x1, x2, y, z):
    """Round bar along X."""
    return cyl(r, x2 - x1, (x1, y, z), (1, 0, 0))


def fuse(*shapes):
    s = shapes[0]
    for o in shapes[1:]:
        s = s.fuse(o)
    try:
        s = s.removeSplitter()
    except Exception:
        pass
    return s


def frame(x1, y1, x2, y2, z1, z2, w):
    """Rectangular ring (picture-frame) plate in XY, of wall width w."""
    return box(x1, y1, z1, x2, y2, z2).cut(
        box(x1 + w, y1 + w, z1 - 1, x2 - w, y2 - w, z2 + 1))


def frame_xz(x1, z1, x2, z2, y1, y2, w):
    """Rectangular ring in XZ (a door or window frame), wall width w."""
    return box(x1, y1, z1, x2, y2, z2).cut(
        box(x1 + w, y1 - 1, z1 + w, x2 - w, y2 + 1, z2 - w))


def torsion_spring(x, y, z, coil_r=7.0, wire_r=1.6, pitch=4.5, turns=9.25):
    """Torsion spring coiled around a hinge pin that runs along X.
    Starts its coil at the bottom of the pin and ends a quarter turn later
    at the rear, so one leg tails forward under the trap and the other
    reacts against the rear wall."""
    h = pitch * turns
    helix = Part.makeHelix(pitch, h, coil_r)
    prof = Part.Wire(Part.makeCircle(wire_r, Vector(coil_r, 0, 0), Vector(0, 1, 0)))
    coil = Part.Solid(Part.Shell(
        Part.Wire(helix.Edges).makePipeShell([prof], True, True).Faces))
    coil.rotate(Vector(0, 0, 0), Vector(0, 1, 0), 90)   # coil axis +Z -> +X
    coil.translate(Vector(x, y, z))
    leg_a = cyl(wire_r, 40, (x, y, z - coil_r), (0, -1, 0))        # under the trap
    leg_b = cyl(wire_r, 13, (x + h, y + coil_r, z), (0, 1, 0))     # on the wall
    return fuse(coil, leg_a, leg_b)


COLORS = {}


def add(doc, name, shape, rgb):
    COLORS[name] = rgb
    o = doc.addObject("Part::Feature", name)
    o.Shape = shape
    if hasattr(o, "ViewObject") and o.ViewObject:
        o.ViewObject.ShapeColor = rgb
    return o


# ---------------- shell ----------------
def build_plinth(doc):
    """Perimeter plinth: carries the walls and the floor, keeps the box
    off the ground, and holds the four ground-anchor bosses."""
    skirt = frame(0, 0, W, D, 0, PL, tp)
    # arched cut-outs -> four corner feet, drained and ventilated
    skirt = skirt.cut(box(95, -1, 7, W - 95, D + 1, PL - 9))
    skirt = skirt.cut(box(-1, 85, 7, W + 1, D - 85, PL - 9))
    ledge = frame(tp, tp, W - tp, D - tp, FLR_Z - 7, FLR_Z, 20)   # floor support
    parts = [skirt, ledge]
    for bx, by in ANCHORS:
        boss = box(bx - 30, by - 30, 0, bx + 30, by + 30, FLR_Z)
        boss = boss.cut(cyl(6.5, FLR_Z + 2, (bx, by, -1)))
        parts.append(boss)
    add(doc, "Plinth", fuse(*parts), DARK)


def build_floor(doc):
    """Welded floor: a fixed 3 mm plate, so there is no seam underneath
    for a lever.  The anchor bolts drop through it into the plinth bosses
    and can only be reached with the front door open."""
    floor = box(tp, tp, FLR_Z, W - tp, D - tp, PL)
    for bx, by in ANCHORS:
        floor = floor.cut(cyl(7, 12, (bx, by, FLR_Z - 1)))
        floor = floor.cut(cyl(14, 4, (bx, by, PL - 1.5)))       # head recess
    for hx in (120, W - 120):                                   # drainage
        for hy in (150, D - 90):
            floor = floor.cut(cyl(4, 12, (hx, hy, FLR_Z - 1)))
    add(doc, "Floor", floor, STEEL)


def build_body(doc):
    """Four walls + corner ribs, open top and bottom, with the retrieval
    door opening cut in the front wall and its rebate frame behind it."""
    front = box(0, 0, PL, W, t, top).cut(
        box(OPX0, -1, OPZ0, OPX1, t + 1, OPZ1))
    walls = [
        front,
        box(0, D - t, PL, W, D, top),        # back
        box(0, t, PL, t, D - t, top),        # left
        box(W - t, t, PL, W, D - t, top),    # right
    ]
    ribs = [
        box(-t, -t, PL, t, t, top),
        box(W - t, -t, PL, W + t, t, top),
        box(-t, D - t, PL, t, D + t, top),
        box(W - t, D - t, PL, W + t, D + t, top),
    ]
    add(doc, "Body", fuse(*(walls + ribs)), GREY)

    # rebate frame: the door shuts against it, so it cannot be pushed in
    fr = [frame_xz(OPX0 - 10, OPZ0 - 10, OPX1 + 10, OPZ1 + 10, t, t + 3, 18)]
    for kz in KEEPS:                       # keeps the locking lugs slide behind
        fr.append(box(OPX1 - 15, t + 3, kz, OPX1 - 5, t + 9, kz + 12))
    for dz in DOGS:                        # keeps for the anti-lift dog bolts
        fr.append(box(OPX0 - 2, t + 3, dz - 14, OPX0 + 20, t + 15, dz + 14))
    frm = fuse(*fr)
    for dz in DOGS:
        frm = frm.cut(cyl(5, 24, (OPX0 + 6, -1, dz), (0, 1, 0)))
    add(doc, "DoorFrame", frm, GREY)

    brackets = []
    for bz in (250, 800):                  # bolt the box to a wall or post
        b = box(120, D, bz, 290, D + 4, bz + 70)
        b = b.fuse(box(120, D + 4, bz + 25, 290, D + 34, bz + 45))
        for hx in (150, 260):
            b = b.cut(cyl(7, 40, (hx, D + 10, bz + 35), (0, 1, 0)))
        brackets.append(b)
    add(doc, "WallBrackets", fuse(*brackets), DARK)


def build_collar(doc):
    """Throat collar: inward flange at the rim plus a 40 mm return.
    Stiffens the mouth, kills the pry edge, guides parcels onto the trap."""
    flange = frame(-t, -t, W + t, D + t, top, top + t, COLL + 2 * t)
    ret = frame(COLL, COLL, W - COLL, D - COLL, top - COLLH, top, t)
    add(doc, "ThroatCollar", fuse(flange, ret), GREY)


def build_flap(doc):
    """Hinged top flap (courier drop-in) with rain overhang, anti-pry
    skirt, drop latch and a hinge that stops the flap at ~85 deg."""
    z0 = top + t
    flap = box(-18, -18, z0, W + 18, D + 18, z0 + 3)
    flap = flap.fuse(box(60, 40, z0 + 3, W - 60, D - 40, z0 + 6))   # stiffener
    # anti-pry skirt on front and sides (rear left clear for the hinge)
    skirt = [box(-18, -18, z0 - 14, W + 18, -18 + t, z0),
             box(-18, -18, z0 - 14, -18 + t, D + 18, z0),
             box(W + 18 - t, -18, z0 - 14, W + 18, D + 18, z0)]
    add(doc, "TopFlap", fuse(flap, *skirt), GREY)

    # hinge: two leaves + pin, with stop tabs that limit the swing
    fh = box(70, D + 16, z0, 150, D + 20, z0 + 12)
    fh = fh.fuse(box(260, D + 16, z0, 340, D + 20, z0 + 12))
    fh = fh.fuse(rod_x(4, 70, 340, D + 18, z0 + 6))
    for sx in (70, 260):                      # swing-limit stop tabs
        fh = fh.fuse(box(sx, D + 12, z0 + 6, sx + 80, D + 20, z0 + 10))
    add(doc, "FlapHinge", fh, DARK)

    fl = box(185, -18, z0, 225, -14, z0 + 3)
    fl = fl.fuse(box(196, -15, z0 + 3, 214, -11, z0 + 16))
    fl = fl.fuse(box(196, -19, z0 + 12, 214, -11, z0 + 16))
    add(doc, "FlapLatch", fl, DARK)


# ---------------- anti-theft trap ----------------
def trap_pivot():
    """Hinge axis of the one-way trap door: (y, z)."""
    return (D - 22, TRAP_Z - 12)


def build_trap(doc):
    """One-way anti-fishing trap.

    A 3 mm plate hinged on a cranked rear axle 12 mm below its own plane.
    Two torsion springs hold it up against the stop ledges, so it can only
    swing DOWNWARD: a parcel pushes it open and drops through, while a
    hand, hook or wire loop pulling upward only jams it harder shut.
    """
    py, pz = trap_pivot()
    plate = box(8, 12, TRAP_Z - tp, 402, py + 8, TRAP_Z)
    lip = box(8, 12, TRAP_Z - 20, 402, 12 + tp, TRAP_Z - tp)      # front stiffener
    web = box(8, py - 4, pz - 6, 402, py + 2, TRAP_Z - tp)        # crank web
    for sx in (96, 266):                                          # clear the springs
        web = web.cut(box(sx, py - 8, pz - 10, sx + 50, py + 6, TRAP_Z))
    for sx in (16, 176, 346):                                     # interleave knuckles
        web = web.cut(box(sx, py - 8, pz - 10, sx + 50, py + 6, TRAP_Z))
    add(doc, "TrapDoor", fuse(plate, lip, web), STEEL)

    straps = [rod_x(3, 20, 392, py, pz)]                          # hinge pin
    for sx in (20, 180, 350):
        straps.append(box(sx, py - 2, pz - 6, sx + 42, D - t, TRAP_Z - tp - 0.5))
    add(doc, "TrapHinge", fuse(*straps), DARK)

    add(doc, "TrapSprings",
        fuse(torsion_spring(100, py, pz), torsion_spring(270, py, pz)), RED)

    # stop ledges: welded to the walls, they block the trap from ever
    # rotating above horizontal
    stops = [
        box(6, t, TRAP_Z + 0.5, 404, 26, TRAP_Z + 4.5),            # front
        box(t, 12, TRAP_Z + 0.5, 26, py + 8, TRAP_Z + 4.5),        # left
        box(W - 26, 12, TRAP_Z + 0.5, W - t, py + 8, TRAP_Z + 4.5),  # right
        box(t, py + 4, TRAP_Z + 1, W - t, D - t, TRAP_Z + 4),      # rear cover
    ]
    add(doc, "TrapStops", fuse(*stops), GREY)


# ---------------- retrieval door + concealed 4-point lock ----------------
HX, HY = OPX0 - 3, -8          # hinge pin axis (x, y)
HINGES = (150, 420, 690)       # hinge stations (z)
BAR_X = 350                    # locking-bar centre x
LOCK_X, LOCK_Z = 310, 435      # cam cylinder in the door face
THROW = 22                     # vertical throw of the locking bar
SWING = -100                   # door opening angle in the open document


def build_front_door(doc):
    """Retrieval door: an inset pan that shuts against the rebate frame,
    so there is no lip to lever and nothing to push in.  Three hinge
    leaves and three dog bolts on one edge, four locking lugs on the
    other."""
    face = box(OPX0 + 2, -6, OPZ0 + 2, OPX1 - 2, -3, OPZ1 - 2)
    rim = frame_xz(OPX0 + 2, OPZ0 + 2, OPX1 - 2, OPZ1 - 2, -3, 2, 10)
    ribs = [box(OPX0 + 12, -3, rz, OPX1 - 12, 1, rz + 20) for rz in (290, 580)]
    leaves = [box(HX, -10, hz, HX + 34, -6, hz + 70) for hz in HINGES]
    handle = fuse(box(250, -28, 405, 262, -6, 417),
                  box(250, -28, 453, 262, -6, 465),
                  box(250, -28, 405, 262, -22, 465))
    door = fuse(face, rim, handle, *(ribs + leaves))
    door = door.cut(cyl(11.5, 10, (LOCK_X, -8, LOCK_Z), (0, 1, 0)))
    add(doc, "FrontDoor", door, GREY)

    hinge = []
    for hz in HINGES:
        hinge.append(box(4, -6, hz, HX, 0, hz + 70))
        hinge.append(cyl(3.5, 74, (HX, HY, hz - 2)))
    add(doc, "DoorHinges", fuse(*hinge), DARK)

    # anti-lift dog bolts on the hinge edge
    add(doc, "DogBolts",
        fuse(*[cyl(4, 12, (OPX0 + 6, 2, dz), (0, 1, 0)) for dz in DOGS]), BRASS)


def build_lock(doc):
    """Concealed cam lock.  A quarter turn lifts one vertical bar; its
    four lugs then sit behind the frame keeps, so the door is held at
    four points along its free edge.  No hasp, no shackle, nothing
    outside but a key barrel."""
    bar = [cyl(5, 615, (BAR_X, 9, 120))]
    for kz in KEEPS:
        bar.append(box(BAR_X, 11.5, kz, BAR_X + 22, 23.5, kz + 12))
    fork = fuse(box(296, 17, LOCK_Z - 32, BAR_X + 6, 27, LOCK_Z - 12),
                box(BAR_X - 5, 4, LOCK_Z - 32, BAR_X + 6, 27, LOCK_Z - 12))
    fork = fork.cut(box(294, 15, LOCK_Z - THROW - 4.5,
                        358, 29, LOCK_Z - THROW + 4.5))
    bar.append(fork)
    add(doc, "LockBar", fuse(*bar), DARK)

    plug = cyl(11, 26, (LOCK_X, -10, LOCK_Z), (0, 1, 0))
    esc = cyl(16, 4, (LOCK_X, -10, LOCK_Z), (0, 1, 0))
    arm = box(LOCK_X - 4, 12, LOCK_Z - THROW, LOCK_X + 4, 16, LOCK_Z)
    pin = cyl(4, 12, (LOCK_X, 16, LOCK_Z - THROW), (0, 1, 0))
    key = box(LOCK_X - 2, -11, LOCK_Z - 7, LOCK_X + 2, -9.5, LOCK_Z + 7)
    add(doc, "CamLock", fuse(plug, esc, arm, pin).cut(key), BRASS)

PARTS = ["Plinth", "Floor", "Body", "DoorFrame", "WallBrackets",
         "ThroatCollar", "TopFlap", "FlapHinge", "FlapLatch",
         "TrapDoor", "TrapHinge", "TrapSprings", "TrapStops",
         "FrontDoor", "DoorHinges", "DogBolts", "LockBar", "CamLock"]

# parts that clamp round a pin, seat on a ledge or carry a weld: touching
# each other is by design
TOUCHING = {("Plinth", "Floor"), ("Plinth", "Body"), ("Body", "Floor"),
            ("Body", "DoorFrame"), ("Body", "WallBrackets"),
            ("Body", "ThroatCollar"), ("Body", "TrapStops"),
            ("Body", "FlapHinge"), ("Body", "DoorHinges"),
            ("ThroatCollar", "TopFlap"), ("ThroatCollar", "FlapHinge"),
            ("TopFlap", "FlapHinge"), ("TopFlap", "FlapLatch"),
            ("TrapDoor", "TrapHinge"), ("TrapDoor", "TrapStops"),
            ("TrapDoor", "TrapSprings"), ("TrapHinge", "TrapStops"),
            ("TrapHinge", "TrapSprings"),
            ("FrontDoor", "DoorHinges"), ("FrontDoor", "DogBolts"),
            ("FrontDoor", "LockBar"), ("FrontDoor", "CamLock"),
            ("FrontDoor", "DoorFrame"), ("LockBar", "CamLock"),
            ("DogBolts", "DoorFrame")}


def build_closed(doc):
    build_plinth(doc)
    build_floor(doc)
    build_body(doc)
    build_collar(doc)
    build_flap(doc)
    build_trap(doc)
    build_front_door(doc)
    build_lock(doc)
    doc.recompute()
    return doc


def build_open(src):
    """Courier's view (flap back, trap tripped by a parcel) plus the
    owner's view (lock thrown, door swung wide)."""
    doc = App.newDocument("ParcelDropBoxOpen")

    def put(name, shape):
        o = doc.addObject("Part::Feature", name)
        o.Shape = shape
        if hasattr(o, "ViewObject") and o.ViewObject:
            o.ViewObject.ShapeColor = COLORS.get(name, GREY)
        return o

    def turned(name, cy, cz, angle):
        s = src.getObject(name).Shape.copy()
        s.rotate(Vector(0, cy, cz), Vector(1, 0, 0), angle)
        return s

    for n in ["TopFlap", "FlapHinge", "FlapLatch"]:
        put(n, turned(n, D + 18, top + t + 6, -85))
    py, pz = trap_pivot()
    put("TrapDoor", turned("TrapDoor", py, pz, TRAP_A))

    # unlock first (bar up, cam turned), then swing the door on its hinges
    bar = src.LockBar.Shape.copy()
    bar.translate(Vector(0, 0, THROW))
    cam = src.CamLock.Shape.copy()
    cam.rotate(Vector(LOCK_X, 0, LOCK_Z), Vector(0, 1, 0), -90)
    swung = {"FrontDoor": src.FrontDoor.Shape.copy(),
             "DogBolts": src.DogBolts.Shape.copy(),
             "LockBar": bar, "CamLock": cam}
    for n, s in swung.items():
        s.rotate(Vector(HX, HY, 0), Vector(0, 0, 1), SWING)
        put(n, s)

    for n in ["Plinth", "Floor", "Body", "DoorFrame", "WallBrackets",
              "ThroatCollar", "TrapHinge", "TrapSprings", "TrapStops",
              "DoorHinges"]:
        put(n, src.getObject(n).Shape)
    doc.recompute()
    return doc


def build_section(src):
    """Closed box cut on the X mid-plane so the trap and the lock show."""
    doc = App.newDocument("ParcelDropBoxSection")
    knife = box(W / 2, -60, -60, W + 80, D + 80, top + 80)
    for n in PARTS:
        o = src.getObject(n)
        cutshape = o.Shape.cut(knife)
        if cutshape.Volume < 1e-6:
            continue
        c = doc.addObject("Part::Feature", n)
        c.Shape = cutshape
        if hasattr(c, "ViewObject") and c.ViewObject:
            c.ViewObject.ShapeColor = COLORS.get(n, GREY)
    doc.recompute()
    return doc


def verify(doc, log):
    log.append("part                 valid   volume cm3   bbox z")
    shapes = {}
    for n in PARTS:
        s = doc.getObject(n).Shape
        shapes[n] = s
        bb = s.BoundBox
        log.append("%-20s %-6s %9.1f   %6.0f..%-6.0f" %
                   (n, s.isValid(), s.Volume / 1000.0, bb.ZMin, bb.ZMax))
    log.append("")
    for i, a in enumerate(PARTS):
        for b in PARTS[i + 1:]:
            try:
                v = shapes[a].common(shapes[b]).Volume
            except Exception:
                continue
            if v <= 1.0:
                continue
            tag = ("clamp " if (a, b) in TOUCHING or (b, a) in TOUCHING
                   else "UNEXPECTED OVERLAP ")
            log.append("%s%s / %s : %.1f mm3" % (tag, a, b, v))
    log.append("steel mass approx %.1f kg" %
               (sum(s.Volume for s in shapes.values()) * 7.85e-6))


def main():
    for d in list(App.listDocuments()):
        App.closeDocument(d)
    closed = build_closed(App.newDocument("ParcelDropBox"))
    opened = build_open(closed)
    build_section(closed)
    if os.environ.get("PDB_NO_SAVE"):
        return                      # rendering only: documents are enough
    cad = os.path.join(OUT, "cad")
    if not os.path.isdir(cad):
        os.makedirs(cad)
    closed.saveAs(os.path.join(cad, "ParcelDropBox.FCStd"))
    opened.saveAs(os.path.join(cad, "ParcelDropBoxOpen.FCStd"))
    Part.export([closed.getObject(n) for n in PARTS],
                os.path.join(cad, "ParcelDropBox.step"))
    log = ["=== closed / armed ==="]
    verify(closed, log)
    log.append("")
    log.append("=== open (flap back, trap tripped, door swung) ===")
    verify(opened, log)
    report = "\n".join(log)
    print(report)
    with open(os.path.join(OUT, "cad", "verify.txt"), "w") as fh:
        fh.write(report + "\n")


# FreeCAD runs a script with __name__ set to the file stem, not "__main__",
# so the build is kicked off unconditionally.
main()
