# Case 2: Solvent-Affinity Scatter Plot

This case reconstructs a dense `1080 x 588` scientific scatter plot as standalone Pillow code. It is useful because the source combines colored filled and hollow markers, three dashed threshold rules, many short leaders, ClearType-like text, mathematical subscripts, and a mixed marker/rule legend.

## Contents

1. Artifacts and result
2. Reconstruction architecture
3. Pixel-comparison algorithms
4. Typography recovery
5. Leader-line audit
6. Native-resolution corrections
7. Failures and lessons
8. Reproduction and verification

## 1. Artifacts and result

| Artifact | Path |
|---|---|
| Reference | `assets/cases/solvent-affinity/reference.png` |
| Reconstruction | `assets/cases/solvent-affinity/reconstruction.png` |
| Heatmap | `assets/cases/solvent-affinity/heatmap.png` |
| 50% overlay | `assets/cases/solvent-affinity/overlay.png` |
| 4x absolute difference | `assets/cases/solvent-affinity/difference_x4.png` |
| Binary error mask | `assets/cases/solvent-affinity/error_mask.png` |
| Metric report | `assets/cases/solvent-affinity/metrics.json` |
| Candidate leader paths | `assets/cases/solvent-affinity/leaders.json` |
| Leader evidence visualization | `assets/cases/solvent-affinity/line-evidence.png` |
| Per-path evidence report | `assets/cases/solvent-affinity/line-evidence.json` |
| Standalone renderer | `scripts/cases/recreate_solvent_affinity.py` |

Final global measurements:

| Metric | Value |
|---|---:|
| Canvas | `1080 x 588`, RGB |
| MAE | `4.643836` |
| RMSE | `23.993312` |
| Exact-pixel fraction | `90.048501%` |
| Pixels within 5 per channel | `92.512125%` |
| Pixels within 10 per channel | `92.944224%` |
| Different pixels | `63,196` |

The exact-pixel fraction is not sufficient by itself because the figure contains substantial white space. The saved report also includes plot, legend, upper-line, middle-line, and lower-line ROIs plus exact-color IoU for all seven marker categories.

The renderer never reads the reference. With the reference moved away, two clean invocations produced the same SHA-256:

```text
98c993c9193dce051a8e077cf6c2e74b521416f7972560f42a3575e5630a992b
```

## 2. Reconstruction architecture

The renderer uses two coordinated rasterization passes.

### Supersampled semantic pass

Most geometry is described in native pixels and multiplied at the drawing boundary:

```python
WIDTH, HEIGHT = 1080, 588
SCALE = 4

def sc(value):
    return round(value * SCALE)
```

Axes, dashed thresholds, leaders, markers, and legend samples are drawn onto a `4320 x 2352` RGB image. That image is reduced once with Lanczos. Coordinates remain native throughout the data tables, avoiding accidental double scaling.

### Native-resolution correction pass

After the single downsample, narrowly measured features are restored:

- exact marker flat-color cores;
- one-pixel axis cores and pale outside fringes;
- exact legend rule blocks;
- LCD-style text and mathematical titles.

This is not a license to paint the source pixel by pixel. Each correction represents a measured semantic primitive with explicit geometry and color.

## 3. Pixel-comparison algorithms

Let reference `R` and output `O` be `H x W x 3` integer arrays. The difference array is computed in signed or floating-point form to prevent unsigned wraparound:

```python
diff = reference.astype(np.int16) - output.astype(np.int16)
absolute = np.abs(diff)
```

### Global and ROI metrics

```python
mae = absolute.mean()
rmse = np.sqrt(np.mean(diff.astype(np.float64) ** 2))
exact = np.all(diff == 0, axis=2).mean()
within_5 = np.all(absolute <= 5, axis=2).mean()
```

The same computation is repeated on named crops. In this case, a dense middle ROI was much more informative than the global exact-pixel fraction.

### Flat-color IoU

For a category color `c`, form exact masks and calculate:

```python
ref_mask = np.all(reference == c, axis=2)
out_mask = np.all(output == c, axis=2)
iou = np.logical_and(ref_mask, out_mask).sum() / np.logical_or(ref_mask, out_mask).sum()
```

IoU exposed marker-size and flat-core errors that were diluted by the white canvas. Final category IoUs ranged from about `0.80` for orange to `0.92` for purple.

### Diagnostic images

The comparison tool writes four complementary views:

- `overlay.png`: checks double edges, displacement, and missing objects;
- `heatmap.png`: maps stronger channel differences to brighter colors;
- `difference_x4.png`: magnifies raw absolute RGB difference by four;
- `error_mask.png`: shows every nonzero-difference pixel without magnitude.

The heatmap is deterministic and percentile-scaled. For each pixel, let `m` be the maximum absolute error among R, G, and B. Let `s` be the 99th percentile of `m`, clamped to at least one, and set `n = clip(m / s, 0, 1)`. The output color is:

```text
R = 255n
G = 180 * clip(1 - 2|n - 0.5|, 0, 1)
B = 0
```

Exact pixels are black, middle errors pass through yellow-green, and the strongest one percent saturate toward red. Percentile scaling prevents a handful of extreme pixels from making the rest of the heatmap unreadably dark. The `difference_x4.png` artifact instead retains channel directionality by multiplying each absolute channel error by four and clipping at 255. The binary mask is simply `m > 0`.

Never resize one side to make a comparison run. A size mismatch must fail.

## 4. Typography recovery

The source contained colored horizontal fringes consistent with subpixel LCD rasterization. Plain grayscale Pillow text produced the correct glyph family but visibly different edges.

The case renderer approximates LCD text by:

1. rendering the glyph mask at three horizontal samples per output pixel;
2. reducing vertically with Lanczos;
3. filtering horizontally with `[1, 4, 6, 4, 1] / 16`;
4. applying a measured gamma;
5. assigning successive samples to R, G, and B coverage;
6. compositing each channel against the existing RGB background.

```python
kernel = np.array((1, 4, 6, 4, 1), dtype=np.float64) / 16.0
filtered = sum(
    weight * padded[:, offset:offset + width]
    for offset, weight in enumerate(kernel)
)
filtered = 255.0 * np.power(np.clip(filtered / 255.0, 0.0, 1.0), 1.7)
coverage = np.stack([filtered[:, channel::3] for channel in range(3)], axis=2)
```

### Shared phase first, per-label offsets second

A local search showed that most plot labels preferred the same `+1/3 px` vertical phase. Applying that shared phase before per-label tuning reduced complexity and improved the global metric. Only labels with a clear local improvement retained an individual horizontal `+/- 1/3 px` or `2/3 px` correction.

### Compose scientific text

Axis titles and `LiPF6` were not rendered as one Unicode string. Roman text, italic Greek letters, and subscripts were drawn as separate runs with measured positions. This avoids fallback-font surprises and allows the subscript baseline to be fitted independently.

### Check the actual character

The top note was initially implemented as `~150 solvents`. Native inspection showed that the source used `≈150 solvents`. Similar-looking glyph substitutions change width, shape, and every antialiased edge.

## 5. Leader-line audit

The hardest semantic failure was not a one-pixel offset. Several plausible-looking black leaders were invented even though the source contained no stroke.

### Per-path ablation

Leaders are stored as a list of polylines. For each path, render the complete figure and a second version with that path omitted:

```text
delta_remove = absolute_error_without_path - absolute_error_with_path
```

If `delta_remove` is negative, deletion improved the match. That path is absent or geometrically wrong. The first audit showed that removing the whole inaccurate leader set lowered MAE from about `4.70` to `4.47`, proving that visual plausibility had overruled source evidence.

### Grayscale evidence corridor

The source leaders are grayscale, while most marker interiors are colored and text edges include RGB subpixel fringes. A second audit therefore:

1. selects pixels where `R == G == B` and intensity is below a threshold;
2. dilates that mask by one or two pixels;
3. rasterizes each proposed path alone;
4. measures the fraction of path pixels inside the dilated evidence mask.

For reference image `R`, grayscale tolerance `t`, darkness threshold `q`, dilation radius `r`, and rasterized candidate mask `P`, the screen is:

```text
G(x, y) = max(R) - min(R) <= t  and  max(R) <= q
D = dilate(G, radius=r)
support(P) = |P intersect D| / |P|
```

The committed case uses `t=0`, `q=210`, and `r=2` pixels.

Low support triggers a native crop inspection. It is not an automatic delete because a marker drawn later may cover the end of a valid leader.

The reusable `scripts/audit_line_evidence.py` tool implements this screen. On the final 36 candidate paths, 35 met the default dilated support threshold of `0.40`; one was classified as `review`. That remaining path was not automatically removed: a threshold screen cannot distinguish every overlap, nearby text pixel, or later-drawn marker. Per-path ablation and the native crop remain the deciding evidence.

Run the audit and save both machine-readable and visual output:

```bash
python scripts/audit_line_evidence.py \
  assets/cases/solvent-affinity/reference.png \
  assets/cases/solvent-affinity/leaders.json \
  --radius 2 \
  --support-threshold 0.40 \
  --json line-evidence.json \
  --visualization line-evidence.png
```

Green paths meet the screen threshold. Red paths require review; red does not mean absent.

This process removed source-absent strokes under or beside:

- `TFEO`;
- `BTFE`;
- `FB13`;
- `FEMC`;
- two hollow green markers;
- one red point cluster.

It also recovered corrected paths for `FB135`, `TBCH`, `TTE`, `METMS`, `DCE`, `EDFA`, `EMS`, `CPME`, and `1,4-DX`.

### Scanline recovery

For the steep `1,4-DX` leader, row scans exposed the true centerline:

```text
y=321: x=263..269
y=340: x=258..259
y=360: x=254
y=370: x=246..252
```

The prior path was shifted about 12 pixels to the right. The corrected polyline was described from these landmarks rather than adjusted by eye.

## 6. Native-resolution corrections

### Inclusive rectangle endpoints

The legend rule samples contain three compact blocks. Source analysis found exact black cores at:

```text
x=918..923, 932..937, 946..951
y=449..455
```

These are `6 x 7` cores because Pillow rectangle endpoints are inclusive. The light and medium rule samples required their own measured colors and slightly different final block bounds.

### Axis cores

The left and bottom axes contained one-pixel dark cores plus pale outside fringes. Supersampling alone spread coverage differently, so the renderer restores those measured rows and columns after reduction.

### Marker cores

Lanczos produces good silhouettes but can reduce exact flat-color counts. Native ellipses restore the measured interior core while leaving the supersampled antialiased perimeter intact. Flat-color IoU, not visual judgment alone, controls this pass.

## 7. Failures and lessons

### A stale renderer can waste the entire run

The initial script targeted an unrelated chart and wrong canvas. Always compare the current output dimensions and content with the active reference before tuning.

### White space can hide severe errors

An exact-pixel score near 90% did not mean labels, leaders, or markers were correct. Named ROIs and color IoU were required.

### A correct-looking line can still be nonexistent

The largest qualitative complaint came from invented leaders. Every optional stroke now needs pixel evidence or a positive ablation result.

### Correct topology beats endpoint nudging

Several early edits moved an incorrect polyline by a few pixels. The useful fix was to recover the correct marker/label relationship and the actual bend points.

### Pixel metrics and visible bounds can disagree

ClearType fringes can make a metric prefer a phase whose dark bounding box appears one pixel different. Inspect both the crop and the number; do not optimize a single thresholded bounding box.

### Rectangle endpoints are inclusive

Measured `6 x 7` blocks became `7 x 8` until the endpoint convention was handled explicitly.

### Subscripts need independent baselines

`LiPF6` could not be matched well as a single text run. The main token and `6` required separate sizes, x positions, and baselines.

### The renderer must survive without the reference

Pixel comparison is a development tool, not a runtime dependency. Move the reference away, invoke the renderer twice, and compare hashes before delivery.

## 8. Reproduction and verification

The case script uses Pillow, NumPy, and macOS Arial font files:

```bash
python scripts/cases/recreate_solvent_affinity.py \
  --output solvent-affinity.png
```

Run the comparison:

```bash
python scripts/compare_reconstruction.py \
  assets/cases/solvent-affinity/reference.png \
  solvent-affinity.png \
  --output-dir comparison \
  --json comparison/metrics.json \
  --roi plot:110,45,900,535 \
  --roi legend:910,50,1060,540
```

Recreate the committed diagnostics in-place:

```bash
python scripts/compare_reconstruction.py \
  assets/cases/solvent-affinity/reference.png \
  assets/cases/solvent-affinity/reconstruction.png \
  --output-dir assets/cases/solvent-affinity \
  --json assets/cases/solvent-affinity/metrics.json \
  --roi plot:110,45,900,535 \
  --roi upper-lines:230,90,725,220 \
  --roi middle-lines:175,225,610,360 \
  --roi lower-lines:185,315,800,430 \
  --roi legend:910,50,1060,540 \
  --color 0,178,56 --color 249,0,0 --color 81,81,81 \
  --color 0,128,189 --color 92,169,217 --color 255,162,53 \
  --color 163,73,168
```

Verify independence and determinism by temporarily moving the reference, rendering twice, and comparing SHA-256 hashes. Restore the reference even if a command fails; a shell `trap` is useful for this test.
