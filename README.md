# Culture Agent 🌸

日本文化・アジア文化を「正しい形」で世界に伝えるAIエージェント。
IBM AI Innovator Hackathon 応募に向けたMVP。

## 目的（成功条件）
ヨーロッパ人からの質問に対し、社内の文化資料を**自分で検索して**、
日本文化の背後にある価値観（謙虚さ・職人精神・マインドフルネスの仏教的ルーツ）を
敬意とともに、質問された言語で答えるAIエージェントを動かす。

## これは「AIを組み込んだシステム」である
| 構成要素 | 実装箇所 |
|---|---|
| ① LLMの組み込み | `agent.py` が `anthropic` SDK 経由で Claude API を呼ぶ |
| ② ツール使用（エージェント） | AIが `search_knowledge` ツールを自分で選んで呼ぶ agentic loop |
| ③ RAG（検索拡張生成） | `knowledge/` の資料を検索し、根拠に基づいて回答 |

「AIにコードを書かせた」のではなく、「コードの中でAIを部品として動かす」点が核心。

## セットアップ

### 1. APIキーを取得する
1. https://console.anthropic.com にアクセスしてアカウント作成
2. 「API Keys」から新しいキーを発行（`sk-ant-...` で始まる文字列）
3. ターミナルで環境変数に設定:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-ここに自分のキー"
   ```
   ※毎回打つのが面倒なら `~/.zshrc` の末尾に上記1行を追記して `source ~/.zshrc`

### 2. ライブラリ（インストール済みなら不要）
```bash
pip3 install anthropic
```

### 3. 実行
```bash
cd ~/RIO/Workspace/Dev/culture-agent
python3 agent.py
```

#### モデルの切り替え（Opus 4.8 ⇄ Fable 5）
デフォルトは `claude-opus-4-8`（高性能・低コスト）。
最上位の **Fable 5**（約2倍コスト・より繊細な回答）で動かすには:
```bash
CULTURE_AGENT_MODEL=claude-fable-5 python3 agent.py
```
起動時に「🤖 使用モデル: ...」で確認できます。
普段のテストはOpus 4.8、本番デモやES用の見せ場だけFable 5、がおすすめ。

## 使い方の例
```
あなた> What is samue and why is it connected to Zen?
あなた> 日本の「謙虚さ」は西洋人にどう誤解されがちですか？
あなた> Is "zen" just a minimalist design style?
```
AIが自動で知識ベースを検索（🔎 が表示される）し、資料を根拠に回答します。

## 次の拡張アイデア（ハッカソン本番に向けて）
- 知識ベースを増やす（茶道・着物・地域文化など）
- 商品在庫を調べるツールを追加 → 作務衣ブランドのカスタマー対応エージェントに
- ベクトル検索（embedding）でRAGの精度を上げる
- Web UI 化（Streamlit など）
