#!/usr/bin/env python3
"""Dimensioned drawings for the parcel drop box.

    FreeCADCmd drawings.py

Writes drawings/*.svg: a general arrangement sheet plus one sheet per
mechanism (the one-way trap and the four-point lock).  Geometry comes
from build_box.py, so the drawings cannot drift away from the model;
dimensions are driven by the same parameters the solids are built from.
"""
import os

import FreeCAD as App
import Part
import TechDraw
from FreeCAD import Vector

import build_box as B

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
OUT = os.path.join(HERE, "drawings")

# ---------------------------------------------------------------- geometry
def project(shape, view):
    """Return (visible, hidden) edge compounds for an orthographic view.
    View axes: front = X right / Z up, right = Y right / Z up,
    top = X right / Y up."""
    s = shape.copy()
    if view == "right":
        s.rotate(Vector(0, 0, 0), Vector(0, 0, 1), -90)
    elif view == "top":
        s.rotate(Vector(0, 0, 0), Vector(1, 0, 0), 90)
    res = TechDraw.project(s, Vector(0, -1, 0))
    return res[0], res[2]


def polylines(compound, tol=0.4):
    """Edges -> lists of (x, y) in drawing coordinates."""
    out = []
    for e in compound.Edges:
        try:
            if isinstance(e.Curve, Part.Line):
                pts = [e.Vertexes[0].Point, e.Vertexes[-1].Point]
            else:
                n = max(3, min(48, int(e.Length / tol) + 3))
                pts = e.discretize(n)
        except Exception:
            continue
        out.append([(p.y, p.x) for p in pts])      # -> (right, down)
    return out


def crop(shapes, xr=None, yr=None, zr=None):
    """Clip solids to a box; None keeps an axis unbounded."""
    big = 4000
    xr = xr or (-big, big)
    yr = yr or (-big, big)
    zr = zr or (-big, big)
    knife = Part.makeBox(xr[1] - xr[0], yr[1] - yr[0], zr[1] - zr[0],
                         Vector(xr[0], yr[0], zr[0]))
    out = []
    for sh in shapes:
        c = sh.common(knife)
        if c.Volume > 1.0:
            out.append(c)
    return out


def slab(shapes, lo, hi, axis=0):
    """Clip solids to a slab, i.e. take a section."""
    big = 4000
    lim = [(-big, big), (-big, big), (-big, big)]
    lim[axis] = (lo, hi)
    knife = Part.makeBox(lim[0][1] - lim[0][0], lim[1][1] - lim[1][0],
                         lim[2][1] - lim[2][0],
                         Vector(lim[0][0], lim[1][0], lim[2][0]))
    out = []
    for s in shapes:
        c = s.common(knife)
        if c.Volume > 1.0:
            out.append(c)
    return out


# ------------------------------------------------------------------- sheet
class Sheet:
    """A drawing sheet in world millimetres, printed at `scale`."""

    def __init__(self, title, subtitle, scale):
        self.title, self.subtitle, self.scale = title, subtitle, scale
        self.k = 1.0 / scale          # world units per printed millimetre
        self.body = []
        self.bb = [1e9, 1e9, -1e9, -1e9]

    # -- primitives
    def _grow(self, x, y):
        self.bb[0] = min(self.bb[0], x)
        self.bb[1] = min(self.bb[1], y)
        self.bb[2] = max(self.bb[2], x)
        self.bb[3] = max(self.bb[3], y)

    def path(self, pts, cls, track=True):
        if len(pts) < 2:
            return
        d = "M %.2f %.2f " % pts[0] + " ".join("L %.2f %.2f" % p for p in pts[1:])
        self.body.append('<path class="%s" d="%s"/>' % (cls, d))
        if track:
            for p in pts:
                self._grow(*p)

    def line(self, x1, y1, x2, y2, cls="dim", track=True):
        self.path([(x1, y1), (x2, y2)], cls, track)

    def text(self, x, y, s, cls="dim", anchor="middle", size=3.2, rot=0):
        t = ' transform="rotate(%g %.2f %.2f)"' % (rot, x, y) if rot else ""
        w = len(s) * size * self.k * 0.58
        off = {"middle": w / 2, "start": 0.0, "end": w}[anchor]
        self._grow(x - off, y - size * self.k)
        self._grow(x - off + w, y + size * self.k * 0.4)
        self.body.append(
            '<text class="%s" x="%.2f" y="%.2f" text-anchor="%s" '
            'font-size="%.2f"%s>%s</text>'
            % (cls, x, y, anchor, size * self.k, t, s))

    def circle(self, x, y, r, cls="vis"):
        self.body.append('<circle class="%s" cx="%.2f" cy="%.2f" r="%.2f"/>'
                         % (cls, x, y, r))

    # -- views
    def view(self, shapes, view, dx=0.0, dy=0.0, hidden=True):
        comp = shapes[0] if len(shapes) == 1 else Part.makeCompound(shapes)
        vis, hid = project(comp, view)
        if hidden:
            for pl in polylines(hid):
                self.path([(x + dx, y + dy) for x, y in pl], "hid")
        for pl in polylines(vis):
            self.path([(x + dx, y + dy) for x, y in pl], "vis")

    # -- dimensions
    def _arrow(self, x, y, dxu, dyu):
        a = 2.2 * self.k
        self.body.append(
            '<path class="arrow" d="M %.2f %.2f l %.2f %.2f l %.2f %.2f Z"/>'
            % (x, y, -dxu * a + dyu * a * 0.3, -dyu * a - dxu * a * 0.3,
               dyu * -a * 0.6, dxu * a * 0.6))

    def dim_h(self, x1, x2, y, label=None, ext_from=None, above=True):
        """Horizontal dimension between x1 and x2, drawn on the line y."""
        g = 1.5 * self.k
        if ext_from is not None:
            for x in (x1, x2):
                self.line(x, ext_from + (g if y > ext_from else -g), x,
                          y + (g if y < ext_from else -g), "ext")
        self.line(x1, y, x2, y)
        self._arrow(x1, y, -1, 0)
        self._arrow(x2, y, 1, 0)
        s = label if label is not None else "%g" % abs(x2 - x1)
        self.text((x1 + x2) / 2.0, y - 1.6 * self.k if above else y + 4 * self.k, s)

    def dim_v(self, y1, y2, x, label=None, ext_from=None, right=True):
        g = 1.5 * self.k
        if ext_from is not None:
            for y in (y1, y2):
                self.line(ext_from + (g if x > ext_from else -g), y,
                          x + (g if x < ext_from else -g), y, "ext")
        self.line(x, y1, x, y2)
        self._arrow(x, y1, 0, -1)
        self._arrow(x, y2, 0, 1)
        s = label if label is not None else "%g" % abs(y2 - y1)
        self.text(x + (1.6 if right else -1.6) * self.k, (y1 + y2) / 2.0, s,
                  anchor="start" if right else "end", rot=0)

    def leader(self, x, y, tx, ty, s, anchor="start"):
        self.line(x, y, tx, ty, "lead")
        self.line(tx, ty, tx + (4 * self.k if anchor == "start" else -4 * self.k),
                  ty, "lead")
        self.circle(x, y, 0.7 * self.k, "dot")
        self.text(tx + (5.2 * self.k if anchor == "start" else -5.2 * self.k),
                  ty + 1.1 * self.k, s, "note", anchor=anchor, size=3.0)

    # -- numbered callouts
    def tag(self, x, y, tx, ty, n):
        """Leader ending in a circled note number."""
        r = 4.2 * self.k
        self.line(x, y, tx, ty, "lead")
        self.circle(tx, ty, r, "tagc")
        self.body.append(
            '<text class="tagn" x="%.2f" y="%.2f" text-anchor="middle" '
            'font-size="%.2f">%d</text>' % (tx, ty + 1.3 * self.k, 3.4 * self.k, n))
        self._grow(tx - r, ty - r)
        self._grow(tx + r, ty + r)

    def notes(self, lines, gap=1.0):
        x = self.bb[0]
        y = self.bb[3] + 26 * self.k * gap
        for i, s_ in enumerate(lines):
            self.text(x, y + i * 13 * self.k, "%d.  %s" % (i + 1, s_),
                      "note", anchor="start", size=3.4)

    # -- output
    def save(self, name):
        m = 22 * self.k
        k = self.k
        x0, y0, x1, y1 = self.bb
        x0 -= m; y0 -= m * 2.4; x1 += m; y1 += m
        w, h = x1 - x0, y1 - y0
        head = (
            '<text class="ttl" x="%.2f" y="%.2f" font-size="%.2f">%s</text>'
            '<text class="note" x="%.2f" y="%.2f" font-size="%.2f">%s</text>'
            '<text class="note" text-anchor="end" x="%.2f" y="%.2f" '
            'font-size="%.2f">scale 1:%g &#183; dimensions in mm</text>'
            % (x0 + m * 0.7, y0 + m * 1.05, 5.2 * k, self.title,
               x0 + m * 0.7, y0 + m * 1.75, 3.2 * k, self.subtitle,
               x1 - m * 0.7, y0 + m * 1.75, 3.2 * k, round(1 / self.scale, 2)))
        svg = """<svg xmlns="http://www.w3.org/2000/svg"
     width="%.1fmm" height="%.1fmm" viewBox="%.2f %.2f %.2f %.2f">
<style>
  path, circle, rect, line {vector-effect: non-scaling-stroke}
  .vis {fill:none; stroke:#14181d; stroke-width:%.2f; stroke-linejoin:round}
  .hid {fill:none; stroke:#9aa3ad; stroke-width:%.2f; stroke-dasharray:%.1f %.1f}
  .ctr {fill:none; stroke:#6c8ebf; stroke-width:%.2f;
        stroke-dasharray:%.1f %.1f %.1f %.1f}
  .dim, .ext, .lead {fill:none; stroke:#b23b2e; stroke-width:%.2f}
  .arrow, .dot {fill:#b23b2e; stroke:none}
  .tagc {fill:#ffffff; stroke:#b23b2e; stroke-width:%.2f}
  .tagn {fill:#b23b2e}
  text {font-family:'DejaVu Sans',Arial,Helvetica,sans-serif; fill:#b23b2e}
  .note {fill:#3d4650}
  .ttl {fill:#14181d; font-weight:600}
  .sheet {fill:#ffffff; stroke:#14181d; stroke-width:%.2f}
  .rule {stroke:#14181d; stroke-width:%.2f}
</style>
<rect class="sheet" x="%.2f" y="%.2f" width="%.2f" height="%.2f"/>
<path class="rule" d="M %.2f %.2f L %.2f %.2f"/>
%s
%s
</svg>
""" % (w * self.scale, h * self.scale, x0, y0, w, h,
       0.5 * k, 0.28 * k, 3 * k, 2 * k,
       0.28 * k, 8 * k, 2 * k, 2 * k, 2 * k,
       0.25 * k, 0.3 * k, 0.5 * k, 0.4 * k,
       x0 + 0.3 * m, y0 + 0.3 * m, w - 0.6 * m, h - 0.6 * m,
       x0 + 0.3 * m, y0 + m * 2.1, x1 - 0.3 * m, y0 + m * 2.1,
       head, "\n".join(self.body))
        if not os.path.isdir(OUT):
            os.makedirs(OUT)
        p = os.path.join(OUT, name)
        with open(p, "w") as fh:
            fh.write(svg)
        return p


# ------------------------------------------------------------------ sheets
def shapes_of(doc, names):
    return [doc.getObject(n).Shape for n in names]


def arc(cx, cy, r, a0, a1, n=32):
    import math
    pts = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / float(n))
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def sheet_ga(doc):
    """General arrangement: three views, overall sizes."""
    s = Sheet("Parcel Drop Box &#8212; general arrangement",
              "front / right / plan, closed and armed", 1 / 6.0)
    allp = shapes_of(doc, B.PARTS)
    dxr, dyt = 780, 960

    s.view(allp, "front", 0, 0, hidden=False)
    s.view(allp, "right", dxr, 0, hidden=False)
    s.view(allp, "top", 0, dyt, hidden=False)

    # front view
    s.dim_h(0, B.W, 95, ext_from=0)
    s.dim_v(0, -998, -150, "998 overall", ext_from=0, right=False)
    s.dim_v(0, -B.PL, -70, "40", ext_from=0, right=False)
    s.dim_v(-B.OPZ0, -B.OPZ1, -260, "670 door", ext_from=0, right=False)
    s.dim_h(B.OPX0, B.OPX1, -800, "340 door opening", ext_from=-B.OPZ1)
    s.dim_v(0, -B.OPZ0, 480, "100 sill", right=True)
    s.leader(B.LOCK_X, -B.LOCK_Z, 560, -560, "CamLock cylinder")
    s.leader(20, -B.HINGES[1] - 35, -430, -300, "DoorHinges (3)", anchor="end")

    # right view
    s.dim_h(dxr, dxr + B.D, 95, "350", ext_from=0)
    s.dim_v(-B.TRAP_Z, -998, dxr + B.D + 130, "170", ext_from=dxr + B.D)
    s.dim_v(0, -B.TRAP_Z, dxr + B.D + 130, "820 trap plane",
            ext_from=dxr + B.D)
    s.line(dxr - 40, -B.TRAP_Z, dxr + B.D + 120, -B.TRAP_Z, "ctr")
    s.leader(dxr + B.D - 20, -300, dxr + B.D + 60, -250, "WallBrackets")

    # plan (model +Y runs up the page: svg_y = dyt - y)
    s.dim_h(0, B.W, dyt + 85, "410", ext_from=dyt)
    s.dim_v(dyt, dyt - B.D, -90, "350", ext_from=0, right=False)
    s.dim_h(B.COLL + 2, B.W - B.COLL - 2, dyt + 155, "356 clear drop opening")
    s.dim_v(dyt - B.COLL - 2, dyt - B.D + B.COLL + 2, B.W + 110, "296",
            ext_from=B.W)
    s.text(B.W / 2, 185, "FRONT", "note", size=4.2)
    s.text(dxr + B.D / 2, 185, "RIGHT", "note", size=4.2)
    s.text(B.W / 2, dyt + 230, "PLAN", "note", size=4.2)
    return s.save("01_general_arrangement.svg")


def sheet_trap(doc):
    """The one-way trap: section through the plate, section through a
    spring, and the swing envelope."""
    s = Sheet("One-way anti-fishing trap &#8212; mechanism",
              "section B-B through the plate, section C-C through a spring",
              1 / 2.6)
    names = ["Body", "ThroatCollar", "TopFlap", "TrapDoor", "TrapHinge",
             "TrapSprings", "TrapStops"]
    body = shapes_of(doc, names)
    py, pz = B.trap_pivot()
    zr = (540, 1010)
    dx = 520

    # --- B-B: through the plate, clear of the springs
    s.view(crop(body, xr=(200, 245), zr=zr), "right", 0, 0)

    # the tripped position, drawn as a phantom, plus the swing arc
    op = doc.getObject("TrapDoor").Shape.copy()
    op.rotate(Vector(0, py, pz), Vector(1, 0, 0), B.TRAP_A)
    for sh in crop([op], xr=(200, 245), zr=zr):
        vis, _ = project(sh, "right")
        for pl in polylines(vis):
            s.path(pl, "hid")
    s.path(arc(py, -pz, 232, 180, 180 - B.TRAP_A), "ctr")
    s.text(py - 232, -pz + 96, "%g&#176;" % B.TRAP_A, "dim", size=4)

    s.dim_v(-B.TRAP_Z, -(B.top + B.t), -70, "170 below the rim",
            ext_from=0, right=False)
    s.dim_h(B.COLL, B.D - B.COLL, -490, "296 clear throat", ext_from=-950)
    s.dim_h(0, B.D, -440, "350")
    s.tag(20, -(B.TRAP_Z + 3), -40, -900, 1)
    s.tag(py, -pz, py + 55, -660, 2)
    s.tag(14, -(B.TRAP_Z - 14), 70, -620, 4)
    s.tag(py - 120, -(B.TRAP_Z - 1.5), 160, -930, 5)

    # --- C-C: through a spring
    s.view(crop(body, xr=(96, 146), zr=zr), "right", dx, 0)
    s.tag(dx + py, -pz, dx + py - 60, -660, 3)
    s.dim_v(-B.TRAP_Z, -(B.TRAP_Z - 12), dx + 390, "12 crank",
            ext_from=dx + 340)

    s.text(B.D / 2, -390, "SECTION B-B", "note", size=4.2)
    s.text(dx + B.D / 2, -390, "SECTION C-C", "note", size=4.2)
    s.notes([
        "TrapStops &#8212; ledges welded to the front and both side walls. "
        "They stop the plate flush and are the whole trick: the trap can "
        "rotate down but never up, so a hook or a hand pulling a parcel "
        "back out only jams it shut harder.",
        "Cranked hinge: the pin sits 12 mm below the plate and its knuckles "
        "interleave with the fixed leaves, so the plate cannot be levered "
        "off the pin from the throat.",
        "TrapSprings &#8212; two torsion springs, coil &#216;18, wire "
        "&#216;3.2, 9&#188; turns, one tail bearing under the plate. Anchor "
        "the reaction tail on a slotted bracket: set the preload so a 500 g "
        "parcel trips the trap.",
        "Front stiffener lip, 20 deep, keeps the free edge straight so the "
        "plate cannot be bent past the side ledges.",
        "TrapDoor &#8212; 3 mm plate, 318 x 394, set 170 below the rim. "
        "Swing shown at %g&#176;; a deep parcel pushes it on round to "
        "vertical, giving the full 296 mm of throat." % B.TRAP_A,
    ])
    return s.save("02_trap_mechanism.svg")


def sheet_lock(doc):
    """The four-point lock: inside elevation, keep section, cam section."""
    s = Sheet("Concealed cam lock &#8212; four-point bar",
              "door inside elevation, keep section D-D, cam section E-E",
              1 / 2.6)
    names = ["Body", "DoorFrame", "FrontDoor", "DoorHinges", "DogBolts",
             "LockBar", "CamLock"]
    parts = shapes_of(doc, names)
    kz = B.KEEPS[1]

    # --- elevation seen from inside: everything behind the door skin
    s.view(crop(parts, yr=(0.5, 60)), "front", 0, 0)
    s.dim_v(-B.OPZ0, -B.OPZ1, -80, "670", ext_from=0, right=False)
    s.dim_v(-B.KEEPS[0] - 6, -B.KEEPS[-1] - 6, B.W + 115, "570 over 4 keeps",
            ext_from=B.W)
    s.dim_v(-B.KEEPS[0] - 6, -B.KEEPS[1] - 6, B.W + 40, "190")
    s.dim_h(B.OPX0, B.OPX1, 55, "340", ext_from=0)
    for z in B.KEEPS:
        s.line(B.BAR_X - 30, -z - 6, B.W + 105, -z - 6, "ctr")
    s.tag(B.BAR_X, -640, B.BAR_X - 120, -830, 1)
    s.tag(B.OPX0 + 6, -B.DOGS[0], B.OPX0 + 80, -140, 3)
    s.tag(B.LOCK_X, -B.LOCK_Z, B.LOCK_X - 90, -B.LOCK_Z - 90, 4)
    s.text(B.W / 2, 120, "DOOR FROM INSIDE", "note", size=4.2)

    # --- D-D: plan section through a keep, lug engaged behind it
    ddx, ddy = 390, -760
    s.view(crop(parts, xr=(250, 410), yr=(-20, 60), zr=(kz + 2, kz + 10)),
           "top", ddx, ddy)
    s.tag(B.BAR_X + 14 + ddx, ddy - 17, B.BAR_X + 60 + ddx, ddy - 80, 2)
    s.dim_h(B.OPX1 - 15 + ddx, B.OPX1 - 5 + ddx, ddy + 55, "10",
            ext_from=ddy - 5)
    s.text(ddx + 330, ddy + 110, "SECTION D-D (locked)", "note", size=4.2)

    # --- E-E: side section through the cylinder and yoke
    dx = 640
    s.view(crop(parts, xr=(B.LOCK_X - 12, B.LOCK_X + 12), yr=(-20, 60),
                zr=(370, 500)), "right", dx, 0)
    s.dim_v(-B.LOCK_Z, -(B.LOCK_Z - B.THROW), dx + 100, "22 throw",
            ext_from=dx + 60)
    s.tag(dx + 25, -(B.LOCK_Z - B.THROW), dx + 25, -300, 5)
    s.text(dx + 40, -240, "SECTION E-E", "note", size=4.2)

    s.notes([
        "LockBar &#216;10 with four lugs. The cam lifts it 22 mm; each lug "
        "then sits behind a keep on the frame, so the free edge of the door "
        "is held at four points 190 mm apart.",
        "With the bar down the lugs pass clear of the keeps, so the door "
        "shuts without forcing anything; the throw is what locks it.",
        "DogBolts &#216;8, three on the hinge edge, engaged in keeps in the "
        "frame: grinding the hinges off still does not free the door.",
        "CamLock &#8212; the only thing outside is the key barrel. No hasp, "
        "no shackle, nothing to cut.",
        "The cam pin runs in a horizontal slot in the yoke: a quarter turn "
        "lifts the bar while the pin slides sideways in the slot.",
    ])
    return s.save("03_lock_mechanism.svg")


def main():
    doc = B.build_closed(App.newDocument("ParcelDropBox"))
    made = [sheet_ga(doc), sheet_trap(doc), sheet_lock(doc)]
    with open(os.path.join(HERE, "drawings.log"), "w") as fh:
        fh.write("\n".join(made) + "\n")


main()
