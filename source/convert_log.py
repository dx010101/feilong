if __name__ == "__main__":
    source_path = "/common/data_triggers/max_15s_turnover/logs/daily_2025-10-22"
    error_lines = []
    with open(source_path, mode="rt", encoding="gbk") as f:
        lines = f.readlines()
        for line in lines:
            if "01600608" in line:
                print(line)