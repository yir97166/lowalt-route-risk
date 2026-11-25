# 参考文献核验报告（2026-11-25）

> 对象：技术报告 v1.0 的 11 条参考文献（`report/refs.bib`）。
> 方法：先用 Crossref `api.crossref.org/works/<DOI>` 逐条解析（DOI 可解析性 + 标题/作者/卷期页比对），
> 中文法规/通告与 JARUS 报告用原文 PDF 与政府网公开页核对。
> 结论：**11 条全部可核**；发现 **5 类必须修正**、**5 类建议修正**，已全部写入 `refs.bib` 并重导出报告。

## 1. 汇总

| 等级 | 条数 | 条目 |
|---|---|---|
| ✅ 已核验、无需修改 | 2 | JARUS SORA 2.5（原文 PDF）、Tatem 2017（Crossref） |
| ❌ 必须修正（作者/卷期页/年份） | 7 | Washington、la Cour-Harbo、Primatesta、Bertrand、Li、Feng、Ford |
| ⚠️ 建议核对（年/note/文章号） | 2 | 深公规〔2017〕3号、国务院令第761号 |

## 2. 逐条结果

| # | key | 核验来源 | 发现 | 处理 |
|---|---|---|---|---|
| 1 | jarus2024 | JARUS 官网 PDF（`data/raw/references/`） | 2.5 版 main body draft，2024-02 对外征求意见；标题/机构一致 | 保留，注明 draft |
| 2 | primatesta2019 | Crossref 10.1007/s10846-019-01015-z | 97 卷、3–4 期、489–509 页，作者 3 人一致；缺期号 | 补 `number = {3--4}` |
| 3 | washington2017 | Crossref 10.1016/j.paerosci.2017.10.001 | 95 卷、24–44 页；bib 缺卷/页 | 补 `volume 95`、`pages 24--44` |
| 4 | lacourharbo2018 | Crossref 10.1007/s10846-018-0853-1 | 93 卷、1–2 期、367–384 页；bib 缺卷/期/页 | 补全 |
| 5 | bertrand2023 | Crossref 10.1109/icuas57906.2023.10156086 | 191–198 页；第二作者应为 **Stéphanie Lala**（bib 写成 M.） | 补页；`Lala, M.`→`Lala, S.` |
| 6 | li2021 | Crossref 10.3390/su132313079 | 作者为 **Shan Li, Honghai Zhang, Zhuolun Li, Hao Liu**（bib 首字母全错：X/Y/Y/Y） | 改为 `Li, S.; Zhang, H.; Li, Z.; Liu, H.` |
| 7 | feng2025 | Crossref 10.3390/drones9050320 | 作者为 **Ouge Feng, Honghai Zhang, Weibin Tang, Fei Wang, Dikun Feng, Gang Zhong**（bib 首字母全错） | 改为 `Feng, O.; Zhang, H.; Tang, W.; Wang, F.; Feng, D.; Zhong, G.` |
| 8 | ford2010 | Crossref 10.2514/6.2010-9056 | 作者为 **Andrew Ford, Kevin McEntee**（bib 写成 A. T. Ford / R. J. McEntee）；会议名不全 | 改为 `Ford, A.; McEntee, K.`；booktitle 补全 10th AIAA ATIO |
| 9 | tatem2017 | Crossref 10.1038/sdata.2017.4 | Scientific Data 4:170004（文章号），2017；与 bib 一致 | 保留（文章号即页码） |
| 10 | szgov2017 | 原文 PDF（深公规〔2017〕3号） | 2017-03-14 成文、2017-04-10 公开；bib 原 note「2017-03-14 发布」不精确 | note 改「成文/公开」 |
| 11 | caac2024 | 中国政府网（国令第761号） | **2023-05-31 公布**，2024-01-01 施行；bib 年份写成 2024 | `year = 2023`，note 注明公布/施行 |

## 3. 仍需人工留意

- **GB/T 7714 的文献类型标识**由 CSL 自动生成；JARUS 报告与地方通告分别渲染为 `[R]`、`[A]`，属可接受近似。
- `tatem2017` 的「页码」是文章号 `170004`，不是连续页码，属期刊体例，不是错误。
- 深公规与国务院令均无 DOI，无法用 Crossref 复核，只能以原文/政府网为准；本报告已记录来源。
- 本报告只核**元数据**，不判断文献内容是否支持正文论断（那属于综述与审稿环节）。

## 4. 复核命令

```powershell
.\.venv\Scripts\python.exe - <<'PY'
# 逐条请求 Crossref，比对标题/作者/卷期页
PY
```

原始返回已存 `docs/ref_check_raw.json`（8 条 DOI 的 Crossref message 摘要）。
