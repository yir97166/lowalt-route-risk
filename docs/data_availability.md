# 数据与代码可用性（Data and Code Availability）

> 用途：给报告、投稿、答辩提供一份可核对的可用性声明；英文段可直接粘贴到投稿系统。
> 最后更新：2026-11-25

## 1. 数据集清单

| 数据 | 类型 | 来源 / 版本 | 标识 | 许可 | 是否随仓库分发 |
|---|---|---|---|---|---|
| WorldPop 2020 中国约束版 100 m（UN-adjusted） | 复用公开数据 | `chn_ppp_2020_UNadj_constrained.tif`，625,678,258 字节，EPSG:4326 | DOI `10.1038/sdata.2017.4`；<https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/CHN/chn_ppp_2020_UNadj_constrained.tif> | CC BY 4.0 | 否（体积过大；`data/raw/` 被忽略） |
| 200 m 网格人口/暴露聚合表 | 本研究生成 | 由 WorldPop 聚合，`data/processed/grid_population.csv` | 仓库 tag `v1.0` | MIT（代码）/ CC BY 4.0（文档） | **是** |
| 合成人口栅格（离线 fallback） | 本研究生成 | `data/processed/synthetic_population.tif` | 仓库 tag `v1.0` | 同上 | **是** |
| 路线与实验表 | 本研究生成 | `results/*.csv`（baseline / compare / pareto / resolution / origin_shift / param_sensitivity 等） | 仓库 tag `v1.0` | 同上 | **是** |
| 图件与图源 | 本研究生成 | `figures/*.png`、`figures/report/*.pdf` | 仓库 tag `v1.0` | 同上 | **是** |
| 代码 | 本研究生成 | `src/`、`scripts/`、`tests/`（Python 3.12） | 仓库 tag `v1.0` | MIT | **是** |
| 深圳机场净空通告 | 复用公开文件 | 深公规〔2017〕3 号（2017-03-14 成文，2017-04-10 公开） | 深圳市公安局 | 政府公开文件 | 否（版权归原机构） |
| 机场航图 | 复用公开文件 | ZGSZ 6A-1、6A-2、2A-1、2P-1（CAAC AIP，图面 `EFF2606101600`） | CAAC AIP | 归原机构 | 否（版权归原机构） |

## 2. 英文声明（投稿草稿）

**Data availability**

> All data generated in this study are available in the public GitHub repository
> <https://github.com/yir97166/lowalt-route-risk> at tag `v1.0`, including the 200 m
> gridded population/exposure table (`data/processed/grid_population.csv`), all route and
> sensitivity result tables (`results/*.csv`), figure source files (`figures/`), and
> configuration files. This study reused the WorldPop 2020 constrained population dataset
> for China (100 m, UN-adjusted; Tatem, 2017, DOI 10.1038/sdata.2017.4; CC BY 4.0),
> downloaded on 23 November 2026. The airport protection-zone geometry follows the publicly
> available Shenzhen Public Security Bureau notice 深公规〔2017〕3号 (2017) and ICAO
> aerodrome charts for ZGSZ (CAAC AIP, effective 2026); these third-party documents are not
> redistributed. No human-subject, sensitive, or newly measured field data were used.

**Code availability**

> The analysis code (Python 3.12) is available at the same repository and tag. The full
> pipeline is reproduced with `python -m src.cli all` (13 steps, about 117 s), and the test
> suite with `pytest` (69 tests).

## 3. 复现所需命令

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
# 下载 WorldPop 到 data/raw/worldpop/chn_ppp_2020_UNadj_constrained.tif
.\.venv\Scripts\python.exe -m src.cli all
.\.venv\Scripts\python.exe -m pytest -q
```

## 4. 待补 / 风险

- 仓库目前**没有 DOI**（只有 GitHub tag）。投 Nature 系期刊前建议用 Zenodo 归档 `v1.0` 并拿到 DOI，再替换声明中的标识。
- `LICENSE`：仓库根目录已有 MIT 许可证；文档按 CC BY 4.0 释出。
- WorldPop 的访问日期、文件大小与 SHA256 已写入 `README.md` 与 `docs/progress_log.md`，审稿人可据此核对版本。
- 若期刊要求「source data 按图逐张提供」，当前 `figures/report/*.pdf` 与 `results/*.csv` 可满足；必要时再补 `Source Data Fig1–4.xlsx`。

## 5. 中文核对

- 声明里写的是「仓库 tag v1.0」，没有写不存在的 DOI；如果学校要求 DOI，先做 Zenodo 归档。
- 第三方航图未随仓库分发，只写来源；不要写成「已公开」以免版权争议。
- 邮箱只放 `18778383063@163.com`，未放手机号。
