import pandas as pd
df = pd.read_csv("data/raw/da_hrl_lmps(1).csv", usecols=["pnode_name", "zone"])
print("Unique pnode_names:")
print(df["pnode_name"].value_counts().head(20))
print("\nUnique zones:")
print(df["zone"].value_counts().head(20))
