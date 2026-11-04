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
  const outlines = [];
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
    ctx.lineWidth = style.width;
    ctx.strokeStyle = style.stroke;
    ctx.stroke(outline);
    outlines.push(outline);
  }
  ctx.lineWidth = scene.current_style.width;
  ctx.strokeStyle = scene.current_style.stroke;
  for (const s of scene.current) ctx.stroke(outlines[s]);
  ctx.restore();

  const c = scene.cross;
  for (const [colour, width] of [[c.halo, 4], [c.colour, 2]]) {
    ctx.beginPath();
    ctx.moveTo(c.x - c.size, c.y); ctx.lineTo(c.x + c.size, c.y);
    ctx.moveTo(c.x, c.y - c.size); ctx.lineTo(c.x, c.y + c.size);
    ctx.lineWidth = width;
    ctx.strokeStyle = colour;
    ctx.stroke();
  }
  return performance.now() - start;
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
