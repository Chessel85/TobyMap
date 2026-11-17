// Paints the core's shape list on the canvas (AD-6). No map logic here: the
// core has already projected every point to canvas pixels.

export function paintScene(canvas, scene) {
  const start = performance.now();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.round(scene.width * dpr);
  canvas.height = Math.round(scene.height * dpr);
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.lineJoin = "round";

  ctx.fillStyle = scene.background;
  ctx.fillRect(0, 0, scene.width, scene.height);
  const g = scene.globe;
  ctx.beginPath();
  ctx.arc(g.cx, g.cy, g.r, 0, 2 * Math.PI);
  ctx.fillStyle = g.fill;
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = g.edge;
  ctx.stroke();
  ctx.save();
  ctx.beginPath();
  ctx.arc(g.cx, g.cy, g.r, 0, 2 * Math.PI);
  ctx.clip();

  const { coords, rings, shapes, seam, shape_style: shapeStyle, styles } = scene;
  const outlines = [], fills = [];
  for (let s = 0; s < shapes.length - 1; s++) {
    const fill = new Path2D();
    const outline = new Path2D();
    for (let r = shapes[s]; r < shapes[s + 1]; r++) {
      const a = rings[r], b = rings[r + 1];
      fill.moveTo(coords[2 * a], coords[2 * a + 1]);
      for (let i = a + 1; i < b; i++) fill.lineTo(coords[2 * i], coords[2 * i + 1]);
      fill.closePath();
      addOutline(outline, coords, seam, a, b);
    }
    const style = styles[shapeStyle[s]];
    ctx.fillStyle = style.fill;
    ctx.fill(fill, "evenodd");
    if (style.width > 0) {   // only the item selected in the panel has a stroke of its own
      ctx.lineWidth = style.width;
      ctx.strokeStyle = style.stroke;
      ctx.stroke(outline);
    }
    outlines.push(outline);
    fills.push(fill);
  }
  // The drawing order (P3-T23, DP198): the rivers, then every area's outline over what is painted, the
  // country borders last, then the roads and railways and the places, then the current feature, tinted.
  const under = scene.lines_under || 0;
  paintLines(ctx, scene, 0, under);
  const outlineStyles = scene.outline_styles || [];
  const outlineShapes = scene.outline_shapes || [], outlineStyle = scene.outline_style || [];
  for (let k = 0; k < outlineShapes.length; k++) {
    const st = outlineStyles[outlineStyle[k]];
    if (!(st.width > 0)) continue;
    ctx.lineWidth = st.width;
    ctx.strokeStyle = st.stroke;
    ctx.stroke(outlines[outlineShapes[k]]);
  }
  paintLines(ctx, scene, under, undefined);
  paintMarkers(ctx, scene);
  const cs = scene.current_style;
  ctx.globalAlpha = cs.tint_alpha || 0;
  ctx.fillStyle = cs.tint || cs.stroke;
  for (const s of scene.current) ctx.fill(fills[s], "evenodd");
  ctx.globalAlpha = 1;
  ctx.lineWidth = cs.width;
  ctx.strokeStyle = cs.stroke;
  for (const s of scene.current) ctx.stroke(outlines[s]);
  paintNames(ctx, scene);
  ctx.restore();

  const c = scene.cross;
  if (c) {
    for (const [colour, width] of [[c.halo, 4], [c.colour, 2]]) {
      ctx.beginPath();
      ctx.moveTo(c.x - c.size, c.y); ctx.lineTo(c.x + c.size, c.y);
      ctx.moveTo(c.x, c.y - c.size); ctx.lineTo(c.x, c.y + c.size);
      ctx.lineWidth = width;
      ctx.strokeStyle = colour;
      ctx.stroke();
    }
  }
  const h = scene.heading;   // the heading arrow at the centre (LOC-7)
  if (h) {
    const a = (h.degrees * Math.PI) / 180;
    const point = (len, turn) => [h.x + len * Math.sin(a + turn), h.y - len * Math.cos(a + turn)];
    ctx.beginPath();
    ctx.moveTo(...point(h.length, 0));
    ctx.lineTo(...point(9, -2.5));
    ctx.lineTo(h.x, h.y);
    ctx.lineTo(...point(9, 2.5));
    ctx.closePath();
    ctx.lineWidth = 3;
    ctx.strokeStyle = h.halo;
    ctx.stroke();
    ctx.fillStyle = h.colour;
    ctx.fill();
  }
  return performance.now() - start;
}

// Line features, such as the graticule: each run of points is one stroke (P2-T10a), from run first
// to before run last. The rivers come first, drawn under the areas' outlines (P3-T23).
function paintLines(ctx, scene, first, last) {
  const { line_coords: xy, line_runs: runs, line_style: style, line_styles: styles } = scene;
  if (!runs) return;
  const end = last === undefined ? runs.length - 1 : last;
  for (let k = first; k < end; k++) {
    const a = runs[k], b = runs[k + 1];
    const s = styles[style[k]];
    ctx.beginPath();
    ctx.moveTo(xy[2 * a], xy[2 * a + 1]);
    for (let i = a + 1; i < b; i++) ctx.lineTo(xy[2 * i], xy[2 * i + 1]);
    ctx.lineWidth = s.width;
    ctx.strokeStyle = s.stroke;
    ctx.stroke();
  }
}

// The areas' names, each centred where the core placed it, on a halo (P2-T12d).
function paintNames(ctx, scene) {
  const names = scene.names;
  if (!names || !names.length) return;
  const style = scene.name_style;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.lineJoin = "round";
  ctx.lineWidth = 3;
  ctx.strokeStyle = style.halo;
  ctx.fillStyle = style.colour;
  for (const n of names) {
    ctx.font = `${n.size}px sans-serif`;
    ctx.strokeText(n.text, n.x, n.y);
    ctx.fillText(n.text, n.x, n.y);
  }
}

// Point features, such as a railway station: a small round marker each.
function paintMarkers(ctx, scene) {
  const { marker_coords: xy, marker_style: style, marker_styles: styles } = scene;
  if (!xy) return;
  for (let k = 0; k < style.length; k++) {
    const s = styles[style[k]];
    ctx.beginPath();
    ctx.arc(xy[2 * k], xy[2 * k + 1], s.radius, 0, 2 * Math.PI);
    ctx.fillStyle = s.fill;
    ctx.fill();
    ctx.lineWidth = 1;
    ctx.strokeStyle = s.stroke;
    ctx.stroke();
  }
}

// Outline a ring, lifting the pen over artificial edges such as the 180
// degree line (AD-17).
function addOutline(path, coords, seam, a, b) {
  const n = b - a;
  let first = -1;
  for (let i = a; i < b; i++) if (seam[i]) { first = i; break; }
  if (first < 0) {
    path.moveTo(coords[2 * a], coords[2 * a + 1]);
    for (let i = a + 1; i < b; i++) path.lineTo(coords[2 * i], coords[2 * i + 1]);
    path.closePath();
    return;
  }
  let penDown = false;
  for (let k = 0; k < n; k++) {
    const i = a + ((first - a + 1 + k) % n);
    const j = a + ((i - a + 1) % n);
    if (!penDown) { path.moveTo(coords[2 * i], coords[2 * i + 1]); penDown = true; }
    if (seam[i]) penDown = false;
    else path.lineTo(coords[2 * j], coords[2 * j + 1]);
  }
}
