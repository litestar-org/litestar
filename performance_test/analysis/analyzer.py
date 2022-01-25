from functools import reduce
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

root_dir = Path(__file__).parent.parent
results_dir = root_dir / "results"
for test_type in ["json", "plaintext"]:
    df = pd.DataFrame()
    for file in results_dir.iterdir():
        if f"-{test_type}-" in file.name:
            if "fastapi" in file.name:
                source = "fastapi"
            elif "starlite" in file.name:
                source = "starlite"
            else:
                source = "starlette"
            loaded = pd.read_json(file)
            loaded = loaded.assign(source=source)
            df = df.append(loaded)

    df_2 = df[["url", "source", "2xx"]]
    grouped_src_url = df_2.groupby(by=["source", "url"]).agg(sum)
    t = grouped_src_url.reset_index()

    starlite_results = t[t["source"] == "starlite"]
    fast_api_results = t[t["source"] == "fastapi"]
    starlette_results = t[t["source"] == "starlette"]
    starlite_results.rename(
        columns={"2xx": "requests_processed_starlite"}, inplace=True
    )
    fast_api_results.rename(columns={"2xx": "requests_processed_fastapi"}, inplace=True)
    starlette_results.rename(
        columns={"2xx": "requests_processed_starlette"}, inplace=True
    )

    merged_df = reduce(
        lambda left, right: pd.merge(left, right, on="url"),
        [starlite_results, fast_api_results, starlette_results],
    )
    merged_df["url"] = merged_df["url"].apply(
        lambda x: x.replace("http://0.0.0.0:8001", "")
        .replace("?first=abc", "")
        .replace("/def", "")
        .replace("/abc", "pp")
        .replace("async", "a-")
        .replace("sync", "s-")
        .replace("json", "")
        .replace("plaintext", "")
        .replace("no-params", "np")
        .replace("query-param", "qp")
        .replace("mixed-params", "mp")
    )
    final_df = merged_df[
        [
            "url",
            "requests_processed_starlite",
            "requests_processed_fastapi",
            "requests_processed_starlette",
        ]
    ].set_index("url")
    ax = final_df.plot.bar(rot=0)
    plt.savefig(str(root_dir.absolute()) + f"/result-{test_type}.png")
