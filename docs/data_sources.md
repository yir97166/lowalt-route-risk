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
- 内容：宝安机场 5 km 缓冲 + 2 个示意多边形。
- 性质：**illustrative only**，不是官方禁飞区，不可用于真实飞行。
- 若需真实数据：以民航局/地方政府公布的临时空域/禁飞公告为准，本项目不采集非公开数据。

## 5. 坐标系统

- 输入/输出：WGS84（EPSG:4326）。
- 距离计算：UTM 49N（EPSG:32649）；深圳跨 49/50 带，本项目范围小，误差可忽略。
- 不要混用 GCJ-02/BD-09（高德/百度坐标），否则地图会偏移。

## 6. 数据降级

- 下载失败：`scripts/make_synthetic_data.py` 生成合成人口栅格。
- 报告中必须标注「真实数据版」或「合成数据版」。
- 合成数据只用于跑通 pipeline，不用于结论外推。
