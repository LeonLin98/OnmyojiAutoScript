# OAS 日常配置記錄

陰陽師 OnmyojiAutoScript 兩台真機的日常配置永久版本記錄。

## 結構：JSON 分開，HTML 一個

```
oas-daily-config/
  README.md                     本檔
  build.py                      生成器（可重跑）
  vN/
    daily-template.json         pair.html 的 DAILY 模板快照
    i18n-zh-CN.json             OAS 官方任务中文名映射（来自 module/config/i18n）
    raw/
      qingcui.json              清脆真機 config 原文（抓取證據）
      suolong.json              索隆真機 config 原文
    qingcui-daily.json          ★ 清脆日常（獨立一份）
    suolong-daily.json          ★ 索隆日常（獨立一份）
    qingcui-drift.json          清脆 日常 vs 真機 差異
    suolong-drift.json          索隆 同上
    qingcui-deployed.json       清脆真機實測（scheduler 段）
    suolong-deployed.json       索隆同上
    qingcui-meta.json           清脆版本資訊
    suolong-meta.json           索隆同上
    daily.html                  ★ 單一報告，左右並列對比兩台（淺色）
```

**兩份 `*-daily.json` 各自獨立、互不含對方設定。** `daily.html` 只是把兩份渲染到同一頁，方便對照。

## 兩台機器

| 名稱 | VM | IP | 手機 | ADB serial | JSON |
|---|---|---|---|---|---|
| 清脆 qingcui | VM106 | 192.168.250.241 | OnePlus5 | `823c342e` | `qingcui-daily.json` |
| 索隆 suolong | VM103 | 192.168.250.240 | K30U | `jzypu4mbbum79lyh` | `suolong-daily.json` |

兩台 OAS 各自獨立（VM / 手機 / ADB / 22288 端口互不相干），同刻執行不互搶。

## 為什麼要有這個

日常配置分散在三個地方，容易說不清「現在到底應該是什麼」：

| 位置 | 性質 | 說明 |
|---|---|---|
| `pair.html` 的 `DAILY` 模板 | **意圖態** | 按「還原」時會寫回真機的值 |
| 真機 `config/*.json` | **實際態** | 部署結果，可能因按鈕操作而偏離 |
| Agent 改動 | 動作 | 同時寫入上面兩處，不是獨立的第三份數據 |

本記錄存的是**合成的日常定義**（`*-daily.json`），另存真機實測（`*-deployed.json`）與差異（`*-drift.json`）作為排查依據。

## ★ 核心規則

1. **`*-daily.json` 是唯一真源。升版本號只看它有沒有變。**
2. **`next_run` 一律不記錄** —— 滾動值，每天不同，記了只會製造假差異。
3. **部署失敗不升版本。** 只更新 `*-deployed.json` 與 `*-drift.json`。
4. **`*-drift.json` 空 = 部署成功；非空 = 排查入口。**
5. **按鈕任務取模板值，其餘取真機值** —— 詳見下節。

## 取值規則

還原按鈕只覆蓋 4 個任務（`ryou_toppa` / `orochi` / `bondling_fairyland` / `realm_raid`），
其餘 52 個任務它不碰。所以：

- **這 4 個任務** → 取 `pair.html` 的 `DAILY` 模板值（還原按鈕寫回什麼，日常就是什麼）
- **其餘 52 個任務** → 取真機值（真機即日常）

## 排查流程

```
vN/<機器>-daily.json（應該是什麼）
        vs
真機實測（實際是什麼）
        ↓
   <機器>-drift.json 的差分
        ↓
   哪個環節把值改壞了
```

| drift 情況 | 含義 | 處理 |
|---|---|---|
| 空 | 部署成功，真機 = 日常 | 無需動作 |
| 有差異 | 部署失敗 / 被按鈕臨時改過 | 看欄位歸屬哪個任務 |
| 真機有模板外的額外值 | 模板漏覆蓋 | 補模板，升版本 |

### 按鈕任務的漂移是預期的

按鈕跑完後真機會偏離日常（燈變黃），**按「還原」後才恢復**。
抓 drift 的時機很重要：**應該在「按還原之後、沒按任何按鈕」時抓**，
否則 drift 全是按鈕造成的臨時值，沒有排查價值。

### 任務中文名來源

全部取 OAS **官方** i18n（`module/config/i18n/zh-CN.json` + `assets/i18n/zh-CN.json`），
不是我自創的譯名。56 個任務段中 55 個有官方中文。

唯一例外 `orochi_moans` 標為「御魂·悲鳴（占位段）」並加 <span>空佔位</span> 標記 ——
它是上游留下的空段：沒有任何配置字段，也不在 `script_menu` 的可運行清單裡，只有一個空的 scheduler。

### `friend_1` 會出現另一台的名字

那是跨號好友名（清脆的 `friend_1` = 索隆的遊戲角色名），屬本機 config 的真實值，
不是把另一台的設定混進來。

## 版本歷史

| 版本 | 日期 | 摘要 |
|---|---|---|
| [v1](v1/daily.html) | 2026-10-26 | 首次基線。清脆 56 任務（啟用 11）、索隆 56 任務（啟用 10）。 |

## 更新方式

```bash
# 1. 抓兩台真機 config 到 vN/raw/
# 2. 抽 pair.html 的 DAILY 到 vN/daily-template.json
# 3. 生成
python3 build.py --version vN --date 2026-MM-DD --captured "2026-MM-DDT..:..:..+08:00"
```

升不升版本，看 `*-daily.json` 有沒有實質變化（換任務 / 改時刻 / 改次數 / 改陣容）。
只是重新部署驗證 → 版本號不動，只更新 `*-deployed.json` 與 `*-drift.json`。
