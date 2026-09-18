"""Small Tiny Shakespeare warm-up for the Homework 3 token splitter."""

from pathlib import Path

from llama_index.core import Document
from llama_index.core.node_parser import TokenTextSplitter


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "reports" / "hw03" / "warmup" / "tinyshakespeare.txt"


def main() -> None:
    text = INPUT.read_text(encoding="utf-8")
    splitter = TokenTextSplitter(chunk_size=256, chunk_overlap=40)
    nodes = splitter.get_nodes_from_documents([Document(text=text)])
    print("Homework 3 warm-up only: Tiny Shakespeare")
    print(f"Characters: {len(text)}")
    print(f"Token chunks: {len(nodes)}")
    print(f"First chunk preview: {' '.join(nodes[0].text.split())[:160]}")


if __name__ == "__main__":
    main()
