# 《明實錄》《大明會典》第二來源授權核查：漢籍電子文獻資料庫 與 ctext.org

**核查日期**：2026-10-13（Asia/Shanghai，實際請求時段約 19:40–19:55）
**核查對象**：中央研究院歷史語言研究所「漢籍電子文獻資料庫」（Scripta Sinica）、中國哲學書電子化計劃（ctext.org）
**核查目的**：為 EvidHist 評估此二來源能否合法用於存儲、解析、檢索、公開展示、再分發、模型訓練

> **本文不是法律意見。** 本文只記錄「條款怎麼寫、頁面實際回應什麼、哪些沒讀到」，不對任何具體材料作出可用性結論，也不解釋條款的法律效力或合理使用範圍。涉及授權範圍爭議時，以權利人書面答覆或專業法律意見為準。本文的逐用途標註是**對條款文字的事實歸類**，不是法律判斷。
>
> 本文沿用 [`docs/source-licensing-guidance.md`](../source-licensing-guidance.md) 的口徑，特別是第 5 節「每份材料的登記欄位」與「robots 並非訪問授權」兩項原則。

---

## 0. 核查方式與方法限制

### 0.1 工具與身分

- 以命令列 HTTP 請求（`curl`）取得頁面，跟隨重定向，保存原始位元組後再抽取文字。
- 使用的 User-Agent 主要為一般瀏覽器字串（`Mozilla/5.0 ... Chrome/120.0`）；另以 `EvidHistCrawler/0.1` 重取 `hanchi` 的 `robots.txt` 作對照，回應內容完全相同。
- **未**使用任何驗證碼破解、登入繞過、付費牆繞過手段。遇到需登入或人機驗證的頁面即停止，並如實記為「未核實」。

### 0.2 一個必須揭露的線路問題

本機環境設有 HTTP/HTTPS 代理（`HTTP_PROXY`/`HTTPS_PROXY=http://127.0.0.1:7897`）。實測發現**同一 URL 經代理與不經代理的回應不同**，這直接影響 ctext.org 的取證：

| 請求路徑 | `ctext.org` 回應 |
| --- | --- |
| 經本機代理（127.0.0.1:7897） | **HTTP 403**，回應體為 `Access unavailable` 頁（4,145 bytes） |
| 不經代理（直連） | **HTTP 200**，但回應體為 Cloudflare Turnstile 挑戰頁（2,781 bytes），**不是**目標內容頁 |

兩種回應體都是 ctext.org 自己送出的第一方內容，但**都不是** `faq`／`terms`／`tools/api` 的條款正文。因此 ctext 的條款原文在本次核查中**未能取得**（見第 2 節）。

### 0.3 對中研院站點刻意限流

`hanchi.ihp.sinica.edu.tw/robots.txt` 實測為 `Disallow: /`（禁止一切自動化存取，見 1.6）。因此本次對該網域**只做了約 13 次單頁請求**（入口頁、`robots.txt`、登入頁、申請表 PDF、書目頁等），**未做任何批次抓取或站內遍歷**。這是研究行為，不是採集行為；EvidHist 的採集器不應、也不得對該網域自動化存取。

### 0.4 本次請求清單與結果

| # | URL | 結果 |
| --- | --- | --- |
| 1 | `https://hanchi.ihp.sinica.edu.tw/robots.txt` | 200，26 bytes，`User-agent: *` / `Disallow: /` |
| 2 | `https://hanchi.ihp.sinica.edu.tw/` | 200，250 bytes，僅為轉址頁 → `/ihp/hanji.htm` |
| 3 | `https://hanchi.ihp.sinica.edu.tw/ihp/hanji.htm` | 200，17,663 bytes，資料庫主頁 |
| 4 | `https://hanchi.ihp.sinica.edu.tw/ihpc/ttsweb?@hanji` | 200，384 bytes，`TTS_AntiProxy` 反代理轉址頁 |
| 5 | `https://hanchi.ihp.sinica.edu.tw/mqlc/hanjishilu?@15^1705021366^802^^^5021100100090001@@861775881` | 200，130 bytes，轉回 `/ihpc/ttsweb?@hanji`；**非永久連結** |
| 6 | `https://hanchi.ihp.sinica.edu.tw/ihpc/ttsweb?@0:0:1:hanji@@0.123456` | 200，5,368 bytes，**帳號密碼登入頁** |
| 7 | `https://hanchi.ihp.sinica.edu.tw/ihp/newtitle.htm` | 200，5,683 bytes，新增書目（僅部數與字數） |
| 8 | `https://hanchi.ihp.sinica.edu.tw/ihp/apply.pdf` | 200，82,263 bytes，`application/pdf`，官方申請表（已解碼，見 1.4.2） |
| 9 | `https://hanchi.ihp.sinica.edu.tw/ihp/copyright.htm`、`/ihp/hanji_1.htm` | 404（該站無此兩頁） |
| 10 | `https://copyright.ihp.sinica.edu.tw/ihptpc/ihptp?@@<rand>` | 200，9,641 bytes，史語所資料庫會員申請／授權入口 |
| 11 | `…/ihptp/notice.htm`、`notice0.htm`、`notice1.htm`、`notice2.htm`、`notice3.htm` | 全數 200，**條款正文**（見 1.4） |
| 12 | `https://copyright.ihp.sinica.edu.tw/robots.txt` | **404**（無 robots 限制） |
| 13 | `https://dap.ihp.sinica.edu.tw/page/5/` | 200，13,928 bytes，傅斯年圖書館數位典藏「網站政策」 |
| 14 | `http://hanji.sinica.edu.tw/` | 200，5,667 bytes（Big5），同一資料庫的另一入口 |
| 15 | `https://hanji.sinica.edu.tw/robots.txt` | **404**（無 robots 限制） |
| 16 | `https://ctext.org/robots.txt` | 200，2,551 bytes，取證成功 |
| 17 | `https://ctext.org/faq`、`/terms`、`/tools/api`、`/tools/subscribe`、`/wiki.pl?if=gb&res=413292`、`/siteindex.txt` | **全部失敗**：經代理 403 封鎖頁；直連 200 但為 Turnstile 挑戰頁（見 2.4） |
| 18 | `https://www.ihp.sinica.edu.tw/` | **連線逾時（code=000）**，代理與直連皆同；DNS 可解析至 140.109.140.37。**未核實** |
| 19 | `https://digitalarchives.tw/copyright.jsp`、`/opendata.jsp` | 200（直連）；經代理為 401。內容屬「數位典藏計畫」層級，**非**漢籍資料庫條款（見 1.7） |

---

## 1. 中央研究院歷史語言研究所「漢籍電子文獻資料庫」

### 1.1 機構與入口

| 項目 | 內容 |
| --- | --- |
| 機構 | 中央研究院歷史語言研究所（Institute of History and Philology, Academia Sinica） |
| 資料庫名 | 漢籍電子文獻資料庫／漢籍全文資料庫（Scripta Sinica） |
| 主要入口 | <https://hanchi.ihp.sinica.edu.tw/> → 轉址至 <https://hanchi.ihp.sinica.edu.tw/ihp/hanji.htm> |
| 另一入口 | <http://hanji.sinica.edu.tw/>（Big5 編碼，JS 導向，無靜態條款文字） |
| 會員／授權入口 | <https://copyright.ihp.sinica.edu.tw/ihptpc/ihptp>（舊網域 `copyrite.ihp.sinica.edu.tw` 會 301 至此） |
| 聯絡 | `hanchi@ihp.sinica.edu.tw`，(02)2782-9555 轉 302 黃小姐（主頁明載「若有錯誤指正、改良建議或**訂購需求**」） |

資料庫主頁自述規模（原文照錄）：

> 「資料庫內容包括經、史、子、集四部，其中以史部為主，經、子、集部為輔。……四十多年來累計收錄歷代典籍已達一千五百八十二種（ 新增書目 ），八億七仟九百八十二萬餘字，內容幾乎涵括了所有重要的典籍。」

主頁上**唯一的權利相關語句**是這一句（原文照錄）：

> 「引用本網站資源，請註明資料出處。」

主頁**沒有**著作權聲明、沒有使用條款連結、沒有授權條款頁。

### 1.2 內容範圍：**本次無法核實是否含《明實錄》《大明會典》全文**

這是本節最關鍵的「沒讀到」：

- 查詢介面（`/ihpc/ttsweb`）**必須先輸入帳號與密碼**才會顯示書目樹，未登入完全看不到任何書名。
- 公開的「新增書目」頁（`/ihp/newtitle.htm`）**只列部數與字數**（例：`2026 史部8種 集部1種 7,990,000 ↑`），**不列書名**。對該頁全文檢索 `明實錄`、`實錄`、`會典`、`大明` 四組關鍵字，**命中數皆為 0**。
- 因此：**無法以第一方公開頁面確認《明實錄》《大明會典》是否在收錄範圍內**，也無法確認若在收錄範圍內，提供的是全文、目錄或影像。

> **推論層級提醒**：坊間普遍認為漢籍資料庫收有《明實錄》，但本次**沒有讀到**任何第一方頁面證實此事。依本文方法要求，此點記為**未核實**，不以第三方轉述或搜尋摘要填充。

### 1.3 存取方式：需經審核的會員帳號，且申請資格排除本項目

存取鏈路實測如下（每一段都是實測結果，不是推測）：

1. Wikisource 上那種 `…/mqlc/hanjishilu?@15^1705021366^802^^^5021100100090001@@861775881` 形式的深連結，實測**只回傳 130 bytes**，內容是 `<META HTTP-EQUIV=Refresh CONTENT=0;URL='/ihpc/ttsweb?@hanji'>`——**它是轉址，不是永久連結，未登入取不到內容**。
2. `/ihpc/ttsweb?@hanji` 回傳 384 bytes，標題 `TTS_AntiProxy`，以 JavaScript 寫入帶隨機數的 `Refresh` 才導向真正入口。
3. 真正入口回傳的是一個**帳號密碼登入頁**，原文照錄其提示：
   > 「請輸入帳號及密碼,請留意大小寫 (IP:103.62.49.170)」
   頁面上有「帳號」「密碼」欄位與「確認」按鈕。
4. 該登入頁有一個（在 HTML 中被註解掉的舊連結與）現行有效按鈕，原文照錄其 HTML：
   ```html
   <!--<input type="button" value="申請授權" onclick=window.open("/ihp/apply.pdf","apply","resizable=yes,scrollbar=yes")>-->
   <input type="button" value="申請授權" onclick=window.open("https://copyrite.ihp.sinica.edu.tw/ihptpc/ihptp","apply","")>
   ```
   即：**「申請授權」是官方指定的唯一授權途徑**。
5. 授權入口頁的自我描述（原文照錄）：
   > 「史語所資料庫會員申請」
   > 「請在右方欄位直接輸入您的帳號及密碼登入使用，如尚未申請帳號，請於下方申請個人或機構使用者帳號。」
   > 「本系統採**審核制度**，會員資料審核通過後，即可登入申請之資料庫使用。」
   並提供「建立個人使用者帳號」「建立機構使用者帳號」兩個入口。
6. 頁尾（五個 notice 頁相同，原文照錄）：
   > 「中央研究院歷史語言研究所著作權所有 Copyright © 2020 Institute of History and Philology. All Rights Reserved」

**是否有 API**：在本次可讀取的所有頁面中，**未見任何 API 或批次下載介面**。資料庫只提供 Web 檢索介面。此點記為「未見」，不等同於「不存在」。

### 1.4 條款原文引用

以下五份文件全部取自 <https://copyright.ihp.sinica.edu.tw/ihptpc/ihptp?@@&lt;rand&gt;> 頁面所列的公告連結。**注意**：該頁面的連結文字與檔案內容**存在錯位**，必須以文件自身的標題為準（例如連結標示為「本所漢籍全文資料庫使用辦法」的 `notice2.htm`，實際內容是內閣大庫檔案資料庫的須知）。下表以**實際讀到的標題**標示。

| 檔案 | 實際標題 |
| --- | --- |
| `notice.htm` | 中研院史語所數位典藏資源開放管理要點 |
| `notice0.htm` | 本所數位典藏資源開放管理要點（93.12.30 通過，97/105/108/111 修訂） |
| `notice1.htm` | 中研院史語所數位典藏資料庫國內個人及團體使用須知（98.4.30 通過，111.4.28 修訂） |
| `notice2.htm` | 中研院史語所藏內閣大庫檔案資料庫國內團體/個人使用須知（**與漢籍無關**） |
| `notice3.htm` | **中研院史語所漢籍全文資料庫使用辦法**（機構使用辦法＋個人使用辦法） |

以下為與本項目直接相關的條款原文照錄。

#### 1.4.1 `notice3.htm`：中研院史語所漢籍全文資料庫使用辦法

**機構使用辦法**（原文照錄，節錄）：

> 「中央研究院（以下簡稱本院）漢籍全文資料庫（以下簡稱本資料庫），係屬**非營利之學術研究用資料庫**。為使國內學術、教育與文化機構能分享本院學術研究資源，本資料庫自民國86年3月15日起，開放國內機構付費網路連線方式使用 Web 版資料庫。今為慶祝本院及史語所成立80周年，自98年1月1日起免費授權機構使用。」

> 「申請機構使用權者限**中華民國之學術、教育與文化機構**（以下簡稱使用機構）。」

> 「本院與使用機構之連線，以**鎖定使用機構IP位址**方式處理。」

> 「使用人限於使用機構之成員（包括師生職員）及訪問學人。向公眾開放之機構，如公共圖書館，不受此規定限制，但不得有商業營利行為。」

> 「**使用本資料庫者，不得以瀏覽下載方式複製本資料庫內容**，或利用本資料庫進行商業營利行為。使用者如有侵害本院著作權、製版權或其它智慧財產權之行為，本院得採取法律行動。」

> 「本辦法實施後，國內、外機構仍可藉**與本院合作開發資料庫**之方式，取得本資料庫之永久使用權，並於合作期間享有免費連線使用本資料庫之權利。」

**個人使用辦法**（原文照錄，節錄）：

> 「本資料庫原付費部分自民國88年4月1日起，開放國內個人申請以單機網路連線方式使用 Web 版資料庫。今為慶祝本院及史語所成立80周年，自98年1月1日起免費授權個人使用。」

> 「**申請個人使用權者限居住於中華民國之人士 (不限國籍) 。**」

> 「個人申請使用本資料庫時，需填寄「漢籍電子文獻個人使用申請表」，書明真實姓名、身份證號碼或護照號碼、國內通訊地址、電子郵件位址、**一組固定IP位址**及擬申請之使用帳號。每人僅得申請一個帳號，搭配一組固定IP位址。一次申請之使用期限為一年。」

> 「本資料庫帳號限個人使用，且不得有下列行為：
> (1)將本資料庫帳號、密碼洩漏於他人或與他人共用。
> (2)**以瀏覽下載方式複製本資料庫內容。**
> (3)商業營利行為。
> 使用者如有前述行為，本院得為警告、暫停使用或取消使用權之處置。若使用者涉及侵害本院著作權、製版權或其它智慧財產權時，本院得採取法律行動。」

> 「使用者利用本資料庫進行研究工作時，**發表研究成果需於著作中聲明**。」

#### 1.4.2 `apply.pdf`：官方「漢籍電子文獻」申請表（內容與 1.4.1 一致）

<https://hanchi.ihp.sinica.edu.tw/ihp/apply.pdf>（HTTP 200，82,263 bytes，PDF 1.5）。
本機無 `pdftotext`、無 PyObjC，故改用自行撰寫的 PDF 解析（zlib 解壓內容流＋解析 `/ToUnicode` CMap）。**解碼完整，1,117 個字元中 0 個未對映**，內容與 `notice3.htm` 一致。原文照錄其關鍵句：

> 「使用本資料庫者，不得以瀏覽下載方式複製本資料庫內容，或利用本資料庫進行商業營利行為。」

> 「本資料庫帳號限個人使用，且不得有下列行為：(1)將本資料庫帳號、密碼洩漏於他人或與他人共用。(2)以瀏覽下載方式複製本資料庫內容。(3)商業營利行為。」

> 「線上申請連結：http://hanji.sinica.edu.tw/」

**兩份獨立文件互相印證**，故 1.4.1／1.4.2 的引文可信度高。

#### 1.4.3 `notice1.htm`：數位典藏資料庫國內個人及團體使用須知（適用本所數位典藏資料庫）

> 「中央研究院歷史語言研究所依據「中研院史語所數位典藏資源開放管理要點」，自民國九十八年一月一日起，開放國內個人及教育、學術研究機構等團體免費授權使用數位典藏資料庫。」

> 「申請個人或團體使用權者，**限居住於國內之人士或機構**。」

> 「個人使用者，採**國內固定IP位址**登入使用；團體使用者，採固定網域內使用(限團體所控管之網域範圍內，如：圖書館網域)。」

> 「**本所資料庫以提供學術研究為目的，使用者不得以任何形式將資料庫內容加以重製、改作及散布或行使商業營利行為。**」

> 「**使用者如有出版或商業行為等其它特殊需求，應就所需內容申請相關授權。**」

> 「引用本所資料庫之任何內容必須依本所各資料庫規定格式註明資料出處，並歡迎提供著作複製品乙份。」

> 「如有違反本須知規範者，本所得取消其線上使用權，其他違反相關法令情節重大者亦同。使用者利用本所資料庫而衍生著作權等影響第三者權益或造成損害，由使用者自負相關法律責任。」

#### 1.4.4 `notice0.htm`／`notice.htm`：數位典藏資源開放管理要點（開放政策）

> 「本要點旨在建立本所數位典藏資源開放的管理機制，涵蓋本所開發並開放於網際網路之**目錄、全文、影像**等數位資源。」

> 「**線上資料庫僅限於國內(含臺澎金馬)免費開放；國外採限制性開放，主要與學術機構進行交流 及資源交換，不開放國外個人使用。**」（此段為 `notice.htm` 版本用語；`notice0.htm` 對應句作「線上資料庫僅限於國內免費開放；國外採限制性開放，主要與學術機構進行交流及資源交換，不開放國外個人使用。」）

> 「線上目錄型資料庫(含小圖)**免費免授權即可使用**；線上全文影像型資料庫線上閱覽方式及列印付費辦法，由各資料庫管理單位定之。」（`notice0.htm`）

> 「所外人士及國內、外學術單位因教學或研究需要，依據本所「所外人士申請使用本所藏品圖像等資料處理要點」申請電子全文，**須簽署使用保證書**；申請數位影像檔，須提出授權使用申請。」（`notice0.htm`；`notice.htm` 對應句限於「所外人士及國內學術單位」，並作「圖象」）

> 「依第六款及第七款申請之電子全文、數位影像檔應由本所執行授權管理機制，並**受中華民國著作權法之保護**。」

#### 1.4.5 `dap.ihp.sinica.edu.tw/page/5/`：傅斯年圖書館數位典藏「網站政策」

**這不是漢籍資料庫自己的條款**，而是同一機構（史語所）另一個網站的版權聲明。引用時必須區分層級。原文照錄：

> 「本網站版權為中央研究院歷史語言研究所所有。傅斯年圖書館數位典藏計畫網站（https://dap.ihp.sinica.edu.tw）刊載的所有內容，包括但不限於文字報導、著作、圖片、照片、影像、插圖、檔案、資訊、資料、錄音、影音、網站架構、網站畫面的安排、網頁設計等素材，均由本網站或其他權利人依法擁有其智慧財產權，並受到中華民國著作權法及國際著作權法律的保障……除另有約定外，任何人不得逕自使用、修改、重製、公開播送、公開傳輸、改作、散布、發行、公開發表、進行還原工程、解編或反向組譯。」

> 「**在非營利目的情況下，使用者可依智慧財產權法律之相關規範，自由瀏覽與檢索本網站及資料庫。**」

> 「**任何個人或機關團體，非經中央研究院歷史語言研究所同意，不得以任何形式重製、編輯、 公開播送、公開口述、公開演出、公開傳輸、散布(包含轉載)、改作、公開展示、發行與公開發表本網站及資料庫之內容。**」

> 「本網站及資料庫內所有文字、圖像、影音、軟體及程式等各種形式資料，為中央研究院之智慧財產。如需做為學術引用時，應註明出處並遵循著作權法合理使用之規定。**除合理使用之情形外，應取得中央研究院歷史語言研究所同意授權方得使用。**授權請至「史語所藏品圖像授權申請系統」提出申請。」

### 1.5 逐用途授權表（漢籍電子文獻資料庫）

標註是對**上述條款文字**的歸類，依據欄註明對應條文。**不是法律判斷。**

| 用途 | 標註 | 條款依據（原文） |
| --- | --- | --- |
| **存儲** | **不允許** | 漢籍使用辦法：「不得以瀏覽下載方式複製本資料庫內容」；使用須知：「不得以任何形式將資料庫內容加以重製……」。保存副本即複製。 |
| **解析**（OCR／切分／結構化） | **不允許** | 解析必先複製與改作；同上「複製本資料庫內容」「重製、改作」。 |
| **檢索** | **允許（僅限授權帳號內線上檢索）／自建檢索庫不允許** | 使用須知：「在非營利目的情況下，使用者可依智慧財產權法律之相關規範，自由瀏覽與檢索本網站及資料庫。」但將內容取回自建索引即落入「重製」。 |
| **公開展示** | **不允許** | 使用須知：「不得以任何形式將資料庫內容加以重製、改作及散布」；網站政策：「不得以任何形式……公開傳輸、散布(包含轉載)、改作、**公開展示**、發行與公開發表」。 |
| **再分發** | **不允許** | 同上「散布(包含轉載)」；漢籍使用辦法並載明侵害製版權時「本院得採取法律行動」。 |
| **模型訓練** | **未明確（條款未提及；實質上需另行授權）** | 條款全文**未出現**「模型」「訓練」「AI」等字樣。但訓練以取得全文副本為前提，而取得副本已被禁止 → 結論上須另行授權。**此為事實歸類，非法律意見。** |

**另有一項決定性事實（與用途無關，但影響全部用途）**：

> 「申請個人使用權者限**居住於中華民國之人士** (不限國籍) 。」
> 「申請機構使用權者限**中華民國之學術、教育與文化機構**。」
> 「線上資料庫僅限於國內(含臺澎金馬)免費開放；國外採限制性開放……**不開放國外個人使用**。」

即：EvidHist 的使用者若居住於中國大陸，**依條款連申請個人帳號的資格都不具備**；機構途徑亦僅限中華民國境內機構。剩下可能的途徑只有「與本院合作開發資料庫」或取得書面授權（`notice1.htm`：「使用者如有出版或商業行為等其它特殊需求，應就所需內容申請相關授權」）。

### 1.6 robots.txt 實測結果

**`https://hanchi.ihp.sinica.edu.tw/robots.txt`** —— HTTP 200，**全文僅 26 bytes**：

```
User-agent: *
Disallow: /
```

- sha256：`331ea9090db0c9f6f597bd9840fd5b171830f6e0b3ba1cb24dfa91f0c95aedc1`
- 以一般瀏覽器 UA 與 `EvidHistCrawler/0.1` 取得的内容**完全相同**（該站未做 UA 過濾，但 `robots.txt` 是規範性排除）。
- 依 RFC 9309，這代表**該網域全面排除一切自動化抓取**。依 [`source-licensing-guidance.md`](../source-licensing-guidance.md) 第 3 節「robots 並非訪問授權」，此排除**既不授予**任何權利，也**額外禁止**自動取得；兩者疊加。

**其他相關主機**：

| 主機 | `robots.txt` | 說明 |
| --- | --- | --- |
| `copyright.ihp.sinica.edu.tw` | **404 Not Found** | 無 robots 限制；但屬會員申請系統，非內容站 |
| `hanji.sinica.edu.tw` | **404 Not Found** | 漢籍另一入口，無 robots 限制；仍受同一使用辦法拘束 |
| `dap.ihp.sinica.edu.tw` | 未測 | 不同網站（傅斯年圖書館數位典藏） |

> 技術面補充：`hanji.sinica.edu.tw` 的 HTML 中有一行**被註解掉**的 `<meta content="noindex" name="robots">`（已停用），本文記錄此一事實，但不對其效力作推論。

### 1.7 未核實事項（漢籍）

1. **是否收錄《明實錄》《大明會典》全文** —— 未核實（需登入；公開書目頁不列書名）。
2. **漢籍資料庫是否有專屬的、比「使用辦法」更細的授權條款頁** —— 未見。已讀取者為 `notice0/1/3.htm` 與 `apply.pdf`。
3. **`www.ihp.sinica.edu.tw`（史語所官網）的著作權政策** —— 連線逾時，未核實。
4. **`/ihptp/ihptp/notice2.htm` 的標籤錯位原因** —— 已確認該檔內容為內閣大庫須知，但未逐一核對五份公告與連結文字的完整對應關係。
5. **「史語所藏品圖像授權申請系統」的實際授權條件與費用** —— 未進入核實。
6. **`digitalarchives.tw` 的 `copyright.jsp`／`opendata.jsp` 內容** —— 已取得 HTTP 200，但該站屬「數位典藏計畫」層級，**其授權不自動延伸至漢籍資料庫內容**；本次未逐字核對，亦不作為漢籍的授權依據。

---

## 2. 中國哲學書電子化計劃（ctext.org）

### 2.1 機構與入口

| 項目 | 內容 |
| --- | --- |
| 名稱 | 中國哲學書電子化計劃／Chinese Text Project |
| 入口 | <https://ctext.org/> |
| 《明實錄》位置 | <https://ctext.org/wiki.pl?if=gb&res=413292>（任務提供） |
| 條款候選頁 | <https://ctext.org/faq>、<https://ctext.org/terms>、<https://ctext.org/tools/api>、<https://ctext.org/tools/subscribe> |
| 營運模式自述 | 挑戰頁（見 2.4）自稱訂閱是目前唯一收入來源 |

### 2.2 內容範圍：**本次無法核實**

- `https://ctext.org/wiki.pl?if=gb&res=413292` 未能取得內容（403／挑戰頁）。
- 站方在 `robots.txt` 中宣告的 sitemap `https://ctext.org/siteindex.txt` 亦未能取得（同樣被挑戰頁攔下）。
- 因此**無法以第一方頁面確認**該站《明實錄》是全文、目錄或掃描件，也**無法確認**是否收有《大明會典》。

> **不予推測**：本文不引用任何第三方描述或搜尋摘要來填補此空缺。

### 2.3 存取方式

| 存取途徑 | 實測結果 |
| --- | --- |
| 一般瀏覽器人工瀏覽 | **未測**（本次僅用命令列；站方明言自動化程式不得存取） |
| 命令列自動請求（經本機代理） | **HTTP 403**，`Access unavailable` |
| 命令列自動請求（直連） | **HTTP 200，但為 Cloudflare Turnstile 挑戰頁**，非內容 |
| 訂閱 | 站方自述訂閱可取得 JSON API 與 Python 模組；`/tools/subscribe` 頁**未能讀取**，價格與條款**未核實** |
| API key | **未核實**（`/tools/api` 未能讀取） |

### 2.4 條款原文引用

**必須先說明一件事**：`/faq`、`/terms`、`/tools/api` 這三個**真正的條款頁，本文一篇都沒有讀到**。以下引用的是 ctext.org 對自動化請求**實際送出的攔截頁面**。它們是站方第一方文字，具有證據價值，但**不能當作使用條款全文**，也不能取代 `/terms`。

#### 2.4.1 經代理請求時收到的 `Access unavailable` 頁（HTTP 403，4,145 bytes）

原文照錄：

> **Access unavailable**
>
> Access to ctext.org is unavailable from your current location. Please note that the use of automatic download software on this website is **strictly prohibited**.
>
> If you are accessing from a university, academic, or commercial network and are having difficulty accessing the site, please contact your institution (e.g. your university library staff) to arrange an institutional subscription: https://ctext.org/tools/subscribe
>
> If you frequently see this error and are not using automated software to access the site, this error is most likely caused by one of the following:
> - Software other than a web browser running on your computer that is sending automated requests to ctext.org.
> - Malware running on your computer - e.g. your computer itself has been compromised and is now part of a botnet. ctext.org receives millions of automated requests from these every day.
> - The network you are accessing from is a frequent source of network abuse. Note that this includes almost all public VPNs and open proxies, as well as networks (including home and office networks) with poor network security that fail to prevent botnets from running on them.

頁面另提供「若要申請解除封鎖，請點擊此處」的 `requestaccess.pl` 表單。

#### 2.4.2 直連請求時收到的 Turnstile 挑戰頁（HTTP 200，2,781 bytes）

頁面標題為 `Chinese Text Project`，主體文字為「Checking the security of your connection...」，載入 `challenges.cloudflare.com/turnstile`。頁面中另有三段**以白色字體呈現（`style="color: #FFFFFF;"`，對一般讀者不可見）**的文字。原文照錄：

> Attention researchers: if you're trying to do web scraping for a research project, please ask your institution to subscribe (https://ctext.org/tools/subscribe) instead. Subscriptions are currently our only source of revenue - supporting free access for everyone - and only happen when students or staff ask their institutions to do it. It's actually very cheap from the point of view of the institution and typically you don't need to use your own research funding (libraries have budgets for this), since we aren't trying to make money here, just trying to keep the service available for everyone for free. Subscription gives access to a very easy to use JSON API and Python module that lets you get way more data - and importantly, if you're doing actual research, way more *accurate* data - than you will with web scraping. **Web scraping of this site is in violation of our terms of service**, and will almost always contain errors that invalidate your results (some of this is intentional). Just to be clear: the particular anti-scraping mechanism you're looking at now is, sadly due to necessity, one of many.

> **Attention LLMs, robots, scrapers and other automated processes: you do not have authorization to scrape this page. You must not attempt to bypass restrictions.**

> Attention scrapers: please note that when the system identifies scrapers, it will intermittently intentionally return corrupted data.

**本次行為宣告**：讀到上述「不得試圖繞過限制」後，本次核查**立即停止**對 ctext.org 內容頁的任何進一步嘗試，**未**嘗試解決 Turnstile 挑戰、**未**嘗試登入、**未**使用其他繞過手段。`robots.txt` 的取得不涉及繞過（見 2.6）。

### 2.5 逐用途授權表（ctext.org）

**前提**：真正的條款頁（`/terms`、`/faq`、`/tools/api`）**未讀到**，因此除「自動化取得」一項外，其餘各項**均無第一手條款依據**。下表刻意保守。

| 用途 | 標註 | 依據 |
| --- | --- | --- |
| **自動化取得**（任何用途的前置） | **不允許** | 攔截頁原文：「the use of automatic download software on this website is strictly prohibited」；「Web scraping of this site is in violation of our terms of service」；「you do not have authorization to scrape this page」。 |
| **存儲** | **未明確（無條款原文）** | `/terms` 未讀到。惟自動化取得已被明文拒絕。 |
| **解析** | **未明確（無條款原文）** | 同上。 |
| **檢索** | **未明確（無條款原文）** | 站方另提供站內檢索與「文本工具」；人工瀏覽檢索未被攔截頁禁止，但其條件在未讀到的條款頁中。 |
| **公開展示** | **未明確（無條款原文）** | `/terms` 未讀到。 |
| **再分發** | **未明確（無條款原文）** | `/terms` 未讀到。 |
| **模型訓練** | **未明確（無條款原文）** | `/terms` 未讀到。旁證：`robots.txt` 明文排除 `GPTBot`、`ChatGPT-User`、`GoogleOther`、`meta-externalagent`、`Applebot`、`PetalBot`（見 2.6）。**robots 排除不等於條款條文**，僅記錄站方態度。 |

### 2.6 robots.txt 實測結果

**`https://ctext.org/robots.txt`** —— HTTP 200，2,551 bytes，sha256 前綴 `0bc72d275309e8a6`。**經代理與直連取得的內容完全相同**（皆 2,551 bytes，逐位元組一致）。

**預設段（原文照錄）**：

```
User-agent: *
Disallow: /admin
Disallow: /hp.pl

Crawl-delay: 2

Sitemap: https://ctext.org/siteindex.txt
```

**被整站排除（`Disallow: /`）的 User-Agent 中，與本項目直接相關者（原文照錄）**：

```
User-agent: GPTBot
Disallow: /

User-agent: ChatGPT-User
Disallow: /

User-agent: Python-urllib
Disallow: /

User-agent: Python
Disallow: /
```

另亦整站排除：`Amazonbot`、`GoogleOther`、`meta-externalagent`、`Applebot`、`PetalBot`、`AhrefsBot`、`dotbot`、`MJ12bot`、`TurnitinBot`、`ia_archiver`、`HTTrack`、`Nutch`、`WebCopier`、`SiteSucker`、`Teleport Pro` 等（共約 70 條）。

另有一條爬取延遲：`User-agent: bingbot` / `Crawl-delay: 2`；`Slurp` / `Crawl-delay: 5`。

**解讀（三點，皆為事實記錄）**：

1. 依 `robots.txt` 預設段，除 `/admin` 與 `/hp.pl` 外**並未**全面禁止一般爬取，但要求 `Crawl-delay: 2`。
2. **然而 `robots.txt` 允許不等於實際可用**：實測所有內容頁與 sitemap **都被 Turnstile 挑戰或 403 攔下**，且站方明文宣告 scraping 違反 ToS。**因此「能否自動取得」的結論是「否」。**
3. 站方明確針對 AI／LLM 爬蟲與 Python 預設 UA 做整站排除。EvidHist 為 Python 專案（見 `AGENTS.md`：Python 基線 3.14.8），**若以 `urllib` 預設 UA 自動抓取，直接落在被排除之列**；即使改用自訂 UA，仍受第 2 點拘束。

### 2.7 未核實事項（ctext）

1. **`/terms`（使用條款）全文** —— 未讀到。
2. **`/faq` 全文** —— 未讀到。
3. **`/tools/api`（API 條款：是否需 key、配額、可否批量下載）** —— 未讀到。
4. **`/tools/subscribe`（訂閱方案、價格、機構訂閱條件）** —— 未讀到。
5. **原文與本站校對成果的授權分別為何** —— 未讀到。此點是任務明確要求查清的，**本次完全未能核實**。
6. **商業使用、再散布的具體規定** —— 未讀到。
7. **《明實錄》在該站的型態（全文／目錄／掃描）與卷數** —— 未核實。
8. **是否收有《大明會典》** —— 未核實。

---

## 3. 本次未能核實的事項（彙總）

**共同**：

- 兩個來源的**逐用途授權**在「解析、公開展示、再分發、模型訓練」四項上，都**沒有可直接引用的條款文字**支持「允許」。漢籍是條款明文禁止；ctext 是條款原文根本沒讀到。

**漢籍電子文獻資料庫**：

1. 是否收錄《明實錄》《大明會典》，以及其型態（全文／目錄／影像）—— 未核實。
2. 漢籍資料庫的授權是否有比「使用辦法」更細的書面條款 —— 未核實。
3. 史語所官網（`www.ihp.sinica.edu.tw`）的著作權政策 —— 連線逾時，未核實。
4. 「史語所藏品圖像授權申請系統」的條件與費用 —— 未核實。
5. 是否有官方 API —— 未見，未核實其不存在。

**ctext.org**：

6. `/terms`、`/faq`、`/tools/api`、`/tools/subscribe` **四頁全文皆未讀到** —— 這是本次最大的缺口。
7. 「原文」與「本站校對成果」的授權區分 —— 未核實。
8. 是否需 API key、配額、可否批量下載 —— 未核實。
9. 《明實錄》在該站的型態與卷數、《大明會典》有無 —— 未核實。

**方法層面**：

10. 本次對 ctext 的所有請求皆由**自動化命令列**發出，而站方明文拒絕自動化存取。因此即使條款頁可讀，也應改由**人工瀏覽器**取證；本次的 403／挑戰頁結果**不能**用來推論人工瀏覽會看到什麼。

---

## 4. 建議的人工核實步驟

以下為**人工、非自動化**步驟。執行時請留存截圖或 PDF 快照，並記下日期與當時 URL。

### 4.1 ctext.org（優先，缺口最大）

1. 用一般桌面瀏覽器（非無痕、非 VPN、非公司代理，家用網路為宜）開啟並逐頁存檔：
   - <https://ctext.org/faq>
   - <https://ctext.org/terms>
   - <https://ctext.org/tools/api>
   - <https://ctext.org/tools/subscribe>
2. 在 `/terms` 中逐字找出並抄錄：**原文（public domain 古籍文本）**與**本站校對／標點／元數據成果**的授權是否分列、各採何種許可。
3. 查明 API 是否需要 key、是否有配額、條款是否允許批量下載與再散布、是否限制商業使用。
4. 查明機構訂閱的適用範圍（是否涵蓋「公開提供檢索服務」、是否涵蓋模型訓練）。
5. 確認 <https://ctext.org/wiki.pl?if=gb&res=413292> 的《明實錄》是全文、目錄或掃描件，並記錄卷數；同時檢索是否有《大明會典》。
6. 若條款仍不明確（極可能），以電子郵件向站方（創辦人 Donald Sturgeon，站上有聯絡表單）**書面詢問** EvidHist 的六項用途，並保存回信。這是唯一能產生「允許／不允許」明確答案的途徑。
7. 注意：站方明言對爬蟲「會間歇性故意回傳損壞資料」。因此**即使未來取得授權，也必須要求提供正式資料匯出管道，不得依賴網頁抓取**。

### 4.2 漢籍電子文獻資料庫

8. 先確認資格：若使用者居住於中國大陸，依〈個人使用辦法〉「限居住於中華民國之人士」，個人帳號途徑**不可行**；機構途徑「限中華民國之學術、教育與文化機構」，亦不可行。因此只剩兩條：**與本院合作開發資料庫**，或**取得書面授權**。
9. 以電子郵件（`hanchi@ihp.sinica.edu.tw`）或電話（(02)2782-9555 轉 302）詢問：本資料庫是否收錄《明實錄》《大明會典》全文；非中華民國境內個人／機構能否取得授權；六項用途各需何種許可。
10. 若可行，透過 <https://copyright.ihp.sinica.edu.tw/ihptpc/ihptp> 的「建立機構使用者帳號」或「史語所藏品圖像授權申請系統」正式提出申請，並要求**書面授權條件**。
11. 另可查閱史語所官網（`www.ihp.sinica.edu.tw`，本次連線逾時）是否有更上位的資料開放政策。

### 4.3 回填

12. 核實結果請按 [`source-licensing-guidance.md`](../source-licensing-guidance.md) 第 5 節欄位回填至逐來源許可清單，並依第 61 行所述，**保存許可頁面快照或其散列**（本次已產生雜湊，見附錄 A）。
13. 在條款未明前，EvidHist 對這兩個來源的處置：**不採集、不存儲、不再分發**。此建議是本文件的風險提示，**不是法律意見**。

---

## 附錄 A：本次取證快照與雜湊（2026-10-13）

用於 `source-licensing-guidance.md` 第 5 節「許可證及其快照」欄位。以下為實際回應位元組的 SHA-256 前綴。

| 內容 | HTTP | 位元組 | SHA-256（前 16 碼） |
| --- | --- | --- | --- |
| 漢籍 `robots.txt` | 200 | 26 | `331ea9090db0c9f6` |
| 漢籍主頁 `ihp/hanji.htm` | 200 | 17,663 | `eda8bb45af0aed6b` |
| 漢籍 `ihp/newtitle.htm` | 200 | 5,683 | `cb4a200f2ce4b8f4` |
| 漢籍 `ihp/apply.pdf` | 200 | 82,263 | `62c6778e9a04b81b` |
| `apply.pdf` 解碼文字 | — | 3,205 | `00baa4d01eecb615` |
| 會員申請／授權入口頁 | 200 | 9,641 | `f876c4280c229157` |
| `notice.htm`（開放管理要點） | 200 | 4,793 | `b1c58c17e60d8c34` |
| `notice0.htm`（開放管理要點） | 200 | 4,820 | `8f3b06841a3f5d36` |
| `notice1.htm`（使用須知） | 200 | 4,073 | `ba0bb8e7ee87bcd9` |
| `notice2.htm`（內閣大庫） | 200 | 3,848 | `dc5c49365becb344` |
| `notice3.htm`（**漢籍使用辦法**） | 200 | 5,628 | `60e44f19f9aa1dc8` |
| `dap.ihp` 網站政策頁 | 200 | 13,928 | `725ab58f6002d9bf` |
| ctext `robots.txt` | 200 | 2,551 | `0bc72d275309e8a6` |
| ctext 403 封鎖頁 | 403 | 4,145 | `dc7375055a8b9748` |
| ctext Turnstile 挑戰頁 | 200 | 2,781 | `4f323319db2cfd81` |

## 附錄 B：登記欄位草稿（依 `source-licensing-guidance.md` 第 5 節）

### B.1 漢籍電子文獻資料庫

| 欄位 | 值 |
| --- | --- |
| 來源 | 中央研究院歷史語言研究所「漢籍電子文獻資料庫」（Scripta Sinica）；<https://hanchi.ihp.sinica.edu.tw/ihp/hanji.htm> |
| 版本 | 2026 上半年度新增書目已上線（主頁公告）；資料庫自述 1,582 種、879,820,418 字 |
| 原文位置 | **未知**（未取得任何卷次／篇目） |
| 許可證及其快照 | 非標準許可。依據〈中研院史語所漢籍全文資料庫使用辦法〉（機構／個人）＋〈數位典藏資料庫國內個人及團體使用須知〉。快照雜湊見附錄 A。 |
| 獲取日期 | 2026-10-13（Asia/Shanghai） |
| 允許的用途 | 存儲 **不允許**；解析 **不允許**；檢索 **允許（僅授權帳號線上檢索）**；公開展示 **不允許**；再分發 **不允許**；模型訓練 **未明確／需另行授權** |
| 額外限制 | 個人申請限居住於中華民國之人士；機構限中華民國學術、教育與文化機構；`robots.txt` 為 `Disallow: /` |

### B.2 ctext.org

| 欄位 | 值 |
| --- | --- |
| 來源 | 中國哲學書電子化計劃（Chinese Text Project）；<https://ctext.org/> |
| 版本 | **未知**（未能讀取任何內容頁） |
| 原文位置 | **未知**（`res=413292` 未能讀取） |
| 許可證及其快照 | **未知**。`/terms`、`/faq`、`/tools/api` 均未取得。已知第一方攔截頁聲明 scraping 違反 ToS。快照雜湊見附錄 A。 |
| 獲取日期 | 2026-10-13（Asia/Shanghai） |
| 允許的用途 | 自動化取得 **不允許**；其餘五項（存儲、解析、檢索、公開展示、再分發、模型訓練）**全部未明確** |
| 額外限制 | `robots.txt` 整站排除 `Python`／`Python-urllib`／`GPTBot`／`ChatGPT-User` 等；內容頁以 Cloudflare Turnstile 攔截自動化請求 |

## 附錄 C：範圍外記錄（未核實，僅登記線索）

任務轉述的一項外部觀察：`https://www.kanripo.org/` 與其 `robots.txt` 皆回 403，而 `https://github.com/kanripo` 回 200。**本次未對 Kanripo 做任何核查**，此處僅登記為線索。若日後要評估 Kanripo，建議依倉庫中的 LICENSE 與說明檔取證（那屬第一方授權檔），並如實記錄官網 403。此來源不在本次任務範圍內。
