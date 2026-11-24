"""Regenerate the offline evidence indexes from the pinned FedOps repository."""
import argparse
import gzip
import json
from pathlib import Path
import re
import subprocess
import tempfile

from source_context import EVIDENCE, REVISION


def git(repo, *args):
    return subprocess.check_output(["git", "-C", repo, *args], text=True)


def repository_rows(repo):
    pattern = r"^[[:space:]]*((async )?def |class |_target_:[[:space:]]+)"
    lines = git(repo, "grep", "-I", "-n", "-E", pattern, REVISION, "--", "*.py", "*.yaml", "*.yml")
    for match in lines.splitlines():
        _, path, number, code = match.split(":", 3)
        yield path, int(number), code.strip()


def export_graph_html(graph):
    import networkx as nx
    from graphify.cluster import cluster, label_communities_by_hub
    from graphify.export import to_html

    network = nx.node_link_graph(graph, edges="edges", directed=True)
    communities = cluster(network)
    labels = label_communities_by_hub(network, communities)
    target = EVIDENCE / "fedops-graph.html"
    with tempfile.TemporaryDirectory() as temp:
        output = Path(temp) / target.name
        if not to_html(network, communities, str(output), community_labels=labels, node_limit=5000):
            raise ValueError("Graphify HTML 생성 실패")
        html = output.read_text().replace(
            "https://unpkg.com/vis-network@9.1.6/standalone/umd/vis-network.min.js",
            "/vis-network.min.js")
        target.write_text(html)


def graph_rows(repo):
    # The extractor sees only the pinned tree, even if the user's checkout is dirty.
    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder) / "FedOps"
        subprocess.run(["git", "clone", "-q", "--local", "--no-checkout", repo, source], check=True)
        git(source, "checkout", "-q", "--detach", REVISION)
        subprocess.run(["graphify", "extract", ".", "--code-only", "--max-workers", "2",
                        "--no-cluster", "--out", folder], cwd=source, check=True)
        graph = json.loads((Path(folder) / "graphify-out/graph.json").read_bytes())
        export_graph_html(graph)
        labels = {node["id"]: node["label"] for node in graph["nodes"]}
        tracked = set(git(source, "ls-files").splitlines())
        for edge in graph["edges"]:
            path = edge.get("source_file")
            location = re.fullmatch(r"L(\d+)(?:-L?\d+)?", edge.get("source_location") or "")
            if path not in tracked or not location:
                continue
            yield (path, int(location[1]), labels.get(edge["source"], edge["source"]),
                   edge["relation"], labels.get(edge["target"], edge["target"]), edge["confidence"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", choices=["repository", "graph"])
    parser.add_argument("checkout", type=Path)
    args = parser.parse_args()
    provider = graph_rows if args.source == "graph" else repository_rows
    rows = sorted(set(provider(args.checkout.resolve())))
    if not rows:
        raise ValueError("빈 컨텍스트 색인")
    data = {"revision": REVISION, "rows": rows}
    if args.source == "graph":
        from importlib.metadata import version
        data["graphify_version"] = version("graphifyy")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
    target = EVIDENCE / (args.source + ".json.gz")
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as out:
        out.write(gzip.compress(payload, mtime=0))
    temp_path = Path(out.name)
    temp_path.chmod(0o644)
    temp_path.replace(target)
    print(f"{target.name} · {len(rows)}건")


if __name__ == "__main__":
    main()
