import pandas as pd

SUBJECTS = ["math", "english", "science"]

df = pd.read_csv("grades.csv")
df["average"] = df[SUBJECTS].mean(axis=1).round(2)
df["rank"] = df["average"].rank(ascending=False, method="min").astype(int)
df = df.sort_values("rank")

print(df[["rank", "name", "average"]].to_string(index=False))
print("\nClass average per subject:")
print(df[SUBJECTS].mean().round(2))