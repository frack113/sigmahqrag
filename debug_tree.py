import sys, os
os.chdir("D:\\rootme\\sigmahqrag")

from src.back.github.git import list_directory_tree
result = list_directory_tree('sigmahq', 'sigma')
with open("C:\\Users\\papa\\AppData\\Local\\Temp\\opencode\\treeout.txt", "w", encoding="utf-8") as f:
    f.write(f"Result type: {type(result)}\n")
    f.write(f"Result count: {len(result)}\n")
    for item in result[:5]:
        f.write(f"  - {item.get('name')}: {item.get('path')}\n")
        if 'children' in item:
            f.write(f"    children: {len(item['children'])} ({[c.get('name') for c in item['children']]})\n")
