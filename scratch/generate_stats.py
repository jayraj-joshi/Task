
import json
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os

def generate_all_stats():
    # Load data
    with open("comparison_results.json", "r") as f:
        data = json.load(f)
    
    df_all = pd.DataFrame(data)
    stats_dir = "stats"
    os.makedirs(stats_dir, exist_ok=True)
    sns.set_theme(style="whitegrid")

    for doc_name in ["First10", "AllTransformer"]:
        df_doc = df_all[df_all["doc"] == doc_name]
        
        # 1. Token Comparison Bar Chart for this doc
        plot_data = []
        for i, r in enumerate(df_doc.to_dict('records')):
            query_label = f"Q{i+1}"
            plot_data.append({"Query": query_label, "Format": "JSON", "Tokens": r["json_tokens"]})
            plot_data.append({"Query": query_label, "Format": "TOON", "Tokens": r["toon_tokens"]})
        df_fmt = pd.DataFrame(plot_data)
        
        plt.figure(figsize=(10, 6))
        ax = sns.barplot(data=df_fmt, x="Query", y="Tokens", hue="Format", palette="viridis")
        plt.title(f"Token Usage Comparison: {doc_name}", fontsize=15)
        for p in ax.patches:
            if p.get_height() > 0:
                ax.annotate(f"{int(p.get_height())}", (p.get_x() + p.get_width()/2., p.get_height()), ha='center', va='bottom', fontweight='bold')
        plt.savefig(os.path.join(stats_dir, f"{doc_name}_comparison.png"), dpi=300)
        plt.close()

        # 2. Savings Pie Chart for this doc
        total_json = df_doc["json_tokens"].sum()
        total_toon = df_doc["toon_tokens"].sum()
        plt.figure(figsize=(8, 8))
        plt.pie([total_toon, total_json - total_toon], labels=["TOON", "Saved"], 
                autopct='%1.1f%%', startangle=140, colors=["#66b3ff", "#99ff99"], explode=(0, 0.1))
        plt.title(f"Savings Proportion: {doc_name}", fontsize=15)
        plt.savefig(os.path.join(stats_dir, f"{doc_name}_savings.png"), dpi=300)
        plt.close()

    # 3. Overall Comparison (Combined)
    plt.figure(figsize=(12, 6))
    sns.boxplot(data=df_all, x="doc", y="reduction_pct", palette="Set2")
    plt.title("Reduction % Distribution by Document Type", fontsize=15)
    plt.ylabel("Reduction %")
    plt.savefig(os.path.join(stats_dir, "reduction_by_doc_type.png"), dpi=300)
    plt.close()

    print(f"Stats generated for both PDFs in /{stats_dir}")

if __name__ == "__main__":
    generate_all_stats()
