# Strategies folder for trading logic

## Active Strategy

Only **UltraDetailedHeikinAshiML** strategy is currently active and maintained.

### Strategy Details
- **File**: `ultra_detailed_heikin_ashi_ml_strategy.py`
- **Symbol**: BNB/USDT (4h timeframe)
- **ML Model**: RandomForest with TimeSeriesSplit validation
- **Features**: Technical indicators (Heikin Ashi, ATR, ADX, EMAs, SAR, Volatility)
- **Risk Management**: ATR-based stops, Kelly fraction sizing

### Configuration
Strategy is activated in `config/config.yaml` under `backtesting.strategies.UltraDetailedHeikinAshiML: true`

### Archived Strategies
All other strategies have been moved to archive and are not maintained. The system is focused solely on the UltraDetailedHeikinAshiML strategy for optimal performance.