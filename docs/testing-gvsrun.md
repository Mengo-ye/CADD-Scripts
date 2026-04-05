# GVSrun 测试指南

本文档描述 GVSrun Python 版本的测试方法，用于验证迁移后的虚拟筛选流水线功能。

---

## 环境准备

```bash
source .venv/bin/activate
cadd --version

export SCHRODINGER=/path/to/schrodinger
export compound_library=/path/to/compound_databases
```

---

## 一、预定义模式测试（14 种）

### 1.1 Fast 模式 — 快速筛选

```bash
cadd gvsrun -i grid.zip -d ligands.mae -m Fast
```

**Pipeline:** `HTVS_Normal+SP_Normal`

**验证：** 生成的 .inp 包含 DOCK_HTVS 和 DOCK_SP 两个阶段

### 1.2 Normal 模式 — 标准流程

```bash
cadd gvsrun -i grid.zip -d ligands.mae -m Normal
```

**Pipeline:** `RDL+HTVS_Normal+QIKPROP+R5R+SP_ExtensionA`

**验证：** 5 个阶段（过滤 + HTVS + 性质 + 五规则 + SP扩展A）

### 1.3 Prep_Normal 模式 — 含预处理

```bash
cadd gvsrun -i grid.zip -d unprepared.sdf -m Prep_Normal
```

**Pipeline:** `No_Dup+RDL+IONIZE+HTVS_Normal+QIKPROP+R5R+SP_ExtensionA`

**验证：** 包含去重和 LigPrep 阶段

### 1.4 Normal_MMGBSA

```bash
cadd gvsrun -i grid.zip -d ligands.mae -m Normal_MMGBSA
```

**Pipeline:** `RDL+HTVS_Normal+QIKPROP+R5R+SP_ExtensionA+MMGBSA_EN`

**验证：** 末尾包含 MMGBSA 阶段

### 1.5 Reference 模式 — 参考配体

```bash
cadd gvsrun -i grid.zip -d ligands.mae -m Reference -R reference.mae
```

**Pipeline:** `HTVS_REF+SP_REF+QIKPROP+R5R`

**验证：** HTVS 和 SP 阶段包含 REF_LIGAND_FILE 参数

### 1.6 Cov_Screening — 共价筛选

```bash
cadd gvsrun -i grid.zip -d ligands.mae -m Cov_Screening -C "cys:A:1425"
```

**Pipeline:** `R+HTVS_Normal+SP_ExtensionA+SP_Enhanced`

**验证：** R 过滤保留反应性基团

### 1.7 Induce_Fit_Screening

```bash
cadd gvsrun -i grid.zip -d ligands.mae -m Induce_Fit_Screening
```

**Pipeline:** `IFT_pre+IFT`

### 1.8 QM_Screening

```bash
cadd gvsrun -i grid.zip -d ligands.mae -m QM_Screening -q "B3LYP-D3(BJ):6-311G**"
```

**Pipeline:** `RDL+HTVS_Normal+QIKPROP+R5R+SP_ExtensionA+QM_redock+RMSD`

### 1.9-1.11 Shape Screening 三种

```bash
cadd gvsrun -i grid.zip -d ligands.mae -m Shape_Screening -R shape.mae
cadd gvsrun -i grid.zip -d ligands.mae -m LocalShape_Screening -R shape.mae
cadd gvsrun -i grid.zip -d ligands.mae -m Advance_Shape_Screening -R shape.mae -E 10000:rapid:100
```

### 1.12 Local — 局部精化

```bash
cadd gvsrun -i grid.zip -d ligands.mae -m Local
```

**Pipeline:** `SP_local+MMGBSA_OPT`

### 1.13 Advance — 增强采样

```bash
cadd gvsrun -i grid.zip -d ligands.mae -m Advance
```

**Pipeline:** `HTVS_Normal+SP_ExtensionA+SP_Enhanced`

### 1.14 GeminiMol_Advance

```bash
cadd gvsrun -i grid.zip -d unprepared.sdf -m GeminiMol_Advance
```

---

## 二、自定义流水线测试

用 `+` 拼接任何已注册的任务：

### 2.1 过滤 + 聚类 + 对接

```bash
cadd gvsrun -i grid.zip -d ligands.mae -m "RDL+Linear_Tanimoto+HTVS_Normal+SP_Normal"
```

### 2.2 多层过滤

```bash
cadd gvsrun -i grid.zip -d ligands.mae -m "No_Dup+EDL+MW+Oral+HTVS_Normal"
```

### 2.3 单独运行聚类

```bash
cadd gvsrun -d ligands.mae -m "No_Dup+RDL+Radial_Tanimoto" -i None
```

---

## 三、过滤任务测试（20 种）

单独测试每个过滤任务：

```bash
# 药物样过滤
cadd gvsrun -i grid.zip -d ligands.sdf -m "RDL+HTVS_Normal"       # Rough Drug-Like
cadd gvsrun -i grid.zip -d ligands.sdf -m "EDL+HTVS_Normal"       # Exact Drug-Like
cadd gvsrun -i grid.zip -d ligands.sdf -m "Fragment+HTVS_Normal"  # 碎片

# 五规则
cadd gvsrun -i grid.zip -d ligands.sdf -m "5R+HTVS_Normal"        # 严格 Rule of 5
cadd gvsrun -i grid.zip -d ligands.sdf -m "R5R+HTVS_Normal"       # Rough Rule of 5
cadd gvsrun -i grid.zip -d ligands.sdf -m "3R+HTVS_Normal"        # Rule of 3

# 渗透性
cadd gvsrun -i grid.zip -d ligands.sdf -m "Oral+HTVS_Normal"      # 口服
cadd gvsrun -i grid.zip -d ligands.sdf -m "BBB+HTVS_Normal"       # 血脑屏障

# 电荷
cadd gvsrun -i grid.zip -d ligands.sdf -m "PosMol+HTVS_Normal"    # 正电分子
cadd gvsrun -i grid.zip -d ligands.sdf -m "NegMol+HTVS_Normal"    # 负电分子

# 反应性
cadd gvsrun -i grid.zip -d ligands.sdf -m "R+HTVS_Normal"         # 仅反应性
cadd gvsrun -i grid.zip -d ligands.sdf -m "NR+HTVS_Normal"        # 非反应性

# 共价
cadd gvsrun -i grid.zip -d ligands.sdf -m "Warhead_SO+HTVS_Normal"

# 其他
cadd gvsrun -i grid.zip -d ligands.sdf -m "No_Dup+HTVS_Normal"    # 去重
cadd gvsrun -i grid.zip -d ligands.sdf -m "MW+HTVS_Normal" -W "200:500"  # MW 范围
cadd gvsrun -i grid.zip -d ligands.sdf -m "QIKPROP+HTVS_Normal"   # 性质计算
```

---

## 四、聚类任务测试（20 种）

5 种指纹 × 4 种相似性 = 20 种组合：

```bash
# Linear 指纹
cadd gvsrun -d ligands.mae -m "Linear_Tanimoto" -i None
cadd gvsrun -d ligands.mae -m "Linear_Euclidean" -i None
cadd gvsrun -d ligands.mae -m "Linear_Cosine" -i None
cadd gvsrun -d ligands.mae -m "Linear_Soergel" -i None

# Radial 指纹
cadd gvsrun -d ligands.mae -m "Radial_Tanimoto" -i None
# ... 4 variants

# MolPrint2D / Topo / Dendritic 指纹（各 4 variants）
```

---

## 五、对接任务测试（21 种）

### HTVS 精度（6 种）

```bash
cadd gvsrun -i grid.zip -d ligands.mae -m "HTVS_Normal"
cadd gvsrun -i grid.zip -d ligands.mae -m "HTVS_Rough"
cadd gvsrun -i grid.zip -d ligands.mae -m "HTVS_Fragment"
cadd gvsrun -i grid.zip -d ligands.mae -m "HTVS_REF" -R ref.mae
cadd gvsrun -i grid.zip -d ligands.mae -m "HTVS_Shape" -R shape.mae -E 10000:rapid:100
cadd gvsrun -i grid.zip -d ligands.mae -m "IFT_pre"
```

### SP 精度（8 种）

```bash
cadd gvsrun -i grid.zip -d ligands.mae -m "SP_Normal"
cadd gvsrun -i grid.zip -d ligands.mae -m "SP_ExtensionA"
cadd gvsrun -i grid.zip -d ligands.mae -m "SP_ExtensionB"
cadd gvsrun -i grid.zip -d ligands.mae -m "SP_REF" -R ref.mae
cadd gvsrun -i grid.zip -d ligands.mae -m "SP_Shape" -R shape.mae -E 10000:rapid:100
cadd gvsrun -i grid.zip -d ligands.mae -m "SP_Fragment"
cadd gvsrun -i grid.zip -d ligands.mae -m "SP_Enhanced"
cadd gvsrun -i grid.zip -d ligands.mae -m "SP_local"
```

### XP 精度（7 种）

```bash
cadd gvsrun -i grid.zip -d ligands.mae -m "XP_Normal"
cadd gvsrun -i grid.zip -d ligands.mae -m "XP_ExtensionA"
cadd gvsrun -i grid.zip -d ligands.mae -m "XP_ExtensionB"
cadd gvsrun -i grid.zip -d ligands.mae -m "XP_REF" -R ref.mae
cadd gvsrun -i grid.zip -d ligands.mae -m "XP_Fragment"
cadd gvsrun -i grid.zip -d ligands.mae -m "XP_Enhanced"
cadd gvsrun -i grid.zip -d ligands.mae -m "XP_local"
```

---

## 六、高级评分测试（7 种）

```bash
cadd gvsrun -i grid.zip -d ligands.mae -m "SP_Normal+IFT"         # 诱导契合
cadd gvsrun -i grid.zip -d ligands.mae -m "SP_Normal+MMGBSA_EN"   # MM-GBSA 能量
cadd gvsrun -i grid.zip -d ligands.mae -m "SP_Normal+MMGBSA_MIN"  # MM-GBSA 最小化
cadd gvsrun -i grid.zip -d ligands.mae -m "SP_Normal+MMGBSA_OPT"  # MM-GBSA 优化
cadd gvsrun -i grid.zip -d ligands.mae -m "SP_Normal+QMMM"        # QM/MM
cadd gvsrun -i grid.zip -d ligands.mae -m "SP_Normal+QM_redock"   # QM 重对接
cadd gvsrun -i grid.zip -d ligands.mae -m "SP_Normal+CD" -C "cys:A:1425"  # 共价对接
```

---

## 七、参数调节测试

### 7.1 VdW 缩放

```bash
cadd gvsrun -i grid.zip -d ligands.mae -m Normal -v 0.5
```

### 7.2 pH 与 LigPrep

```bash
cadd gvsrun -i grid.zip -d unprepared.sdf -m Prep_Normal -p "7.4:1.0"
```

### 7.3 力场选择

```bash
cadd gvsrun -i grid.zip -d ligands.mae -m Normal -F OPLS3e -f OPLS_2005
```

### 7.4 输出数量

```bash
cadd gvsrun -i grid.zip -d ligands.mae -m Normal -a "10%" -b 5000 -c 3
```

### 7.5 应变校正

```bash
cadd gvsrun -i grid.zip -d ligands.mae -m Normal -u
```

### 7.6 主机/并行

```bash
cadd gvsrun -i grid.zip -d ligands.mae -m Normal -H amdnode -N 200 -P 20 -G 180
```

---

## 八、错误处理测试

### 8.1 未设置 SCHRODINGER

```bash
unset SCHRODINGER
cadd gvsrun -i grid.zip -d ligands.mae -m Fast
```

**预期：** `RuntimeError: Schrödinger path not set.`

### 8.2 无效任务名

```bash
cadd gvsrun -i grid.zip -d ligands.mae -m "INVALID_TASK"
```

**预期：** `ValueError: Unknown pipeline task: INVALID_TASK`

### 8.3 无效力场

```bash
cadd gvsrun -i grid.zip -d ligands.mae -m Normal -F INVALID
```

**预期：** Click 报错无效选择

---

## 九、与 Bash 版本对比

```bash
# Bash 版本
bash GVSrun -i grid.zip -d ligands.mae -m Normal -T test_bash

# Python 版本
cadd gvsrun -i grid.zip -d ligands.mae -m Normal -T test_python

# 对比生成的 .inp 文件
diff test_bash.inp test_python.inp
```

关键对比点：
- 每个 [STAGE:*] 块的参数名和值
- INPUTS / OUTPUTS 链是否一致
- CONDITIONS 表达式是否一致
- FORCEFIELD / PRECISION 等是否一致
- PERCENT_TO_KEEP / NUM_TO_KEEP 格式是否一致

---

## 十、任务清单汇总

Python 版已注册 **81 个任务**：
- 20 过滤任务（17 LigFilter + No_Dup + QIKPROP + MW）
- 21 对接任务（6 HTVS + 8 SP + 7 XP）
- 10 LigPrep 任务
- 20 聚类任务（5 指纹 × 4 相似性）
- 7 评分任务（IFT + 3 MMGBSA + QMMM + QM_redock + CD）
- 3 工具任务（RMSD + PhaseShape + localShape）

以及 14 个预定义模式。
