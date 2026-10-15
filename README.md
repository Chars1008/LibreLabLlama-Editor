# 🦙 LibreLlama Reviewer (多情境寫作審查與改寫工作台) v0.9.0

> **⚠️ 封閉開發階段 (Closed Development / Pre-release) ｜ 正式公開發布時定為 ver 1.0**  
> **多語系介面切換 (繁體中文 / Pure English) ｜ 四大情境寫作模式 ｜ 文章範圍與章節定位 ｜ 道地搭配詞與 3~4 種多樣選項 ｜ 100% 離線隱私或線上旗艦 API**

---

## 📌 專案背景與封閉開發目標

在國際論文發表、海外留學申請、重要商務談判與高階學術通訊中，高品質的英文書寫是決定成敗的關鍵門檻。
多數寫作者常面臨以下核心困境：
1. **未公開資料的極致隱私保護**：原創草稿、專利數據、未發表論文上傳至第三方雲端有洩漏風險。
2. **缺乏情境適配性**：市面工具多半「一套標準套用所有文體」，無法區分學術期刊論文（嚴謹謙抑）、商務書信（得體外交）、求學自述 SOP（量化成就動詞）與商務決策報告（金字塔結構）。
3. **生硬的搭配詞（Awkward Collocations）**：字詞單看文法正確，但母語人士絕不這樣搭配（例如 *make an experiment*、*statistically big difference*），且一般工具僅提供單一死板改法，缺乏多樣語感選擇。
4. **片面段落被斷章取義**：使用者往往只修改論文其中一節（如僅修 Methodology 或僅修 Introduction），一般 LLM 常誤判「缺乏結論」或「缺少背景」。

**LibreLlama Reviewer** 於 **v0.9.0 封閉開發版** 針對上述問題進行了全方位重構與升級，為即將到來的 **v1.0 正式公開發布** 奠定扎實架構！

---

## 🚀 v0.9.0 五大核心新功能

### 1. 🌐 多語系操作切換（支援純英文 Pure English 模式）
- 工具列提供 **「🌐 English / 繁體中文」** 一鍵切換。
- **純英文模式 (Pure English Mode)**：
  - 界面全面切換為專業英文，**完全隱藏並杜絕任何正體中文註解**。
  - 後端推論 Prompt 自動注入純英文強制指令，LLM 產出的主旨解析、評語批判、補強策略、修改理由皆保證 100% 正統專業英文。
- **正體中文模式**：保有優質繁體中文文意分析與中英雙語對照呈現，利於華人學者撰寫 Rebuttal Letter。

### 2. 📝 四大情境寫作模式 (Multi-Context Writing Profiles)
支援頂部控制列一鍵切換不同寫作情境，推論引擎將自動切換專家角色（Persona）與評判維度：
1. **🔬 學術期刊論文 (Academic Research Paper)**：
   - 角色：頂級國際期刊 Reviewer #2 與資深學術編輯。
   - 焦點：消融實驗、顯著性檢定、因果推論、學術謙抑詞（Hedging）、杜絕過度斷言。
2. **✉️ 專業書信往來 (Professional Correspondence / Email)**：
   - 角色：高級學術聯絡官與商務通訊專家。
   - 焦點：外交級語氣（Diplomatic tone）、溝通得體性、明確的行動呼籲（Call to Action）。
3. **🎓 留學與求職自述 (Statement of Purpose / Cover Letter)**：
   - 角色：常春藤名校審查委員與高階獵頭合夥人。
   - 焦點：量化成就強動詞（Action verbs）、故事脈絡（Hook）、個人亮點與目標系所契合度。
4. **💼 商務決策報告 (Business & Analytical Report)**：
   - 角色：麥肯錫（McKinsey）高級戰略諮詢顧問。
   - 焦點：金字塔原則（Pyramid Principle）、數據洞察支撐、執行可行性與 ROI 決策論述。

### 3. 📑 文章範圍與章節針對性定位 (Scope & Section Targeting)
- **範圍選擇**：
  - 📄 **全篇完整文章 (Full Document)**：評估全文結構流暢度、起承轉合與邏輯閉環。
  - 📑 **局部段落選取 (Partial Excerpt)**：專注評審特定篇章。
- **動態章節定位**：
  - 切換為局部段落時，章節選單自動依寫作情境調整（如學術模式提供 Abstract / Introduction / Methodology / Results / Discussion / Conclusion 等）。
  - LLM 獲得明確的局部章節定位資訊，**絕不因缺少其他章節內容而誤判或扣分**，專注於該章節的黃金標準！

### 4. 🟢 道地搭配詞檢視與 3~4 種多樣風格選項 (Collocations & Multi-Options)
- 新增 **「🟢 道地搭配詞 (Collocation Defect)」** 一級問題分類，專門揪出不自然、生硬的詞語搭配。
- **3 至 4 個不同語感改寫選項**：
  - **選項 A**：標準規範／高頻道地搭配 (Standard / High-Frequency Native Phrasing)
  - **選項 B**：簡練高能／行動導向 (High-Impact Concise / Action-Oriented)
  - **選項 C**：學術謙抑／謹慎精確 (Cautious & Hedged / Nuanced)
  - **選項 D**：權威正式／書面典雅 (Authoritative / Formal Register)
- 點選任何選項，右欄修訂全文即時連動並精準高亮，給予寫作者充分的詞彙主控權！

### 5. ⚡ 本機秒篩 Linter 與高對比暗黑模式
- **本機秒篩 (0.001s)**：即時攔截常見縮寫、口語贅詞與生硬搭配詞，支援一鍵秒級修復。
- **高對比暗黑模式**：左側草稿文字純白（`#ffffff`），夜間寫作極度抗疲勞；五色彩色高亮標記（🔴文法 🟠推論 🟡邏輯 🔵修辭 🟢搭配詞）清晰分明。

---

## 🛠️ 架構總覽

```
+-----------------------------------------------------------------------------------+
|                        🦙 LibreLlama Reviewer (三欄式專業工作台)                    |
|  [控制列] 寫作情境模式 (4大類) ｜ 文章範圍 (全篇/局部) ｜ 章節定位 ｜ 語言切換 (中/EN)  |
+--------------------------+------------------------------+-------------------------+
|     【左欄：原始草稿】     |    【中欄：審查意見與選項】   |   【右欄：修訂後全文】   |
|                          |                              |                         |
|  • 輸入各情境英文段落    |  • 全文主旨判斷與情境總評    |  • 確定性動態合成引擎   |
|  • 暗黑純白高對比輸入    |  • 🔬 實證/策略補強建議      |  • 5 色高亮即時響應:    |
|  • 即時字數統計          |    (中英雙語或純英文)        |     🔴 文法與句構       |
|                          |                              |     🟠 推論缺陷         |
|  [⚡ 本機秒篩 Linter]    |  • ✍️ 逐句穿透式窮舉審查     |     🟡 邏輯矛盾         |
|  • 縮寫/口語/搭配詞預警  |  • 🟢 道地搭配詞分析         |     🔵 修辭風格         |
|  • 一鍵 0.001 秒秒級修正 |  • 3~4 種多風格改寫選項      |     🟢 道地搭配詞       |
|                          |    (Option A, B, C, D)       |  • 點擊選項即時連動     |
+--------------------------+------------------------------+-------------------------+
             |                                                         ^
             | (傳送情境與章節中繼資料)                                | (即時切換)
             v                                                         |
+----------------------------------------------------------------------+------------+
|                          雙模後端引擎 (Dual Hybrid Engine)                         |
|                                                                                   |
|  • 模式 A：在地 Ollama (100% 離線私隱，內建環境與模型管理精靈)                      |
|  • 模式 B：線上 OpenAI 相容 API (DeepSeek, GPT-4o, Gemini, Groq)                   |
+-----------------------------------------------------------------------------------+
|                         生命週期與維護管理 (Lifecycle & Maintenance)              |
|  • 獨立安裝精靈 (Setup.exe) ➔ 自動建立桌面/開始功能表捷徑與環境檢查               |
|  • 完整解安裝程式 (uninstall.exe) ➔ 整合 Windows「已安裝的應用程式」與登錄檔註銷    |
|  • 線上檢查更新模組 (Update Checker) ➔ 支援 GitHub Releases 一鍵升級               |
+-----------------------------------------------------------------------------------+
```

---

## 📖 版本歷程與發布計畫 (Roadmap)

- **v0.9.0 (當前版本 ─ 封閉開發版 Closed Development Pre-release)**：
  - 專案正式命名為 LibreLlama Reviewer。
  - 新增多語系介面（繁體中文 / Pure English）。
  - 新增四大情境寫作模式（學術、書信、留學求職、商務報告）。
  - 新增文章範圍（Full Text / Partial Excerpt）與章節針對性定位。
  - 新增道地搭配詞檢視（Collocation Defect）與 3~4 種改寫選項。
  - Windows 原生安裝、解安裝與線上更新機制就緒。
- **v1.0.0 (預計公開發布版本 Official Release)**：
  - 完成社群封測反饋修復。
  - 支援全文 PDF / LaTeX / DOCX 匯入與導出。
  - 擴充更多專業領域 Prompt 知識庫。

---

## 📦 使用與啟動方式

1. **直接免安裝執行**：雙擊專案目錄下的 [啟動LibreLlama.bat](file:///c:/Users/Chars%20Hsieh/Desktop/Editor%20project/啟動LibreLlama.bat)。
2. **開發除錯執行**：
   ```powershell
   python academic_reviewer_app.py
   ```
3. **打包獨立安裝精靈**：
   ```powershell
   pyinstaller --noconfirm --onedir --windowed --name "LibreLlamaReviewer" academic_reviewer_app.py
   pyinstaller --noconfirm --onefile --windowed --name "uninstall" uninstall.py
   # 複製 uninstall.exe 至 dist/LibreLlamaReviewer 後打包為 app_bundle.zip
   pyinstaller --noconfirm --onefile --windowed --name "LibreLlamaReviewer_Setup_v0.9" --add-data "app_bundle.zip;." installer.py
   ```
