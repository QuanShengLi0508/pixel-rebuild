# Pixel Rebuild

像素级图像重建与零差异验证工具 —— 证明"数据可以 1:1 反推图像"。

## 核心链路

```
源图像 → 无数据背景 + 像素级CSV → 重建图像 → 零RGB差异
```

## 两种数据层

| 层 | 内容 | 用途 |
|---|------|------|
| **语义数据** | 从坐标轴标定的曲线/点数据 | 科学分析、数值计算 |
| **视觉像素数据** | 逐像素 `(x, y, R, G, B, A)` 记录 | 精确图像重建（含抗锯齿） |

## 快速开始

```bash
# 1. 生成颜色遮罩
python3 pixel_rebuild.py color-mask \
  --source source.png \
  --out data_mask.png \
  --rule red:170-255,0-120,0-120 \
  --dilate 2

# 2. Inpaint 生成无数据背景
python3 pixel_rebuild.py inpaint \
  --source source.png \
  --mask data_mask.png \
  --out no_data_background.png

# 3. 一键导出+重建+验证
python3 pixel_rebuild.py all \
  --source source.png \
  --mask data_mask.png \
  --background no_data_background.png \
  --csv visual_data_layer_pixels.csv \
  --rebuilt rebuilt_from_visual_data.png \
  --diff rebuilt_diff.png \
  --metrics pixel_rebuild_metrics.json
```

## 命令列表

| 命令 | 功能 |
|------|------|
| `color-mask` | 基于 RGB 阈值规则生成二值遮罩 |
| `inpaint` | 用 OpenCV 移除数据区域，生成无数据背景 |
| `export` | 从遮罩区域导出像素到 CSV |
| `rebuild` | 从背景 + CSV 重建图像 |
| `verify` | 计算 MAE / MSE / max_abs / non-zero pixels |
| `all` | 一键 export + rebuild + verify |
| `package` | 打包所有产出为 ZIP |

## 依赖

```bash
pip install numpy pillow opencv-python
```

## 验证指标

零差异重建的判定标准：

```json
{
  "mean_abs_rgb": 0.0,
  "mse_rgb": 0.0,
  "max_abs_rgb": 0.0,
  "nonzero_diff_pixels": 0,
  "pixel_arrays_equal": true
}
```

## 目录结构

```
pixel-rebuild/
├── SKILL.md                 # Hermes skill 定义
├── agents/openai.yaml       # Agent 配置
├── assets/templates/        # 模板脚本
├── references/              # 参考文档
│   ├── commands.md          # 命令模板
│   ├── mask-strategy.md     # 遮罩策略
│   └── output-contract.md   # 输出规范
└── scripts/
    └── pixel_rebuild.py     # 核心脚本 (336行)
```

## 工作原理

1. **遮罩 = 契约**：`mask > 0` 的像素被导出到视觉数据 CSV
2. **无数据背景**：通过 OpenCV inpainting 移除数据层
3. **像素级 CSV**：格式 `pixel_x, pixel_y, red, green, blue, alpha`
4. **重建**：将 CSV 像素覆盖到背景上
5. **验证**：逐像素 RGB 对比源图与重建图
