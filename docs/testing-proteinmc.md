# ProteinMC 测试指南

本文档描述 ProteinMC Python 版本的测试方法，用于验证迁移后的功能与原 Bash 版本一致。

---

## 环境准备

```bash
# 激活虚拟环境
source .venv/bin/activate

# 确认安装
cadd --version
# 预期输出: cadd, version 2.0.0

# 设置环境变量
export SCHRODINGER=/path/to/schrodinger
export rosetta_app=/path/to/rosetta/bin
export rosetta_db=/path/to/rosetta/database
```

---

## 一、Prime 子命令测试

### 1.1 蛋白制备 — Normal

```bash
cadd proteinmc prime -i protein.mae -t Normal
```

**验证要点：**
- 调用了 `$SCHRODINGER/utilities/prepwizard`
- pH 参数为 `-epik_pH 6.9 -epik_pHt 0.6 -propka_pH 6.9`
- 输出文件为 `protein_Normal-prep.maegz`

### 1.2 蛋白制备 — Lysozyme

```bash
cadd proteinmc prime -i lysozyme.mae -t Lysozyme
```

**验证要点：**
- pH 参数为 `-epik_pH 4.75 -epik_pHt 0.75 -propka_pH 4.75`
- 输出文件为 `lysozyme_Lysozyme-prep.maegz`

### 1.3 Monte Carlo 精化

```bash
cadd proteinmc prime -i protein.mae -t MC -s 100 -n 5
```

**验证要点：**
- 生成 `protein_MC.inp` 文件
- 检查 .inp 文件内容：
  ```
  STRUCT_FILE	<绝对路径>/protein.mae
  JOB_TYPE	REFINE
  PRIME_TYPE	MC
  SELECT	asl=all
  NSTEPS	100
  NUM_OUTPUT_STRUCT	5
  USE_RANDOM_SEED	yes
  ```
- 调用了 `$SCHRODINGER/prime`

### 1.4 侧链预测 — SIDE_PRED

```bash
cadd proteinmc prime -i protein.mae -t SIDE_PRED -R "chain A"
```

**验证要点：**
- 生成 `protein_SIDE_PRED.inp`
- .inp 中 `PRIME_TYPE` 为 `SIDE_PRED`
- .inp 中 `SAMPLE_BACKBONE yes`
- .inp 中 `SELECT asl=chain A`

### 1.5 侧链优化 — SIDE_OPT

```bash
cadd proteinmc prime -i protein.mae -t SIDE_OPT
```

**验证要点：**
- job_name 为 `protein_SIDE_PRED`（与 Bash 版一致）
- .inp 中 `PRIME_TYPE` 为 `SIDE_PRED`
- .inp 中 `SAMPLE_BACKBONE no`

### 1.6 PPI MM-GBSA

```bash
cadd proteinmc prime -i complex.mae -t PPI_MMGBSA -1 "chain A" -2 "chain B"
```

**验证要点：**
- 调用了 `$SCHRODINGER/prime_mmgbsa`
- `-ligand` 参数为 `chain B`
- `-jobname` 为 `complex_PPI_MMGBSA-MMGBSA`

### 1.7 带约束的 MC

```bash
cadd proteinmc prime -i protein.mae -t MC -c "backbone" -f 15.0 -d 0.5
```

**验证要点：**
- .inp 末尾包含：`CONSTRAINT_0 asl=backbone;15.00;0.50`
- 注意浮点数保留两位小数

### 1.8 膜环境 MC

```bash
cadd proteinmc prime -i protein.mae -t MC -m
```

**验证要点：**
- .inp 中 `USE_MEMBRANE yes`

### 1.9 PDB 输入转换

```bash
cadd proteinmc prime -i protein.pdb -t MC
```

**验证要点：**
- 先调用 `structconvert` 将 PDB 转为 MAE
- 再执行 MC 任务

### 1.10 目录输入

```bash
# 准备一个包含多个 PDB 的目录
mkdir test_pdbs && cp *.pdb test_pdbs/
cadd proteinmc prime -i test_pdbs -t MC
```

**验证要点：**
- 调用 `structcat` 合并所有 PDB 为 MAE
- 再执行 MC 任务

### 1.11 禁用随机种子

```bash
cadd proteinmc prime -i protein.mae -t MC --no-random-seed
```

**验证要点：**
- .inp 中 `USE_RANDOM_SEED no`

---

## 二、Rosetta 子命令测试

### 2.1 快速弛豫 — MPI 模式（单 PDB）

```bash
cadd proteinmc rosetta -i protein.pdb -t Fast_Relax -n 5 -H CPU -N 30
```

**验证要点：**
- 生成 `protein_Fast_Relax.pbs`
- PBS header 包含 `#PBS -q siais_pub_cpu` 和 `:centos7`
- 命令包含 `mpirun -np 30` 和 `-relax:fast`
- 创建了 `protein_Fast_Relax_OUT/` 目录
- 调用 `qsub`

### 2.2 高周期弛豫

```bash
cadd proteinmc rosetta -i protein.pdb -t Relax -H amdnode -N 64
```

**验证要点：**
- PBS header 包含 `#PBS -q amdnode`，无 `:centos7`
- 命令包含 `-relax:thorough`

### 2.3 界面弛豫

```bash
cadd proteinmc rosetta -i complex.pdb -t PPI_Relax -1 A -2 B
```

**验证要点：**
- 命令包含 `-relax:script InterfaceRelax2019`

### 2.4 MAE 输入 — parallel 模式

```bash
cadd proteinmc rosetta -i structures.maegz -t Fast_Relax -n 3
```

**验证要点：**
- 自动拆分 MAE 为多个 PDB
- 生成 `*_input.list` 文件
- PBS 中使用 `cat ... | parallel` 而非 `mpirun`

### 2.5 目录输入

```bash
cadd proteinmc rosetta -i pdb_dir/ -t Relax
```

**验证要点：**
- 只读取 `.pdb` 文件（忽略其他文件）
- 生成 `*_input.list` 文件
- 使用 parallel 模式

### 2.6 柔性多肽对接

```bash
cadd proteinmc rosetta -i complex.pdb -t FlexPepDock -1 A -2 B -n 10
```

**验证要点：**
- 必须为单个 PDB 文件（MPI 模式）
- 命令包含 `FlexPepDocking` 可执行文件
- 包含 `-flexPepDocking:lowres_abinitio` 和 fragment 参数
- 末尾有 `InterfaceAnalyzer` 并行命令

### 2.7 柔性多肽精化

```bash
cadd proteinmc rosetta -i complex.pdb -t FlexPepRefine -1 A -2 B
```

**验证要点：**
- 包含 `-flexPepDocking:pep_refine`
- 不包含 `-flexPepDocking:lowres_abinitio`

### 2.8 蛋白-蛋白对接

```bash
cadd proteinmc rosetta -i complex.pdb -t PPI_Dock -1 A -2 B -n 20
```

**验证要点：**
- 先调用 `docking_prepack_protocol`
- 再调用 `docking_protocol`，包含 `-dock_pert 3 8 -randomize2 -spin` 等参数
- 末尾有 `InterfaceAnalyzer`

### 2.9 蛋白-蛋白精化

```bash
cadd proteinmc rosetta -i complex.pdb -t PPI_Refine -1 A -2 B
```

**验证要点：**
- `docking_protocol` 参数比 PPI_Dock 简单（无 `-randomize2 -spin` 等）

### 2.10 fat 节点

```bash
cadd proteinmc rosetta -i protein.pdb -t Fast_Relax -H fat
```

**验证要点：**
- PBS header 包含 `#PBS -q pub_fat`

---

## 三、错误处理测试

### 3.1 未设置 SCHRODINGER

```bash
unset SCHRODINGER
cadd proteinmc prime -i protein.mae -t MC
```

**预期：** `RuntimeError: Schrödinger path not set. Use --schrodinger or set $SCHRODINGER.`

### 3.2 未设置 Rosetta 路径

```bash
unset rosetta_app
cadd proteinmc rosetta -i protein.pdb -t Fast_Relax
```

**预期：** `RuntimeError: Rosetta app path not set. Use --rosetta-app or set $rosetta_app.`

### 3.3 无效任务类型

```bash
cadd proteinmc prime -i protein.mae -t InvalidType
```

**预期：** Click 报错 `Invalid value for '-t' / '--type'`

### 3.4 不支持的 Rosetta host

```bash
cadd proteinmc rosetta -i protein.pdb -t Fast_Relax -H localhost
```

**预期：** `ValueError: Unsupported host 'localhost' for Rosetta jobs. Supported: CPU, amdnode, fat`

### 3.5 对接模式使用非 PDB 输入

```bash
cadd proteinmc rosetta -i structures.maegz -t FlexPepDock -1 A -2 B
```

**预期：** `ValueError: Must specify only one pdb file path for docking mode!`

### 3.6 空目录

```bash
mkdir empty_dir
cadd proteinmc prime -i empty_dir -t MC
```

**预期：** `ValueError: No .pdb files found in directory: ...`

---

## 四、与 Bash 版本对比测试

对于关键任务类型，建议同时运行 Bash 版本和 Python 版本，对比生成的文件：

```bash
# 1. 用 Bash 版本生成 .inp
bash ProteinMC -i protein.mae -t MC -s 50

# 2. 用 Python 版本生成 .inp
cadd proteinmc prime -i protein.mae -t MC -s 50

# 3. 对比两个 .inp 文件
diff protein_MC.inp protein_MC.inp.bak
```

需要对比的文件：
- MC 模式的 `.inp` 文件
- SIDE_PRED / SIDE_OPT 模式的 `.inp` 文件
- Rosetta 各模式的 `.pbs` 文件
