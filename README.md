# CADD-Scripts (using Schrödinger and Rosetta)

用于运行 Schrödinger 和 Rosetta 计算任务的自动化工具集。

[![DOI](https://zenodo.org/badge/365661221.svg)](https://zenodo.org/badge/latestdoi/365661221)

新闻
----
* 2025/04/02，新增 `-u` 选项控制应变能校正。默认关闭，这可能导致 GVSrun 的行为与之前不同。

安装
----

```bash
git clone https://github.com/Wang-Lin-boop/CADD-Scripts
cd CADD-Scripts
pip install -e .
```

安装完成后，`cadd` 命令即可在终端中使用。

工具说明
----

- **GVSrun** — 虚拟筛选自动化流水线
- **XDock** — 反向对接、全局对接与批量格点生成
- **ProteinMC** — 蛋白质弛豫、蛋白-蛋白对接、MM-GBSA 计算

使用 `--help` 查看帮助信息，例如 `cadd gvsrun --help`。

快速示例
----

```bash
cadd proteinmc prime -i protein.mae -t MC
cadd xdock -P proteins/ -L ligand.mae -m SITEMAP
cadd gvsrun -i grid.zip -d ligands.mae -m Normal
```

相关项目
----

分子动力学模拟的自动化执行与轨迹分析请参考 [AutoMD](https://github.com/Wang-Lin-boop/AutoMD)。

中文文档
----

[XDock](https://zhuanlan.zhihu.com/p/387371069)

[靶标垂钓](https://zhuanlan.zhihu.com/p/422890966)

[GVSrun and plmd](https://zhuanlan.zhihu.com/p/370850885)

环境变量
----

以下环境变量需要在使用前设置：

1. `SCHRODINGER`（Schrödinger 安装路径）— `GVSrun`、`XDock` 和 `ProteinMC` 均需要；
2. `compound_library`（化合物数据库路径）— `GVSrun` 使用数据库名称时需要；
3. `rosetta_app` 或 `rosetta_db`（Rosetta 安装路径）— `XDock` 的 Rosetta 相关功能需要。

可以将这些变量添加到 `~/.bashrc` 中，例如：

```bash
export SCHRODINGER=/public/home/wanglin3/software/SCHRODINGER
export compound_library=/public/home/wanglin3/compound_databases
```

引用方式
----

建议通过链接引用本工具（例如：`GVSrun(https://github.com/Wang-Lin-boop/CADD-Scripts)`），或参考 [Ways to cite a GitHub Repo](https://www.wikihow.com/Cite-a-GitHub-Repository) 以提高工作的可重复性。

作者
----

Wang Lin (wanglin3@shanghaitech.edu.cn)
