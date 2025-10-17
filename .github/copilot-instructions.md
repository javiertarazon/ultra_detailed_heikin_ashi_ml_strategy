# AI Agent Instructions for Bot Trader Copilot

## Architecture Overview
This is a modular trading system with centralized entry via `descarga_datos/main.py`. Key components:
- **Core**: Data providers (CCXT for crypto, MT5 for forex), order executors, live trading orchestrators
- **Strategies**: ML-enhanced strategies like `UltraDetailedHeikinAshiML` using trained models from `models/`
- **Backtesting**: Parallel optimization with Optuna, results in `data/dashboard_results/`
- **Data Flow**: SQLite primary → CSV fallback → auto-download via `utils/storage.py`
- **Config**: Centralized in `descarga_datos/config/config.yaml` (YAML format)

## Critical Workflows
- **Backtest**: `python descarga_datos/main.py --backtest` (uses config.yaml symbols/timeframes)
- **Optimize**: `python descarga_datos/main.py --optimize` (Optuna trials, saves to models/)
- **Live Trading**: `python descarga_datos/main.py --live` (sandbox mode by default in config)
- **Tests**: `python -m pytest descarga_datos/tests/test_quick_backtest.py` (smoke test)
- **Data Download**: Handled automatically by `ensure_data_availability()` in backtests

## Project Conventions
- **Sandbox First**: Always enable `sandbox: true` in exchange configs for testing
- **ML Models**: Train via optimization, load from `models/` using `ModelManager`
- **Indicators**: Use TALIB via `utils/talib_wrapper.py`, fallback to pandas implementations
- **Risk Management**: ATR-based stops, max drawdown limits from config
- **Logging**: Structured via `utils/logger.py`, metrics in `utils/logger_metrics.py`
- **Dependencies**: Install from root `requirements.txt`, uses virtual env `.venv/`

## Integration Points
- **Exchanges**: CCXT for crypto (Binance/Bybit), MT5 for forex
- **Data Sources**: Yahoo Finance fallback, auto-download for missing data
- **External APIs**: Streamlit dashboard, Plotly for visualization
- **Cross-Component**: Strategies call indicators, risk management applies to all trades

## Examples
- Add new strategy: Extend `strategies/base_strategy.py`, register in config.yaml `strategies:` section
- Modify indicators: Update `indicators/technical_indicators.py`, ensure TALIB compatibility
- Change config: Edit `config/config.yaml`, reload via `config_loader.py`

## AI Response Guidelines
- **Language**: All responses must be in Spanish.
- **Code Modifications**: The strategy (`strategies/ultra_detailed_heikin_ashi_ml_strategy.py`) and main modules (`descarga_datos/main.py`, core modules) are blocked from structural modifications. Only parameter improvements are allowed that enhance functionality and profitability without altering the core structure.

## Data Management Rules
- **Centralized Configuration**: All configuration is centralized in `descarga_datos/config/config.yaml`. Use this for all parameters.
- **Data Verification Flow**: When executing any main function requiring historical data (backtest, optimization, data download, data audit, model training), first verify if data exists in the SQLite database. If present, use those data. If not, proceed to download with corresponding modules, process, verify, calculate necessary indicators, and execute the corresponding main function.
- **Data Priority**: SQLite primary → CSV fallback → auto-download. Never skip verification steps.

## Error Prevention Rules
- **Avoid SQL Metadata Errors**: Ensure correct column count in INSERT statements (e.g., 9 values for 9 columns in data_metadata). Reference `utils/storage.py` fixes.
- **Handle KeyboardInterrupt Gracefully**: Implement try/except/finally blocks for shutdown, always launch dashboard if results exist.
- **Normalize Metrics Consistently**: Win rate must be decimal (0-1), not percentage. Validate in tests.
- **Dashboard Port Fallback**: Check port availability (8519-8523) and use fallback if occupied.
- **Async Shutdown Handling**: Manage `asyncio.CancelledError` and close connections properly.
- **Avoid Synthetic Data**: Never use or generate synthetic data; all operations must use real downloaded or live data.

## Data Integrity Rules
- **Real Data Only**: All metrics, results, and strategy executions must derive from real downloaded or live data. No artificial alterations, improvements, or synthetic enhancements.
- **Result Authenticity**: Metrics and results must be the direct outcome of strategy execution on real data, without manipulation or optimization beyond parameter tuning.

Reference: `descarga_datos/ARCHIVOS MD/README.md` for sandbox testing details.