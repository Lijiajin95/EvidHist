<!-- SPDX-License-Identifier: CC-BY-NC-SA-4.0 -->

# 明代史料開放來源與許可核查（中文維基文庫與商業資料庫之外）

日期：2026-10-13（Asia/Shanghai）。
核查人：EvidHist 研究 agent（受託執行來源與許可核查）。
適用的專案口徑：[《史料来源与许可指南》](../source-licensing-guidance.md)第 2 節（可選途徑）與第 5 節（每份材料的登記欄位）。

> **本文不是法律意見。** 本文只記錄在本次核查時點、以本機網路位置實際讀到的官方條款文字與檢索結果，不對任何具體材料作出可用性、合法性或侵權與否的結論。條款頁面會被修改；本文引用的每一條都附實際讀到的 URL 與讀取方式，但**未做第三方公證留存或雜湊快照**。涉及授權範圍爭議時，以權利人書面答覆或專業法律意見為準。
>
> **本文回答的是「有沒有這些書」與「條款怎麼寫」，不是「能不能用」。** 第七節按用途逐項標註 `允許` / `不允許` / `未明確` / `需另行授權`，依據是引用的條款原文；「未明確」一律照寫「未明確」，不以推測填空。

---

## 0. 核查方式、工具與成敗總覽

### 0.1 使用的工具

| 工具 | 具體做法 |
| --- | --- |
| `curl` | 跟隨重定向（`-L`）、壓縮（`--compressed`）、桌面瀏覽器 User-Agent、`Accept-Language: zh-CN,zh;q=0.9,ja;q=0.8,en;q=0.7`、逾時 25–45 秒。用於抓取條款頁、robots.txt、授權檔與 API 回應。 |
| 正文抽取 | 對抓回的 HTML 移除 `<script>` / `<style>` 後抽取純文字，人工比對關鍵條款措辭。 |
| 官方 API | Internet Archive `advancedsearch.php` / `metadata/<id>`；NDL Search OpenSearch（`ndlsearch.ndl.go.jp/api/opensearch`）；Wikimedia Commons MediaWiki API（`action=query`、`list=search`、`prop=imageinfo|revisions`）；Hugging Face Hub API；Zenodo REST API。 |
| Wayback Machine | 僅在**現行頁面已改為 JS 客戶端渲染、curl 讀不到正文**時使用（Internet Archive Terms of Use、Kanripo 站點頁腳）。使用處均明確標註為 Wayback 快照，並附快照 URL。 |

### 0.2 讀到了什麼、沒讀到什麼（失敗清單）

**成功讀到正文的官方頁面**（逐條原文見後續各節）：

- `https://archive.org/robots.txt`（200）
- `https://archive.org/developers/`、`https://archive.org/developers/bots.html`、`https://archive.org/developers/ias3.html`（200）
- `https://help.archive.org/help/rights/`（200）
- `https://web.archive.org/web/20230601000000/https://archive.org/about/terms.php`（200，Wayback 快照）
- `https://dl.ndl.go.jp/robots.txt`、`https://www.ndl.go.jp/robots.txt`（200）
- `https://www.ndl.go.jp/copy/copyright`、`https://www.ndl.go.jp/sitepolicy/terms`、`https://www.ndl.go.jp/use/digital_transmission`、`https://www.ndl.go.jp/use/digital_transmission_individuals`（200）
- `https://ndlsearch.ndl.go.jp/help/api`（200）
- `https://ndlsearch.ndl.go.jp/api/opensearch?title=…`（200；大量重複查詢後觸發 429，見失敗清單）
- `http://www.nlc.cn/web/dsb_footer/bqsm/index.shtml`（200）
- `http://read.nlc.cn/`（200）、`http://read.nlc.cn/allSearch/searchList?...`（200，伺服器端渲染，無需登入）
- `https://library.harvard.edu/about/policies/harvard-library-cc-copyright-policy`（200）
- `https://library.harvard.edu/robots.txt`（200）
- `https://www.wul.waseda.ac.jp/kotenseki/`、`.../about.html`、`.../html/`（200）
- `https://www.waseda.jp/library/user/using-images/`（200）
- `https://ctext.org/robots.txt`（200）
- `https://commons.wikimedia.org/robots.txt`、`https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia`（200）
- `https://foundation.wikimedia.org/wiki/Policy:User-Agent_policy`（200）
- `https://www.loc.gov/robots.txt`、`https://www.loc.gov/legal/`（200）
- `https://www.wul.waseda.ac.jp/robots.txt`（**404，即不存在**）、`http://read.nlc.cn/robots.txt`（**404**）、`http://www.nlc.cn/robots.txt`（**404**）、`https://www.ndl.go.jp/robots.txt` 存在（內容見 3.5）
- `https://hanchi.ihp.sinica.edu.tw/ihp/hanji.htm`（200）、`https://newarchive.ihp.sinica.edu.tw/`（200）、`https://newarchive.ihp.sinica.edu.tw/robots.txt`（200）
- `https://www.shuge.org/robots.txt`（200）
- `https://huggingface.co/datasets/kltng/mingshilu-web` 及其 `README.md`、`manifest.json`（200）

**抓取失敗、明確記錄為「未能核實」**：

| 目標 | 結果 | 失敗性質 |
| --- | --- | --- |
| `https://www.kanripo.org/`（及 `/catalog`） | **403**，回應本文只有 `Just a moment...` | Cloudflare 人機驗證。**未讀到現行站點條款**。另經 `github.com/kanripo/krp-docs` 官方頁面得知站點自 2026-02-05 起硬體故障停機（原文見 1.4）。 |
| `https://archive.org/about/terms.php`、`/about/`、`/terms` | **200 但只有 1,951 bytes 的 JS 外殼** | 純客戶端渲染，`curl` 與工具型抓取都只拿到 `<app-root></app-root>` 與「Javascript is required for this site」。**現行 Terms of Use 正文未讀到**；本文引用的是 Wayback 快照（被快照頁面自身標註日期為「31 Dec 2014」）。 |
| `https://curiosity.lib.harvard.edu/chinese-rare-books`、`/catalog?q=…`、`/catalog.json?q=…` | **202**，回應長度 **0 bytes** | 反爬（`202 Accepted` 空回應）。**哈佛善本門戶的館藏內容完全未核實**。 |
| `https://iiif.lib.harvard.edu/robots.txt`、`https://iiif.lib.harvard.edu/manifests/drs:123` | **429** | 速率限制。 |
| `https://www.hathitrust.org/robots.txt`、`/policies/`、`babel.hathitrust.org` 檢索 | **403**，回應本文 `Just a moment...` | Cloudflare 人機驗證。**HathiTrust 全部未核實**。 |
| `https://www.loc.gov/search/`、`https://www.loc.gov/books/`（`fo=json`） | **403** | 本機網路位置被拒。LoC 的自動化檢索未核實；只有 `robots.txt` 與 `/legal/` 讀到。 |
| `https://ctext.org/faq`、`/terms`、`/tools/api`、`/ming` | **403**，回應為 ctext.org 自製的「Access unavailable」頁 | 站點依來源網路位置封鎖。**CTEXT 的條款頁與書目頁均未讀到**；只讀到 403 封鎖頁本身的文字與 `robots.txt`。 |
| `https://www.shidianguji.com/zh/user-agreement` 等 7 個候選條款路徑 | 一律 **200**，但內容是「抱歉，您訪問的頁面不存在···」 | 前端路由 catch-all（SPA），無法用狀態碼區分存在與否。**條款正文未讀到**。 |
| `https://data.ihp.sinica.edu.tw/` | 連線失敗（curl exit 000） | 站點不可達。 |
| `https://blog.kanripo.org/` | 連線失敗（curl exit 000） | 站點不可達。 |
| `https://ndlsearch.ndl.go.jp/api/opensearch` 追加 `dpid=` 過濾條件的查詢 | 反覆 **429** | 速率限制。**「NDL 數位館藏中是否有明代史料」未能用 API 窮盡核實**，只能依官方頁面自述與既有檢索結果推斷（見 3.2、3.6）。 |
| `https://www.wul.waseda.ac.jp/kotenseki/search/`、`.../html/list.html` | **404** | 早稲田古典籍庫沒有公開的站內檢索端點可供腳本查詢；只能逐頁瀏覽資料一覽。 |

---

## 1. 總表：來源 × 是否有書 × 文本或影像 × 授權 × 可否自動化

**記法**：`有` = 本次以官方檢索或官方倉庫實際命中；`無` = 官方目錄/檢索明確查無；`未核實` = 抓取失敗，不做推測。
「可自動化」只描述**技術與站點規則層面**（有無官方 API／`robots.txt` 是否允許／有無明確禁止爬取條款），**不等於授權允許**。

| # | 來源 | 《明實錄》 | 《大明會典》 | 《國榷》 | 其他目標書 | 文本／影像 | 授權（條款事實） | 可自動化 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | **Kanseki Repository 漢籍リポジトリ**（含 GitHub `kanripo/*`） | **無**（官方目錄 `KR2b` 編年類無此書） | **有**，但為**弘治本《明會典》180 卷**（KR2m0010），非萬曆 228 卷本 | **無** | 《明一統志》90 卷（KR2k0008）**有**；《皇明通紀》《萬曆起居注》《崇禎長編》**無** | **純文字**（`.txt`，含 `<pb:…>` 頁面標記） | 站點頁腳：`CC BY SA`（**未標版本**，且見 1.3 的範圍限制）；**GitHub 倉庫內查無 LICENSE 檔** | 可（`git clone` / `raw.githubusercontent.com`）。現行 `www.kanripo.org` 因伺服器故障＋Cloudflare 而不可用 |
| 2 | **Internet Archive** | **有**：`mingshilu` 單一條目，43 冊 PDF，**含《崇禎長編》《崇禎實錄》《明熹宗七年都察院實錄》與各朝《寶訓》**；另有 `_djvu.txt`／`_hocr.html` OCR | **有**：`02088024.cn`–`02088136.cn` 等 **113 冊**（申時行等修，萬曆本，CADAL／北京大學圖書館掃描） | 同名條目 **無** | 《皇明通紀法傳全錄》25 冊**有**；《大明一統志》**無**（只有《欽定大清一統志》）；《萬曆起居注》**無** | **兩者都有**：掃描 PDF ＋ 機器 OCR 文字層 | **條目層面 `licenseurl` / `rights` / `possible-copyright-status` 全部為空**（逐條實測，見 2.3）。站點條款要求使用者自負其責 | 技術上可（官方 API、S3-like、`ia` CLI）；官方有明確的 User-Agent 與速率要求（見 2.4） |
| 3 | **Wikimedia Commons**（本次新發現，非使用者列出的候選） | **有**：`NLC892-*` 國圖數字古籍掃描（《大明實錄》等）；`SSID-*` **中央研究院歷史語言研究所校印本《明實錄 附校勘記》** | **有**：`CADAL02088*` **113 冊 djvu**（與 IA 第 2 項同批掃描） | **有**：`NLC892-411999016504-*`《國榷》多冊 | 《大明一統志》**有**（`NLC892-411999032705-*`）；《皇明通紀集要》**有**、《崇禎長編》**僅見於《痛史》第 13–14 冊**；《萬曆起居注》**查無** | **影像為主**（PDF／DjVu）；`SSID` 系列為中研院校印本掃描 | 檔案頁標示 `Public domain`、`PD-old-100-expired` / `PD-scan (PD-old-100-expired)` / `PD-old` / `CC-PD-Mark`。**這是 Commons 貢獻者的著作權判斷，不是權利人聲明**（見 8.2） | 技術上高度可（MediaWiki API＋官方 dumps）；受 WMF User-Agent 政策約束 |
| 4 | **日本国立国会図書館デジタルコレクション** | **未能核實**（見 3.6）。NDL Search 命中的《明實錄》為**中央研究院歴史語言研究所 1962 校印本紙本**，無數位館藏連結 | 未能核實 | 未能核實 | 未能核實 | （若確有則為影像） | 站點內容：PDL 1.0；「インターネット公開」為全文影像公開，「図書館送信」限館內且**明文不得以電子檔取得影像**（見 3.3、3.4） | **不宜**：`dl.ndl.go.jp/robots.txt` 明文 `Disallow: /api/`，僅放行 `/api/iiif/` |
| 5 | **中國國家圖書館·中華古籍資源庫**（`read.nlc.cn`） | **有**：《明太宗實錄》《明宣宗實錄》《明宣宗皇帝實錄 一百十五卷》《明世宗肅皇帝實錄 五百六十六卷》《明熹宗實錄 八十七卷》等（免登入可檢索） | **有** | **有**（談遷撰，多筆） | 《崇禎長編》《大明一統志》《皇明通紀》《萬曆起居注》**皆有**命中 | **掃描影像** | 《版权声明》明文禁止未經書面許可的「數據採集、網絡爬蟲或類似…行為」（原文見 5.3） | **不可**：站點條款明文禁止；`robots.txt` 不存在（404） |
| 6 | **Harvard Library Chinese Rare Books** | **未核實** | 未核實 | 未核實 | 未核實 | — | 政策頁讀到（CC BY **不含**館藏書籍與數位館藏影像）；館藏條目權利欄位因抓取失敗未讀到 | 未核實（門戶以 `202` 空回應阻擋腳本） |
| 7 | **早稲田大学古典籍総合データベース** | 抽樣**未見** | 未見 | 未見 | 未見 | 影像 | 站點明文：「無斷…使用することは一切認めておりません」；申請豁免僅限「半分以下の翻刻」等（見 7.3） | 未有明文禁止爬取的 robots；但**再利用須申請**，且無官方 API |
| 8 | **CTEXT 中國哲學書電子化計劃** | 未核實（403） | 未核實 | 未核實 | 未核實 | — | 403 頁（由 ctext.org 自身發出）明文「**嚴禁使用自動下載軟体**」；`robots.txt` 對 GPTBot／ia_archiver 等 `Disallow: /` | **不可** |
| 9 | **識典古籍（shidianguji.com）** | 首頁書庫**列出《明实录》**（標為「抄本」） | 未見於首頁清單 | 未見 | 未見 | 未核實 | **條款正文未讀到**（SPA；多個候選路徑都回「頁面不存在」） | 未核實；`robots.txt` 只封 `/profile`、`/passport`、部分 `/api/...` |
| 10 | **中研院史語所：漢籍全文資料庫（Scripta Sinica）** | 未能核實是否收《明實錄》 | 未能核實 | 未能核實 | — | 純文字 | 頁面自述「**訂購需求**」；「引用本網站資源，請註明資料出處。」 | 不可（訂購制、無公開 API） |
| 11 | **中研院史語所：內閣大庫檔案／明清檔案工作室** | — | — | — | 明清檔案（原件遠溯至明代，主體為清代） | 影像 | 「一般讀者可免費瀏覽包含『後設資料』之目錄；**註冊後取得帳號之讀者可進入影像資料庫**」；頁尾「© Copyright All rights reserved」 | **不可**：`newarchive.ihp.sinica.edu.tw/robots.txt` 為 `User-agent: * / Disallow: /` |
| 12 | **Hugging Face `kltng/mingshilu-web`** | **有**（SQLite 全文＋FTS 索引，411 MB） | 無 | 無 | 無 | 純文字（衍生自《明實錄》之整理資料庫，含 CBDB 實體連結） | **卡上沒有任何 `license` 欄位**（實測 front-matter 只有 `pretty_name` 與 `tags`）。**未標示授權 ≠ 授權** | 技術上可（Hub API／range request） |
| 13 | **HathiTrust** | 未核實（403 Cloudflare） | 未核實 | 未核實 | 未核實 | — | 未核實 | 未核實 |
| 14 | **Library of Congress** | 未核實（API 403） | 未核實 | 未核實 | 未核實 | — | `/legal/` 讀到速率要求與封鎖權；`robots.txt` `Disallow: /search` | 未核實；官方明示多媒體物件**並非全部**公版，需逐件看權利欄位 |
| 15 | **書格 shuge.org** | 未逐頁核 | 未逐頁核 | 未逐頁核 | 未逐頁核 | 多為 PDF 影像 | 只讀到 `robots.txt`（`Crawl-delay: 10`、`Disallow: /dl/`）；條款頁未逐頁核實 | 未核實（且 `/dl/` 被 robots 封） |

### 1.1 總表之外、但必須先講的三個結論

1. **《明實錄》在「明確開放授權」的來源裡，本次只找到三條路**：(a) Wikimedia Commons 的 `NLC892-*` 國圖掃描與 `SSID-*` 中研院校印本（標 PD，但判斷人是 Commons 貢獻者）；(b) Internet Archive 的 `mingshilu` 條目（**無任何授權標示**）；(c) Hugging Face 的 `kltng/mingshilu-web`（**無任何授權標示**）。
2. **《國榷》《大明一統志》《皇明通紀》的「有＋標示 PD」組合，本次只在 Wikimedia Commons 的 `NLC892-*` 系列出現**；Internet Archive 與 Kanripo 都沒有《國榷》。
3. **《大明會典》228 卷（萬曆重修本）在 Kanripo 沒有**：Kanripo 的 KR2m0010 是**弘治十年（1497）本、180 卷**，卷數與專案需求（228 卷）不符，屬不同版本，不能互相替代登記。

---

## 2. Internet Archive（archive.org）

### 2.1 機構與入口

- 站點：<https://archive.org/>
- 條目檢索 API：`https://archive.org/advancedsearch.php`
- 條目 metadata API：`https://archive.org/metadata/<identifier>`
- 開發者入口：<https://archive.org/developers/>

### 2.2 內容範圍（實測）

以 `advancedsearch.php` 逐項查詢（`--data-urlencode` 帶引號中文標題，避免分詞汙染）：

| 查詢 | `numFound` | 備註 |
| --- | --- | --- |
| `title:("大明會典")` | **113** | identifier `02088024.cn` … `02088136.cn`，collection 為 `universallibrary`，sponsor 為 `China-America Digital Academic Library (CADAL)`，`scanningcenter`／`contributor` 為「北京大學圖書館」，creator 為「(明)申時行等修」 |
| `creator:("申時行")` | **114** | 比上一項多一筆 `02081819.cn`《召對錄》 |
| `title:("皇明通紀")` | **25** | `0207992x.cn`–`0207994x.cn`，書名為《皇明通紀法傳全錄(一)…(二十二)》 |
| `title:("明實錄")`（繁體） | **0** | — |
| `title:("明实录")`（簡體） | 8（其中 1 筆為目標） | `mingshilu` 條目名稱即簡體「明实录」 |
| `title:("國榷")` / `title:("国榷")` | **0 / 0** | — |
| `title:("崇禎長編")` / `title:("崇祯长编")` | **0 / 0** | 但《崇禎長編》**存在於 `mingshilu` 條目的附錄中**（見下） |
| `title:("大明一統志")` | **0** | `title:("一統志")` 的 194 筆全部是《欽定大清一統志》 |
| `title:("萬曆起居注")` | **0** | — |
| `identifier:02088*` | 1003 | CADAL／北大掃描的整批古籍（含《欽定大清會典事例》《國朝宮史續編》等） |
| `identifier:nlc-892*` | **8,059** | 由 Wikimedia Commons 備份的國圖「數字古籍」影像（見 2.2.3） |

#### 2.2.1 `mingshilu` 條目（《明實錄》）的實際內容

以 `https://archive.org/metadata/mingshilu` 讀到的 metadata：

```
identifier = mingshilu
title      = 明实录
mediatype  = texts
collection = opensource
uploader   = qixumusic@gmail.com
scanner    = Internet Archive HTML5 Uploader 1.7.0
publicdate = 2026-01-02 05:19:47
ocr        = tesseract 5.3.0-6-g76ae
ocr_parameters = -l eng+chi_sim+HanS
noarchivetorrent = true
curation   = [curator]kaplan@archive.org[/curator][date]20260726062134[/date][state]un-dark[/state]
```

檔案共 **367 個**，其中 **43 個 PDF**，卷次如下（逐字取自檔案清單）：

```
明实录.01.明太祖实录.pdf      … 明实录.13.明熹宗实录.pdf
明实录.14.明太祖实录校勘记.pdf … 明实录.26.明熹宗实录校勘记.pdf
明实录.附录.01.明囗宗囗皇帝实录.pdf
明实录.附录.02.崇祯实录.pdf
明实录.附录.03.明熹宗七年都察院实录.pdf
明实录.附录.04.崇祯长编.pdf
明实录.附录.05.明太祖宝训.pdf … 明实录.附录.17.明熹宗宝训.pdf
```

每個 PDF 另有：`_djvu.txt`（DjVuTXT 純文字）、`_djvu.xml`、`_hocr.html`、`_hocr_searchtext.txt.gz`、`_chocr.html.gz`、`_jp2.zip`、`_page_numbers.json`、`_scandata.xml`。
即：**這一條目同時提供掃描影像與機器 OCR 文字層**，且覆蓋專案最缺的《明英宗實錄》與《崇禎長編》。

> **必須一併登記的版本事實**：檔名中的「校勘記」與「附錄」結構，與**中央研究院歷史語言研究所 1962 年起校印本**的編排一致。該版本含現代學者的校勘成果。此條目的 metadata 中**沒有任何版本說明、出版者或來源機構欄位**，本次未能核實其掃描底本來源。專案若要使用，須把「底本是何版本」列為未知並人工核實。

#### 2.2.2 《大明會典》113 冊

`https://archive.org/metadata/02088105.cn` 讀到：

```
title            = 大明會典(八十二)
creator          = (明)申時行等修
collection       = universallibrary
sponsor          = China-America Digital Academic Library (CADAL)
scanningcenter   = 北京大學圖書館
contributor      = 北京大學圖書館
description      = ['原書有些字跡不清、有些頁殘', '古籍']
ppi              = 600
imagecount       = 152
```

檔案含 `02088105.cn.pdf`、`_djvu.txt`、`_hocr.html`、`_chocr.html.gz`、`_tif.zip`、`_cnbook.zip`。
卷次編號自「一」連續至「一百十三」（本次以 `sort=identifier asc` 取全部 113 筆並解析書名括號內卷次確認）；**未逐冊核對頁數與缺頁**。

#### 2.2.3 `nlc-892-*`：由 Wikimedia Commons 備份的國圖掃描

共 **8,059** 筆（另有 45 筆 `nlc-wenxian-*` 為《文獻》期刊，與明代史料無關）。以 `nlc-892-001932324-328889` 為例，metadata 讀到：

```
description = <p>中國國家圖書館「數字古籍」影像，經 Wikimedia Commons 備份。</p>…
licenseurl  = https://creativecommons.org/publicdomain/mark/1.0/
rights      = Public domain — the same determination as for this file on Wikimedia Commons (see source).
source      = https://commons.wikimedia.org/wiki/File%3ANLC892-001932324-328889_…
uploader    = archive@linshuang.info
subject     = ['古籍','Chinese rare books','National Library of China','數字古籍']
```

以 `identifier:nlc-892*` 加標題過濾實測這批備份的明代史料覆蓋：

| 過濾 | `numFound` | 命中示例 |
| --- | --- | --- |
| `title:(明實錄)` | 20 | 全部是**《明季實錄》**（顧炎武），非《明實錄》 |
| `title:(會典)` | 2 | 《會典鈔略》 |
| `title:(國榷)` | **0** | — |
| `title:(一統志)` | **0** | — |
| `title:(皇明通紀)` | **0** | — |

→ **IA 上的國圖備份這一批，實際上不含專案最需要的《明實錄》《國榷》《大明一統志》《皇明通紀》。** 這些書只在 **Wikimedia Commons 的 `NLC892-*`** 中（見第 4 節），該批掃描數量更大。

### 2.3 逐項授權狀態（重點）

| 條目 | `licenseurl` | `rights` | `possible-copyright-status` | 授權狀態事實 |
| --- | --- | --- | --- | --- |
| `mingshilu`（《明實錄》） | **無此欄位** | **無此欄位** | **無此欄位** | **未標示任何授權**；collection 為 `opensource`（社群上傳區），uploader 為個人信箱 |
| `02088136.cn`（大明會典 一百十三） | `None` | `None` | `None` | 未標示任何授權；sponsor 為 CADAL |
| `02079927.cn`（皇明通紀法傳全錄 四） | `None` | `None` | `None` | 未標示任何授權；sponsor 為 CADAL |
| `nlc-892-001932324-328889` | `https://creativecommons.org/publicdomain/mark/1.0/` | `Public domain — the same determination as for this file on Wikimedia Commons (see source).` | — | **有明確 PD 標示，但判斷來源是 Wikimedia Commons 的貢獻者，不是國圖或 IA** |

`universallibrary` 集合自身的 metadata 只有專案沿革說明（Carnegie Mellon 的 Million Books Project、印度／中國／埃及政府出資掃描、IA 做自動轉換），**沒有任何授權或權利狀態欄位**。

### 2.4 條款原文引用

**（a）Terms of Use。** 現行 `https://archive.org/about/terms.php` 只回傳 JS 外殼（1,951 bytes），本次**未能讀到現行正文**。以下引用自 Wayback 快照
`https://web.archive.org/web/20230601000000/https://archive.org/about/terms.php`（快照頁面自身標註日期「31 Dec 2014」）：

> “Access to the Archive's Collections is provided at no cost to you and is granted for scholarship and research purposes only.”

> “You agree to abide by all applicable laws and regulations, including intellectual property laws, in connection with your use of the Archive. In particular, you certify that your use of any part of the Archive's Collections will be limited to noninfringing or fair use under copyright law.”

> “If a Creative Commons or other license has been declared for particular material on the Archive, to the extent you trust the declaration and declarer (which is rarely the Internet Archive), you may use the content according to the terms and conditions of the applicable license.”

> “Because the content of the Collections comes from around the world and from many different sectors, the Collections may contain information that might be deemed offensive… The Archive does not endorse or sponsor any content in the Collections, nor does it guarantee or warrant that the content available in the Collections is accurate, complete, noninfringing, or legal”

**（b）官方 Rights FAQ。** `https://help.archive.org/help/rights/`（200）逐字：

> “The Internet Archive does not make guarantees as to the copyright status of items on archive.org and cannot guarantee information posted on item details or collection pages regarding copyright or other intellectual property rights. Our Terms of Use require that users make use of the Internet Archive's Collections at their own risk and ensure that such use is non-infringing and in accordance with all applicable laws.”

> “The person who uploads an item often provides information related to use rights, either by way of directly entering it in the description field or by selection of a Creative Commons license. The latter, if included by the uploader, will be viewable via a Creative Commons logo on the details page, which serves as a link to a description of the specific type of license that the uploader has assigned.”

**（c）自動化取得的官方要求。** `https://archive.org/developers/bots.html`（200，標題「Bots, LLMs, and Automated Access」）逐字：

> “All automated requests to archive.org must include a descriptive User-Agent header that identifies: The tool or bot name; Version number; For AI agents: the model being used (e.g., `claude-sonnet-4-20250514`)”

> “Automated tools should respect rate limits: Add delays between requests for bulk operations; Honor 429 Too Many Requests responses and Retry-After headers; Use `--checksum` flags to avoid re-downloading/re-uploading unchanged files; Consider using GNU Parallel with `-j` to limit concurrent requests”

**（d）`robots.txt`（實測原文，`https://archive.org/robots.txt`，200）：**

```
Sitemap: https://archive.org/sitemap/sitemap.xml

##############################################
#
# Welcome to the Internet Archive!
#
##############################################

User-agent: *
Disallow: /control/
Disallow: /report/
```

→ 檢索與 metadata API 路徑**未被 robots 封鎖**。

### 2.5 逐用途授權表（Internet Archive）

| 用途 | 判定 | 條款依據 |
| --- | --- | --- |
| 存儲 | **未明確** | 站點條款不禁止下載；但「scholarship and research purposes only」＋「noninfringing or fair use」把判斷責任推給使用者。條目本身無授權標示 |
| 解析／OCR | **未明確** | 同上；OCR 成果另生新檔案，權利狀態未在任何條款中處理 |
| 檢索 | **未明確** | 同上 |
| 公開展示 | **未明確（高風險）** | 條款只授權「scholarship and research purposes」；公開展示是否落在其內，條款未寫 |
| 再分發 | **未明確（高風險）** | 未標示授權的條目，條款未授予再分發權；FAQ 明示 IA 不保證權利狀態 |
| 模型訓練 | **未明確** | 條款未提及；`bots.html` 只規定 User-Agent 與速率，不是內容授權 |
| 自動化取得（技術層） | **允許（附條件）** | `bots.html` 要求識別性 User-Agent、尊重 429／Retry-After、加延遲；`robots.txt` 未封檢索路徑 |

### 2.6 未核實事項（Internet Archive）

- 現行（非 Wayback 快照）Terms of Use 正文。
- `mingshilu` 條目的掃描底本版本與來源機構（metadata 無此欄位）。
- 《大明會典》113 冊是否完整覆蓋 228 卷、有無缺冊缺頁。
- IA 是否有本次未命中的《國榷》《大明一統志》《萬曆起居注》（本次以標題精確查詢為 0，但可能存在標題變體）。

---

## 3. 日本国立国会図書館デジタルコレクション（dl.ndl.go.jp）

### 3.1 機構與入口

- 數位館藏：<https://dl.ndl.go.jp/>
- 圖書館整體利用說明入口：<https://www.ndl.go.jp/use>
- NDL Search（跨庫檢索，含 OpenSearch API）：<https://ndlsearch.ndl.go.jp/>

### 3.2 內容範圍（實測）

以官方 OpenSearch API 查 `title=<書名>`，逐筆檢查是否存在指向 `dl.ndl.go.jp` 的數位館藏連結：

| 查詢 | `totalResults` | 與數位館藏相關的命中 |
| --- | --- | --- |
| `title=明實錄`（首次，`cnt=200`） | 1,142（每次抽樣 200 筆） | 200 筆中，**《明憲宗實録》《明世宗實録》《明英宗實録校勘記》等均為 `中央研究院歴史語言研究所` 出版、`dcterms:issued=[1962]` 的紙本書目**，`<category>図書</category><category>紙</category>`，**無 `dl.ndl.go.jp/pid/…` 連結** |
| `title=國榷` | 14 | **0 筆**指向數位館藏 |
| `title=大明一統志` | 238 | 1 筆疑似（`大明一統志通考`，為現代書目）；**無明代《大明一統志》數位化** |
| `title=皇明通紀` | 27 | **0 筆**指向數位館藏 |
| `title=大明會典` / `title=崇禎長編` / `title=萬曆起居注` | — | 查詢觸發 **429**，**未能核實** |

單筆明細示例（`https://ndlsearch.ndl.go.jp/api/opensearch?title=明實錄`）：

```
<title>明英宗實録校勘記 /</title>
<dcndl:seriesTitle>明實録 / 中央研究院歴史語言研究所校 ; 74-75</dcndl:seriesTitle>
<dc:publisher>中央研究院歴史語言研究所,</dc:publisher>
<dcterms:issued>[1962]</dcterms:issued>
<category>図書</category><category>紙</category>
```

### 3.3 「インターネット公開」與「図書館送信」的官方區別

`https://www.ndl.go.jp/use/digital_transmission`（200，標題「図書館向けデジタル化資料送信サービス」）逐字：

> 「図書館向けデジタル化資料送信サービス（図書館送信）は、国立国会図書館のデジタル化資料のうち、絶版等の理由で入手が困難な資料を全国の公共図書館、大学図書館等（当館の承認を受けた図書館に限ります。）の館内で利用できるサービスです。」

> 「国立国会図書館がデジタル化した資料は、国立国会図書館デジタルコレクションに収録して提供しています。著作権保護期間が満了した資料、著作権者の許諾を得た資料等については、インターネットを通じて本文の画像を公開しており、どなたでも自宅のパソコン等から利用することができます。インターネットに公開していないデジタル化資料のうち、絶版等の理由で入手困難な資料については、デジタル化資料送信サービスで利用することができます」

> 「※閲覧できる場所は、図書館の施設内に限られます。また、ご自身で持ち込んだパソコンなどではご利用になれません。」

> 「※デジタル化資料の画像を電子ファイルで入手することはできません。」

**同一頁的古典籍範圍自述（對本案直接相關）：**

> 「古典籍　明治期以降の貴重書等や**清代後期以降の漢籍等**　約2万点」

→ 官方自述的漢籍主體是**清代後期以降**，與專案要的明代史料時段不符。這是本次能取得的、最接近「NDL 數位館藏有無明代史料」的一手線索；但它是**送信服務清單**的說明，不等於「デジコレ完全沒有明代史料」，故 3.6 仍列為未核實。

### 3.4 站點內容授權與二次利用

**（a）NDL 網站內容利用規約。** `https://www.ndl.go.jp/sitepolicy/terms`（200，標題「国立国会図書館ウェブサイトのコンテンツ利用規約」）逐字：

> 「国立国会図書館ウェブサイト（ndl.go.jpドメイン及びkodomo.go.jpドメインで提供するウェブサイト。以下特に記載がない限り同じ。）で公開している情報（書誌データ等を含む。以下総称して「コンテンツ」といいます。）は、別の利用ルールが適用されるコンテンツを除き、公共データ利用規約（第1.0版）（以下「PDL1.0」といいます。）に準拠した利用条件の下で、利用することができます。」

> 「第三者が著作権を有するコンテンツや、別の利用ルールが適用されるコンテンツについては、次に掲げる「国立国会図書館ウェブサイトのコンテンツの利用に係るPDL1.0に関する重要情報」を参照してください。」

> 「（1）画像、写真、文書ファイル等のうち、国立国会図書館以外の著作者名の表記があるもの…」

> 「３ 合意管轄について　本利用規約によるコンテンツの利用及び本利用規約に関する紛争については、東京地方裁判所を、第一審の専属的な合意管轄裁判所とします。」

→ **這是 ndl.go.jp 網站內容的規則**（PDL 1.0）；同一頁明示數位館藏內的第三方著作物與另有規則的內容除外，須依各服務案內。**這條不能直接套到デジコレ的資料影像上。**

**（b）著作權注意事項。** `https://www.ndl.go.jp/copy/copyright`（200）逐字：

> 「著作権が保護される期間は、個人の著作物の場合は、原則として創作のときから「著作者の死後70年を経過するまで」（著作権法第51条）、また、団体名義の著作物の場合は原則として「その著作物の公表後70年を経過するまで」（著作権法第53条）です。」

> 「著作権保護期間内である「著作物の一部分」を超えて複写する場合や調査研究目的以外（掲載等の二次利用目的等）で複写する場合は、複写申込みに加えて、著作権者の許諾を得た旨が記載された許諾書の提出が必要です。」

**（c）NDL Search API 的利用條件。** `https://ndlsearch.ndl.go.jp/help/api`（200）逐字：

> 「（1）営利企業・団体の方　営利目的でのご利用にあたるため、利用申請が必要です。ただし、データ提供機関があらかじめ利用目的を問わず利用を許諾しているデータについては、利用申請・許諾は不要です。」

> 「（2）個人・非営利団体等の方　データ利用により収益を得ない場合　データを利用することにより、収益を得ない場合は、営利目的にあたらないため、利用申請は不要です。」

> 「（3）継続的にアクセスを行われる方　継続的にアクセスを行われる場合、API利用実態の把握のために、事前の利用申請の要否にかかわらずNDLサーチAPI利用申請フォームよりご連絡先、ご利用内容等をお知らせいただけますようご協力をお願いします。」

> 「（2）クレジットの表示　本APIを利用するサイトやアプリケーションには、NDLサーチのAPIを用いていることを明記してください。」

> 「（1）大量アクセスに関するご注意　サーバへの過負荷を避けるため、同時リクエスト数には制限を設けています。また、特定のサーバから継続して大量のアクセスがある場合は、アクセスを遮断する等の措置を行う場合があります。※アクセス数の上限につきましては…具体的な数値の目安をお示しすることができません。」

### 3.5 robots.txt 實測原文

`https://dl.ndl.go.jp/robots.txt`（200）：

```
# robots.txt for dl.ndl.go.jp

# すべてのUser-agent 向けのルール
User-agent: *

# 検索結果画面はクロールさせない
Disallow: /search
Disallow: /search/
Disallow: /ja/search
Disallow: /ja/search/
Disallow: /en/search
Disallow: /en/search/
# デジコレはコレクション検索画面もクロールさせない
Disallow: /collections/
Disallow: /ja/collections/
Disallow: /en/collections/

# ログインページはクロールさせない
Disallow: /login
…（/ja/login、/en/login 同理）…

# 管理者ページはクロールさせない
Disallow: /manage
…

# 公開調査検索結果ページはクロールさせない
Disallow: /openinq/search
…

# マイコレクションページはクロールさせない
Disallow: /mycollection
…

# APIはすべてクロールさせない(ただしデジコレIIIFはクロールさせる)
Disallow: /api/
Allow: /api/iiif/

Sitemap: https://dl.ndl.go.jp/sitemap.xml
```

`https://www.ndl.go.jp/robots.txt`（200，全文）：

```
User-agent: *
Allow: /

Sitemap: https://www.ndl.go.jp/sitemap.xml
```

### 3.6 逐用途授權表（NDL）

| 用途 | 判定 | 條款依據 |
| --- | --- | --- |
| 存儲（**インターネット公開** 資料） | **未明確** | 「著作権保護期間が満了した資料、著作権者の許諾を得た資料等については、インターネットを通じて本文の画像を公開しており、どなたでも自宅のパソコン等から利用することができます。」——只說「利用」，未逐一列出存儲／再分發 |
| 存儲（**図書館送信** 資料） | **不允許** | 「※デジタル化資料の画像を電子ファイルで入手することはできません」「※閲覧できる場所は、図書館の施設内に限られます」 |
| 解析／OCR | **未明確** | 站點條款未提及 OCR；送信服務明文不得取得電子檔 |
| 檢索 | **允許（網站內容）／未明確（資料影像）** | 網站內容依 PDL1.0；資料影像「別の利用ルールが適用されるコンテンツ」被排除在 PDL1.0 之外 |
| 公開展示 | **未明確** | 未見針對「インターネット公開」資料的公開展示專門條款；`/copy/copyright` 對「掲載等の二次利用目的」要求著作權者許諾書，但那是**複寫服務**的規則，不能直接套用於線上公開資料 |
| 再分發 | **未明確** | 同上 |
| 模型訓練 | **未明確** | 站點條款未提及 |
| 自動化取得（技術層） | **部分允許、部分不允許** | `Disallow: /api/`（僅 `Allow: /api/iiif/`）、`/search` 與 `/collections/` 皆被 Disallow。以 API 或搜尋結果頁批次抓取**不符 robots 規則** |

### 3.7 未核實事項（NDL）

- **デジコレ是否確有《明實錄》《大明會典》《國榷》等明代史料數位化**：本次 API 追加過濾條件的查詢一律 429，未取得結論。已知的《明實錄》命中都是 1962 年中研院校印本紙本書目。
- デジコレ各筆資料在閱讀器上顯示的「利用條件」文字（站點為 Vue SPA，`/ja/terms`、`/ja/help` 都只回 JS 外殼；未以瀏覽器實際開啟）。
- NDL 是否另有「古典籍資料」專門二次利用頁（本次以 sitemap 全域搜尋 `secondary|tenzai|fukukoku` 未找到對應 URL）。

---

## 4. Wikimedia Commons（本次新發現，開放授權路徑最完整）

> 這一節不在委託清單內，但它是本次核查中**唯一同時具備「有書」＋「檔案頁明確標示公版」＋「有官方 API 與 dumps」**的來源，對專案最關鍵，故單獨成節。

### 4.1 機構與入口

- 站點：<https://commons.wikimedia.org/>
- 查詢 API：`https://commons.wikimedia.org/w/api.php`
- 再利用指引：<https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia>
- WMF User-Agent 政策：<https://foundation.wikimedia.org/wiki/Policy:User-Agent_policy>

### 4.2 內容範圍（以 MediaWiki API 實測）

以 `action=query&list=search&srnamespace=6`（File 命名空間）查詢：

| 查詢 | `totalhits` | 命中示例（逐字取自 API 回傳標題） |
| --- | --- | --- |
| `明實錄` | 4,972 | `File:SSID-10485587 明實錄 明英宗實錄 13-20.pdf`、`File:SSID-13484294 明實錄 附校勘記 65 明神宗實錄 光宗實錄.pdf`、`File:SSID-12446616 明實錄 明神宗實錄 卷413-449.pdf` |
| `大明會典` | 62,893 | `File:CADAL02088026 大明會典（三）.djvu`、`File:CADAL02088113 大明會典（九十）.djvu`、`File:CADAL02000148 大明會典（五）.djvu` |
| `NLC892 明實錄` | 862 | `File:NLC892-411999022616-39297 大明實錄 第9冊.pdf`、`File:NLC892-411999030882-146624 明季實錄 第1冊.pdf` |
| `NLC892 國榷` | 105 | `File:NLC892-411999016504-32835 國榷 第10冊.pdf`、`File:NLC892-0263-207277 國榷 第3冊.pdf` |
| `NLC892 大明一統志` | 393 | `File:NLC892-411999032705-164508 大明一統志 第9冊.pdf`、`File:NLC892-412000000085-23205 大明一統志 第6冊.pdf` |
| `NLC892 皇明通紀` | 64 | `File:NLC892-411999004536-104725 皇明通紀集要 第16冊.pdf` |
| `NLC892 崇禎長編` | **2** | `File:NLC892-312002011573-362802 痛史 第14冊.pdf`、`…362801 痛史 第13冊.pdf`（即《崇禎長編》只以《痛史》叢書子目形式出現） |
| `NLC892 萬曆起居注` | **0** | — |
| `NLC892`（總量） | 236,665 | 國圖「數字古籍」整批 |

**三個子系列要分開登記：**

| 子系列 | 前綴 | 對應的紙本 | 授權模板 |
| --- | --- | --- | --- |
| 國圖數字古籍 | `NLC892-*` | 中國國家圖書館藏（`Digitized Ancient Books in the National Library of China`） | `{{PD-scan\|PD-old-100-expired}}` |
| CADAL | `CADAL02088*`、`CADAL020001*` | 北京大學圖書館藏，CADAL 掃描（`Scans from the China Academic Digital Associative Library`） | `{{PD-old}}` |
| SSID | `SSID-*` | **中央研究院歷史語言研究所校印本**《明實錄 附校勘記》 | `{{PD-scan}}`（分類含 `PD-scan (PD-old)`） |

### 4.3 條款與授權標示原文

**（a）國圖系列模板。** `Template:Digitized Ancient Book in the National Library of China` 逐字（節錄）：

```
 |Source           = 
                     {{Institution:National Library of China|1=collapse}}
                     ({{NLC-Book-Link|{{{dbid|892}}}|{{{bookid}}}|catid=10024|text=中華古籍資源庫 數字古籍}})
                     <!-- batch at Sep 2022: 20k+ books / ? volumes-->
…
<includeonly>
== {{int:license-header}} ==
{{PD-scan|PD-old-100-expired}}
</includeonly>
```

**（b）檔案頁的授權欄位（`extmetadata` 實測）：**

`File:NLC892-411999016504-32835 國榷 第10冊.pdf`：

```
LicenseShortName = Public domain
UsageTerms       = Public domain
Artist           = 〔明〕談遷撰
Credit           = National Library of China
Categories       = Images with watermarks|Books with Wikidata item|國榷|PD-old-100-expired|
                   PD-scan (PD-old-100-expired)|CC-PD-Mark|
                   Digitized Ancient Books in the National Library of China|…
```

`File:NLC892-411999032705-164508 大明一統志 第9冊.pdf`：

```
LicenseShortName = Public domain
Artist           = 〔明〕李賢 萬安等纂修
Categories       = …|PD-old-100-expired|大明一統志|PD-scan (PD-old-100-expired)|CC-PD-Mark|
                   Digitized Ancient Books in the National Library of China|Images with watermarks|…
```

`File:NLC892-411999004536-104725 皇明通紀集要 第16冊.pdf`：

```
LicenseShortName = Public domain
Artist           = 〔明〕陳建撰
Categories       = …|PD-old-100-expired|PD-scan (PD-old-100-expired)|CC-PD-Mark|…
```

`File:CADAL02088026 大明會典（三）.djvu`：

```
LicenseShortName = Public domain
UsageTerms       = Public domain
Artist           = （明）申時行等修
Credit           = Peking University
Categories       = 大明會典|Books with Wikidata item|PD Old|CC-PD-Mark|
                   Scans from the China Academic Digital Associative Library|…
wikitext 模板     = {{Book}} {{China Academic Digital Associative Library link|02088026}} {{Institution:Peking University}} {{PD-old}}
```

`File:SSID-10485587 明實錄 明英宗實錄 13-20.pdf`：

```
LicenseShortName = Public domain
Artist           = 中共研究院历史语言研究所      ←（原文如此，疑為「中央研究院」誤植）
Categories       = Files with no machine-readable source|Books with Wikidata item|PD Old|明實錄|
                   PD-scan (PD-old)|CC-PD-Mark|Scans with a SSID|
                   PD-old missing SDC copyright status|…
wikitext 模板     = {{Book}} {{PD-scan}}
```

**（c）Commons 再利用指引。** `https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia`（200）逐字：

> “This page is intended for those who wish to reuse material (text and/or graphics) from Wikimedia Commons — on their own website, in print, or otherwise.”

> “All images on Commons should be reusable but… each may have different requirements for crediting a photographer, linking a license, etc.”

### 4.4 robots.txt 實測

`https://commons.wikimedia.org/robots.txt` 回 200（17,713 bytes，標準 MediaWiki robots，未逐一貼出；實測未阻擋 `w/api.php`）。

### 4.5 逐用途授權表（Wikimedia Commons）

| 用途 | 判定 | 條款依據 |
| --- | --- | --- |
| 存儲 | **允許** | 檔案頁 `Public domain` / `PD-old-100-expired` / `PD-scan`；Commons 明示所有檔案「should be reusable」 |
| 解析／OCR | **允許（就掃描件本身）** | 同上。**但 OCR 產出的文字層是新生成果，其權利狀態不在 Commons 檔案頁的聲明範圍內** |
| 檢索 | **允許** | 同上 |
| 公開展示 | **允許（附姓名標示等條件依個別授權）** | 「each may have different requirements for crediting…」；PD 標示者無姓名標示義務 |
| 再分發 | **允許** | 同上 |
| 模型訓練 | **未明確** | 檔案頁的 PD 標示處理的是著作權，未就訓練另設條款；WMF User-Agent 政策只規範技術識別 |
| 自動化取得（技術層） | **允許（附條件）** | WMF User-Agent 政策（見 4.6）；`robots.txt` 未封 API |

### 4.6 WMF User-Agent 政策原文

`https://foundation.wikimedia.org/wiki/Policy:User-Agent_policy`（200）逐字：

> “As of February 15, 2010, Wikimedia sites require a HTTP User-Agent header for all requests. … The rationale is, that clients that do not send a User-Agent string are mostly ill behaved scripts that cause a lot of load on the servers, without benefiting the projects.”

### 4.7 未核實事項（Wikimedia Commons）

- **PD 判斷的正當性未經權利人確認**：`NLC892-*` 的 `PD-old-100-expired`、`CADAL02088*` 的 `PD-old`、`SSID-*` 的 `PD-scan` 都是 **Commons 貢獻者依其判斷掛上的模板**。國圖、北大圖書館、中研院史語所**均未在這些檔案頁上出具授權聲明**。
- **`SSID-*` 系列風險最高**：其 Artist 欄寫「中央研究院历史语言研究所校印」，即 1962 年校印本。該本含現代校勘成果；用 `{{PD-scan}}`（掃描件本身無新權利）處理**不等於**處理了校勘記與整理成果的權利。本次**未找到**任何來自中研院的授權聲明。
- **`NLC892-*` 檔案分類含 `Images with watermarks`**：影像帶有浮水印，未核實浮水印的性質與可否去除。
- 各書是否卷冊齊全、有無缺頁，未逐冊核對。

---

## 5. 中國國家圖書館·中華古籍資源庫（read.nlc.cn）

### 5.1 入口與可訪問性

- 讀者雲門戶：<http://read.nlc.cn/>（200，內容 1.5 MB）
- 檢索端點（伺服器端渲染，**無需登入**）：`http://read.nlc.cn/allSearch/searchList?searchType=10024&showType=1&pageNo=1&searchWord=<關鍵詞>`
- 古籍資源庫分類入口：`searchType=10024`（數字古籍）

**實測結果：無需登入即可檢索並取得書目與責任者資訊。** 首頁可見 2021-11-24 的〈国家图书馆关于部分古籍数字资源库免登录访问的通告〉：

> 「为进一步方便读者使用，我馆将国家图书馆读者云门户平台部分古籍类资源（包括东文研汉籍影像库、法藏敦煌遗书、哈佛大学善本特藏、天津图书馆古籍、云南图书馆古籍、上海图书馆家谱、**数字古籍**、赵城金藏…等20个资源库）的服务方式调整为免登录访问。」

### 5.2 內容範圍（實測）

`searchWord` 逐項查詢，回傳結果頁每頁 12 筆書目（本次僅取第 1 頁，未逐頁翻完）：

| 關鍵詞 | 命中書目示例（逐字取自結果頁） |
| --- | --- |
| 明實錄 | 《明太宗實錄》（(明)張輔、楊士奇等纂修）、《明宣宗實錄 一百十五卷》、《明宣宗皇帝實錄 一百十五卷》、《明世宗肅皇帝實錄 五百六十六卷》、《明熹宗實錄 八十七卷》（(明)溫體仁[等]修）、《明季實錄》（(清)顧炎武／題(明)顧炎武輯）、《皇明獻實》（(明)袁袠撰）、《明長陵碑錄》 |
| 大明會典 | 有命中（責任者欄為空，疑為原書未題） |
| 國榷 | **有**，責任者「(明)談遷撰」，多筆 |
| 崇禎長編 | 有命中（結果頁混入《(明)李自滋,劉萬春纂修》與《（清）倦圃老人撰》等他書，需逐筆辨識） |
| 大明一統志 | 有命中 |
| 皇明通紀 | **有**，責任者「(明)陳建撰」「(明)陳建撰@@@(明)高汝栻撰」 |
| 萬曆起居注 | 有命中（同頁混入《(唐)溫大雅撰》之《大唐創業起居注》） |

書目頁連結形如：

```
http://read.nlc.cn/allSearch/searchDetail?searchType=10024&showType=1&indexName=data_892&fid=411999016504
```

→ **內容覆蓋是本次所有來源中最完整的**（七部目標書全有，且多為多版本）。但存取與再利用受下列條款限制。

### 5.3 條款原文引用

`http://www.nlc.cn/web/dsb_footer/bqsm/index.shtml`（200，標題「版权声明」）逐字：

> 「您在使用中国国家图书馆·中国国家数字图书馆网站（下称"本网站"）各项产品及服务之前，请务必仔细阅读本声明。…访问、浏览或使用本网站，表明您已阅读、理解并同意以下条款内容，并遵守所有适用的法律法规。如果您不同意以下任何条款，请停止浏览、使用本网站。」

> 「一、著作权声明　本网站发布的所有自建的或与他人共同开发的信息和内容，包括但不限于标识、图文、音频、视频、网站版式、网页设计等各项内容，除特别注明外，相关作品的著作权均为国家图书馆所有。任何单位或个人未经事先书面许可，均不得将以上内容用于任何商业用途，未经许可用于商业用途或非法目的而侵害我馆合法权益甚至影响我馆声誉的，我馆保留依法追究其法律责任的权利。如需使用相关资料，请提前与我馆相关部门联系（联系邮箱：webmaster@nlc.cn）。」

> 「二、网站内容的使用和修改　任何单位或个人在以转载、引用、摘编、下载等方式使用本网站内容时，均须注明作者，并标明内容的出处为"中国国家图书馆·中国国家数字图书馆网站"或"https://www.nlc.cn/"。**未经国家图书馆或相关权利人的书面许可，不得修改所使用的内容，也不得进行侵犯或可能侵犯国家图书馆权益的数据采集、网络爬虫或类似的数据收集以及数据摘录等行为。**」

> 「四、不保证声明　本网站力图提供准确的信息和内容，但我馆并不对本网站所载的信息和内容，包括但不限于图文、数据、观点、建议、网页等的准确性、完整性、充分性和可靠性作出保证，也不对所载信息和内容作出任何明示或默示的、包括但不限于有关权利、质量和没有计算机病毒的保证。」

> 「本声明之修改权和最终解释权均属国家图书馆所有。」

### 5.4 robots.txt 實測

- `http://read.nlc.cn/robots.txt` → **404**（不存在）
- `http://www.nlc.cn/robots.txt` → **404**（不存在）

→ 沒有 robots 規則；但**站點條款明文禁止爬蟲**。依專案既有口徑（[許可指南](../source-licensing-guidance.md)第 3 節：「遵守 robots.txt、控制請求頻率只是採集規則，不能替代內容使用許可」），robots 不存在**不構成**授權。

### 5.5 逐用途授權表（NLC）

| 用途 | 判定 | 條款依據 |
| --- | --- | --- |
| 存儲 | **未明確**，且自動化取得本身被禁止 | 條款只允許「以轉載、引用、摘編、下載等方式使用」並須註明出處；同時禁止「數據採集、網絡爬蟲或類似…行為」 |
| 解析／OCR | **不允許（未經書面許可）** | 「未經國家圖書館或相關權利人的書面許可，不得修改所使用的内容」 |
| 檢索 | **未明確** | 條款未就「檢索」單獨表態；但站內檢索為其服務本身 |
| 公開展示 | **未明確（須書面許可）** | 「如需使用相關資料，請提前與我館相關部門聯繫」 |
| 再分發 | **不允許（未經書面許可）** | 同上；商業用途明文禁止 |
| 模型訓練 | **不允許（未經書面許可）** | 資料採集／數據摘錄被明文禁止 |
| 自動化取得（技術層） | **不允許** | 「不得進行侵犯或可能侵犯國家圖書館權益的數據採集、網絡爬蟲或類似的数据收集以及數據摘錄等行為」 |

### 5.6 未核實事項（NLC）

- 單一書目頁（`searchDetail`）的閱讀器是否需登入、是否提供整本下載（本次只取到檢索結果頁）。
- 各書的卷冊完整性與版本細節。
- 是否有官方 API 或機構合作授權管道（條款只留 `webmaster@nlc.cn`）。

---

## 6. Harvard Library Chinese Rare Books

### 6.1 入口

- 善本門戶：<https://curiosity.lib.harvard.edu/chinese-rare-books>
- 版權政策：<https://library.harvard.edu/about/policies/harvard-library-cc-copyright-policy>

### 6.2 內容範圍：**完全未能核實**

實測（curl，桌面 UA）：

| URL | 結果 |
| --- | --- |
| `https://curiosity.lib.harvard.edu/robots.txt` | **202**，0 bytes |
| `https://curiosity.lib.harvard.edu/chinese-rare-books` | **202**，0 bytes |
| `https://curiosity.lib.harvard.edu/chinese-rare-books/catalog?q=明實錄` | **202**，0 bytes |
| `https://curiosity.lib.harvard.edu/chinese-rare-books/catalog.json?q=明實錄` | **202**，0 bytes |
| `https://curiosity.lib.harvard.edu/chinese-rare-books/catalog.json?q=大明會典` | **202**，0 bytes |
| `https://iiif.lib.harvard.edu/manifests/drs:123` | **429**，0 bytes |

→ **本次沒有讀到哈佛善本門戶的任何館藏資料**。依方法要求，此處不做任何推測：**哈佛是否有《明實錄》《大明會典》《國榷》等，本次未核實。**

### 6.3 版權政策原文引用（政策頁本身 200，可讀）

> “We evaluate copyright before making collections material available online. When possible, we provide rights information in catalog records, finding aids, and other information that accompanies collections or items. **However, we do not guarantee the accuracy of that information. It is the user's obligation to evaluate rights issues in light of their own use.** The Library makes no express or implied warranty to others who wish to use the content on its web pages. Transmission or reproduction of protected items beyond that allowed by copyright exceptions such as fair use or by specific agreement requires the permission of the copyright owner.”

> “Many of the Harvard Library web pages are labeled and available under a Creative Commons Attribution 4.0 License (CC BY). **When a Harvard Library page is labeled as "CC BY," the license applies to textual content written by Harvard Library staff as part of their employment**, where the President and Fellows of Harvard College holds the copyright, as described more fully below.”

> “**The following material appearing on a Harvard Library web page displaying the CC BY icon is not included:** … **Articles, letters, books, and other works of authorship that are part of our collections or licensed resources** … **Photographs, images, sound recordings, audiovisual works, software, and any other non-textual content, unless any such item of non-textual content bears its own CC BY icon. Hence, for example, images in our digital collections are excluded unless they separately bear the CC BY icon.** … Content on pages **without** a CC BY icon is **not** licensed under the CC BY license.”

> “The users of any web page content may not suggest or imply that Harvard Library endorses, approves of, or participated in their projects. Harvard's name may not be used in the title or the name of any product or work, and may not be used as a metadata search term or as part of a website name or web address, or be large or prominent.”

→ **與委託提示一致的關鍵點已由官方頁面證實**：CC BY 只覆蓋哈佛圖書館員撰寫的**頁面文字**，**不覆蓋館藏書籍與數位館藏影像**（除非該影像自己另掛 CC BY 圖示）。

### 6.4 robots.txt 實測

- `https://curiosity.lib.harvard.edu/robots.txt` → 202 空回應（非標準 robots 回應，**未取得內容**）
- `https://library.harvard.edu/robots.txt` → 200，內容為 Drupal 標準 robots：`User-agent: *` 下 `Disallow: /core/`、`Disallow: /profiles/`、`Disallow: /admin/`、`Disallow: /search/`、`Disallow: /search?`、`Disallow: /user/register` 等；**未封一般內容頁**。

### 6.5 逐用途授權表（Harvard）

| 用途 | 判定 | 條款依據 |
| --- | --- | --- |
| 存儲 | **未明確** | 館藏條目的權利欄位未讀到；政策頁明示「不保證資訊正確，判斷責任在使用者」 |
| 解析／OCR | **未明確** | 同上 |
| 檢索 | **未明確** | 同上 |
| 公開展示 | **未明確** | 館藏影像被明文排除在 CC BY 之外 |
| 再分發 | **未明確** | 同上；「Transmission or reproduction of protected items beyond … requires the permission of the copyright owner」 |
| 模型訓練 | **未明確** | 政策頁未提及 |
| 自動化取得（技術層） | **未核實** | 門戶以 202 空回應阻擋腳本；未取得其 robots 規則 |

### 6.6 未核實事項（Harvard）

- 館藏是否含目標書（**必須以瀏覽器人工核實**）。
- 單一館藏條目的 `Usage Rights` / `Rights` 欄位原文。
- 是否提供整本 PDF／影像下載、是否有 IIIF manifest（429 未取得）。
- `curiosity.lib.harvard.edu` 的 robots 規則。

---

## 7. 早稲田大学古典籍総合データベース

### 7.1 入口

- 資料庫：<https://www.wul.waseda.ac.jp/kotenseki/>
- 資料一覽（依請求記號）：<https://www.wul.waseda.ac.jp/kotenseki/html/>
- 圖像利用案內：<https://www.waseda.jp/library/user/using-images/>

### 7.2 內容範圍：抽樣未見明代史料

- 資料一覽共列出 **175 個請求記號群**（`ab`、`bunko01`…`chi01`–`chi13`、`he01`…`wa20` 等）；實測抓取 `chi01`–`chi13` 的 13 個 `index.html` 均為 **200**。
- 這些索引頁**只列內部 ID**（如 `chi01_00556`），不含書名。本次抽樣開啟 6 筆明細頁（`chi01_00556`、`chi03_00770`、`chi06_00005`、`chi09_00136`、`chi12_00104`、`chi13_00261`），**全部是日本古典籍**（如《寺社宝物展閲目録》《玉淵集》《歌舞妓雑談》），**無明代史料**。
- 站內**沒有可腳本查詢的檢索端點**：`https://www.wul.waseda.ac.jp/kotenseki/search/` 與 `https://www.wul.waseda.ac.jp/kotenseki/html/list.html` 均回 **404**；`description.html` 亦為 404。

→ **抽樣未見，但不等於「無」。** 完整判斷需以人工在 175 個分類中逐頁檢視或使用早稲田 OPAC（WINE）。

### 7.3 條款原文引用

**（a）資料庫首頁** `https://www.wul.waseda.ac.jp/kotenseki/`（200）逐字：

> 「このデータベースは、早稲田大学図書館が所蔵する古典籍について、その書誌情報と関連研究資料、さらには全文の画像を、学術研究に資する目的で広く全世界に公開しようとするものです。」

> 「なお、**本データベースに収載された画像、書誌情報等を当館に無断で、テレビ放映、出版物（各種電子媒体を含む）、ホームページ等に使用することは一切認めておりません。**詳しくは当館ホームページの「利用者別案内」をご覧ください。」

**（b）利用者別案内** `https://www.waseda.jp/library/user/using-images/`（200）逐字：

> 「当館の所蔵資料は、学術・教育・文化振興のための使用に限り、出版物への図版掲載、テレビやWeb等放送への使用を許可しています。使用に際しては、事前に申請が必要です。」

> 「◆以下の用途に限り、申請は不要です。
> ・資料1点につき**半分以下の翻刻**。
> ・**研究資料として個人的に手元に保存する場合。**
> ・学校の授業や学会等で、一時的に使用する場合。
> ・卒業論文、修士論文。
> ・学術目的のWebサイトから古典籍総合データベースの画像データへのリンク。この場合、リンク先が「早稲田大学図書館古典籍総合データベース」である旨を明記してください。」

> 「A. 注意・確認事項
> (1) 当館所蔵資料の画像データ等を、**無断で利用することを禁じます**。
> (2) 著作権者等の同意が必要な場合、事前にその許諾を得てください。当館からの使用許可は、著作権者等の同意を前提としています。
> …
> (8) **当館の許可なく、当該画像を加工・改変しての使用は、お断りしています。**」

> 「(5)画像のダウンロードは、保存したい画像を開きカーソルをあわせ、右クリックから「名前を付けて画像を保存」の項目を選ぶことなどで可能です。」

**（c）個別資料頁的頁尾**（如 `https://www.wul.waseda.ac.jp/kotenseki/html/chi01/chi01_00556/index.html`）：

> 「公開者　Copyright 早稲田大学図書館 (Waseda University Library)」
> 「Copyright (C) Waseda University Library, All Rights Reserved.」

### 7.4 robots.txt 實測

`https://www.wul.waseda.ac.jp/robots.txt` → **404**（不存在）。
`https://www.waseda.jp/robots.txt` → 本次未測（非本次抓取主機）。

### 7.5 逐用途授權表（早稲田）

| 用途 | 判定 | 條款依據 |
| --- | --- | --- |
| 存儲 | **個人研究用途允許；其他需另行授權** | 「研究資料として個人的に手元に保存する場合」申請不要；但另「無斷で…使用することを一切認めておりません」 |
| 解析／OCR | **未明確／部分不允許** | 「半分以下の翻刻」申請不要；「當館の許可なく、當該圖像を加工・改変しての使用は、お斷りしています」；OCR 是否算「加工」條款未明示 |
| 檢索 | **未明確** | 條款未單獨表態 |
| 公開展示 | **需另行授權** | 「出版物への図版掲載、テレビやWeb等放送への使用を許可しています。使用に際しては、事前に申請が必要です」；Web 使用需申請且有料金事例 |
| 再分發 | **需另行授權** | 同上；「増補・改訂・転用をおこなう場合、あらためて申請をしてください」 |
| 模型訓練 | **未明確** | 條款未提及 |
| 自動化取得（技術層） | **未明確** | `robots.txt` 不存在；但站點條款對「無斷利用」的限制與自動化與否無關 |

### 7.6 未核實事項（早稲田）

- 全庫是否含明代史料（需人工以 WINE/OPAC 檢索）。
- 是否有 IIIF 端點或官方 API。
- 各資料的權利狀態是否因資料而異。

---

## 8. 其他來源

### 8.1 CTEXT 中國哲學書電子化計劃（ctext.org）

- 入口：<https://ctext.org/>；條款／FAQ：`/faq`、`/terms`；API：`/tools/api`。
- **實測：`/faq`、`/terms`、`/tools/api`、`/ming` 一律回 403**，回應為 ctext.org 自製的封鎖頁。**條款正文與書目頁均未讀到。**
- 但該 403 頁本身的文字是 **ctext.org 第一方發出的陳述**，逐字引用如下（URL：`https://ctext.org/faq`，HTTP 403）：

> 英文：“Access to ctext.org is unavailable from your current location. Please note that **the use of automatic download software on this website is strictly prohibited**.”

> 中文：「很抱歉，暫時無法向您所在網絡位置提供服務。請留意，**本網站嚴禁使用自動下載軟体下載或訪問本站的內容**。」

- `https://ctext.org/robots.txt`（200）要點逐字：

```
User-agent: GPTBot
Disallow: /

User-agent: ChatGPT-User
Disallow: /

User-agent: ia_archiver
Disallow: /

User-agent: GoogleOther
Disallow: /

User-agent: meta-externalagent
Disallow: /

User-agent: Applebot
Disallow: /

User-agent: *
Disallow: /admin
Disallow: /hp.pl

Crawl-delay: 2
```

- **逐用途（僅就讀到的封鎖頁文字）**：存儲／解析／檢索／公開展示／再分發／模型訓練 全部 **不允許或未明確**，且「自動下載軟體」被明文禁止；自動化取得（技術層）**不允許**。
- **未核實**：CTEXT 是否收《明實錄》《大明會典》（因 403 未取得任何書目頁）；其正式版權條款文字。

### 8.2 識典古籍（shidianguji.com）

- 入口：<https://www.shidianguji.com/>。
- 首頁（200，伺服器端渲染）的書庫清單中**逐字列出**：

> 「明实录（明实录）　[明] 《明实录》历朝实录馆 著 · 抄本」

  同頁另有《永樂大典》（嘉靖副本）、《天工開物》、《三命通會》等明代典籍。
  另列出合作專題：「高清影像数据库（第一辑）　合作单位：国家图书馆出版社、北京大学数字人文研究中心」「哈佛燕京数据库　合作单位：哈佛燕京图书馆、北京大学数字人文研究中心」。
- **條款未讀到**：`/zh/user-agreement`、`/user-agreement`、`/zh/agreement`、`/protocol`、`/zh/protocol`、`/about/terms`、`/zh/privacy` **全部回 200 但內容是「抱歉，您访问的页面不存在···」**（前端路由 catch-all），無法用狀態碼判斷。頁面上有「用户协议」「识典古籍隐私政策」字樣但未取得正文。
- `https://www.shidianguji.com/robots.txt`（200）要點：`User-agent: Googlebot/Bingbot/Baiduspider/Bytespider/...` 後列出

```
Disallow: /profile
Disallow: /eden-web-socket-server
Disallow: /api/ancientlib/read/count/volume-version
Disallow: /passport
Disallow: /ttwid
```

  → 未見對一般內容路徑的全面封鎖，但也**沒有** `User-agent: *` 段落，規則結構特殊。
- **逐用途**：全部 **未明確**（無條款正文可依）。
- **未核實**：《明实录》在該站的實際內容（全文？影像？校對狀態？）；授權條款；是否允許批量取得。

### 8.3 中央研究院歷史語言研究所：漢籍全文資料庫（Scripta Sinica）

- 入口：<https://hanchi.ihp.sinica.edu.tw/ihp/hanji.htm>（200）
- 頁面逐字：

> 「『漢籍全文資料庫計畫』的建置肇始於民國七十三年…四十多年來累計收錄歷代典籍已達一千五百八十二種…八億七仟九百八十二萬餘字」

> 「引用本網站資源，請註明資料出處。」

> 「若有錯誤指正、改良建議或**訂購需求**，請寄電子郵件至 hanchi@ihp.sinica.edu.tw」

- **未核實**：是否收《明實錄》等目標書（頁面未列書目清單；「新增書目」為另頁）；授權條款全文。已知事實是**有「訂購需求」字樣，屬需取得資格的資料庫**，且無公開 API。
- 逐用途：**全項未明確／需另行授權**。

### 8.4 中央研究院歷史語言研究所：內閣大庫檔案／明清檔案工作室

- 入口：<https://newarchive.ihp.sinica.edu.tw/>（200）
- 頁面逐字：

> 「中央研究院歷史語言研究所藏「內閣大庫檔案」，係民初由本所輾轉購買…今藏本所的這部分，總數約三十一萬件。本所所藏內閣大庫檔案原件時間遠溯至明代，下抵民初…」

> 「一般讀者可以免費瀏覽包含「後設資料」之目錄；**註冊後取得帳號之讀者可進入影像資料庫**。」

> 「© Copyright　All rights reserved」

- `https://newarchive.ihp.sinica.edu.tw/robots.txt`（200，全文）：

```
User-agent: *
Disallow: /
```

- 逐用途：存儲／解析／檢索／公開展示／再分發／模型訓練 **全項未明確或需另行授權**；自動化取得（技術層）**不允許**（robots 全面 Disallow）。
- 內容以清代檔案為主體（原件上溯明代），**不是**《明實錄》等明代史料的來源。

### 8.5 書格 shuge.org

- `https://www.shuge.org/robots.txt`（200）逐字要點：

```
User-agent: *
Sitemap: https://www.shuge.org/sitemap.xml
Crawl-delay: 10
Disallow: /dl/
Disallow: /wp-admin/
Disallow: /wp-content/plugins/
Disallow: /?s=*
Disallow: /feed
Disallow: /*/*/feed
Disallow: /trackback
Disallow: /*/*/trackback
Disallow: /*.php$
Disallow: /*.css$
Allow: /wp-content/uploads/
Allow: /wp-admin/admin-ajax.php

User-agent: AhrefsBot
Disallow: /
（SemrushBot、Dotbot、MJ12bot、PetalBot 同）
```

- **未核實**：站點條款頁（本次未逐頁核）；是否收目標書。**逐用途全部未明確。**

### 8.6 HathiTrust

- `https://www.hathitrust.org/robots.txt`、`https://www.hathitrust.org/policies/`、`https://babel.hathitrust.org/cgi/ls?q1=明實錄;…` **全部 403**，回應本文為 `Just a moment...`（Cloudflare 人機驗證）。
- **全部未核實**（有無目標書、逐件權利狀態、再利用條款）。

### 8.7 Library of Congress

- `https://www.loc.gov/search/?q=明實錄&fo=json` → **403**（本機網路位置被拒）。**書目未核實。**
- `https://www.loc.gov/robots.txt`（200）逐字要點：

```
User-agent: *
Disallow: /cgi-bin/
Disallow: /web_arch/
…
Disallow: /search
Disallow: /pictures/search
Disallow: /pictures/related
Crawl-Delay: 5

Sitemap: https://www.loc.gov/sitemap.xml
```

- `https://www.loc.gov/legal/`（200）逐字：

> “We reserve the right to block IP addresses that fail to honor our websites' robot.txt files, or submit requests at a rate that negatively impacts service delivery to patrons. **Current guidelines recommend that software programs submit a total of no more than 10 requests per minute to our applications, regardless of the number of machines used to submit requests.** We also reserve the right to terminate programs that require more than 24 hours to complete.”

- 逐用途：**全項未明確**（書目與逐件權利欄位皆未取得）。

### 8.8 Zenodo

- 以 `https://zenodo.org/api/records?q=…` 實測 `q=明實錄`（`total` 14,481）、`q=ming shilu`（`total` 20,428）：**回傳結果與明代史料無關**（分詞把中文查詢打散，命中不相關的現代論文）。**未發現以 CC 授權發布的明代史料語料庫。**
- 逐用途：不適用（無目標材料）。

### 8.9 Hugging Face：`kltng/mingshilu-web`

- 條目：<https://huggingface.co/datasets/kltng/mingshilu-web>（200）
- 內容（取自 `manifest.json` 與 dataset card）：4 個 SQLite 檔，共 **411 MB**：
  `text.sqlite3` 96,833,536 B（`entry` ＋ contentless FTS5 索引）、`ents.sqlite3` 100,052,992 B（`entity_link`、`link_candidate`、人物與官職權威表）、`meta.sqlite3` 16,756,736 B、`one.sqlite3` 196,882,432 B。
  card 逐字：

> 「SQLite databases for a static browser client that reads them over HTTP range requests. There is no loader script: the files are meant to be range-read, not downloaded whole.」
> 「Edition: `mingshilu-web-e1` · date: `2026-09-04`」
> 「`cbdb_id` values and `entity_link.authority = 'cbdb'` are authority identifiers used to join the entity tables.」

- **授權：dataset card 的 front-matter 只有 `pretty_name` 與 `tags`，沒有 `license` 欄位**（實測 `https://huggingface.co/api/datasets/kltng/mingshilu-web` 的 `cardData` 亦無 `license`）。→ **未標示授權**。
- 逐用途：**全項未明確**（無授權欄位可依）。技術上可自動化取得（Hub API／range request）。

### 8.10 其他查過但無收穫的線索

- 日本国立公文书馆：已在專案既有文件 [ming-dynasty-sources-2026-10-12.md](ming-dynasty-sources-2026-10-12.md) 第 2.1 節記錄，本次未重複核查。
- `https://data.ihp.sinica.edu.tw/`：連線失敗（curl exit 000）。
- `https://blog.kanripo.org/`：連線失敗（curl exit 000）。

---

## 9. 逐用途彙總對照

只列「有書」的來源。**空白＝本次未核實，非「允許」。**

| 來源 | 存儲 | 解析／OCR | 檢索 | 公開展示 | 再分發 | 模型訓練 | 自動化取得 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Kanseki Repository**（純文字） | 未明確（站點 CC BY SA，未標版本；GitHub 倉庫無 LICENSE 檔） | 未明確 | 未明確 | 未明確 | 未明確 | 未明確 | 允許（`git clone`；但現行站點停機） |
| **Internet Archive** `mingshilu` / 大明會典 | 未明確 | 未明確 | 未明確 | 未明確 | 未明確 | 未明確 | 允許（附 UA 與速率條件） |
| **Internet Archive** `nlc-892-*`（僅《明季實錄》《會典鈔略》） | 允許（PD Mark 1.0） | 允許（掃描件） | 允許 | 允許 | 允許 | 未明確 | 允許（附條件） |
| **Wikimedia Commons** `NLC892-*`／`CADAL*`／`SSID-*` | 允許 | 允許（掃描件；OCR 成果另計） | 允許 | 允許 | 允許 | 未明確 | 允許（附 WMF UA 政策） |
| **NDL デジコレ**（インターネット公開） | 未明確 | 未明確 | 未明確 | 未明確 | 未明確 | 未明確 | 不允許（`Disallow: /api/`、`/search`、`/collections/`） |
| **NDL デジコレ**（図書館送信） | 不允許 | 不允許 | 不允許 | 不允許 | 不允許 | 不允許 | 不允許 |
| **NLC 中華古籍資源庫** | 未明確（自動化取得被禁） | 不允許 | 未明確 | 未明確（須書面許可） | 不允許 | 不允許 | 不允許（條款明文禁爬蟲） |
| **早稲田古典籍**（若有目標書） | 個人研究用途允許 | 未明確 | 未明確 | 需另行授權 | 需另行授權 | 未明確 | 未明確（無 robots；無 API） |
| **CTEXT** | 不允許／未明確 | 同 | 同 | 同 | 同 | 同 | 不允許（明文禁自動下載） |
| **識典古籍** | 未明確 | 未明確 | 未明確 | 未明確 | 未明確 | 未明確 | 未核實 |
| **HF `kltng/mingshilu-web`** | 未明確（無授權欄位） | 未明確 | 未明確 | 未明確 | 未明確 | 未明確 | 允許（Hub API） |

---

## 10. 按可行性排序的建議

排序依據：**（1）是否真的有關鍵書；（2）授權條款是否白紙黑字允許再利用；（3）是否可自動化取得並留下可核查的許可快照。** 這不是法律結論，是「先做哪一項人工許可核查」的優先序。

### 第一順位：Wikimedia Commons（`NLC892-*` / `CADAL02088*` / `SSID-*`）

**理由**：本次唯一同時滿足「有《國榷》《大明一統志》《皇明通紀集要》＋《大明會典》113 冊＋《明實錄》（含中研院校印本附校勘記）」、「檔案頁有明確的公版標示」、「有官方 API 與標準授權欄位可留快照」、「`robots.txt` 未封 API」四項的來源。

**要先人工確認的三件事（依重要性）**：
1. **`SSID-*` 系列的底本與權利人**：Artist 欄寫「中央研究院历史语言研究所校印」。需向中研院史語所確認 1962 年校印本與其校勘記的權利狀態，以及是否同意以 PD 方式流通。**這一項沒有解決前，不建議把 `SSID-*` 的《明實錄》納入語料。**
2. **國圖（`NLC892-*`）與北大圖書館（`CADAL*`）對掃描件的態度**：Commons 的 PD 模板是社群判斷。需以專案名義發函（國圖 `webmaster@nlc.cn`；CADAL 有 `China Academic Digital Associative Library link` 模板可查聯繫方式）確認「不主張掃描件的新權利」。
3. **浮水印**：`NLC892-*` 分類含 `Images with watermarks`；確認浮水印性質與可否在處理副本中去除。

### 第二順位：Kanseki Repository 的《明一統志》與《明會典》（KR2k0008／KR2m0010）

**理由**：**純文字**、有四庫全書文淵閣版底本標記（`BASEEDITION WYG`、`SOURCE` 行有卷頁）、可用 `git clone` 取得、站點頁腳有 `CC BY SA` 聲明。對專案「優先取得可用文本」的需求最直接。

**要先人工確認的三件事**：
1. **「CC BY SA」的版本與範圍**：站點只寫 `CC BY SA`，**未標 3.0/4.0**，也寫的是「作成されたコンテンツ」。需向 Kanripo 維護者確認 (a) 版本、(b) 是否涵蓋四庫全書底本的全文轉錄、(c) 是否含未來新增資料。**目前 `www.kanripo.org` 因硬體故障停機，正好是發信時機。**
2. **GitHub 倉庫缺 LICENSE 檔**：`KR-Catalog`、`KR1a0001`、`KR2k0008`、`KR2m0010` 的倉庫根目錄都只有內容檔與 `.gitignore`，**沒有 LICENSE**。依 [許可指南](../source-licensing-guidance.md)第 3 節「沒有許可證時，默認版權規則仍適用」，站點頁腳聲明與倉庫實況不一致，須以書面釐清。
3. **BY-SA 與專案文件授權的相容性**：依 [許可指南](../source-licensing-guidance.md)第 6 節，引入 BY-SA 內容後，含該部分的成果不能直接改以 CC BY-NC-SA 發布。這會影響專案未來公開查詢時的授權安排，需在引入前決定。

### 第三順位：Internet Archive 的 `mingshilu`（《明實錄》＋《崇禎長編》）

**理由**：內容最貼近專案缺口（43 冊含《明英宗實錄》與《崇禎長編》），**同時提供掃描件與 tesseract OCR 文字層**，且有官方 API。

**但它是風險最高的一項**：條目**沒有任何授權欄位**，collection 是社群上傳區，uploader 是個人信箱，且檔名結構指向 1962 年中研院校印本。**在確認底本與權利狀態前，只建議作為「人工核對用的掃描件」，不作為文本語料來源。**

### 第四順位：中國國家圖書館·中華古籍資源庫（內容最全，但需走書面授權）

**理由**：七部目標書全有命中，且免登入可檢索。但《版權聲明》**明文禁止數據採集與網絡爬蟲**，也沒有 robots 可供技術規避（robots 不存在不等於授權）。

**唯一合理路徑是機構合作**：以「個人研究、未來可能公開查詢」為由，依條款留的 `webmaster@nlc.cn` 提出書面申請，明確列出存儲／OCR／檢索／公開展示／再分發／模型訓練的範圍。**在取得書面答覆前，不應以腳本採集。**

### 明確不建議優先投入的

- **NDL デジコレ**：`Disallow: /api/`（除 IIIF）；且官方自述其漢籍主體是清代後期以降。除非人工在瀏覽器上確實找到「インターネット公開」的明代史料，否則投入產出比低。
- **CTEXT**：站點明文禁止自動下載，且本次 403 完全無法核實內容。
- **HathiTrust／Library of Congress**：本次全部因 403 未核實，需換網路環境或人工瀏覽器處理。
- **中研院漢籍全文資料庫／內閣大庫**：訂購制或註冊制＋`robots.txt` 全面 Disallow。

---

## 11. 本次未能核實的事項（總清單）

| # | 未核實事項 | 原因 |
| --- | --- | --- |
| 1 | NDL デジコレ是否確有明代史料數位化 | API 追加過濾條件一律 429；站點為 SPA，搜尋頁被 robots 封 |
| 2 | NDL デジコレ各筆資料的「利用條件」文字 | 純客戶端渲染，`/ja/terms`、`/ja/help` 只回 JS 外殼 |
| 3 | Harvard Chinese Rare Books 的全部館藏（含目標書有無） | 門戶以 202 空回應阻擋腳本；IIIF 429 |
| 4 | Harvard 各館藏條目的 `Usage Rights` / `Rights` 原文 | 同上 |
| 5 | Harvard `curiosity.lib.harvard.edu` 的 robots 規則 | 202 空回應 |
| 6 | HathiTrust 全部內容與條款 | 403 Cloudflare 人機驗證 |
| 7 | Library of Congress 是否有目標書與逐件權利欄位 | 檢索 API 403（本機網路位置） |
| 8 | CTEXT 是否收《明實錄》《大明會典》及其正式條款 | `/faq`、`/terms`、`/ming` 皆 403 |
| 9 | 識典古籍的授權條款與《明实录》實際內容形式 | SPA 前端路由 catch-all，7 個候選路徑皆非真實頁 |
| 10 | 早稲田古典籍全庫是否含明代史料 | 站內無可腳本查詢的檢索端點；僅抽樣 6 筆明細頁 |
| 11 | Internet Archive 現行 Terms of Use 正文 | 純客戶端渲染；只取得 Wayback 快照（頁面自標 2014-12-31） |
| 12 | IA `mingshilu` 的掃描底本與來源機構 | metadata 無版本／出版者／來源欄位 |
| 13 | IA《大明會典》113 冊是否完整覆蓋 228 卷、有無缺冊 | 未逐冊核對頁數 |
| 14 | 中研院漢籍全文資料庫是否收目標書及其條款 | 頁面無書目清單；屬訂購制 |
| 15 | 書格 shuge.org 的條款與是否收目標書 | 未逐頁核 |
| 16 | Kanripo「CC BY SA」的版本與涵蓋範圍 | 站點停機；只能取得 Wayback 快照的頁腳一句 |
| 17 | Wikimedia Commons `SSID-*` 系列底本的權利人立場 | 未聯繫中研院史語所 |
| 18 | 國圖／北大圖書館對 Commons 上掃描件 PD 標示的立場 | 未聯繫 |
| 19 | 各來源目標書的卷冊完整性 | 本次只做「有沒有」與「條款怎麼寫」，未逐卷驗收 |
| 20 | 各站的許可頁面雜湊快照 | 本次只記錄 URL 與讀取日期，未做付費／第三方公證留存 |

---

## 12. 建議的人工核實步驟

1. **Kanripo（最高優先，且現在正是時機）**
   發信給 GitHub `@kanripo` 或站點聯絡表單，具體問三件事：(a) `CC BY SA` 是哪一個版本；(b) 是否涵蓋 `KR2k0008 明一統志`、`KR2m0010 明會典` 的全文轉錄；(c) GitHub 倉庫是否會補上 LICENSE 檔。同時以 `git clone --depth 1 https://github.com/kanripo/KR2k0008` 與 `…/KR2m0010` 取回全文，在**離線**環境清點卷數後，再決定是否納入。

2. **Wikimedia Commons（第二優先）**
   以瀏覽器開啟 `File:SSID-10485587 明實錄 明英宗實錄 13-20.pdf` 的檔案頁，人工確認：(a) 上傳者是誰、有無討論頁爭議；(b) `{{PD-scan}}` 是否附有來源說明。再分別向中研院史語所、國圖、北大圖書館發函確認對掃描件的主張。**在收到回覆前，只把 Commons 當作「掃描件核對來源」，不當作語料來源。**

3. **Internet Archive**
   以瀏覽器開啟 `https://archive.org/details/mingshilu`，確認頁面上是否顯示任何 CC 圖示或權利聲明（本次 API 讀到的 metadata 沒有，但頁面上可能有 uploader 在 description 中補述）。並以人工比對 `明实录.05.明英宗实录.pdf` 的首頁，確認底本版本。

4. **中國國家圖書館**
   以瀏覽器開啟 `http://read.nlc.cn/allSearch/searchDetail?searchType=10024&showType=1&indexName=data_892&fid=411999016504`（《國榷》），確認閱讀器是否需登入、是否可整本瀏覽，並記錄實際畫面。然後依《版权声明》留的 `webmaster@nlc.cn` 提出書面授權申請。

5. **NDL / Harvard / HathiTrust / LoC / CTEXT / 識典古籍**
   全部需要在**正常瀏覽器**（必要時換網路環境）中人工開啟並截圖留存條款頁。NDL 另需在デジコレ站內以「明代」「實錄」「會典」等關鍵詞人工檢索，確認有無「インターネット公開」的明代史料。

6. **登記方式**
   依 [許可指南](../source-licensing-guidance.md)第 5 節，對每一個實際引入的條目登記：來源 ID 與入口、版本、原文位置、**許可證名稱與官方條款連結、許可頁面快照或其散列、獲取日期**、逐用途授權。本文可直接作為「許可證核查」欄位的初始依據，但**每一條的雜湊快照仍需另行留存**。

---

## 13. 本次核查的範圍與限制聲明

- 本次**只做來源與許可核查，未下載任何史料全文或掃描件**，未修改倉庫中除本檔以外的任何檔案。
- 本次**未做法律判斷**。文中出現的「不允許」「允許」是對**條款文字**的逐字對應，不是對專案具體行為的法律評價。
- 本次所有「有／無」結論都建立在**官方檢索或官方倉庫**的實際命中上；「未核實」一律照寫，未以搜尋摘要、第三方轉述或推測填充。
- 本次使用的 Wayback 快照**只有兩處**（Internet Archive Terms of Use、Kanripo 站點頁腳），均已在文中明確標註快照 URL 與快照頁面自標日期。
- 條款頁面會變動；本文引用的 URL 在 2026-10-13 的內容已記錄於文中，但**未留存雜湊**。
