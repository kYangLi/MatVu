# MatVu 设计笔记

> MatVu — Automatic Viewpoint Optimization and Visualization for Materials Structures
> MatVu = Materials + View
> 输入结构，不必手动旋转，直接得到适合展示的球棍模型。

## 核心原则

1. **视点优化是项目资产。** 渲染只是出口；`view="auto"` 的质量（清晰、少遮挡、构图均衡）决定工具是否好用。
2. **核心与后端解耦。** 结构模型、键连、投影、评分不依赖任何渲染库；matplotlib、web（交互）、未来 PyVista 都是可插拔后端。
3. **插件化输入。** `io` 注册表 + 统一 `Structure` 模型；POSCAR 起步，后续以适配器扩展 CIF/XYZ/ASE，不触碰核心。
4. **轻依赖。** 核心只依赖 numpy，默认渲染依赖 matplotlib。

## 模块地图

| 模块 | 职责 |
| --- | --- |
| `structure.py` | `Structure` 数据模型（晶格 + 笛卡尔坐标 + 元素 + pbc） |
| `io/` | 读取器注册表与格式嗅探；`io/vasp.py` 为内置 POSCAR 读取器 |
| `elements.py` | 元素数据：共价半径、范德华半径、质量、Jmol 颜色 |
| `geometry.py` | 最小镜像、距离矩阵、键连、惯量主轴、视角基 |
| `scene.py` | 由 `Structure` 构建可渲染 `Scene`；正交投影 `project()` |
| `viewpoint.py` | 候选视角生成、评分、`auto` 搜索（项目核心算法） |
| `gallery.py` | 候选视角排名与连拍图（评估 / 校准工具） |
| `style.py` | 渲染样式（原子/键尺寸、光照、画布、输出参数） |
| `backends/` | 后端注册与实现：`base.py` 协议、`mpl.py` matplotlib |
| `render.py` | 高层 API：`render()` / `auto_view()` / `resolve_view()` |
| `cli.py` | `matvu render` / `matvu info` |

## 视点优化 v0

候选方向：

- Fibonacci 球面均匀采样（默认 240 个）
- 原子坐标惯量主轴 ±
- 晶格矢量 ±（周期性体系）

评分（惩罚越小越好，`score = 1 - penalty`）：

- **遮挡率** 权重 0.60：每个原子投影圆盘被更靠近相机的原子覆盖的面积比例（圆交叠解析计算，连续度量；"差一点就重叠"也会被合理扣分）
- **键压缩** 权重 0.25：投影键长 / 真实键长低于 0.35 的部分按比例惩罚（避免键指向相机）
- **长宽比** 权重 0.15：投影包围盒超过约 2.2:1 后惩罚（避免构图过扁）

搜索流程：全局候选 → 同分时优先对齐高对称方向（主轴/晶格矢量）→ 两轮锥形局部精修。

已知局限：

- 正交投影；评分暂未利用对称性与背景原子；每个候选 O(N²)，大体系需换 KD-tree。
- 键只在"当前显示的原子之间"绘制（不画跨周期边界的镜像键），因此单胞边界会出现悬挂原子。渲染时用 `--supercell NX NY NZ` 或 API 的 `supercell=` 补全内部键（这也是后续"自动补全周期键"功能的动机）。

## 后端矩阵

| 后端 | 状态 | 输出 | 备注 |
| --- | --- | --- | --- |
| tracer | 可用（默认） | PNG（可嵌入 PDF/SVG） | 纯 numpy 解析光线投射 + z-buffer：球/柱精确遮挡，默认 2× 超采样抗锯齿 |
| matplotlib | 可用（快速预览） | PNG/PDF/SVG | 2D 投影 + 深度排序 + 球面渐变 sprite；键端按投影球面裁剪 |
| web | 计划 | 交互式 HTML | 支持旋转/缩放，初始相机取自动视角 |
| pyvista | 未来可选 | 图片/动画 | 真实光照，依赖重，作为额外后端 |

## IO 插件接口

```python
from matvu import Structure, register_reader

def read_cif(text: str) -> Structure:
    ...

register_reader("cif", read_cif)
```

内置读取器注册在 `matvu.io.vasp`，通过 `register_reader("vasp", read_poscar)` 接入。
未知文件按扩展名/文件名（`POSCAR`、`CONTCAR`、`*.vasp`）嗅探。

## 路线图

- **v0.1（当前）**：核心模型、POSCAR 读取、自动视角 v0、matplotlib 后端、CLI
- **v0.2**：候选视角连拍图（✅ `matvu candidates`）；web 交互后端；`view="interactive"`
- **v0.3**：CIF/XYZ 读取器；透视相机；spacefill/wireframe 样式；超胞与选区
- **v0.4**：对称性感知视角；旋转/动画导出；论文模板（配色、字号、构图）

## 开发约定

- 本地优先：功能收敛后再做第一次 push；PyPI 名 `matvu` 可用（2026-10-03 核查）；GitHub 用户名 `Matvu` 被一个休眠账号占用（0 仓库），仓库建在个人账号下、名为 `MatVu` 即可。历史上另有同名的矩阵可视化研究工具（数值线性代数领域），领域不同，无现实冲突。
- License：GPL-3.0-or-later
- 开发命令：`uv venv && uv pip install -e ".[dev]"`，测试 `pytest`
- 每个新功能必须带可离线运行的单元测试（不依赖网络与显示环境）
