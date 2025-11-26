# Gapless Crypto ClickHouse Examples

This directory contains comprehensive examples demonstrating how to use the gapless-crypto-clickhouse package for ultra-fast cryptocurrency data collection with ClickHouse storage.

## 🚀 Quick Start

### Prerequisites

Make sure you have the package installed:

```bash
# Using UV (recommended)
uv add gapless-crypto-clickhouse

# Or using pip
pip install gapless-crypto-clickhouse
```

## 📁 Example Files

### 1. [simple_api_examples.py](simple_api_examples.py) ⭐ **NEW**

**Demonstrates:** Function-based API for simple data collection

**Key Features:**

- Intuitive `fetch_data()` and `download()` functions
- Symbol and timeframe discovery
- Simple gap filling
- Multiple usage patterns

**Run it:**

```bash
uv run python examples/simple_api_examples.py
```

### 2. [advanced_api_examples.py](advanced_api_examples.py) ⭐ **NEW**

**Demonstrates:** Class-based API for complex workflows

**Key Features:**

- Advanced data collection with custom configuration
- Detailed gap detection and analysis
- Atomic file operations
- Validation and quality checks

**Run it:**

```bash
uv run python examples/advanced_api_examples.py
```

### 3. [basic_data_collection.py](basic_data_collection.py)

**Demonstrates:** Basic data collection workflow

**Key Features:**

- Initialize BinancePublicDataCollector
- Collect data for multiple timeframes
- Analyze collected data

**Run it:**

```bash
uv run python examples/basic_data_collection.py
```

### 4. [gap_filling_example.py](gap_filling_example.py)

**Demonstrates:** Gap detection and filling

**Key Features:**

- Create sample data with gaps
- Detect gaps using UniversalGapFiller
- Fill gaps with authentic Binance API data
- Verify results

**Run it:**

```bash
uv run python examples/gap_filling_example.py
```

### 3. [complete_workflow.py](complete_workflow.py)

**Demonstrates:** End-to-end data pipeline

**Key Features:**

- Complete data collection workflow
- Data quality analysis
- Gap detection and filling
- Final data validation

**Run it:**

```bash
uv run python examples/complete_workflow.py
```

## 🎯 Example Workflows

### Quick Demo (2-3 minutes)

Perfect for testing and understanding the package:

```bash
# 1. Simple API demo (start here!)
uv run python examples/simple_api_examples.py

# 2. Advanced API demo (for complex workflows)
uv run python examples/advanced_api_examples.py

# 3. Basic collection
uv run python examples/basic_data_collection.py
```

> **Note**: This package provides a Python API only (no CLI). See the examples for usage patterns.

### Production Workflow

For real-world data collection with ClickHouse:

```bash
# Complete workflow demo with ClickHouse storage
uv run python examples/complete_workflow.py
```

## 📊 Expected Output

When you run the examples, you'll see:

1. **Ultra-fast collection** (22x faster than APIs)
2. **Progress indicators** showing download status
3. **File generation** with metadata
4. **Gap detection** and filling results
5. **Data validation** summaries

### Sample Output Structure

```
├── binance_spot_BTCUSDT-1h_20240101-20240131_v2.5.0.csv
├── binance_spot_BTCUSDT-1h_20240101-20240131_v2.5.0.metadata.json
├── binance_spot_ETHUSDT-4h_20240101-20240131_v2.5.0.csv
└── binance_spot_ETHUSDT-4h_20240101-20240131_v2.5.0.metadata.json
```

## 🔧 Customization

All examples can be customized by modifying:

- **Symbols:** Change `symbol` parameter (e.g., BTCUSDT, ETHUSDT, SOLUSDT)
- **Timeframes:** Modify timeframes list (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h)
- **Date ranges:** Adjust start_date and end_date
- **Output locations:** Change file paths and directories

## 💡 Pro Tips

1. **Start small:** Use 1-2 day ranges for testing
2. **Scale gradually:** Increase to weeks/months for production
3. **Monitor performance:** Check file sizes and processing times
4. **Validate data:** Always run gap detection after collection
5. **Use multiple timeframes:** Different analyses need different granularity

## 🚨 Important Notes

- **Network dependency:** Examples require internet for data downloads
- **Storage space:** Large date ranges generate significant data
- **API limits:** Respect Binance public data fair usage
- **File cleanup:** Examples may create temporary files

## 📚 Further Reading

- [Main README](../README.md) - Package overview and installation
- [API Documentation](../docs/) - Detailed API reference
- [GitHub Issues](https://github.com/terrylica/gapless-crypto-clickhouse/issues) - Report problems or request features

## 🤝 Contributing

Found an issue with examples or have ideas for new ones? Please:

1. Check existing issues
2. Create a new issue with details
3. Submit a pull request with improvements

---

**Happy data collecting! 🚀📊**
