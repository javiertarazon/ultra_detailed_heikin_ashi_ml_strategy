import streamlit as st
import pandas as pd
import json
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import yaml
from datetime import datetime
from utils.logger import get_logger

# Inicializar logger
logger = get_logger(__name__)

# ==============================================================
# Funciones puras reutilizables (aptas para tests sin Streamlit)
# ==============================================================

def sanitize_numeric_value(value, max_value=1e12):
    """Sanitiza valores numéricos para evitar overflow y valores irreales."""
    if value is None:
        return 0.0
    
    if not isinstance(value, (int, float)):
        return 0.0
    
    if np.isnan(value) or np.isinf(value):
        return 0.0
    
    # Limitar valores extremos
    if abs(value) > max_value:
        return max_value if value > 0 else -max_value
    
    return float(value)

def summarize_results_structured(results: dict) -> pd.DataFrame:
    """Genera un DataFrame resumen (símbolo/estrategia) a partir de la
    estructura de resultados cargada por load_results().

    Estructura esperada:
    {
        'BTC/USDT': {
            'symbol': 'BTC/USDT',
            'strategies': {
                'MyStrategy': { 'total_trades': ..., 'win_rate': ..., 'total_pnl': ... }
            }
        },
        ...
    }

    Returns:
        DataFrame con columnas: ['symbol','strategy','total_trades','win_rate','total_pnl','max_drawdown']
        (win_rate en decimal 0-1, no porcentaje)
    """
    rows = []
    for sym, data in results.items():
        strategies = data.get('strategies', {}) if isinstance(data, dict) else {}
        for strat_name, strat_data in strategies.items():
            if not isinstance(strat_data, dict):
                continue
            wr = strat_data.get('win_rate', 0) or 0
            # Normalizar win_rate si viene como porcentaje (>1)
            if isinstance(wr, (int, float)) and wr > 1:
                wr = wr / 100.0
            
            # Sanitizar valores numéricos para evitar overflow
            total_pnl = sanitize_numeric_value(strat_data.get('total_pnl', 0.0))
            max_drawdown = sanitize_numeric_value(strat_data.get('max_drawdown', 0.0))
            
            rows.append({
                'symbol': sym,
                'strategy': strat_name,
                'total_trades': strat_data.get('total_trades', 0) or 0,
                'win_rate': wr,
                'total_pnl': total_pnl,
                'max_drawdown': max_drawdown
            })
    return pd.DataFrame(rows)

st.set_page_config(layout="wide", page_title="Dashboard de Backtesting Avanzado", page_icon="🤖")

# Definir estilos CSS para hacer la interfaz más compacta
st.markdown("""
<style>
    /* Reducir tamaño de títulos */
    .st-emotion-cache-10trblm {
        font-size: 1.2rem; /* Título principal más pequeño */
        margin-bottom: 0.5rem;
    }
    /* Reducir tamaño de subtítulos */
    .st-emotion-cache-1629p8f {
        font-size: 1.0rem; /* Subtítulos más pequeños */
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }
    /* Hacer más compactos los widgets de métricas */
    .st-emotion-cache-1r6slb0 {
        padding-top: 0.2rem;
        padding-bottom: 0.2rem;
    }
    /* Reducir espacio vertical entre elementos */
    .st-emotion-cache-16txtl3 {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    /* Ajustar el tamaño del texto en las métricas */
    .st-emotion-cache-1xarl3l {
        font-size: 0.9rem; /* Texto de etiqueta más pequeño */
    }
    .st-emotion-cache-1wivap2 {
        font-size: 1.1rem; /* Texto de valor más pequeño */
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=30)  # Cache por 30 segundos para permitir actualizaciones en live trading
def load_results():
    """
    Carga datos de LIVE TRADING directamente desde Binance, o archivos de backtesting.
    Prioriza datos REALES de operaciones ejecutadas en Binance.
    """
    # Intentar cargar datos DIRECTOS de Binance primero
    live_data = load_live_data_from_binance()

    if live_data and live_data.get('is_live_data', False):
        logger.info("✅ Cargando datos DIRECTOS de operaciones ejecutadas en Binance")
        return live_data['results'], live_data['global_summary']

    # Si no hay datos directos de Binance, intentar archivos guardados
    live_results_dir = Path(__file__).parent.parent / "data" / "live_trading_results"

    if live_results_dir.exists():
        # Buscar el archivo de resultados de live trading más reciente
        live_files = sorted(live_results_dir.glob("crypto_live_results_*.json"))
        if live_files:
            latest_live_file = live_files[-1]
            try:
                with open(latest_live_file, 'r', encoding='utf-8') as f:
                    live_data = json.load(f)

                # Verificar que tenga datos válidos
                if 'live_metrics' in live_data and live_data['live_metrics'].get('total_trades', 0) > 0:
                    logger.info(f"📁 Cargando datos de archivo guardado: {latest_live_file.name}")

                    # Crear estructura compatible con dashboard para live trading
                    results = {}
                    global_summary = create_global_summary_from_live_metrics(live_data['live_metrics'])

                    results['LIVE_TRADING'] = {
                        'symbol': 'LIVE_TRADING',
                        'strategies': {
                            'LiveStrategy': live_data['live_metrics']
                        }
                    }

                    return results, global_summary

            except Exception as e:
                st.warning(f"Error cargando datos de live trading guardados: {e}")

    # Si no hay datos de live trading, cargar datos de backtesting normales
    logger.info("📊 Cargando datos de backtesting (no hay datos de live trading)")
    results, global_summary = load_backtesting_results()
    return results, global_summary


def load_live_data_from_binance():
    """
    Carga datos DIRECTOS de operaciones ejecutadas en Binance.

    Returns:
        Diccionario con datos de live trading desde Binance, o None si no hay datos
    """
    try:
        from utils.live_trading_data_reader import LiveTradingDataReader

        # Determinar si usar testnet o cuenta real
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        try:
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # Verificar configuración de live trading
            live_config = config.get('live_trading', {})
            account_type = live_config.get('account_type', 'SANDBOX')
            use_testnet = account_type.upper() == 'SANDBOX'

        except Exception:
            use_testnet = True  # Por defecto usar testnet

        # Inicializar lector de datos
        reader = LiveTradingDataReader(testnet=use_testnet)

        if not reader.test_connection():
            logger.warning("No se pudo conectar a Binance para leer datos en tiempo real")
            return None

        # Obtener métricas directamente desde Binance
        live_metrics = reader.calculate_live_metrics_from_binance()

        if not live_metrics or live_metrics.get('total_trades', 0) == 0:
            logger.info("No se encontraron operaciones ejecutadas en Binance")
            return None

        # Obtener balance actual
        balance_info = reader.get_account_balance()

        # Actualizar métricas con balance real
        if balance_info:
            live_metrics['current_balance'] = balance_info.get('free_usdt', 0)
            live_metrics['total_balance'] = balance_info.get('total_usdt', 0)

        # Crear estructura para dashboard
        results = {}
        global_summary = create_global_summary_from_live_metrics(live_metrics)

        results['LIVE_TRADING_BINANCE'] = {
            'symbol': 'LIVE_TRADING_BINANCE',
            'strategies': {
                'BinanceLive': live_metrics
            }
        }

        logger.info(f"✅ Datos cargados directamente desde Binance: {live_metrics.get('total_trades', 0)} operaciones")

        return {
            'results': results,
            'global_summary': global_summary,
            'is_live_data': True,
            'data_source': 'BINANCE_DIRECT'
        }

    except Exception as e:
        logger.error(f"Error cargando datos directos de Binance: {e}")
        return None


def create_global_summary_from_live_metrics(live_metrics):
    """
    Crea el resumen global compatible con dashboard desde métricas de live trading.
    """
    return {
        'period': {
            'start_date': live_metrics.get('start_time', 'N/A'),
            'end_date': live_metrics.get('end_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            'timeframe': 'LIVE',
            'mode': 'LIVE_TRADING_BINANCE'
        },
        'metrics': {
            'total_pnl': live_metrics.get('total_pnl', 0),
            'total_trades': live_metrics.get('total_trades', 0),
            'avg_win_rate': live_metrics.get('win_rate', 0) * 100,  # Convertir a porcentaje
            'max_drawdown': live_metrics.get('max_drawdown', 0) * 100,  # Convertir a porcentaje
            'profit_factor': live_metrics.get('profit_factor', 0),
            'expectancy': live_metrics.get('expectancy', 0),
            'sharpe_ratio': live_metrics.get('sharpe_ratio', 0),
            'sortino_ratio': live_metrics.get('sortino_ratio', 0),
            'calmar_ratio': live_metrics.get('calmar_ratio', 0),
            'recovery_factor': live_metrics.get('recovery_factor', 0),
            'current_balance': live_metrics.get('current_balance', 0),
            'total_volume': live_metrics.get('total_volume', 0)
        },
        'total_symbols': len(live_metrics.get('symbols_traded', [])),
        'mode': 'LIVE_TRADING_BINANCE',
        'data_source': live_metrics.get('data_source', 'UNKNOWN')
    }


def load_backtesting_results():
    """
    Carga archivos JSON de resultados de backtesting (función original).
    """
    base = Path(__file__).parent.parent / "data" / "dashboard_results"
    results, global_summary = {}, {}
    if not base.exists():
        return {}, {}

    # Guardar lista de estrategias encontradas para debug
    all_strategies_found = set()

    # Cargar archivos de símbolo
    for f in sorted(base.glob("*_results.json")):
        if f.name == 'global_summary.json':
            continue
        # Excluir archivos con datos simulados para mantener consistencia
        if 'realistic' in f.name:
            continue

        try:
            with open(f, 'r', encoding='utf-8') as fh:
                d = json.load(fh)

            # Extraer símbolo del nombre del archivo
            sym = f.stem.replace('_results', '').replace('_', '/')

            # Normalización y validación de estructura JSON
            if isinstance(d, dict):
                # Caso 1: Formato estándar {'symbol': 'XXX', 'strategies': {'Strategy1': {...}, 'Strategy2': {...}}}
                if 'symbol' in d and 'strategies' in d and isinstance(d['strategies'], dict):
                    # Ya tiene el formato correcto
                    normalized_data = d

                # Caso 2: Solo tiene estrategias {'Strategy1': {...}, 'Strategy2': {...}}
                elif all(isinstance(v, dict) and 'total_trades' in v for k, v in d.items()):
                    normalized_data = {'symbol': sym, 'strategies': d}

                # Caso 3: Un solo resultado sin estructura {'total_trades': X, 'win_rate': Y, ...}
                elif 'total_trades' in d and 'win_rate' in d:
                    normalized_data = {'symbol': sym, 'strategies': {'Default': d}}

                # Caso 4: El símbolo es la clave principal {'EURUSD': {'Strategy1': {...}, 'Strategy2': {...}}}
                elif len(d) == 1 and isinstance(list(d.values())[0], dict):
                    symbol_key = list(d.keys())[0]
                    strategies_data = d[symbol_key]

                    # Verificar si strategies_data ya es un dict de estrategias o solo una estrategia
                    if all(isinstance(v, dict) and 'total_trades' in v for k, v in strategies_data.items()):
                        normalized_data = {'symbol': symbol_key, 'strategies': strategies_data}
                    else:
                        normalized_data = {'symbol': symbol_key, 'strategies': {'Default': strategies_data}}
                else:
                    # Formato desconocido, intentar adaptarlo lo mejor posible
                    normalized_data = {'symbol': sym, 'strategies': {'Default': d}}
            else:
                # No es un diccionario, error en el archivo
                st.warning(f"Archivo {f.name} no contiene un diccionario válido. Contenido: {d}")
                continue

            # Recopilar todas las estrategias encontradas
            for strategy_name in normalized_data['strategies'].keys():
                all_strategies_found.add(strategy_name)

            results[sym] = normalized_data

        except Exception as e:
            st.error(f"Error al cargar {f.name}: {str(e)}")
            continue

    # Guardar lista de estrategias encontradas en un archivo para debug
    try:
        with open(base / "estrategias_encontradas.txt", 'w', encoding='utf-8') as f:
            f.write("Estrategias encontradas en archivos JSON:\n")
            for strategy in sorted(all_strategies_found):
                f.write(f"- {strategy}\n")
    except Exception:
        pass

    # Cargar resumen global
    gs = base / 'global_summary.json'
    if gs.exists():
        with open(gs, 'r', encoding='utf-8') as fh:
            global_summary = json.load(fh)

    return results, global_summary


@st.cache_data(ttl=60)  # Cache configuración por 1 minuto
def load_config():
    """
    Carga la configuración actual del sistema.
    """
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        st.error(f"Error cargando configuración: {e}")
        return None


def calculate_drawdown_percentage(max_drawdown, total_pnl):
    """
    DEPRECATED: El drawdown ya viene calculado correctamente del backtester.
    Esta función se mantiene por compatibilidad pero no debe usarse.
    """
    return max_drawdown  # Retornar el valor directo ya que viene en porcentaje


def generate_equity_curve_from_trades(trades, initial_capital):
    """
    Genera una curva de equity a partir de una lista de trades.
    """
    if not trades:
        return [initial_capital]
    
    equity_curve = [initial_capital]
    current_capital = initial_capital
    
    for trade in trades:
        pnl = trade.get('pnl', 0)
        current_capital += pnl
        equity_curve.append(current_capital)
    
    return equity_curve


def validate_and_clean_metrics(strategy_data):
    """
    Valida y limpia los datos de métricas para evitar errores de presentación.
    """
    cleaned_data = {}
    
    # Métricas numéricas que deben ser float
    float_metrics = [
        'total_pnl', 'max_drawdown', 'sharpe_ratio', 'profit_factor', 
        'avg_trade_pnl', 'avg_win_pnl', 'avg_loss_pnl', 'largest_win', 
        'largest_loss', 'total_compensation_pnl'
    ]
    
    # Métricas que deben ser int
    int_metrics = [
        'total_trades', 'winning_trades', 'losing_trades', 'compensated_trades'
    ]
    
    # Métricas de porcentaje que necesitan normalización especial
    percentage_metrics = [
        'win_rate', 'compensation_success_rate', 'compensation_ratio'
    ]
    
    # Procesar métricas float normales
    for metric in float_metrics:
        value = strategy_data.get(metric, 0)
        try:
            cleaned_value = float(value) if value is not None else 0.0
            # Manejar valores infinitos
            if cleaned_value == float('inf'):
                cleaned_value = 999.99
            elif cleaned_value == float('-inf'):
                cleaned_value = -999.99
            # Manejar NaN
            elif cleaned_value != cleaned_value:  # NaN check
                cleaned_value = 0.0
            cleaned_data[metric] = cleaned_value
        except (ValueError, TypeError):
            cleaned_data[metric] = 0.0
    
    # Procesar métricas de porcentaje (normalizar a decimal 0-1)
    for metric in percentage_metrics:
        value = strategy_data.get(metric, 0)
        try:
            cleaned_value = float(value) if value is not None else 0.0
            # Si el valor es mayor a 1, asumimos que está en formato porcentaje (ej: 34.6 = 34.6%)
            # y lo convertimos a decimal (ej: 0.346)
            if cleaned_value > 1.0:
                cleaned_value = cleaned_value / 100.0
            # Limitar entre 0 y 1
            cleaned_value = max(0.0, min(1.0, cleaned_value))
            cleaned_data[metric] = cleaned_value
        except (ValueError, TypeError):
            cleaned_data[metric] = 0.0
    
    # Procesar métricas int
    for metric in int_metrics:
        value = strategy_data.get(metric, 0)
        try:
            cleaned_data[metric] = int(value) if value is not None else 0
        except (ValueError, TypeError):
            cleaned_data[metric] = 0
    
    # Copiar otros datos sin modificar
    for key, value in strategy_data.items():
        if key not in float_metrics and key not in int_metrics and key not in percentage_metrics:
            cleaned_data[key] = value
    
    return cleaned_data


def plot_equity_curve(equity_curve, symbol, strategy_name):
    """Genera la figura de la curva de equity con análisis detallado."""
    if not equity_curve or len(equity_curve) < 2:
        # Crear figura vacía con mensaje
        fig = go.Figure()
        fig.add_annotation(
            text="No hay datos de equity curve disponibles",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle',
            showarrow=False, font=dict(size=16)
        )
        fig.update_layout(
            title=f"Curva de Capital - {symbol} ({strategy_name})",
            height=400
        )
        return fig

    df = pd.DataFrame({'Equity': equity_curve})
    df['Punto'] = df.index + 1  # Número de punto en la curva (1-based)
    df['Drawdown'] = ((df['Equity'].cummax() - df['Equity']) / df['Equity'].cummax() * 100).fillna(0)  # Drawdown como valores positivos

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                       subplot_titles=[f"Curva de Capital - {symbol} ({strategy_name})", "Drawdown"],
                       vertical_spacing=0.1)

    # Curva de equity
    fig.add_trace(go.Scatter(x=df['Punto'], y=df['Equity'], mode='lines',
                            name='Capital', line=dict(color='blue', width=2)), row=1, col=1)

    # Drawdown (ya calculado como valores positivos)
    fig.add_trace(go.Scatter(x=df['Punto'], y=df['Drawdown'], mode='lines',
                            name='Drawdown', fill='tozeroy',
                            line=dict(color='red', width=1),
                            fillcolor='rgba(255, 0, 0, 0.3)'), row=2, col=1)

    fig.update_layout(height=600, template="plotly_white", showlegend=True)
    fig.update_yaxes(title_text="Capital ($)", row=1, col=1, tickformat="$,.0f")
    fig.update_yaxes(title_text="Drawdown (%)", row=2, col=1, tickformat=".1f")
    fig.update_xaxes(title_text="Puntos en la Curva", row=2, col=1, tickmode='auto')

    # Añadir estadísticas como anotaciones
    max_equity = df['Equity'].max()
    max_drawdown_value = df['Drawdown'].max()  # Drawdown ya es positivo
    final_equity = df['Equity'].iloc[-1]
    total_return = ((final_equity - df['Equity'].iloc[0]) / df['Equity'].iloc[0]) * 100

    fig.add_annotation(
        text=f"📊 Estadísticas de Rendimiento<br>" +
             f"Capital Inicial: ${df['Equity'].iloc[0]:,.0f}<br>" +
             f"Capital Final: ${final_equity:,.0f}<br>" +
             f"Retorno Total: {total_return:.1f}%<br>" +
             f"Máximo Capital: ${max_equity:,.0f}<br>" +
             f"Max Drawdown: {max_drawdown_value:.1f}%",
        xref="paper", yref="paper",
        x=0.02, y=0.98, xanchor='left', yanchor='top',
        showarrow=False, font=dict(size=10),
        bgcolor="rgba(255,255,255,0.9)", bordercolor="gray", borderwidth=1,
        align="left"
    )

    return fig


def plot_pnl_distribution(trades, strategy_name):
    """Genera análisis detallado de distribución de P&L."""
    if not trades:
        return go.Figure()

    pnl_values = [t.get('pnl', 0) for t in trades]
    # Asegurar que los porcentajes se muestren correctamente (algunos pueden venir en formato decimal)
    pnl_percent = [t.get('pnl_percent', 0) for t in trades]
    # Convertir a porcentaje si los valores son muy pequeños (probablemente decimales)
    if pnl_percent and max(abs(p) for p in pnl_percent if isinstance(p, (int, float))) < 10:
        pnl_percent = [p * 100 for p in pnl_percent]

    fig = make_subplots(rows=1, cols=2,
                       subplot_titles=[f"Distribución P&L ($) - {strategy_name}",
                                     f"Distribución P&L (%) - {strategy_name}"])

    # Histograma de P&L en dólares
    fig.add_trace(go.Histogram(x=pnl_values, name='P&L ($)', nbinsx=50,
                              marker_color='lightblue'), row=1, col=1)

    # Histograma de P&L en porcentaje
    fig.add_trace(go.Histogram(x=pnl_percent, name='P&L (%)', nbinsx=50,
                              marker_color='lightgreen'), row=1, col=2)

    fig.update_layout(height=400, template="plotly_white")
    return fig


def plot_winners_vs_losers(trades, strategy_name):
    """Analiza y grafica traders ganadores vs perdedores."""
    if not trades:
        return go.Figure()

    winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
    losing_trades = [t for t in trades if t.get('pnl', 0) <= 0]

    win_pnl = [t['pnl'] for t in winning_trades]
    lose_pnl = [t['pnl'] for t in losing_trades]

    # Estadísticas
    avg_win = np.mean(win_pnl) if win_pnl else 0
    avg_loss = np.mean(lose_pnl) if lose_pnl else 0
    largest_win = max(win_pnl) if win_pnl else 0
    largest_loss = min(lose_pnl) if lose_pnl else 0

    fig = make_subplots(rows=2, cols=2,
                       subplot_titles=[f"Trades Ganadores ({len(winning_trades)})",
                                     f"Trades Perdedores ({len(losing_trades)})",
                                     "Estadísticas Ganadores", "Estadísticas Perdedores"],
                       specs=[[{"type": "histogram"}, {"type": "histogram"}],
                             [{"type": "table"}, {"type": "table"}]])

    # Histogramas
    if win_pnl:
        fig.add_trace(go.Histogram(x=win_pnl, name='Ganadores', marker_color='green'), row=1, col=1)
    if lose_pnl:
        fig.add_trace(go.Histogram(x=lose_pnl, name='Perdedores', marker_color='red'), row=1, col=2)

    # Tablas de estadísticas
    fig.add_trace(go.Table(
        header=dict(values=['Métrica', 'Valor ($)']),
        cells=dict(values=[
            ['Promedio', 'Máximo', 'Total'],
            [f"${avg_win:.2f}", f"${largest_win:.2f}", f"${sum(win_pnl):.2f}"]
        ])
    ), row=2, col=1)

    fig.add_trace(go.Table(
        header=dict(values=['Métrica', 'Valor ($)']),
        cells=dict(values=[
            ['Promedio', 'Mínimo', 'Total'],
            [f"${avg_loss:.2f}", f"${largest_loss:.2f}", f"${sum(lose_pnl):.2f}"]
        ])
    ), row=2, col=2)

    fig.update_layout(height=800, template="plotly_white")
    return fig


def plot_strategy_comparison(results, selected_symbol):
    """Compara todas las estrategias para un símbolo específico."""
    if selected_symbol not in results:
        return go.Figure()

    strategies = results[selected_symbol].get('strategies', {})
    if not strategies:
        return go.Figure()

    strategy_names = []
    pnl_values = []
    win_rates = []
    total_trades = []
    max_drawdowns = []

    for name, data in strategies.items():
        strategy_names.append(name)
        # Sanitizar P&L para evitar valores extremos
        pnl_values.append(sanitize_numeric_value(data.get('total_pnl', 0)))
        # Guardar win_rate en formato decimal (0-1) para evitar doble multiplicación
        raw_wr = data.get('win_rate', 0)
        # Normalizar si viene como porcentaje (>1)
        if raw_wr > 1:
            raw_wr = raw_wr / 100.0
        win_rates.append(raw_wr)
        total_trades.append(data.get('total_trades', 0))
        max_drawdowns.append(sanitize_numeric_value(data.get('max_drawdown', 0)))  # Sanitizar drawdown también

    fig = make_subplots(rows=2, cols=2,
                       subplot_titles=["P&L Total por Estrategia",
                                     "Win Rate por Estrategia",
                                     "Total Trades por Estrategia",
                                     "Max Drawdown (%) por Estrategia"])

    # P&L Total
    fig.add_trace(go.Bar(x=strategy_names, y=pnl_values, name='P&L Total',
                        marker_color='lightblue'), row=1, col=1)

    # Win Rate
    # Convertir win_rate a porcentaje para visualización correcta
    win_rates_pct = [wr * 100 for wr in win_rates]
    fig.add_trace(go.Bar(x=strategy_names, y=win_rates_pct, name='Win Rate (%)',
                        marker_color='lightgreen'), row=1, col=2)

    # Total Trades
    fig.add_trace(go.Bar(x=strategy_names, y=total_trades, name='Total Trades',
                        marker_color='orange'), row=2, col=1)

    # Max Drawdown %
    fig.add_trace(go.Bar(x=strategy_names, y=max_drawdowns, name='Max Drawdown (%)',
                        marker_color='red'), row=2, col=2)

    fig.update_layout(height=600, template="plotly_white", showlegend=False)
    return fig


def get_binance_connection_status():
    """
    Verifica el estado de conexión a Binance y retorna información detallada.

    Returns:
        dict: Información sobre el estado de conexión
    """
    try:
        from utils.live_trading_data_reader import LiveTradingDataReader

        # Determinar configuración
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        use_testnet = True
        account_type = "SANDBOX"

        try:
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            live_config = config.get('live_trading', {})
            account_type = live_config.get('account_type', 'SANDBOX')
            use_testnet = account_type.upper() == 'SANDBOX'
        except Exception:
            pass

        reader = LiveTradingDataReader(testnet=use_testnet)

        connection_ok = reader.test_connection()
        balance_info = None
        trade_count = 0

        if connection_ok:
            try:
                balance_info = reader.get_account_balance()
                trades = reader.get_recent_trades(days=30)
                trade_count = len(trades) if trades else 0
            except Exception as e:
                logger.warning(f"Error obteniendo datos adicionales de Binance: {e}")

        return {
            'connected': connection_ok,
            'account_type': account_type,
            'testnet': use_testnet,
            'balance_info': balance_info,
            'trade_count': trade_count,
            'last_check': datetime.now().strftime('%H:%M:%S')
        }

    except Exception as e:
        logger.error(f"Error verificando conexión Binance: {e}")
        return {
            'connected': False,
            'account_type': 'UNKNOWN',
            'testnet': True,
            'balance_info': None,
            'trade_count': 0,
            'error': str(e),
            'last_check': datetime.now().strftime('%H:%M:%S')
        }


def display_data_source_indicator(results, global_summary):
    """
    Muestra un indicador visual de la fuente de datos actual.
    """
    if not global_summary:
        return

    mode = global_summary.get('mode', 'UNKNOWN')
    data_source = global_summary.get('data_source', 'UNKNOWN')

    if 'BINANCE_DIRECT' in data_source:
        st.success("🟢 **DATOS DIRECTOS DE BINANCE** - Métricas calculadas desde operaciones reales ejecutadas")
        st.info("💡 **Fuente**: API de Binance en tiempo real | **Actualización**: Automática cada 30s")

        # Mostrar balance si está disponible
        if 'current_balance' in global_summary.get('metrics', {}):
            balance = global_summary['metrics']['current_balance']
            st.metric("💰 Balance Actual (Binance)", f"${balance:.2f}")

    elif 'LIVE_TRADING' in mode:
        st.warning("🟡 **DATOS DE ARCHIVO GUARDADO** - Usando resultados de sesión anterior")
        st.info("💡 **Fuente**: Archivo JSON guardado | **Nota**: No refleja operaciones más recientes")

        # Verificar si hay conexión disponible
        status = get_binance_connection_status()
        if status['connected']:
            st.info(f"🔗 **Conexión Binance disponible** - {status['trade_count']} operaciones en los últimos 30 días")
        else:
            st.error("❌ **Sin conexión a Binance** - No se pueden obtener datos en tiempo real")

    else:
        st.info("📊 **MODO BACKTESTING** - Datos históricos de simulación")


def main():
    try:
        # Cargar datos usando la nueva lógica
        results, global_summary = load_results()

        # Detectar fuente de datos para el título
        data_source = global_summary.get('data_source', 'UNKNOWN') if global_summary else 'UNKNOWN'
        is_live_binance = 'BINANCE_DIRECT' in data_source
        is_live_saved = 'LIVE_TRADING' in global_summary.get('mode', '') if global_summary else False

        # Título dinámico según la fuente de datos
        if is_live_binance:
            st.title("🚀 Dashboard de LIVE TRADING - Sistema Modular")
            st.markdown("### 🟢 **MODO LIVE ACTIVO - DATOS DIRECTOS DE BINANCE**")
            st.markdown("**Métricas calculadas desde operaciones reales ejecutadas en Binance**")

            # Auto-refresh cada 30 segundos en modo live
            st.markdown("""
            <meta http-equiv="refresh" content="30">
            <script>
                setInterval(function(){
                    window.location.reload();
                }, 30000);
            </script>
            """, unsafe_allow_html=True)
            st.info("🔄 **Dashboard se actualiza automáticamente cada 30 segundos**")

        elif is_live_saved:
            st.title("🚀 Dashboard de LIVE TRADING - Sistema Modular")
            st.markdown("### 🟡 **MODO LIVE - DATOS DE ARCHIVO GUARDADO**")
            st.markdown("**Usando resultados de sesión de live trading anterior**")
            st.info("💡 **Nota**: Para datos en tiempo real, asegúrese de que las credenciales de Binance estén configuradas")

        else:
            st.title("📊 Dashboard de Backtesting - Sistema Modular")
            st.markdown("### 📈 **MODO BACKTESTING**")
            st.markdown("**Análisis de estrategias con datos históricos**")

        # Mostrar indicador de fuente de datos
        display_data_source_indicator(results, global_summary)

        # Verificar si hay datos para mostrar
        if not results:
            st.warning("⚠️ No se encontraron datos para mostrar")
            st.info("💡 **Posibles causas:**")
            st.info("   - No hay resultados de backtesting guardados")
            st.info("   - No hay operaciones de live trading ejecutadas")
            st.info("   - Error en la carga de datos")

            # Intentar cargar datos de respaldo
            st.info("🔄 Intentando cargar datos de respaldo...")
            try:
                results_backup, global_summary_backup = load_backtesting_results()
                if results_backup:
                    st.success("✅ Datos de respaldo cargados exitosamente")
                    results = results_backup
                    global_summary = global_summary_backup
                else:
                    st.error("❌ No se pudieron cargar datos de respaldo")
                    return
            except Exception as e:
                st.error(f"❌ Error cargando datos de respaldo: {e}")
                return

        # Cargar configuración para obtener capital inicial
        try:
            config = load_config()
            initial_capital = 10000  # valor por defecto
            if config and 'backtesting' in config:
                initial_capital = config['backtesting'].get('initial_capital', 10000)
        except Exception as e:
            logger.warning(f"Error cargando configuración: {e}")
            initial_capital = 10000

        # Procesar datos y construir dashboard
        process_dashboard_data(results, global_summary, initial_capital)

    except Exception as e:
        st.error(f"❌ Error crítico en el dashboard: {e}")
        logger.error(f"Error crítico en dashboard: {e}", exc_info=True)
        st.info("🔧 **Solución sugerida:** Revisar logs del sistema para más detalles")


def process_dashboard_data(results, global_summary, initial_capital):
    """Procesa y muestra los datos del dashboard de manera segura."""

    # Process dashboard data without complex try/catch

if __name__ == "__main__":
    main()