# XDock 测试指南

本文档描述 XDock Python 版本的测试方法，用于验证迁移后的功能与原 Bash 版本一致。

---

## 环境准备

```bash
source .venv/bin/activate
cadd --version

export SCHRODINGER=/path/to/schrodinger
export rosetta_app=/path/to/rosetta/bin
export rosetta_db=/path/to/rosetta/database
```

---

## 一、模式测试（11 种模式）

### 1.1 SITEMAP — SiteMap 口袋检测 + 对接

```bash
cadd xdock -P protein_lib/ -L ligand.mae -m SITEMAP
```

**验证要点：**
- .inp 中包含 `RECEPTOR` 行（每个蛋白一行）
- 包含 `SITEMAP TRUE` 和 `SITEMAP_MAXSITES 2`
- 包含 `DOCKING_METHOD confgen` 和 `PRECISION SP`
- 调用 `$SCHRODINGER/run xglide.py`

### 1.2 AllSite — SiteMap + 复合物配体位置

```bash
cadd xdock -P complex_lib/ -L ligand.mae -m AllSite
```

**验证要点：**
- .inp 中包含 `COMPLEX` 行（带配体 ASL）
- 同时包含 `SITEMAP TRUE`

### 1.3 Native — 原位重对接

```bash
cadd xdock -P complex_lib/ -m Native
```

**验证要点：**
- .inp 中包含 `NATIVEONLY TRUE`
- 不需要 `-L` 配体输入

### 1.4 COMPD — 复合物定义口袋 + 对接

```bash
cadd xdock -P complex_lib/ -L ligand.mae -m COMPD -a "res.num 1"
```

**验证要点：**
- .inp 中包含 `COMPLEX` 行
- 不包含 SITEMAP 部分

### 1.5 COMPI — 复合物定义 + Induce Fit

```bash
cadd xdock -P complex_lib/ -L ligand.mae -m COMPI -A "A:999"
```

**验证要点：**
- 调用 `$SCHRODINGER/ifd`（不是 xglide）
- IFD .inp 包含 `BINDING_SITE ligand A:999`

### 1.6 GCD — 用户定义网格中心 + 对接

```bash
cadd xdock -P protein_lib/ -L ligand.mae -m GCD -g "10.0, 20.0, 30.0"
```

**验证要点：**
- .inp 包含 `GRIDGEN_GRID_CENTER 10.0, 20.0, 30.0`
- 精度强制为 SP

### 1.7 GCI — 用户定义中心 + Induce Fit

```bash
cadd xdock -P protein_lib/ -L ligand.mae -m GCI -g "10.0, 20.0, 30.0"
```

**验证要点：**
- 调用 IFD，不是 xglide
- IFD .inp 包含 `BINDING_SITE coords 10.0, 20.0, 30.0`

### 1.8 SiteMapGrid — SiteMap 网格生成（不对接）

```bash
cadd xdock -P protein_lib/ -m SiteMapGrid
```

**验证要点：**
- .inp 包含 SITEMAP 部分
- 不包含 DOCKING_METHOD 等对接参数

### 1.9 ComplexGrid — 复合物网格生成

```bash
cadd xdock -P complex_lib/ -m ComplexGrid -a "res.num 1"
```

**验证要点：**
- .inp 包含 `COMPLEX` 行
- 不包含对接参数

### 1.10 CenterGrid — 坐标网格生成

```bash
cadd xdock -P protein_lib/ -m CenterGrid -g "10.0, 20.0, 30.0"
```

**验证要点：**
- .inp 包含 `GRIDGEN_GRID_CENTER`
- 不包含对接参数

### 1.11 Dock — 使用预生成网格对接

```bash
cadd xdock -P grid_dir/ -L ligand.mae -m Dock
```

**验证要点：**
- .inp 包含 `GRID` 行（每个 .zip/.grd 文件一行）
- 不包含蛋白制备参数

---

## 二、蛋白制备模式测试

### 2.1 none — 不制备

```bash
cadd xdock -P protein_lib/ -L ligand.mae -m SITEMAP -p none
```

**验证：** .inp 中 `PPREP FALSE`

### 2.2 rough — 粗略制备

```bash
cadd xdock -P protein_lib/ -L ligand.mae -m SITEMAP -p rough
```

**验证：** `PPREP TRUE`，其余均 FALSE

### 2.3 fine — 精细制备

```bash
cadd xdock -P protein_lib/ -L ligand.mae -m SITEMAP -p fine
```

**验证：** `PPREP TRUE, PPREP_REHTREAT TRUE, PPREP_EPIK TRUE`

### 2.4 hopt — H 键优化

```bash
cadd xdock -P protein_lib/ -L ligand.mae -m SITEMAP -p hopt
```

**验证：** 在 fine 基础上 `PPREP_PROTASSIGN TRUE`

### 2.5 mini — 约束最小化

```bash
cadd xdock -P protein_lib/ -L ligand.mae -m SITEMAP -p mini
```

**验证：** 所有 PPREP 标志均为 TRUE

### 2.6 rosetta — Rosetta 预处理

```bash
cadd xdock -P protein_lib/ -L ligand.mae -m SITEMAP -p rosetta
```

**验证：** 先调用 `score_jd2`，然后蛋白制备设为 none

---

## 三、配体制备模式测试

### 3.1 epik

```bash
cadd xdock -P protein.mae -L ligand.mae -m SITEMAP -l epik
```

**验证：** `LIGPREP TRUE, LIGPREP_EPIK TRUE`

### 3.2 ionizer

```bash
cadd xdock -P protein.mae -L ligand.mae -m SITEMAP -l ionizer
```

**验证：** `LIGPREP TRUE, LIGPREP_EPIK FALSE`

### 3.3 none

```bash
cadd xdock -P protein.mae -L ligand.mae -m SITEMAP -l none
```

**验证：** `LIGPREP FALSE, LIGPREP_EPIK FALSE`

---

## 四、对接参数测试

### 4.1 XP 精度

```bash
cadd xdock -P protein.mae -L ligand.mae -m SITEMAP -x XP -n 5
```

**验证：** `PRECISION XP, POSES_PER_LIG 5`

### 4.2 增强采样

```bash
cadd xdock -P protein.mae -L ligand.mae -m SITEMAP -e
```

**验证：** `ENHANCED_SAMPLING 3, MAXKEEP 15000`

### 4.3 原位精化

```bash
cadd xdock -P protein.mae -L ligand.mae -m SITEMAP -w
```

**验证：** `DOCKING_METHOD mininplace`

### 4.4 禁用应变校正

```bash
cadd xdock -P protein.mae -L ligand.mae -m SITEMAP -1
```

**验证：** `POSTDOCKSTRAIN FALSE`

### 4.5 VdW 缩放

```bash
cadd xdock -P protein.mae -L ligand.mae -m SITEMAP -v 0.6 -V 0.9
```

**验证：** `LIG_VSCALE 0.6, GRIDGEN_RECEP_VSCALE 0.9`

---

## 五、多肽处理测试

### 5.1 多肽分段

```bash
cadd xdock -P protein.pdb -L ligand.mae -m SITEMAP -d "12:5"
```

**验证：**
- 生成 `Segment.jl` 文件
- 创建 `Peptides_Lib/` 目录
- 调用 `julia Segment.jl`

### 5.2 仅分段（不对接）

```bash
cadd xdock -P protein.pdb -m SITEMAP -d "12:5" -0
```

**验证：** 输出分段结果后退出，不进行对接

### 5.3 从 FASTA 构建多肽

```bash
cadd xdock -P protein.mae -m SITEMAP -f peptide.fasta
```

**验证：** 调用 `build_peptide.py`，输出到 `Peptides_lib/`

### 5.4 多肽加帽

```bash
cadd xdock -P protein.mae -m SITEMAP -f peptide.fasta -c
```

**验证：** `build_peptide.py` 命令包含 `-c`（而非 `-z`）

### 5.5 多肽对接模式

```bash
cadd xdock -P protein.mae -L ligand.mae -m SITEMAP -t
```

**验证：** .inp 中包含 `GRIDGEN_PEPTIDE TRUE`

---

## 六、Induce Fit 对接测试

### 6.1 复合物模式 IFD

```bash
cadd xdock -P complex_lib/ -L ligand.mae -m COMPI -A "A:999" -F OPLS4 -D 6.0
```

**验证要点：**
- 先 `structcat` 合并蛋白和配体
- IFD .inp 包含所有阶段（VDW_SCALING, PREDICT_FLEXIBILITY, INITIAL_DOCKING 等）
- `BINDING_SITE ligand A:999`
- `OPLS_VERSION OPLS4`
- `DISTANCE_CUTOFF 6.0`
- 调用 `$SCHRODINGER/ifd`

### 6.2 坐标模式 IFD

```bash
cadd xdock -P protein_lib/ -L ligand.mae -m GCI -g "10.0, 20.0, 30.0"
```

**验证：** `BINDING_SITE coords 10.0, 20.0, 30.0`

---

## 七、错误处理测试

### 7.1 未设置 SCHRODINGER

```bash
unset SCHRODINGER
cadd xdock -P protein.mae -m SITEMAP
```

**预期：** `RuntimeError: Schrödinger path not set.`

### 7.2 无效模式

```bash
cadd xdock -P protein.mae -m INVALID
```

**预期：** Click 报错无效选择

### 7.3 无效精度

```bash
cadd xdock -P protein.mae -m SITEMAP -x INVALID
```

**预期：** Click 报错无效选择

### 7.4 无效力场

```bash
cadd xdock -P protein.mae -m COMPI -F INVALID
```

**预期：** Click 报错无效选择

### 7.5 IFD 模式使用 SiteMap（不支持）

```bash
# GCI/COMPI 才支持 IFD，SiteMap 模式不应触发 IFD
cadd xdock -P protein.mae -m SITEMAP -L ligand.mae
# 这应正常运行 xglide，不是 IFD
```

---

## 八、与 Bash 版本对比测试

```bash
# Bash 版本
bash XDock -P protein_lib -L ligand.mae -m SITEMAP -p rough -l epik

# Python 版本
cadd xdock -P protein_lib -L ligand.mae -m SITEMAP -p rough -l epik

# 对比生成的 .inp 文件
diff *XDOCK.inp *XDOCK.inp.bak
```

需要对比的关键 .inp 内容：
- SITEMAP 模式的 xglide .inp
- COMPD 模式的 xglide .inp
- Native 模式的 .inp
- COMPI 模式的 IFD .inp
- 各蛋白制备模式的 PPREP 标志组合
