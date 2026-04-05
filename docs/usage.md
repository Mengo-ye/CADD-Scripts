# CADD-Scripts 使用文档

## 安装

### 环境要求

- Python >= 3.10
- [Schrödinger Suite](https://www.schrodinger.com/)（必需）
- [Rosetta](https://www.rosettacommons.org/)（可选，仅 Rosetta 相关任务需要）

### 安装步骤

```bash
git clone <repo-url>
cd CADD-Scripts
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

安装完成后，`cadd` 命令即可使用。

---

## ProteinMC — 蛋白质精化与蒙特卡洛模拟

ProteinMC 提供两个子命令：

- `cadd proteinmc prime` — 基于 Schrödinger Prime 的蛋白质精化
- `cadd proteinmc rosetta` — 基于 Rosetta 的弛豫与对接

---

### Prime 子命令

```bash
cadd proteinmc prime -i <输入文件> -t <任务类型> [选项]
```

#### 任务类型（`-t`）

| 类型 | 说明 |
|------|------|
| `Normal` | 标准蛋白制备（pH 6.9） |
| `Lysozyme` | 溶菌酶专用蛋白制备（pH 4.75） |
| `MC` | 混合蒙特卡洛精化 |
| `SIDE_PRED` | 侧链预测（含骨架采样） |
| `SIDE_OPT` | 侧链优化（不含骨架采样） |
| `PPI_MMGBSA` | 蛋白-蛋白界面 MM-GBSA 能量计算 |

#### 选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `-i`, `--input` | 输入结构文件（`.mae`、`.maegz`、`.pdb`）或包含 `.pdb` 的目录 | 必填 |
| `-t`, `--type` | 任务类型 | 必填 |
| `-H`, `--host` | CPU 队列名称 | `CPU` |
| `-N`, `--njobs` | 并行子任务数（CPU 核数） | `30` |
| `-S`, `--schrodinger` | Schrödinger 安装路径（默认读取 `$SCHRODINGER` 环境变量） | `$SCHRODINGER` |
| `-n`, `--output-num` | 每个输入结构输出的构象数量 | `3` |
| `-s`, `--steps` | MC 模拟步数 | `50` |
| `-r`, `--random-seed` | 使用随机种子 | 开启 |
| `-m`, `--membrane` | 在模拟中考虑膜环境 | 关闭 |
| `-R`, `--range` | 精化范围的 ASL 表达式 | `all` |
| `-c`, `--constraints` | 位置约束的 ASL 表达式 | 无 |
| `-f`, `--constraints-force` | 约束力常数 | `10.0` |
| `-d`, `--constraints-tolerance` | 约束距离容差 | `0.0` |
| `-1`, `--comp1` | 组分1（受体）的 ASL 表达式 | `A` |
| `-2`, `--comp2` | 组分2（配体/多肽）的 ASL 表达式 | `B` |

#### 示例

```bash
# 标准蛋白制备
cadd proteinmc prime -i protein.mae -t Normal

# MC 精化，100 步，输出 5 个构象
cadd proteinmc prime -i protein.mae -t MC -s 100 -n 5

# 侧链预测，指定精化范围
cadd proteinmc prime -i protein.mae -t SIDE_PRED -R "chain A and res.num 50-100"

# 带约束的 MC 精化
cadd proteinmc prime -i protein.mae -t MC -s 50 -c "backbone" -f 10.0

# PPI MM-GBSA 能量计算
cadd proteinmc prime -i complex.mae -t PPI_MMGBSA -1 "chain A" -2 "chain B"

# 考虑膜环境的 MC 精化
cadd proteinmc prime -i protein.mae -t MC -m
```

---

### Rosetta 子命令

```bash
cadd proteinmc rosetta -i <输入文件> -t <任务类型> [选项]
```

#### 任务类型（`-t`）

| 类型 | 说明 |
|------|------|
| `Fast_Relax` | 快速全原子弛豫 |
| `Relax` | 高周期数全原子弛豫 |
| `PPI_Relax` | 蛋白-蛋白界面弛豫 |
| `FlexPepDock` | 柔性多肽全局对接 |
| `FlexPepRefine` | 柔性多肽局部精化 |
| `PPI_Dock` | 蛋白-蛋白全局对接 |
| `PPI_Refine` | 蛋白-蛋白对接精化 |

#### 选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `-i`, `--input` | 输入结构文件（`.mae`、`.maegz`、`.pdb`）或包含 `.pdb` 的目录 | 必填 |
| `-t`, `--type` | 任务类型 | 必填 |
| `-H`, `--host` | CPU 队列名称（`CPU`、`amdnode`、`fat`） | `CPU` |
| `-N`, `--njobs` | 并行子任务数（CPU 核数） | `30` |
| `-S`, `--schrodinger` | Schrödinger 安装路径 | `$SCHRODINGER` |
| `-n`, `--output-num` | 每个输入结构输出的构象数量 | `3` |
| `-A`, `--rosetta-app` | Rosetta 可执行文件路径 | `$rosetta_app` |
| `-B`, `--rosetta-db` | Rosetta 数据库路径 | `$rosetta_db` |
| `-1`, `--comp1` | 组分1（受体）的链名 | `A` |
| `-2`, `--comp2` | 组分2（配体/多肽）的链名 | `B` |

#### 输入格式说明

- **`.mae` / `.maegz`**：自动拆分为单独结构并转换为 PDB，使用 `parallel` 并行处理
- **`.pdb`**：单个文件，使用 MPI 模式运行
- **目录**：读取目录中所有文件，使用 `parallel` 并行处理

#### 支持的 HPC 队列

| `-H` 值 | PBS 队列 | 备注 |
|---------|----------|------|
| `CPU` | `siais_pub_cpu` | centos7 节点约束 |
| `amdnode` | `amdnode` | AMD 节点 |
| `fat` | `pub_fat` | 大内存节点 |

#### 示例

```bash
# 快速弛豫单个 PDB
cadd proteinmc rosetta -i protein.pdb -t Fast_Relax -n 5

# 高周期弛豫，使用 AMD 节点
cadd proteinmc rosetta -i protein.pdb -t Relax -H amdnode -N 64

# 蛋白-蛋白界面弛豫
cadd proteinmc rosetta -i complex.pdb -t PPI_Relax -1 A -2 B

# 柔性多肽全局对接
cadd proteinmc rosetta -i complex.pdb -t FlexPepDock -1 A -2 B -n 10

# 柔性多肽局部精化
cadd proteinmc rosetta -i complex.pdb -t FlexPepRefine -1 A -2 B

# 蛋白-蛋白全局对接
cadd proteinmc rosetta -i complex.pdb -t PPI_Dock -1 A -2 B -n 20

# 从 MAE 文件批量弛豫（自动拆分 + 并行）
cadd proteinmc rosetta -i structures.maegz -t Fast_Relax -n 3
```

---

## XDock — 反向对接、全局对接与格点生成

XDock 用于批量蛋白-配体对接，支持多种格点生成方式（SiteMap 预测、共晶配体、指定坐标）和对接模式（XGlide 标准对接、诱导契合对接 IFD）。

```bash
cadd xdock -P <蛋白输入> -L <配体输入> -m <模式> [选项]
```

---

### 对接模式（`-m`）

XDock 提供 11 种模式，覆盖格点生成和对接的不同策略：

| 模式 | 说明 | 格点来源 | 是否对接 |
|------|------|----------|----------|
| `SITEMAP` | SiteMap 预测结合位点并对接 | SiteMap | 是（XGlide） |
| `AllSite` | 共晶配体 + SiteMap 联合定义位点 | 共晶配体 + SiteMap | 是（XGlide） |
| `Native` | 使用原生蛋白/配体结构直接处理 | 无 | 否 |
| `COMPD` | 共晶配体定义格点并 XGlide 对接 | 共晶配体 | 是（XGlide） |
| `COMPI` | 共晶配体定义格点并诱导契合对接 | 共晶配体 | 是（IFD） |
| `GCD` | 指定坐标定义格点并 XGlide 对接 | 指定坐标 | 是（XGlide） |
| `GCI` | 指定坐标定义格点并诱导契合对接 | 指定坐标 | 是（IFD） |
| `SiteMapGrid` | SiteMap 预测位点仅生成格点 | SiteMap | 否 |
| `ComplexGrid` | 共晶配体位点仅生成格点 | 共晶配体 | 否 |
| `CenterGrid` | 指定坐标仅生成格点 | 指定坐标 | 否 |
| `Dock` | 使用已有格点文件直接对接 | 预生成格点 | 是（XGlide） |

---

### 蛋白制备模式（`-p`）

| 模式 | 说明 |
|------|------|
| `none` | 不进行蛋白制备 |
| `rosetta` | 使用 Rosetta 弛豫 |
| `rough` | Schrödinger 粗糙制备（默认） |
| `fine` | Schrödinger 精细制备 |
| `hopt` | 氢原子优化 |
| `mini` | 最小化制备 |

### 配体制备模式（`-l`）

| 模式 | 说明 |
|------|------|
| `none` | 不进行配体制备 |
| `epik` | 使用 Epik 生成质子化态（默认） |
| `ionizer` | 使用 Ionizer 生成质子化态 |

---

### 选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `-P`, `--protein` | 蛋白库目录或结构文件 | 必填 |
| `-L`, `--ligand` | 配体文件或目录 | 无 |
| `-m`, `--mode` | 对接模式（见上表） | `SITEMAP` |
| `-p`, `--pro-prep` | 蛋白制备模式 | `rough` |
| `-l`, `--lig-prep` | 配体制备模式 | `epik` |
| `-H`, `--host` | CPU 队列名称 | `CPU` |
| `-N`, `--njobs` | 并行任务数 | `50` |
| `-S`, `--schrodinger` | Schrödinger 安装路径 | `$SCHRODINGER` |
| `-R`, `--rosetta-app` | Rosetta 可执行文件路径 | `$rosetta_app` |
| `-B`, `--rosetta-db` | Rosetta 数据库路径 | `$rosetta_db` |
| `-M`, `--rosetta-version` | Rosetta 版本（`mpi` / `static`） | `mpi` |
| `-g`, `--grid-center` | 格点中心坐标（`x, y, z`） | 无 |
| `-s`, `--sites` | 每个蛋白的 SiteMap 位点数 | `2` |
| `-a`, `--ligand-asl` | 配体 ASL 表达式（复合物模式） | 无 |
| `-n`, `--poses` | 每个配体的对接构象数 | `1` |
| `-o`, `--output` | 每个蛋白输出的最优复合物数 | `1` |
| `-x`, `--precision` | 对接精度（`SP` / `XP` / `HTVS`） | `SP` |
| `-F`, `--force-field` | 力场 | `OPLS_2005` |
| `-v`, `--vdw` | 配体 VdW 缩放因子 | `0.8` |
| `-V`, `--vdw-rec` | 受体 VdW 缩放因子 | `1.0` |
| `-i`, `--inner` | 内盒大小（A） | `12` |
| `-b`, `--buffer` | 外盒缓冲区（A） | `5` |
| `-A`, `--ref-ligand` | 参考配体 ASL（IFD 用） | `A:999` |
| `-D`, `--distance` | IFD 柔性残基距离（A） | `5.0` |
| `-r`, `--prime-njobs` | Prime 许可证数 | `10` |
| `-e`, `--enhanced` | 增强采样（3x，maxkeep=15000） | 关闭 |
| `-w`, `--refine-inplace` | 原位精化配体（mininplace） | 关闭 |
| `-t`, `--peptide` | 多肽对接模式 | 关闭 |
| `-d`, `--peptide-segment` | 多肽分段参数（`length:stepwise`） | 无 |
| `-f`, `--peptide-fasta` | 从 FASTA 文件构建多肽 | 无 |
| `-c`, `--cap` | 为多肽加帽 | 关闭 |
| `-0`, `--only-segment` | 仅执行多肽分段后停止 | 关闭 |
| `-1`, `--no-strain` | 禁用应变校正 | 关闭 |
| `-T`, `--title` | 任务标题 | 自动生成 |
| `-u`, `--uniprot-list` | UniProt ID 列表（格点过滤） | 无 |
| `-U`, `--grid-lib` | 格点库路径（UniProt 过滤） | 无 |

---

### 示例

```bash
# SiteMap 预测位点并对接
cadd xdock -P proteins/ -L ligand.mae -m SITEMAP

# 共晶配体位点对接
cadd xdock -P complex_proteins/ -L ligands/ -m COMPD -a "res.ptype UNK"

# 指定坐标对接
cadd xdock -P proteins/ -L ligand.mae -m GCD -g "10.5, 20.3, 15.7"

# 仅生成 SiteMap 格点
cadd xdock -P proteins/ -m SiteMapGrid -s 3

# 使用已有格点对接
cadd xdock -P grids/ -L ligands/ -m Dock -x XP

# 诱导契合对接
cadd xdock -P complex_proteins/ -L ligand.mae -m COMPI -D 5.0

# 多肽对接
cadd xdock -P proteins/ -L peptide.mae -m SITEMAP -t -d "10:3"

# Rosetta 制备后对接
cadd xdock -P proteins/ -L ligand.mae -m SITEMAP -p rosetta

# 增强采样对接
cadd xdock -P proteins/ -L ligand.mae -m SITEMAP -e -n 3
```

---

## GVSrun — 虚拟筛选自动化流水线

GVSrun 提供完整的虚拟筛选自动化流水线，支持从化合物过滤、LigPrep 预处理、多级对接到后处理评分的全流程。可以使用预定义模式快速启动，也可以通过 `+` 连接任意已注册任务来组建自定义流水线。

```bash
cadd gvsrun -i <格点文件> -d <配体文件> -m <模式> [选项]
```

---

### 预定义模式（14 种）

| 模式 | Pipeline 展开 | 说明 |
|------|--------------|------|
| `Fast` | `HTVS_Normal+SP_Normal` | 快速筛选 |
| `Normal` | `RDL+HTVS_Normal+QIKPROP+R5R+SP_ExtensionA` | 标准流程 |
| `Prep_Normal` | `No_Dup+RDL+IONIZE+HTVS_Normal+QIKPROP+R5R+SP_ExtensionA` | 含预处理的标准流程 |
| `Normal_MMGBSA` | `RDL+HTVS_Normal+QIKPROP+R5R+SP_ExtensionA+MMGBSA_EN` | 标准流程 + MM-GBSA |
| `Reference` | `HTVS_REF+SP_REF+QIKPROP+R5R` | 参考配体模式 |
| `Induce_Fit_Screening` | `IFT_pre+IFT` | 诱导契合筛选 |
| `Cov_Screening` | `R+HTVS_Normal+SP_ExtensionA+SP_Enhanced` | 共价筛选 |
| `QM_Screening` | `RDL+HTVS_Normal+QIKPROP+R5R+SP_ExtensionA+QM_redock+RMSD` | QM 筛选 |
| `Shape_Screening` | `localShape+SP_local` | 形状筛选 |
| `LocalShape_Screening` | `PhaseShape+SP_local` | 局部形状筛选 |
| `Advance_Shape_Screening` | `HTVS_Shape+SP_Shape` | 增强形状筛选 |
| `Local` | `SP_local+MMGBSA_OPT` | 局部精化 |
| `Advance` | `HTVS_Normal+SP_ExtensionA+SP_Enhanced` | 增强采样 |
| `GeminiMol_Advance` | `No_Dup+RDL+EPIK4+HTVS_Normal+QIKPROP+R5R+SP_ExtensionA+SP_Enhanced` | GeminiMol 增强 |

---

### 自定义流水线

使用 `+` 连接任意已注册任务名称构建自定义流水线：

```bash
# 过滤 + 聚类 + 对接
cadd gvsrun -i grid.zip -d ligands.mae -m "RDL+Linear_Tanimoto+HTVS_Normal+SP_Normal"

# 多层过滤
cadd gvsrun -i grid.zip -d ligands.mae -m "No_Dup+EDL+MW+Oral+HTVS_Normal"

# 仅聚类（不需要格点）
cadd gvsrun -d ligands.mae -m "No_Dup+RDL+Radial_Tanimoto" -i None
```

---

### 选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `-i`, `--input` | 格点文件（`.zip`）或通配符；`None` 表示不需要格点 | `None` |
| `-D`, `--database` | `$compound_library` 中的数据库名称 | `Custom_DB` |
| `-d`, `--db-path` | 自定义配体文件或目录路径 | 无 |
| `-m`, `--mode` | 运行模式名称或自定义 pipeline | `Fast` |
| `-T`, `--title` | 任务标题（空则自动生成） | 自动 |
| `-R`, `--reference` | 参考配体文件 | 无 |
| `-a`, `--htvs-out-num` | HTVS 输出数量（百分比 `5%` 或绝对数 `500`） | `5%` |
| `-b`, `--docking-out-num` | SP/XP 输出化合物数 | `4000` |
| `-e`, `--set-pull-num` | IFT/MMGBSA/CD 候选数 | `500` |
| `-c`, `--dock-out-conf` | 每个配体输出构象数 | `1` |
| `-p`, `--ph` | LigPrep pH 值（`pH:tolerance`） | `7.0:2.0` |
| `-s`, `--smarts` | SMARTs 过滤表达式 | 无 |
| `-q`, `--qm-set` | QM 方法与基组（`method:basis`） | `B3LYP-D3(BJ):6-311G**` |
| `-W`, `--mw-range` | 分子量范围（`min:max`） | `100:400` |
| `-v`, `--vdw` | 配体 VdW 缩放因子 | `0.8` |
| `-C`, `--covalent-residue` | 共价残基（如 `cys:A:1425`） | 无 |
| `-E`, `--shape-screen` | 形状筛选参数（`keep:method:confs`） | 无 |
| `-F`, `--force-field` | 对接力场（`OPLS4` / `OPLS3e` / `OPLS3` / `OPLS_2005`） | `OPLS4` |
| `-f`, `--coarse-ff` | HTVS 粗糙力场 | `OPLS_2005` |
| `-u`, `--strain-correction` | 启用应变能校正 | 关闭 |
| `-H`, `--host` | CPU 队列名称 | `CPU` |
| `-N`, `--njobs` | 最大并行任务数 | `100` |
| `-S`, `--schrodinger` | Schrödinger 安装路径 | `$SCHRODINGER` |
| `-P`, `--prime-njobs` | Prime 许可证数 | `10` |
| `-G`, `--glide-njobs` | Glide 许可证数 | `90` |
| `-L`, `--ligprep-njobs` | LigPrep 许可证数 | `30` |
| `-A`, `--phase-njobs` | Phase 许可证数 | `10` |
| `-Q`, `--qsite-njobs` | QSite 许可证数 | `10` |
| `-K`, `--qikprop-njobs` | QikProp 许可证数 | `10` |
| `-M`, `--macromodel-njobs` | MacroModel 许可证数 | `10` |

---

### 任务类别

GVSrun 流水线中的任务分为以下六类：

**过滤任务（20 种）** — 基于分子性质的化合物筛选，包括 17 种 LigFilter 过滤器（RDL、EDL、Fragment、R、NR、NPSE、PosMol、NegMol、5R、R5R、3R、Star、Oral、BBB、Oral_Drug、Warhead_SO、Warhead_N）以及 No_Dup（去重）、QIKPROP（性质计算）、MW（分子量范围）。

**LigPrep 任务（10 种）** — 配体预处理与构象生成，包括 IONIZE、EPIK4 等离子化/质子化工具和构象搜索。

**对接任务（21 种）** — 三种精度（HTVS 6 种、SP 8 种、XP 7 种），支持标准、增强、碎片、参考配体、形状等对接策略。

**聚类任务（20 种）** — 5 种分子指纹（Linear、Radial、MolPrint2D、Topo、Dendritic）与 4 种相似性度量（Tanimoto、Euclidean、Cosine、Soergel）的组合。

**评分任务（7 种）** — 高级评分方法，包括 IFT（诱导契合）、MMGBSA_EN / MMGBSA_MIN / MMGBSA_OPT（MM-GBSA）、QMMM（QM/MM）、QM_redock（QM 重对接）、CD（共价对接）。

**工具任务（3 种）** — 辅助工具，包括 RMSD（RMSD 计算）、PhaseShape（Phase 形状比较）、localShape（局部形状比较）。

---

### 示例

```bash
# 快速筛选
cadd gvsrun -i grid.zip -d ligands.mae -m Fast

# 标准虚拟筛选
cadd gvsrun -i grid.zip -d ligands.mae -m Normal

# 含预处理的标准流程（SDF 输入）
cadd gvsrun -i grid.zip -d unprepared.sdf -m Prep_Normal

# 使用化合物数据库
cadd gvsrun -i grid.zip -D ChemDiv -m Normal

# 参考配体模式
cadd gvsrun -i grid.zip -d ligands.mae -m Reference -R reference.mae

# 共价筛选
cadd gvsrun -i grid.zip -d ligands.mae -m Cov_Screening -C "cys:A:1425"

# QM 筛选
cadd gvsrun -i grid.zip -d ligands.mae -m QM_Screening -q "B3LYP-D3(BJ):6-311G**"

# 自定义流水线
cadd gvsrun -i grid.zip -d ligands.mae -m "RDL+HTVS_Normal+SP_ExtensionA+MMGBSA_EN"

# 调整输出数量与并行
cadd gvsrun -i grid.zip -d ligands.mae -m Normal -a "10%" -b 5000 -H amdnode -N 200
```

---

## 环境变量

| 变量 | 说明 | 必需 |
|------|------|------|
| `SCHRODINGER` | Schrödinger Suite 安装路径 | 是（除非通过 `-S` 指定） |
| `compound_library` | 化合物数据库路径（GVSrun 使用 `-D` 指定数据库名称时需要） | 仅 GVSrun 数据库模式需要 |
| `rosetta_app` | Rosetta 可执行文件目录 | 仅 Rosetta 任务需要 |
| `rosetta_db` | Rosetta 数据库路径 | 仅 Rosetta 任务需要 |

可以在 shell 配置文件中设置：

```bash
export SCHRODINGER=/opt/schrodinger/2024-1
export compound_library=/data/compound_databases
export rosetta_app=/opt/rosetta/bin
export rosetta_db=/opt/rosetta/database
```
