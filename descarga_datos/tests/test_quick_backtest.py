import os
import pandas as pd
import asyncio
from strategies.ut_bot_psar_compensation import UTBotPSARCompensationStrategy
from config.config_loader import load_config_from_yaml
from utils.logger import setup_logging, get_logger
from main import save_backtest_results, save_global_summary


def test_quick_backtest_smoke():
    os.chdir(os.path.join(os.path.dirname(__file__), '..'))
    df = pd.read_csv('data/csv/AAPL_US_15m.csv').head(600)
    strat = UTBotPSARCompensationStrategy(max_account_drawdown=7.5, anticipatory_stop_threshold=0.98)
    res = strat.run(df, 'AAPL.US')

    # Estructura básica
    assert isinstance(res, dict)
    assert 'total_trades' in res
    assert 'trades' in res
    assert 'equity_curve' in res

    # Trades y métricas coherentes
    assert res['total_trades'] >= 0
    assert isinstance(res['trades'], list)

    # Persistencia simple
    config = load_config_from_yaml()
    setup_logging(config.system.log_level, config.system.log_file)
    logger = get_logger(__name__)

    async def persist():
        await save_backtest_results({'Estrategia_Compensacion': res}, 'AAPL.US', config, logger)
        await save_global_summary({'AAPL.US': {'Estrategia_Compensacion': res}}, config, logger)

    asyncio.run(persist())

    # Verifica archivos generados
    out_file = os.path.join('data', 'dashboard_results', 'AAPL_US_results.json')
    assert os.path.exists(out_file)
