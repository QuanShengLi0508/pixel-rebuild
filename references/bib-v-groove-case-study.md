# BIB V-groove 三维结构示意图：从视觉修补到几何契约

本案例来自一次科研器件结构图的重绘。目标不是把微信截图放进 PPT，而是从两张参考图中提取结构证据，重新生成一张白底、低饱和配色、等轴测视角的 BIB 探测器示意图，并让 PPT、SVG 和预览图都来自同一套几何定义。

案例资产位于 [`assets/cases/bib-v-groove/`](../assets/cases/bib-v-groove/)：

- `reference.png`：下方器件结构参考图；
- `style-reference.png`：上方配色和半透明层次参考图；
- `reconstruction.svg`：可缩放的矢量重绘；
- `BIB_structure_editable_v30.pptx`：最终检查过的可编辑 PowerPoint；
- `reconstruction.png`：渲染预览；
- `scene_manifest.json` 与 `vector-audit.json`：几何约束和审计结果。

## 这次真正暴露的问题

这些问题在缩略图里常常只表现为“有点不像”，放大后才会变成明显的廉价感。它们应当被记录成回归规则，而不是每次靠肉眼重新修补。

| 现象 | 根因 | 处理规则 |
| --- | --- | --- |
| 顶部接触块不像正常方块 | 只有一个平面，缺少与顶面方向一致的薄侧面 | 用同一底面加统一挤出厚度构成薄长方体；三块接触的厚度进入 `thickness_groups` |
| 接触块下方颜色和原图不同 | 把局部半透明接触区域误画成新的器件层，或透明度叠加顺序错误 | 保留局部 under-face；把它当作接触细节，先验证叠加后的实际颜色 |
| V-groove 两侧厚薄不一、底部不平 | 左右面分别估计，端点没有共享坐标 | 使用一个连续的 `Groove-continuous-metal` 多边形；底边端点必须通过 shared-edge 审计 |
| 层与层之间出现白线、深色线或台阶 | 相邻面有亚像素间隙，或 PowerPoint 默认轮廓/阴影被继承 | 结构面不设置 stroke；相邻边复用同一端点；导出后检查长边的非目标颜色 |
| BL、AL、钝化层颜色分不出来 | 只统一色相，没有区分面向观察者的 front/right 面 | 为每个物理层定义 front、right 两个固定色；颜色属于语义层，不按局部视觉随意改色 |
| 黄色虚线长短不齐、最外面多出一条 | 逐段手放虚线，拐点处重复绘制 | 由同一个 dash 函数等距分配段长；每个 contour 记录长度和间距的变异系数 |
| 黑箭头不够尖或箭头压住块 | 轴、箭头头部和目标块没有分开建模 | 箭杆在箭头头部前结束，箭头头部是独立三角形；箭头 tip/base 进入角度审计 |
| 引线内收后压住 Al:V+ 或接触块 | 引线只按标签位置移动，没有检查目标对象的保护区 | 先定义目标对象的安全边界，再将线端点落在边界外；两条同类引线使用相同退让规则 |
| 看起来像透明蒙层，实际却有灰黑边 | 透明度和 outline 同时存在，或不同软件用不同颜色空间合成 | 半透明只用于局部接触 under-face；结构主体用稳定纯色，禁止结构面黑色 outline |
| 参考图和聊天 UI 混在一起 | 直接用整张微信截图作为输入 | 先裁出两张科研图，只把下图当结构证据、上图当风格证据，头像和聊天气泡不进入资产 |

## 结构建模顺序

先建立 `High purity substrate → Bottom contact → AL → BL → Passivation layer` 的层序，再绘制连续钝化表面和 V-groove 金属，最后叠加接触块、虚线、电气连线、箭头和可编辑文字。这个顺序解决了两个容易混淆的问题：

1. BL 与 AL 的物理上下关系不会因为颜色调整而改变；
2. 引线和标签不会意外成为器件层的一部分。

每个文字都保留为独立文本框；每个层、接触块和 groove 都是独立矢量对象。PPTX 中不嵌入参考图片，SVG 也不引用外部位图。

## 可执行的审计契约

`scene_manifest.json` 记录的是应当保持不变的几何事实，而不是渲染器的第二份实现。审计器会检查：

- 多边形是否有非零面积；
- 相邻面的共享端点误差是否小于容差；
- 接触块和面厚度的离散程度；
- 虚线段长和间距的变异系数；
- 箭头尖端角度是否落在允许范围；
- 同一材料是否意外出现多个颜色；
- 结构面是否出现黑色或深灰 outline；
- layer order 是否被后续修改打乱。

运行：

```bash
python scripts/audit_vector_scene.py \
  assets/cases/bib-v-groove/scene_manifest.json \
  --json assets/cases/bib-v-groove/vector-audit.json
```

审计失败时返回非零退出码，适合接入 CI。比如把 V-groove 的一个端点改成 `[137.8, 258]`，`shared-edge:groove-bottom-to-substrate` 会立即失败；把某个结构面加上 `#222222` outline，`palette:structural-outlines` 会失败。

## 可重复生成和交付

矢量后端的源代码在 [`scripts/cases/rebuild_bib_v_groove.py`](../scripts/cases/rebuild_bib_v_groove.py)，它只读取代码中的几何和颜色常量，不读取参考图：

```bash
python -m pip install -r requirements-vector.txt
python scripts/cases/rebuild_bib_v_groove.py \
  --output-dir assets/cases/bib-v-groove/generated
```

脚本会生成不含栅格媒体的 `BIB_structure_editable.pptx`、`BIB_structure.svg` 和 `validation.json`。PowerPoint 预览仍应通过渲染后检查；预览不是源文件，也不应反向成为绘图输入。

本案例把“视觉相似度”和“结构可编辑性”拆开记录：PNG 只用于检查效果，SVG/PPTX 才是可编辑交付，manifest 则负责防止下一次迭代重新引入白线、厚度漂移和错误层序。

## 后续可以继续做什么

下一步可以把 `audit_vector_scene.py` 提升为后端无关的 scene schema，并增加：共享边自动提取、保护区碰撞检查、SVG/PPTX 层序对照、结构面长边扫描和截图裁剪记录。这样这个仓库就同时覆盖栅格科学图和可编辑科研结构图，而不是只保存某一次修图结果。
