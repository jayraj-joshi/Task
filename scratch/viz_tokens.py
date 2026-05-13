
import json
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os

def create_viz():
    # Load data
    with open("comparison_results.json", "r") as f:
        data = json.load(f)
    
    # Prepare data for Seaborn
    plot_data = []
    for i, r in enumerate(data):
        query_label = f"Q{i+1}"
        plot_data.append({"Query": query_label, "Format": "JSON", "Tokens": r["json_tokens"]})
        plot_data.append({"Query": query_label, "Format": "TOON", "Tokens": r["toon_tokens"]})
    
    df = pd.DataFrame(plot_data)
    
    # Set style
    sns.set_theme(style="whitegrid", palette="viridis")
    plt.figure(figsize=(10, 6))
    
    # Create plot
    ax = sns.barplot(data=df, x="Query", y="Tokens", hue="Format")
    
    # Add titles and labels
    plt.title("Token Usage Comparison: JSON vs TOON", fontsize=16, pad=20)
    plt.xlabel("Query ID", fontsize=12)
    plt.ylabel("Token Count", fontsize=12)
    
    # Add value labels on top of bars
    for p in ax.patches:
        ax.annotate(format(p.get_height(), '.0f'), 
                   (p.get_x() + p.get_width() / 2., p.get_height()), 
                   ha = 'center', va = 'center', 
                   xytext = (0, 9), 
                   textcoords = 'offset points',
                   fontsize=10, fontweight='bold')

    plt.tight_layout()
    
    # Save to artifacts directory
    artifact_dir = "/Users/jayrajjoshi/.gemini/antigravity/brain/8a148c96-e996-42dc-91c8-83a46770e438/"
    save_path = os.path.join(artifact_dir, "token_usage_chart.png")
    plt.savefig(save_path, dpi=300)
    print(f"Chart saved to {save_path}")

if __name__ == "__main__":
    create_viz()
