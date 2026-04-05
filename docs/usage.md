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

## 环境变量

| 变量 | 说明 | 必需 |
|------|------|------|
| `SCHRODINGER` | Schrödinger Suite 安装路径 | 是（除非通过 `-S` 指定） |
| `rosetta_app` | Rosetta 可执行文件目录 | 仅 Rosetta 任务需要 |
| `rosetta_db` | Rosetta 数据库路径 | 仅 Rosetta 任务需要 |

可以在 shell 配置文件中设置：

```bash
export SCHRODINGER=/opt/schrodinger/2024-1
export rosetta_app=/opt/rosetta/bin
export rosetta_db=/opt/rosetta/database
```
