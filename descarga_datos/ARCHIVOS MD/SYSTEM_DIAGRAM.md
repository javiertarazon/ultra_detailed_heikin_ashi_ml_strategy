# 🗺️ Diagrama Visual del Sistema BotCopilot SAR v3.0

## ARQUITECTURA GENERAL

```
┌─────────────────────────────────────────────────────────────────┐
│                         USUARIO / CLI                           │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                          main.py                                 │
│                   (PUNTO DE ENTRADA ÚNICO)                       │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ --train-ml  │  │ --optimize   │  │ --backtest   │           │
│  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘           │
│         │                │                  │                    │
│         │                │                  │                    │
│  ┌──────▼──────┐  ┌──────▼───────┐  ┌──────▼───────┐           │
│  │ --live-ccxt │  │ --live-mt5   │  │ --data-audit │           │
│  └─────────────┘  └──────────────┘  └──────────────┘           │
└─────────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CAPA DE CONFIGURACIÓN                         │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              config/config.yaml                            │ │
│  │                                                            │ │
│  │  • Símbolos: [BNB/USDT]                                   │ │
│  │  • Timeframe: 4h                                          │ │
│  │  • Estrategia: UltraDetailedHeikinAshiML                  │ │
│  │  • ML Training: Random Forest enabled                     │ │
│  │  • Períodos: 2022-2024                                    │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CAPA DE DATOS                                 │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │  SQLite DB       │  │  CSV Files       │  │  Downloader   │ │
│  │  (Prioridad #1)  │◄─┤  (Fallback)      │◄─┤  (Auto)       │ │
│  │                  │  │                  │  │               │ │
│  │  data/data.db    │  │  data/csv/       │  │  CCXT + MT5   │ │
│  └──────────────────┘  └──────────────────┘  └───────────────┘ │
│                                                                  │
│  Función Centralizada: ensure_data_availability()               │
└─────────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CAPA DE PROCESAMIENTO                         │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │           TechnicalIndicators (Centralizado)              │  │
│  │                                                           │  │
│  │  • Heikin Ashi    • RSI          • MACD                  │  │
│  │  • EMA            • Stochastic   • Volume                │  │
│  │  • ATR            • ADX          • Bollinger             │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                     │
            ┌────────┴────────┐
            │                 │
            ▼                 ▼
┌───────────────────┐  ┌───────────────────┐
│   ML TRAINING     │  │   BACKTESTING     │
│                   │  │                   │
│  MLTrainer        │  │  Orchestrator     │
│  ├─ Download      │  │  ├─ Load Data     │
│  ├─ Features      │  │  ├─ Load Strategy │
│  ├─ Labels        │  │  ├─ Execute       │
│  ├─ TimeSeriesSplit│  │  ├─ Calculate    │
│  ├─ Train RF      │  │  ├─ Metrics       │
│  └─ Save Model    │  │  └─ Save Results  │
│                   │  │                   │
│  models/          │  │  data/dashboard_  │
│  BNB_USDT/        │  │  results/         │
│  RandomForest.pkl │  │  *_results.json   │
└────────┬──────────┘  └─────────┬─────────┘
         │                       │
         │                       │
         ▼                       ▼
┌───────────────────┐  ┌───────────────────┐
│  OPTIMIZATION     │  │   DASHBOARD       │
│                   │  │                   │
│  OptimizationPipe │  │  Streamlit App    │
│  ├─ Train ML      │  │  ├─ Load Results  │
│  ├─ Optuna Study  │  │  ├─ Visualize     │
│  ├─ N Trials      │  │  ├─ Metrics       │
│  ├─ Best Params   │  │  ├─ Equity Curve  │
│  └─ Backtest      │  │  └─ Trade List    │
│                   │  │                   │
│  data/optimization│  │  Port: 8520       │
│  _results/        │  │  Auto-launch      │
└───────────────────┘  └───────────────────┘
```

---

## FLUJO DE DATOS DETALLADO

```
┌─────────────────────────────────────────────────────────────────┐
│                   FLUJO COMPLETO DE DATOS                        │
└─────────────────────────────────────────────────────────────────┘

  USER INPUT
      │
      ▼
  ┌─────────┐
  │ main.py │
  └────┬────┘
       │
       ├───[1]─→ validate_system()
       │            └─→ Verificar config + estrategias + deps
       │
       ├───[2]─→ verify_data_availability()
       │            │
       │            ├─→ [A] Check SQLite
       │            │      ├─ EXISTS? → Return data ✅
       │            │      └─ NOT EXISTS? → Continue to [B]
       │            │
       │            ├─→ [B] Check CSV
       │            │      ├─ EXISTS? → Save to SQLite → Return data ✅
       │            │      └─ NOT EXISTS? → Continue to [C]
       │            │
       │            └─→ [C] Download Automatically
       │                   ├─ CCXT (Binance/Bybit)
       │                   ├─ MT5 (Forex/Stocks)
       │                   ├─ Save to SQLite
       │                   ├─ Save to CSV
       │                   └─ Return data ✅
       │
       ├───[3]─→ MODE SELECTION
       │         │
       │         ├─→ [--train-ml]
       │         │      │
       │         │      └─→ MLTrainer
       │         │             │
       │         │             ├─→ download_data()
       │         │             │      └─→ ensure_data_availability()
       │         │             │
       │         │             ├─→ prepare_features()
       │         │             │      └─→ TechnicalIndicators.calculate_all()
       │         │             │
       │         │             ├─→ create_labels()
       │         │             │      └─→ future_returns based
       │         │             │
       │         │             ├─→ TimeSeriesSplit(n_splits=5)
       │         │             │      ├─ Fold 1: Train[0:20%] → Val[20:40%]
       │         │             │      ├─ Fold 2: Train[0:40%] → Val[40:60%]
       │         │             │      ├─ Fold 3: Train[0:60%] → Val[60:80%]
       │         │             │      ├─ Fold 4: Train[0:80%] → Val[80:100%]
       │         │             │      └─ NO LOOK-AHEAD BIAS ✅
       │         │             │
       │         │             ├─→ train_random_forest()
       │         │             │      ├─ n_estimators: 100
       │         │             │      ├─ max_depth: 10
       │         │             │      └─ Cross-validation
       │         │             │
       │         │             └─→ save_model()
       │         │                    ├─ models/BNB_USDT/RandomForest.joblib
       │         │                    ├─ models/BNB_USDT/RandomForest_scaler.joblib
       │         │                    └─ models/BNB_USDT/RandomForest_metadata.json
       │         │
       │         ├─→ [--optimize]
       │         │      │
       │         │      └─→ OptimizationPipeline
       │         │             │
       │         │             ├─→ Phase 1: Train ML
       │         │             │      └─→ MLTrainer.run()
       │         │             │
       │         │             ├─→ Phase 2: Optimize Parameters
       │         │             │      ├─→ Optuna Study
       │         │             │      ├─→ N Trials (100)
       │         │             │      └─→ Multi-objective:
       │         │             │             • Max: PnL, Win Rate, Profit Factor
       │         │             │             • Min: Max Drawdown
       │         │             │
       │         │             ├─→ Phase 3: Backtest with Best Params
       │         │             │      └─→ AdvancedBacktester
       │         │             │
       │         │             └─→ Phase 4: Save Results
       │         │                    └─→ data/optimization_results/
       │         │
       │         ├─→ [--backtest-only]
       │         │      │
       │         │      └─→ BacktestingOrchestrator
       │         │             │
       │         │             ├─→ load_strategies_from_config()
       │         │             │      └─→ UltraDetailedHeikinAshiML
       │         │             │
       │         │             ├─→ ensure_data_availability()
       │         │             │      └─→ SQLite → CSV → Download
       │         │             │
       │         │             ├─→ FOR EACH SYMBOL:
       │         │             │      │
       │         │             │      └─→ FOR EACH STRATEGY:
       │         │             │             │
       │         │             │             ├─→ strategy.run(data, symbol)
       │         │             │             │      │
       │         │             │             │      ├─→ calculate_heikin_ashi()
       │         │             │             │      ├─→ calculate_indicators()
       │         │             │             │      ├─→ predict_signal() [ML]
       │         │             │             │      ├─→ apply_filters()
       │         │             │             │      └─→ execute_trades()
       │         │             │             │
       │         │             │             └─→ AdvancedBacktester
       │         │             │                    ├─ Entry signals
       │         │             │                    ├─ Exit signals
       │         │             │                    ├─ Position sizing (Kelly)
       │         │             │                    ├─ Risk management
       │         │             │                    └─ Calculate metrics
       │         │             │
       │         │             ├─→ save_results()
       │         │             │      └─→ data/dashboard_results/*.json
       │         │             │
       │         │             └─→ launch_dashboard()
       │         │                    └─→ http://localhost:8520
       │         │
       │         ├─→ [--live-ccxt]
       │         │      │
       │         │      └─→ LiveTradingOrchestrator (CCXT)
       │         │             │
       │         │             ├─→ Verify Security (DEMO/REAL)
       │         │             ├─→ Connect to Exchange (Binance)
       │         │             ├─→ Load Strategy
       │         │             ├─→ LOOP:
       │         │             │      ├─ Fetch OHLCV
       │         │             │      ├─ Generate Signal
       │         │             │      ├─ Check Position
       │         │             │      ├─ Execute Order
       │         │             │      ├─ Monitor SL/TP
       │         │             │      └─ Wait next cycle
       │         │             └─→ Emergency Stop
       │         │
       │         ├─→ [--live-mt5]
       │         │      │
       │         │      └─→ LiveTradingOrchestrator (MT5)
       │         │             └─→ (Similar flow to CCXT)
       │         │
       │         └─→ [--data-audit]
       │                │
       │                └─→ check_data_status()
       │                       ├─→ Verify SQLite
       │                       ├─→ Verify CSV
       │                       ├─→ Identify missing
       │                       └─→ Download missing
       │
       └───[4]─→ RESULTS OUTPUT
                  │
                  ├─→ Terminal Logs
                  ├─→ logs/bot_trader.log
                  ├─→ data/dashboard_results/*.json
                  └─→ Dashboard UI (port 8520)
```

---

## FLUJO DE ML PREDICTION

```
┌─────────────────────────────────────────────────────────────────┐
│         PREDICCIÓN ML EN ESTRATEGIA (predict_signal)             │
└─────────────────────────────────────────────────────────────────┘

  ENTRADA: data (DataFrame con OHLCV + indicadores)
      │
      ▼
  ┌─────────────────────────────────────────────────────┐
  │ 1. Cargar Modelo y Scaler                           │
  │                                                      │
  │    model_path = models/BNB_USDT/RandomForest.joblib │
  │    model = joblib.load(model_path)                  │
  │    scaler = joblib.load(scaler_path)                │
  └────────────────────┬────────────────────────────────┘
                       │
                       ▼
  ┌─────────────────────────────────────────────────────┐
  │ 2. Preparar Features (IDÉNTICOS al entrenamiento)   │
  │                                                      │
  │    features = prepare_features(data)                │
  │    │                                                 │
  │    ├─→ RSI, EMA, MACD, ATR, ADX, Stochastic        │
  │    ├─→ Volume indicators                            │
  │    ├─→ Heikin Ashi features                         │
  │    └─→ Price patterns                               │
  └────────────────────┬────────────────────────────────┘
                       │
                       ▼
  ┌─────────────────────────────────────────────────────┐
  │ 3. Validar Número de Features (DINÁMICO)            │
  │                                                      │
  │    expected_features = len(features.columns)  ✅    │
  │    # NO hardcodear: expected_features = 21 ❌       │
  │                                                      │
  │    if features.shape[1] != expected_features:       │
  │        raise ValueError("Feature mismatch")         │
  └────────────────────┬────────────────────────────────┘
                       │
                       ▼
  ┌─────────────────────────────────────────────────────┐
  │ 4. Validar Scaler Fitted                            │
  │                                                      │
  │    if not hasattr(scaler, 'mean_'):                 │
  │        logger.warning("Scaler not fitted")          │
  │        return pd.Series(0.5, index=data.index)      │
  │        # Retornar señales neutrales como fallback   │
  └────────────────────┬────────────────────────────────┘
                       │
                       ▼
  ┌─────────────────────────────────────────────────────┐
  │ 5. Normalizar Features                              │
  │                                                      │
  │    features_scaled = scaler.transform(features)     │
  │    # StandardScaler: (x - mean) / std               │
  └────────────────────┬────────────────────────────────┘
                       │
                       ▼
  ┌─────────────────────────────────────────────────────┐
  │ 6. Predecir Probabilidades                          │
  │                                                      │
  │    probas = model.predict_proba(features_scaled)    │
  │    │                                                 │
  │    ├─→ probas[:, 0] = Probabilidad SHORT (-1)      │
  │    ├─→ probas[:, 1] = Probabilidad NEUTRAL (0)     │
  │    └─→ probas[:, 2] = Probabilidad LONG (1)        │
  └────────────────────┬────────────────────────────────┘
                       │
                       ▼
  ┌─────────────────────────────────────────────────────┐
  │ 7. Convertir a Señales con Threshold                │
  │                                                      │
  │    signals = pd.Series(0, index=data.index)         │
  │    │                                                 │
  │    if probas[:, 2] > ml_threshold:                  │
  │        signals = 1   # LONG                         │
  │    elif probas[:, 0] > ml_threshold:                │
  │        signals = -1  # SHORT                        │
  │    else:                                            │
  │        signals = 0   # NEUTRAL                      │
  │                                                      │
  │    # ml_threshold típicamente = 0.5                 │
  └────────────────────┬────────────────────────────────┘
                       │
                       ▼
  ┌─────────────────────────────────────────────────────┐
  │ 8. Aplicar Filtros Adicionales                      │
  │                                                      │
  │    ├─→ ADX > 25 (tendencia fuerte)                 │
  │    ├─→ Volume ratio > 1.4                           │
  │    ├─→ Stochastic overbought/oversold               │
  │    └─→ ML confidence > threshold                    │
  └────────────────────┬────────────────────────────────┘
                       │
                       ▼
  ┌─────────────────────────────────────────────────────┐
  │ 9. Retornar Señales Finales                         │
  │                                                      │
  │    return signals                                   │
  │    │                                                 │
  │    └─→ pd.Series con valores: -1, 0, 1             │
  └─────────────────────────────────────────────────────┘
      │
      ▼
  SALIDA: signals → Usadas por la estrategia para entry/exit
```

---

## VALIDACIÓN DE INTEGRIDAD

```
┌─────────────────────────────────────────────────────────────────┐
│                    CHECKPOINTS DE VALIDACIÓN                     │
└─────────────────────────────────────────────────────────────────┘

  [✅] Punto de Entrada Único
       └─→ Solo main.py autorizado
       └─→ NO usar archivos alternativos

  [✅] Configuración Centralizada
       └─→ Solo config/config.yaml
       └─→ Una sola estrategia activa

  [✅] Datos Reales Obligatorios
       └─→ SQLite prioritario
       └─→ CSV fallback
       └─→ Descarga automática
       └─→ NO sintéticos

  [✅] ML Sin Sesgos
       └─→ TimeSeriesSplit ✅
       └─→ NO train_test_split ❌
       └─→ Features dinámicos
       └─→ Labels sin NaN

  [✅] Modelos Centralizados
       └─→ models/ única ubicación
       └─→ ModelManager gestiona
       └─→ Validación de scaler

  [✅] Estrategia Única
       └─→ UltraDetailedHeikinAshiML
       └─→ Indicadores centralizados
       └─→ ML integrado

  [✅] Backtesting Preciso
       └─→ Comisiones reales
       └─→ Slippage considerado
       └─→ Métricas completas

  [✅] Seguridad Live Trading
       └─→ Verificación DEMO/REAL
       └─→ Advertencias críticas
       └─→ Emergency stop
```

---

## RESUMEN EJECUTIVO

```
┌──────────────────────────────────────────────────────────────┐
│                    ESTADO DEL SISTEMA                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ✅ Arquitectura: Centralizada y Modular                     │
│  ✅ Punto de Entrada: Único (main.py)                        │
│  ✅ Configuración: Simplificada (config.yaml)                │
│  ✅ Datos: SQLite-First con fallback automático              │
│  ✅ ML: TimeSeriesSplit (sin look-ahead bias)                │
│  ✅ Estrategia: Una sola activa y optimizada                 │
│  ✅ Modelos: Centralizados en descarga_datos/models/         │
│  ✅ Backtesting: Completo y preciso                          │
│  ✅ Optimización: Pipeline Optuna integrado                  │
│  ✅ Live Trading: Seguro con verificaciones                  │
│  ✅ Dashboard: Auto-lanzamiento en puerto 8520               │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                    PRÓXIMO PASO                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  🚀 ENTRENAR MODELO ML:                                      │
│     cd descarga_datos                                        │
│     python main.py --train-ml                                │
│                                                              │
│  📊 EJECUTAR BACKTEST:                                       │
│     python main.py --backtest-only                           │
│                                                              │
│  🔬 OPTIMIZAR (opcional):                                    │
│     python main.py --optimize                                │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

**Diagrama generado**: 9 de octubre de 2025  
**Versión**: 3.0 - Clean & Optimized  
**Estado**: ✅ Sistema Validado y Listo para Uso
