# 🦙 LibreLlama Reviewer (學術英文審查與改寫工作台) v1.2

> **專為國際頂級期刊（Nature, IEEE, Science, ACM, Elsevier 等）投稿學者與學術寫作教師打造的 AI 審查工作台**  
> **混合雙模架構 ｜ 100% 離線在地 Ollama 隱私保護 ｜ 線上旗艦 API 自由切換 ｜ 審稿實證中英雙語對照 ｜ 獨立安裝與解安裝精靈 ｜ GitHub 線上檢查更新系統**

---

## 📌 專案背景與核心理念

學術界在投稿頂級論文（SCI / SSCI / EI / 國際頂會）前，往往高度仰賴語言潤飾工具。然而傳統雲端服務（如 Grammarly, ChatGPT 等）存在三大痛點：
1. **資料隱私與未發表論文版權洩漏**：未發表原創草稿、專利數據或機密實驗結果上傳至雲端伺服器，具高度資安與版權風險。
2. **審查流於表面且不徹底**：一般工具或預設 LLM 往往「點到為止」，一段 200 字草稿僅抓出 2-3 個表面問題，遺漏了深層的學術用詞精準度與句構缺陷。
3. **缺乏審稿人層級的「實證與上下文完整度批判」**：傳統工具只能改字改文法，無法指出「實驗設計缺少了什麼」、「統計顯著性缺少了什麼」、「如何補做實驗才能防禦 Reviewer #2 的質疑」。

**LibreLlama Reviewer** 透過 **Python + PySide6** 現代桌面 GUI 框架，打造出支援 **本地 Ollama 離線模型** 與 **線上旗艦 API 資源（DeepSeek, OpenAI, Gemini, Groq 等）** 的雙核驅動學術編輯工作台，兼顧機密資料隱私與頂級同儕評審（Peer Review）深度。

---

## 🚀 系統架構與重大技術特點

```
+-----------------------------------------------------------------------------------+
|                        🦙 LibreLlama Reviewer (三欄式專業工作台)                    |
+--------------------------+------------------------------+-------------------------+
|     【左欄：原始草稿】     |    【中欄：審稿評析與選項】   |   【右欄：修訂後全文】   |
|                          |                              |                         |
|  • 輸入學術英文段落      |  • 全文主旨判斷 (正體中文)   |  • 確定性合成引擎       |
|  • 暗黑模式高對比純白字  |  • 🔬 審稿人實證補強建議     |  • 100% 準確彩色高亮:   |
|  • 字數即時統計          |    (中英雙語對照呈現)        |     🔴 文法與句構       |
|                          |                              |     🟠 推論缺陷         |
|  [⚡ 本機秒篩 Linter]    |  • ✍️ 逐句穿透式窮舉審查     |     🟡 邏輯矛盾         |
|  • 縮寫/口語/宣稱預警    |    (深度挖掘 6~10 處改寫點)  |     🔵 修辭風格         |
|  • 一鍵 0.001 秒秒級修正 |  • 多風格改寫 (Hedged/       |  • 隨選項即時動態連動   |
|                          |    Concise/Assertive)        |                         |
+--------------------------+------------------------------+-------------------------+
             |                                                         ^
             | (預處理完成後傳送)                                      | (即時連動)
             v                                                         |
+----------------------------------------------------------------------+------------+
|                          雙模後端引擎 (Dual Hybrid Engine)                         |
|                                                                                   |
|  Layer 1: 純 Python 規則庫 (0.001s) ➔ 縮寫、口語詞、超長句、基礎啟發式快篩         |
|                                                                                   |
|  Layer 2: 雙模推論引擎 (支援 QThread 即時 Token 串流 + 智慧 JSON 修復)            |
|           ├── 模式 A：在地 Ollama (100% 離線私隱，內建環境與模型管理精靈)          |
|           └── 模式 B：線上 OpenAI 相容 API (DeepSeek, GPT-4o, Gemini, Groq)       |
+-----------------------------------------------------------------------------------+
|                         生命週期與維護管理 (Lifecycle & Maintenance)              |
|  • 獨立安裝精靈 (Setup.exe) ➔ 自動建立桌面/開始功能表捷徑與環境檢查               |
|  • 完整解安裝程式 (uninstall.exe) ➔ 整合 Windows「已安裝的應用程式」與登錄檔註銷    |
|  • 線上檢查更新模組 (Update Checker) ➔ 支援 GitHub Releases 一鍵升級               |
+-----------------------------------------------------------------------------------+
```

### 1. 審稿人實質建議「中英雙語對照」（Bilingual Peer-Review Insights）
全新實質建議架構均以**繁體中文／英文雙語平鋪對照**：
- **實證與論述缺陷分析**（Evidence Gap Identified）
- **具體補做或補強方案**（Concrete Actionable Proposal，如消融實驗、顯著性檢定、變因排除）
- **對同儕評審防禦之實質效益**（Peer-Review Defense Impact）
卡片視覺化分離顯示，點選可直接複製英文精準術語，方便學者撰寫學術反駁信（Rebuttal Letter）或補入論文討論章節（Discussion）。

### 2. 沉浸式暗黑模式與純白高對比輸入（High-Contrast Dark Mode）
- **左側原始草稿文字全面強制優化為純白高對比（`#ffffff`）**，無論手動輸入、貼上文本或執行一鍵修復，文字均保持極致清晰。
- 修訂四色高亮標記（🔴文法 🟠推論 🟡邏輯 🔵修辭）全面調色，確保在深色背景下色彩識別度 100%。

### 3. 雙模運算：在地 Ollama 離線隱私 ＋ 線上旗艦 LLM API
- **在地 Ollama 模式**：100% 離線推論，保障論文未發表資料絕對不外洩。
- **線上 API 模式**：工具列提供「⚙️ API 設定」，支援 DeepSeek, OpenAI (GPT-4o), Google Gemini, Groq, OpenRouter 等。支援 SSE Token 串流顯示。

### 4. 完整的 Windows 軟體生命週期管理
- **安裝精靈 (`LibreLlamaReviewer_Setup_v1.2.exe`)**：
  - 單一檔案即開即裝，自動解壓應用程式檔案至本機目錄（免管理員權限）。
  - 自動在「桌面」與「開始功能表」建立捷徑。
  - 自動註冊至 Windows **「設定 ➔ 應用程式 ➔ 已安裝的應用程式」**，提供原生軟體管理體驗。
  - 安裝過程中自動偵測 Ollama，未安裝時可一鍵背景下載官方安裝檔並一鍵拉取學術模型（`llama3.1:8b`）。
- **獨立解安裝精靈 (`uninstall.exe`)**：
  - 放置於安裝目錄下，並於開始功能表建立「解除安裝 LibreLlama Reviewer」捷徑。
  - 使用者在 Windows 設定中點選「解除安裝」時即可自動呼叫。
  - 具備跳板自解構機制、安全終止進程、清理所有捷徑與目錄、登錄檔乾淨註銷。

### 5. 線上檢查更新機制（Check for Updates）
- 工具列新增 **「🚀 檢查更新」** 按鈕。
- 支援 GitHub 倉庫中的 `version.json` 比對版本號。
- 偵測到新版本時視覺化展示更新日誌（Release Notes），提供 **「📥 立即下載並安裝更新」**。
- 下載完成後自動啟動新版安裝精靈覆蓋更新，並完整保留原有的個人設定（`app_config.json`）。

---

## 🛠️ 功能特點總覽

| 功能模組 | 技術實現 | 適用場景 |
| :--- | :--- | :--- |
| **獨立安裝導引** | `LibreLlamaReviewer_Setup_v1.2.exe` | 朋友同事免學 Python 與命令列，雙擊即可自動安裝並配置 Ollama |
| **獨立解安裝精靈** | `uninstall.exe` + Windows Registry | 支援從 Windows「已安裝的應用程式」或開始功能表乾淨移除 |
| **線上檢查更新系統** | `UpdateDialog` + GitHub Releases | 隨時檢查最新版本、檢視更新日誌，一鍵背景下載與自動覆蓋升級 |
| **本機環境與模型精靈** | 視覺化模型庫 + Ollama 串流拉取 | 一鍵檢測服務狀態，直接點擊下載 `llama3.1:8b` 或 `qwen2.5:14b` |
| **中英對照實質建議** | 雙語 Schema + 實證缺失因果推理 | 具體指出需補做的**消融實驗、顯著性檢定、變因排除方案**，中英對照便於寫入 Rebuttal |
| **窮舉式逐句審查** | 頂刊 Reviewer #2 極限 Prompt | 深入挖掘 6~10 處改寫點，涵蓋學術謙抑、精確性與句構 |
| **線上/離線雙模運算** | Ollama + OpenAI 相容 API (httpx SSE) | 本機離線保護極限隱私；或一鍵切換雲端 DeepSeek/GPT-4o 享受旗艦推論力 |
| **高對比暗黑/明亮主題** | 現代 Slate/Zinc 主題引擎 | 原始草稿純白高對比，長時間夜間寫作抗疲勞 |

---

## 🌐 GitHub 專案建立與發布維護指引

本專案已做好開源與團隊維護準備。以下為發布至 GitHub 與日後推播更新的標準流程：

### 1. 於 GitHub 建立新倉庫
1. 登入 [GitHub](https://github.com/) 並點擊右上角的 **New repository**。
2. 倉庫名稱建議命名為：`LibreLlama-Reviewer`。
3. 設為 **Public**（公開）或 **Private**（私人）。
4. **不要**勾選 "Initialize this repository with a README"（本機已有完整檔案）。
5. 點擊 **Create repository**。

### 2. 連接遠端倉庫並推送代碼
在專案根目錄開啟 PowerShell 執行：
```powershell
# 設定使用者識別 (若尚未設定)
git config --global user.name "Your Name"
git config --global user.email "your_email@example.com"

# 關聯遠端倉庫 (請將 USERNAME 換成您的 GitHub 帳號)
git remote add origin https://github.com/USERNAME/LibreLlama-Reviewer.git

# 推送至 main 分支
git branch -M main
git push -u origin main
```

### 3. 發布 Release 與配置自動更新 (`version.json`)
當您打包出新版安裝檔（如 `LibreLlamaReviewer_Setup_v1.2.exe`）後：
1. 進入 GitHub 專案頁面右側的 **Releases** ➔ **Draft a new release**。
2. Tag 標籤填寫 `v1.2.0`，Title 填寫 `LibreLlama Reviewer v1.2.0`。
3. 將編譯出的 `LibreLlamaReviewer_Setup_v1.2.exe` 拖曳上傳至 **Attach binaries** 區域。
4. 點擊 **Publish release** 發布。
5. 更新專案中的 `version.json` 內的 `download_url` 為該 Release 附件的直接下載鏈結，並將 `version.json` push 至 GitHub：
   ```json
   {
     "latest_version": "1.2.0",
     "release_date": "2026-10-16",
     "download_url": "https://github.com/USERNAME/LibreLlama-Reviewer/releases/download/v1.2.0/LibreLlamaReviewer_Setup_v1.2.exe",
     "changelog": "【v1.2.0 更新】..."
   }
   ```
6. 使用者在軟體內點擊「🚀 檢查更新」時，軟體便會直接從該 URL 下載最新安裝檔並自動覆蓋更新！

---

## 📦 發行與分發給同仁的方法

### 方法 A：使用獨立安裝檔（推薦給朋友與同事）
直接傳送根目錄下的 [LibreLlamaReviewer_Setup_v1.2.exe](file:///c:/Users/Chars%20Hsieh/Desktop/Editor%20project/LibreLlamaReviewer_Setup_v1.2.exe)（單一可執行檔）：
1. 雙擊執行 `LibreLlamaReviewer_Setup_v1.2.exe`。
2. 依照安裝精靈引導完成解壓、註冊與捷徑建立。
3. 精靈會自動檢查 Ollama，若尚未安裝可一鍵下載官方安裝檔並一鍵拉取模型。
4. 安裝完成後勾選「立即啟動 LibreLlama Reviewer」即可開始使用！
5. 日後若欲移除，可直接在 Windows「設定 ➔ 應用程式」點擊解除安裝，或從開始功能表點選「解除安裝 LibreLlama Reviewer」。

### 方法 B：免安裝綠色版（直接執行）
雙擊專案目錄下的 [啟動LibreLlama.bat](file:///c:/Users/Chars%20Hsieh/Desktop/Editor%20project/啟動LibreLlama.bat)，直接呼叫主程式開啟。

---

## 📖 專案檔案結構

```
Editor project/
│
├── LibreLlamaReviewer_Setup_v1.2.exe # ★ 獨立一鍵安裝檔 (內含完整程式、解安裝程式與模型引導)
├── academic_reviewer_app.py          # 主應用程式原始碼 (GUI、雙模推論、中英對照、環境精靈、更新檢查)
├── installer.py                      # 安裝精靈原始碼 (含 Windows Add/Remove 註冊)
├── uninstall.py                      # 解安裝程式原始碼 (清理目錄、捷徑與登錄檔)
├── version.json                      # 版本發布與更新日誌中繼資料
├── 啟動LibreLlama.bat                # 雙擊一鍵免安裝啟動
├── README.md                         # 專案技術架構與完整說明書
├── .gitignore                        # Git 忽略設定 (排除大型二進位檔與個人組態)
├── app_config.json                   # 使用者個人偏好設定檔 (暗黑模式狀態、API 設定)
└── dist/                             # 打包發行目錄
    ├── LibreLlamaReviewer/           # 綠色獨立執行檔目錄
    │   ├── LibreLlamaReviewer.exe    # 主程式執行檔
    │   └── uninstall.exe             # 獨立解安裝程式
    └── LibreLlamaReviewer_Setup_v1.2.exe # 單一安裝精靈執行檔
```
