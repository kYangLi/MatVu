# MatVu 项目思路与路线图

> 本文件是项目的"活文档"：定位、原则、现状、技术决策、待办与交接方式。
> 目录被移动/改名后，新会话请先读本文件 + `docs/design.md`，再跑一次测试确认基线。
>
> 最后更新：2026-10-03，版本 0.1.0.dev0（本地开发，未推送、未发布）

## 1. 一句话定位

**MatVu（Materials + View）—— 输入结构文件，自动寻找最佳观察视角，输出论文级球棍模型；同时支持交互式查看与多渲染后端。**

```python
from matvu import render
render("POSCAR", view="auto")      # 自动视角 -> PNG
```

## 2. 差异化与用户价值

- 手动工具（VESTA/ASE 等）选视角靠人肉旋转试错；MatVu 把"从哪里看"变成优化问题：
  遮挡少、键不压缩、构图均衡，一条命令出图。
- 面向论文配图：矢量输出、结果可复现（同一结构 + 同一参数 → 同一张图）。
- 不绑定晶体：分子、2D 材料、MOF、非周期结构共用一套 `Structure` 模型
  （这也是名字里不含 Crystal/POSCAR 的原因）。

## 3. 设计原则（动代码前先读）

1. **视点优化是核心资产**：候选生成与评分必须在与渲染无关的 `viewpoint.py` 里。
2. **核心/后端解耦**：`Backend` 协议 + 注册表；matplotlib 是默认实现，web 交互后端计划中，
   PyVista 作为未来可选后端。
3. **插件化输入**：`io` 注册表 + 统一 `Structure`；POSCAR 内置，其他格式按需加适配器，不碰核心。
4. **轻依赖**：核心只依赖 numpy，默认渲染依赖 matplotlib；不把 ASE/pymatgen 作为硬依赖。
5. **后端只负责展示**：颜色、半径、评分都在核心层，保证同一视角在不同后端一致。

## 4. 现状（已实现）

- 版本 `0.1.0.dev0`；**27 个单元测试全部通过**；git 本地单提交，无 remote。
- 模块地图：

```
src/matvu/
  structure.py     # Structure：晶格 + 笛卡尔坐标 + 元素 + pbc
  io/              # 读取器注册表 + vasp.py（POSCAR 解析）
  elements.py      # 共价/范德华半径、质量、Jmol 颜色
  geometry.py      # 最小镜像、距离矩阵、键连、惯量主轴、视角基
  scene.py         # Scene 构建 + 正交投影 Projection
  viewpoint.py     # ★ 候选视角 + 评分 + auto 搜索（项目核心）
  gallery.py       # 候选视角排名 + 连拍图（评估/校准）
  style.py         # 尺寸/光照/画布样式
  backends/        # base.py 协议 + mpl.py 实现 + 注册表
  render.py        # 高层 API：render / auto_view / resolve_view
  cli.py           # matvu render / matvu info
```

- 已实现功能：
  - POSCAR 解析：VASP 4/5、负 scale（目标体积）、Cartesian/Direct、Selective dynamics
  - 距离键连：默认"显示原子之间"（可画），`use_mic=True` 得无限晶体邻接表；
    金属–金属默认不成键，无键结构自动使用清晰分离的晶格球半径（`Style.unbonded_atom_scale` 可调）
  - 自动视角 v0（算法见 §5）
  - tracer 后端（默认）：纯 numpy 解析光线投射、精确遮挡 + 边缘暗化；
    透视相机（默认 0.18）；晶胞框只给三维晶体绘制（分子盒/准二维板层自动跳过，`--no-cell` 可关）；
    周期性边界镜像原子（`Style.boundary_padding`，默认 0.1）使晶胞两侧对称
  - matplotlib 后端：PNG/PDF/SVG 快速预览（球面 sprite + 深描边双色键）
  - 风格预设：`3d`（立体光照）、`toon`（动画赛璐珞：双色调阴影 + 描边）、`flat`（纯平涂 + 描边），
    三者共用透视相机；`toon`/`flat` 带景深衰减；原子显示半径严格按共价半径等比（无最小值钳制）
  - CLI：`matvu render` / `matvu info` / `matvu candidates`
- 示例与演示：`examples/structures/`（Si、NaCl、graphene、water 四个算例）；
  `examples/out/` 有 4 张自动视角渲染图（被 gitignore，本地生成）。
- 已知限制：
  - 正交投影，无透视；
  - 键只在"当前显示原子之间"绘制，周期镜像键不画 → 单胞边界出现悬挂原子，
    暂时用 `--supercell` 补全；
  - 每候选评分 O(N²)，大体系需降采样或 KD-tree；
  - matplotlib 后端按平均深度排序，仅作快速预览（精确遮挡用 tracer 后端，默认）。

## 5. 自动视角 v0（核心算法）

- 候选生成：Fibonacci 球面 240 方向 + 惯量主轴 ± + 晶格矢量 ±，按 ~3° 容差去重。
- 评分：`score = 1 - (0.60 × 遮挡率 + 0.25 × 键压缩 + 0.15 × 长宽比)`
  - 遮挡率：原子投影中心被前方原子圆盘覆盖的比例；
  - 键压缩：投影键长/真实键长低于 0.35 的部分按比例惩罚（防止键指向相机）；
  - 长宽比：投影包围盒超过约 2.2:1 后惩罚。
- 搜索：全局最优 → 同分（1% 内）优先对齐高对称方向 → 两轮锥形局部精修（20°、约 7°）。
- 调参入口：`src/matvu/viewpoint.py` 顶部权重常量；
  `pick_view(scene, n_surface=..., refine_rounds=..., samples_per_round=..., seed=...)`。
- 评估工具：`matvu candidates`（P0-1，已完成）把评分最高的候选排成网格便于肉眼校准；
  遮挡度量已由"中心 0/1 判定"升级为"投影圆盘被覆盖的面积比例"（连续），解决了评分饱和问题。

## 6. 开放问题（未定，不要当结论）

1. web 后端选型：3Dmol.js（成熟、交互完整）vs 自研 Three.js（控制力强）
   —— 建议先用 3Dmol.js 打通闭环，再评估。
2. 周期键补全：已实现周期性边界镜像原子（margin 0.1，默认），跨边界键多数可补全；
   更远距离的补全策略（按键长自适应 margin、"部分键"、虚线）仍是后续工作。
3. 评分权重：手工设定 vs 用户可调 vs 数据驱动（先手工 + 连拍图评估校准）。
4. 是否需要"构图意图"参数（突出层状/孔道/配位多面体等），把审美变成可控目标。
6. 键连判据：已实现"金属–金属默认不成键"（`Style.metal_metal_bonds` 可开启），
   没有任何键的结构自动切换为密堆积半径；更细的元素对/配位启发式仍是后续工作。
7. ✅ 已解决：三维晶体在近优候选（分数 ≥ 最优 − 0.02）中按 maximin 投影分散度选择视角
   （原子在画面中尽量均匀散开）；2D 材料用斜视规则，分子保持正面视角。

## 7. 路线图

### P0（下一步，建议按序）

1. ✅ **候选视角连拍图**（2026-10-03 完成）`matvu candidates POSCAR -o sheet.png -n 12`
   - 实现：`src/matvu/gallery.py` 的 `rank_candidates()` + `render_candidate_sheet()`；
     每格标注方位角/仰角/总分，高亮最优；同分时与 `pick_view` 一致地优先对齐高对称方向。
   - 副产品：发现并修复评分饱和——遮挡度量改为投影圆盘的连续面积覆盖；
     待评估：是否加入"立体感"偏好（见 §6 开放问题）。
2. **Web 交互后端** `matvu render POSCAR --backend web -o view.html`
   - 验收：单文件 HTML 可离线打开；旋转/缩放；初始相机 = 自动视角方向；
     通过后端注册表接入，不污染核心。

### P1

3. ✅ 透视相机（`Style.perspective`，默认 0.25；`--perspective 0` 为正交）；
   二维板层自动斜视（偏离法线约 32°）。后续：tracer 进阶效果（环境光遮蔽、柔和阴影）。
4. 对称性感知视角（高对称方向加权/加分，周期性体系）。
5. CIF / XYZ 读取器（验证 io 插件接口，第二个格式优先 CIF）。
6. 样式扩展：spacefill/wireframe、配色方案、透明背景、论文预设（字号/线宽/边距）。

### P2

7. 动画（自旋/环绕）导出；选区/高亮；晶胞框绘制。
8. PyVista 可选后端；KD-tree 加速；周期性镜像键自动补全。
9. 发布准备：GitHub Actions CI、文档、PyPI 首次发布（占名 `matvu`）。

## 8. 开发与交接

### 环境与常用命令

```bash
uv venv && uv pip install -e ".[dev]"
.venv/bin/python -m pytest                      # 27 个测试，应全部通过
.venv/bin/matvu render examples/structures/water.POSCAR --print-view
.venv/bin/matvu info examples/structures/Si.POSCAR
```

### 目录被改名/移动后

1. venv 内部是绝对路径，移动后失效，重建：`rm -rf .venv && uv venv && uv pip install -e ".[dev]"`；
2. git 不受影响（仓库在目录内部），无 remote；
3. 新会话开场白（可直接复制给 AI）：

   > 读 `docs/roadmap.md` 与 `docs/design.md`，先跑 pytest 确认 27 个测试通过，
   > 然后从路线图 P0 开始实现；保持核心/后端解耦与现有代码风格。

### 首次 push 流程（已商定）

1. 在 GitHub 建公开仓库 `MatVu`；
2. （本机密钥与远程配置属于私有记录，不入库）
3. `git remote add origin git@github.com:<账号>/MatVu.git && git push -u origin main`。

### 命名与许可核查记录（2026-10-03）

- PyPI `matvu` / `mat-vu` 均未注册，可用；
- GitHub 用户名 `Matvu` 被一个 2023 年创建的休眠账号占用（0 仓库），仓库建在个人账号下即可；
- 历史上另有 1990 年代同名的矩阵可视化研究工具（数值线性代数领域），领域不同，无现实冲突；
- License：GPL-3.0-or-later。

## 9. 术语表

- **Structure**：结构数据（晶格 + 笛卡尔坐标 + 元素 + 周期性）
- **Scene**：可渲染描述（位置 / 显示半径 / 颜色 / 键）
- **View**：相机方向（方向向量指向相机），`basis = [right, up, direction]`
- **Backend**：渲染出口（matplotlib / web / ...）
- **Projection**：正交投影结果（平面坐标 xy、深度 depth、投影半径）
