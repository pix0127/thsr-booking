# 🚄 台灣高鐵訂票小幫手

**純研究用途，請勿用於不當用途**

自動訂購高鐵車票的工具，支援 CLI 和 Web 介面。

## 安裝

```bash
pip install -r requirements.txt
```

## 使用

### Web 介面
```bash
streamlit run src/streamlit_app.py
```

### CLI
```bash
python src/main.py -i    # 互動模式
python src/main.py -n    # 新增預訂
python src/main.py -r    # 執行所有預訂
python src/main.py --list # 列出預訂
```

## 設定

TDX API（時刻表用）：
```bash
export TDX_CLIENT_ID="your_id"
export TDX_CLIENT_SECRET="your_secret"
```

無 TDX 時會使用本地的 `timetable_cache.json`。

## 架構

```
src/
├── controller/       # 業務邏輯
├── remote/          # HTTP 客戶端
├── utils/          # 工具函式
├── tests/          # 測試
└── main.py         # CLI 入口
```

## 授權

MIT
