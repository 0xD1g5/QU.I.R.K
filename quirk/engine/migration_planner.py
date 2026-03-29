def categorize_waves(findings):
    waves = {
        "NOW": [],
        "NEXT": [],
        "LATER": []
    }

    for f in findings:
        if f["severity"] == "CRITICAL":
            waves["NOW"].append(f)
        elif f["severity"] == "HIGH":
            waves["NEXT"].append(f)
        else:
            waves["LATER"].append(f)

    return waves
