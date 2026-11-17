if __name__ == "__main__":
    # source_file = "20250923/SSEMarketData20250923.csv"
    # target_file = "20250923/SSEMarketDataSlim20250923.csv"
    source_file = "20250923/SZSEMarketData20250923.csv"
    target_file = "20250923/SZSEMarketDataSlim20250923.csv"

    with open(source_file, 'rb') as infile, \
        open(target_file, 'wb') as outfile:
    
        # 读取前30000行
        for i, line in enumerate(infile):
            if i < 300000:
                outfile.write(line)
            else:
                break

print("处理完成！")

    # read first 30000 lines and