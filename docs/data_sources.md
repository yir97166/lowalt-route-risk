# 数据来源与许可

> 最后更新：2026-11-17  
> 原则：只用公开数据；禁飞区为示意，不碰非公开/涉密空域数据。

## 1. 人口栅格

| 来源 | 用途 | 地址 | 许可 | 备注 |
|---|---|---|---|---|
| WorldPop 2020 China 100 m | 地面风险 | https://www.worldpop.org/ | CC BY 4.0 | 首选；文件较大，需裁剪 |
| GHSL 2020 100 m | 备选 | https://ghsl.jrc.ec.europa.eu/ | CC BY 4.0 | WorldPop 下载失败时用 |

裁剪到 `configs/aoi.yaml` 的 bbox；统一 EPSG:4326。

## 2. 地图底图

| 来源 | 用途 | 地址 | 许可 | 备注 |
|---|---|---|---|---|
| OpenStreetMap | 底图/背景 | https://www.openstreetmap.org/ | ODbL | 可用 Overpass Turbo 导出 bbox；不参与路由 |
| Geofabrik | OSM 提取 | https://download.geofabrik.de/ | ODbL | 中国包很大，优先 Overpass |

## 3. 地形（可选）

| 来源 | 用途 | 地址 | 许可 |
|---|---|---|---|
| SRTM 30 m / Copernicus DEM | 高程（MVP 不用） | https://portal.opentopography.org/ | 公开 |

MVP 按平地处理；若后续加地形，单独开 issue，不阻塞主线。

## 4. 禁飞/敏感区

- 文件：`configs/aoi.yaml` 的 `no_fly` 段。
- 机场净空保护区：官方尺寸（跑道中线两侧各 10 km、端外 20 km），来源为
  深圳市公安局《关于加强深圳机场净空区域安全保护的通告》深公规〔2017〕3 号，
  以及 AIP 深圳宝安 2A-1（ARP N22°38.3′ E113°48.7′、跑道 3400×45 / 3800×60、
  磁方位 156°/336°、磁差 3.0°W）。模型中按**受控/需审批**处理，不当硬禁飞。
- 另外 2 个多边形（梧桐山、深圳水库）是手工示意，**illustrative only**。
- 本项目的空域数据不可用于真实飞行；真实运行以民航局/地方政府现行公告为准，
  本项目不采集非公开数据。

## 5. 坐标系统

- 输入/输出：WGS84（EPSG:4326）。
- 距离计算：UTM 49N（EPSG:32649）；深圳跨 49/50 带，本项目范围小，误差可忽略。
- 不要混用 GCJ-02/BD-09（高德/百度坐标），否则地图会偏移。

## 6. 数据降级

- 下载失败：`scripts/make_synthetic_data.py` 生成合成人口栅格。
- 报告中必须标注「真实数据版」或「合成数据版」。
- 合成数据只用于跑通 pipeline，不用于结论外推。
