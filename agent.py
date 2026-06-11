"""
Culture Agent — 日本文化・アジア文化を「正しい形」で世界に伝えるAIエージェント.

IBM AI Innovator Hackathon 向けMVP。
このスクリプトは「AIを使って書いたコード」ではなく、
「コードの中からLLM(大規模言語モデル)を部品として呼び出し、
 AI自身がツールを選んで使う自律エージェント」である。

3つの構成要素:
  1. LLMの組み込み   : anthropic SDK 経由で Claude API を実行
  2. ツール使用       : AIが search_knowledge ツールを自分で呼ぶ (agentic loop)
  3. RAG(検索拡張生成): knowledge/ の資料を検索し、根拠に基づいて回答
"""

import os
import sys
import re
from pathlib import Path

import anthropic

# モデルは環境変数で切り替え可能。
#   未設定         → claude-opus-4-8（高性能・低コスト。普段のテスト向き）
#   Fableを使う場合 → 実行時に CULTURE_AGENT_MODEL=claude-fable-5 を指定（最上位・約2倍コスト）
MODEL = os.environ.get("CULTURE_AGENT_MODEL", "claude-opus-4-8")
KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"

SYSTEM_PROMPT = """\
あなたは「文化アンバサダー」AIエージェントです。
使命は、日本文化・アジア文化を正しい形で、敬意とともに世界に伝えることです。

行動原則:
- 必ず search_knowledge ツールで社内の資料を検索し、その内容を根拠に答える。
  資料にない事柄は推測せず「資料には記載がない」と正直に述べる。
- 表面的な「エキゾチックな日本」ではなく、その背後にある価値観
  (謙虚さ・職人精神・もったいない・マインドフルネスの仏教的ルーツ)を伝える。
- 質問された言語で答える(英語の質問には英語で、日本語には日本語で)。
- ステレオタイプや誤解には、丁寧に正しい情報で応える。
"""


def load_knowledge() -> dict[str, str]:
    """knowledge/ 配下の全mdファイルを {ファイル名: 本文} で読み込む."""
    docs = {}
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        docs[path.name] = path.read_text(encoding="utf-8")
    return docs


def search_knowledge(query: str, docs: dict[str, str], top_k: int = 2) -> str:
    """
    シンプルなキーワードスコアリングによる検索 (RAGの retrieval 部分).
    クエリ語と各資料の重なりを数え、上位 top_k 件の関連箇所を返す.
    """
    terms = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 1]
    scored = []
    for name, text in docs.items():
        lowered = text.lower()
        score = sum(lowered.count(t) for t in terms)
        if score > 0:
            scored.append((score, name, text))
    scored.sort(reverse=True, key=lambda x: x[0])

    if not scored:
        return "（関連する資料は見つかりませんでした）"

    chunks = []
    for score, name, text in scored[:top_k]:
        chunks.append(f"--- 出典: {name} (関連度スコア {score}) ---\n{text}")
    return "\n\n".join(chunks)


# AIに渡すツール定義。AIはこの説明を読んで「いつ呼ぶか」を自分で判断する。
TOOLS = [
    {
        "name": "search_knowledge",
        "description": (
            "日本文化・作務衣・禅・マインドフルネス・日本の価値観に関する"
            "社内資料を検索する。ユーザーの質問に答える前に必ず呼び出すこと。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "検索したいキーワードやトピック",
                }
            },
            "required": ["query"],
        },
    }
]


def run_agent(client: anthropic.Anthropic, user_message: str, docs: dict[str, str]) -> str:
    """
    エージェントの中核ループ(agentic loop)。
    AIがツールを呼ばなくなる(end_turn)まで、ツール実行→結果返却を繰り返す。
    """
    messages = [{"role": "user", "content": user_message}]

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # AIがもうツールを使わず、回答を確定した
        if response.stop_reason == "end_turn":
            return "".join(b.text for b in response.content if b.type == "text")

        # AIがツールを呼びたがっている → 実行して結果を返す
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use" and block.name == "search_knowledge":
                    query = block.input["query"]
                    print(f"  🔎 AIが知識ベースを検索中: 「{query}」", file=sys.stderr)
                    result = search_knowledge(query, docs)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            messages.append({"role": "user", "content": tool_results})
            continue

        # 想定外の停止理由
        return f"(エージェントが予期せず停止しました: {response.stop_reason})"


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("エラー: 環境変数 ANTHROPIC_API_KEY が設定されていません。", file=sys.stderr)
        print("README.md の手順に従ってAPIキーを設定してください。", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic()
    docs = load_knowledge()
    print(f"🤖 使用モデル: {MODEL}")
    print(f"📚 知識ベース読み込み完了: {list(docs.keys())}\n")
    print("文化アンバサダーAIエージェント (終了するには Ctrl+C)\n")

    while True:
        try:
            user_message = input("\nあなた> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nさようなら。")
            break
        if not user_message:
            continue
        answer = run_agent(client, user_message, docs)
        print(f"\n🌸 エージェント> {answer}")


if __name__ == "__main__":
    main()
