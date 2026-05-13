import json

def toon_encode(value, indent_level=0, options=None):
    indent_size = (options or {}).get("indent", 2)
    indent = " " * (indent_level * indent_size)
    
    if isinstance(value, dict):
        lines = []
        for k, v in value.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{indent}{k}:")
                lines.append(toon_encode(v, indent_level + 1, options))
            else:
                lines.append(f"{indent}{k}: {v}")
        return "\n".join(lines)
    
    elif isinstance(value, list):
        if not value:
            return f"{indent}[]"
            
        # Check if it's a tabular array (list of dicts with same keys)
        is_tabular = False
        if all(isinstance(x, dict) for x in value) and len(value) > 0:
            keys = list(value[0].keys())
            if all(list(x.keys()) == keys for x in value):
                # Check if values are primitives
                if all(all(not isinstance(v, (dict, list)) for v in x.values()) for x in value):
                    is_tabular = True
        
        if is_tabular:
            keys = list(value[0].keys())
            header = f"{indent}[{len(value)},]{{{','.join(keys)}}}:"
            lines = [header]
            for item in value:
                row = ",".join(str(item[k]) for k in keys)
                lines.append(f"{indent}{' ' * indent_size}{row}")
            return "\n".join(lines)
        
        # Check if it's a primitive array
        if all(not isinstance(x, (dict, list)) for x in value):
            return f"{indent}[{len(value)}]: {','.join(str(x) for x in value)}"
            
        # Mixed/Standard array (bulleted)
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{indent}-")
                lines.append(toon_encode(item, indent_level + 1, options))
            else:
                lines.append(f"{indent}- {item}")
        return "\n".join(lines)
    
    else:
        return f"{indent}{value}"

def extract_tree(nodes):
    tree = []
    for node in nodes:
        entry = {
            "id": node.get("node_id"),
            "title": node.get("title"),
            "pages": f"{node.get('start_index')}-{node.get('end_index')}",
            "summary": node.get("summary", "")
        }
        if "nodes" in node and node["nodes"]:
            entry["children"] = extract_tree(node["nodes"])
        tree.append(entry)
    return tree

def main():
    try:
        with open("output.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: output.json not found.")
        return

    root_nodes = data.get("structure", [])
    tree_data = {
        "document": data.get("doc_name"),
        "tree": extract_tree(root_nodes)
    }
    
    # Save JSON tree
    with open("tree.json", "w") as f:
        json.dump(tree_data, f, indent=2)
    
    # Save TOON tree
    toon_str = toon_encode(tree_data)
    with open("tree.toon", "w") as f:
        f.write(toon_str)
    
    print("Successfully created tree.json and tree.toon")
    print("\nTOON Tree Preview:")
    print("-" * 20)
    print(toon_str)

if __name__ == "__main__":
    main()
