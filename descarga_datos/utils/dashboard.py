import streamlit as st
import pandas as pd
import json
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import yaml

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


@st.cache_data(ttl=30)  # Cache por 30 segundos para permitir actualizaciones
def load_results():
    """
    Carga archivos JSON de resultados por símbolo y el resumen global.
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


def generate_equity_curve_from_trades(trades, initial_capital=10000):
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
    df['Trade'] = df.index
    df['Drawdown'] = ((df['Equity'] - df['Equity'].cummax()) / df['Equity'].cummax() * 100).fillna(0)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                       subplot_titles=[f"Curva de Capital - {symbol} ({strategy_name})", "Drawdown"],
                       vertical_spacing=0.1)

    # Curva de equity
    fig.add_trace(go.Scatter(x=df['Trade'], y=df['Equity'], mode='lines',
                            name='Capital', line=dict(color='blue', width=2)), row=1, col=1)

    # Drawdown (en valores negativos para mejor visualización)
    fig.add_trace(go.Scatter(x=df['Trade'], y=df['Drawdown'], mode='lines',
                            name='Drawdown', fill='tozeroy', 
                            line=dict(color='red', width=1.5)), row=2, col=1)

    fig.update_layout(height=600, template="plotly_white", showlegend=True)
    fig.update_yaxes(title_text="Capital ($)", row=1, col=1)
    fig.update_yaxes(title_text="Drawdown (%)", row=2, col=1)
    fig.update_xaxes(title_text="Número de Trade", row=2, col=1)

    # Añadir estadísticas como anotaciones
    max_equity = df['Equity'].max()
    min_drawdown = df['Drawdown'].min()
    final_equity = df['Equity'].iloc[-1]
    
    fig.add_annotation(
        text=f"Capital Final: ${final_equity:,.0f}<br>Máximo: ${max_equity:,.0f}<br>Max DD: {min_drawdown:.1f}%",
        xref="paper", yref="paper",
        x=0.02, y=0.98, xanchor='left', yanchor='top',
        showarrow=False, font=dict(size=10),
        bgcolor="rgba(255,255,255,0.8)", bordercolor="gray", borderwidth=1
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


def main():
    st.title("📈 Dashboard Avanzado de Backtesting - Sistema Modular")

    # Cargar configuración para obtener capital inicial
    config = load_config()
    initial_capital = 10000  # valor por defecto
    if config and 'backtesting' in config:
        initial_capital = config['backtesting'].get('initial_capital', 10000)

    # Cargar datos
    results, global_summary = load_results()

    # Generar equity_curve faltante si existen trades pero no equity (post-procesado)
    def _build_equity_curve(trades, initial_capital=initial_capital):
        equity = [initial_capital]
        running = initial_capital
        for t in trades:
            running += t.get('pnl', 0)
            equity.append(running)
        return equity

    for sym, sym_data in list(results.items()):
        strategies = sym_data.get('strategies', {}) if isinstance(sym_data, dict) else {}
        for sname, sdata in strategies.items():
            if isinstance(sdata, dict):
                trades = sdata.get('trades', [])
                eq = sdata.get('equity_curve', [])
                if trades and (not eq or len(eq) < 2):
                    sdata['equity_curve'] = _build_equity_curve(trades)

    # Construir resumen tabular global (símbolo / estrategia)
    summary_rows = []
    for sym, sym_data in results.items():
        strategies = sym_data.get('strategies', {}) if isinstance(sym_data, dict) else {}
        for sname, sdata in strategies.items():
            if not isinstance(sdata, dict):
                continue
            wr = sdata.get('win_rate', 0)
            if wr > 1:
                wr = wr / 100.0
            summary_rows.append({
                'Símbolo': sym,
                'Estrategia': sname,
                'Trades': sdata.get('total_trades', 0),
                'WinRate%': round(wr * 100, 2),
                'P&L': sanitize_numeric_value(sdata.get('total_pnl', 0)),
                'MaxDD%': round(sanitize_numeric_value(sdata.get('max_drawdown', 0)), 2)
            })

    if not results:
        st.error("❌ No se encontraron resultados de backtesting.")
        st.info("Ejecuta `python main.py` para generar resultados.")
        return

    # Información del período y resumen global
    period_info = global_summary.get('period', {})
    metrics_info = global_summary.get('metrics', {})
    if period_info:
        total_symbols = global_summary.get('total_symbols', len(results))
        total_pnl_global = sanitize_numeric_value(metrics_info.get('total_pnl', 0))
        total_trades_global = metrics_info.get('total_trades', 0)
        avg_win_rate_raw = metrics_info.get('avg_win_rate', 0)
        # Normalizar win rate global si viene >1 (asumido porcentaje)
        avg_win_rate = avg_win_rate_raw/100.0 if avg_win_rate_raw > 1 else avg_win_rate_raw
        st.info(
            f"📅 **Período:** {period_info.get('start_date', 'N/A')} → {period_info.get('end_date', 'N/A')}  | "
            f"⏱️ **TF:** {period_info.get('timeframe', 'N/A')}  | "
            f"📊 **Símbolos:** {total_symbols}  | "
            f"💰 **P&L Total:** {total_pnl_global:,.2f}  | "
            f"🎯 **Win Rate Promedio:** {avg_win_rate*100:.1f}%  | "
            f"🧪 **Trades Totales:** {total_trades_global}"
        )
    else:
        st.warning("No se encontró información de período en global_summary.json")

    # Panel resumen global al inicio
    if summary_rows:
        import pandas as _pd
        st.subheader("📌 Resumen Global de Estrategias")
        df_summary = _pd.DataFrame(summary_rows)
        # Ordenar por P&L desc
        df_summary = df_summary.sort_values('P&L', ascending=False).reset_index(drop=True)
        st.dataframe(df_summary, width='stretch', height=min(400, 40 + 25 * len(df_summary)))
    else:
        st.warning("No hay filas de resumen para mostrar (posible error de parsing de JSON).")

    # Sidebar con controles
    st.sidebar.title("🎛️ Controles")

    # Selector de símbolo
    available_symbols = sorted(results.keys())
    selected_symbol = st.sidebar.selectbox(
        "📈 Seleccionar Símbolo",
        available_symbols,
        key="symbol_selector"
    )

    # Selector de estrategia
    symbol_data = results[selected_symbol]
    
    # Verificar que symbol_data tiene la estructura correcta
    if isinstance(symbol_data, dict) and 'strategies' in symbol_data and isinstance(symbol_data['strategies'], dict):
        available_strategies = list(symbol_data['strategies'].keys())
    else:
        # Corregir estructura si no es correcta
        st.error(f"⚠️ Formato incorrecto de datos para {selected_symbol}. Estructura: {type(symbol_data)}")
        st.write(symbol_data)
        st.stop()
    
    # Verificar si hay estrategias disponibles
    if not available_strategies:
        st.error(f"⚠️ No hay estrategias disponibles para {selected_symbol}. Por favor, ejecute un backtesting primero.")
        st.write("Estructura de datos:", symbol_data)
        st.stop()
        
    selected_strategy = st.sidebar.selectbox(
        "🎯 Seleccionar Estrategia",
        available_strategies,
        key="strategy_selector"
    )

    # Botón de refresco para forzar recarga de datos
    if st.sidebar.button("🔄 Refrescar Datos", key="refresh_button", type="primary"):
        st.cache_data.clear()
        st.success("✅ Datos refrescados correctamente")
        st.rerun()

    # Mostrar información de carga de datos
    from datetime import datetime
    st.sidebar.write(f"📅 Datos cargados: {datetime.now().strftime('%H:%M:%S')}")

    # Mostrar configuración actual
    config = load_config()
    if config:
        with st.sidebar.expander("⚙️ Configuración Actual"):
            if 'backtesting' in config:
                bt_config = config['backtesting']
                
                # Símbolos configurados
                if 'symbols' in bt_config:
                    st.write(f"**📊 Símbolos ({len(bt_config['symbols'])}):**")
                    for symbol in bt_config['symbols']:
                        st.write(f"• {symbol}")
                
                # Estrategias activas
                if 'strategies' in bt_config:
                    active_strategies = [k for k, v in bt_config['strategies'].items() if v is True]
                    st.write(f"**🎯 Estrategias activas ({len(active_strategies)}):**")
                    for strategy in active_strategies:
                        st.write(f"• {strategy}")

    # Debug info expandido
    with st.sidebar.expander("🐛 Debug Info - Datos Raw"):
        st.write(f"**Símbolo:** {selected_symbol}")
        st.write(f"**Estrategia:** {selected_strategy}")
        st.write(f"**Estrategias disponibles:** {available_strategies}")
        
        if selected_strategy in symbol_data.get('strategies', {}):
            debug_data = symbol_data['strategies'][selected_strategy]
            st.write("**Métricas Raw:**")
            
            # Verificar que debug_data es un diccionario
            if not isinstance(debug_data, dict):
                st.error(f"❌ Error: debug_data no es un diccionario, es: {type(debug_data)}")
                st.write(f"Valor: {debug_data}")
                return
            
            # Verificar coherencia de datos
            total_trades = debug_data.get('total_trades', 0)
            winning_trades = debug_data.get('winning_trades', 0)
            losing_trades = debug_data.get('losing_trades', 0)
            
            if total_trades != (winning_trades + losing_trades):
                st.warning(f"⚠️ Inconsistencia detectada: Total trades ({total_trades}) ≠ Winning ({winning_trades}) + Losing ({losing_trades})")
            
            # Mostrar métricas principales raw
            metrics_to_show = [
                'total_pnl', 'win_rate', 'total_trades', 'max_drawdown',
                'sharpe_ratio', 'profit_factor', 'avg_trade_pnl',
                'winning_trades', 'losing_trades'
            ]
            
            for metric in metrics_to_show:
                value = debug_data.get(metric, 'N/A')
                st.write(f"• {metric}: {value} ({type(value).__name__})")
                
            # Validar estructura de trades
            trades = debug_data.get('trades', [])
            st.write(f"**Total trades en data:** {len(trades)}")
            if trades:
                st.write(f"**Primer trade sample:** {trades[0] if trades else 'None'}")
                
            # Validar equity curve
            equity_curve = debug_data.get('equity_curve', [])
            st.write(f"**Equity curve length:** {len(equity_curve) if isinstance(equity_curve, list) else 'Not list'}")

    # Obtener y limpiar datos de la estrategia seleccionada
    if selected_strategy not in symbol_data.get('strategies', {}):
        st.error(f"⚠️ La estrategia '{selected_strategy}' no existe en los datos para {selected_symbol}.")
        st.write("Estrategias disponibles:", list(symbol_data.get('strategies', {}).keys()))
        st.write("Datos brutos:", symbol_data)
        st.stop()
    
    # Verificar que los datos de la estrategia son un diccionario    
    raw_strategy_data = symbol_data['strategies'][selected_strategy]
    if not isinstance(raw_strategy_data, dict):
        st.error(f"⚠️ Los datos para la estrategia '{selected_strategy}' no son válidos. Formato: {type(raw_strategy_data)}")
        st.write("Datos recibidos:", raw_strategy_data)
        # Intentar recuperar con un diccionario vacío
        raw_strategy_data = {'total_trades': 0, 'win_rate': 0, 'total_pnl': 0}
        
    strategy_data = validate_and_clean_metrics(raw_strategy_data)

    # Métricas principales en cards
    st.header(f"📊 Métricas - {selected_symbol} | {selected_strategy}")

    # Extraer datos ya validados (ya están normalizados por validate_and_clean_metrics)
    total_pnl = strategy_data.get('total_pnl', 0.0)
    raw_wr = strategy_data.get('win_rate', 0.0)
    # Normalizar win_rate: si >1 asumimos que ya era porcentaje
    win_rate = raw_wr/100.0 if raw_wr > 1 else raw_wr
    total_trades = strategy_data.get('total_trades', 0)
    max_drawdown = abs(strategy_data.get('max_drawdown', 0.0))
    sharpe_ratio = strategy_data.get('sharpe_ratio', 0.0)
    profit_factor = strategy_data.get('profit_factor', 0.0)
    avg_trade_pnl = strategy_data.get('avg_trade_pnl', 0.0)
    winning_trades = strategy_data.get('winning_trades', 0)
    losing_trades = strategy_data.get('losing_trades', 0)
    
    # Validar consistencia de datos
    total_trades_calc = winning_trades + losing_trades
    if total_trades != total_trades_calc:
        st.warning(f"⚠️ Inconsistencia: Total trades ({total_trades}) ≠ Sum ({total_trades_calc})")

    # Validar consistencia del win_rate
    if total_trades > 0:
        win_rate_calc = winning_trades / total_trades
        win_rate_diff = abs(win_rate - win_rate_calc)
        if win_rate_diff > 0.01:  # Tolerancia del 1%
            st.warning(f"⚠️ Win Rate inconsistente: Reportado ({win_rate:.1%}) ≠ Calculado ({win_rate_calc:.1%})")
    
    # Primera fila - Métricas principales
    st.subheader("📊 Métricas Principales")
    metrics_row1 = st.container()
    col1, col2, col3, col4 = metrics_row1.columns([1, 0.85, 0.85, 1.3])  # Ajuste de proporciones para optimizar espacio
    
    with col1:
        # Formato más compacto para grandes cantidades
        if abs(total_pnl) >= 1000:
            formatted_pnl = f"${total_pnl/1000:.1f}K" if abs(total_pnl) < 1000000 else f"${total_pnl/1000000:.2f}M"
        else:
            formatted_pnl = f"${total_pnl:.2f}"
        st.metric("💰 P&L", formatted_pnl, delta=None)  # Título más corto

    with col2:
        st.metric("🎯 Win Rate", f"{win_rate*100:.1f}%", delta=None)

    with col3:
        st.metric("📊 Trades", f"{total_trades}", delta=None)  # Sin formateo de miles para ahorro de espacio

    with col4:
        # Usar drawdown directo del backtester (ya viene en porcentaje)
        # max_drawdown ya está validado y limpio de validate_and_clean_metrics
        st.metric("📉 Max DD", f"{max_drawdown:.1f}%", delta=None)

    # Segunda fila - Métricas adicionales
    st.markdown('<hr style="margin: 0.3rem 0; border-top: 1px solid rgba(0,0,0,0.1);">', unsafe_allow_html=True)
    st.subheader("📈 Métricas de Rendimiento")
    metrics_row2 = st.container()
    col5, col6, col7, col8 = metrics_row2.columns([1, 1, 1.2, 0.8])  # Ajuste de proporciones para optimizar espacio
    
    with col5:
        st.metric("📈 Sharpe", f"{sharpe_ratio:.2f}", delta=None)  # Título más corto

    with col6:
        st.metric("⚡ Profit F.", f"{profit_factor:.2f}", delta=None)  # Título más corto

    with col7:
        # Formato más compacto para el P&L promedio
        if abs(avg_trade_pnl) >= 1000:
            formatted_avg = f"${avg_trade_pnl/1000:.1f}K"
        else:
            formatted_avg = f"${avg_trade_pnl:.1f}"  # Menos decimales
        st.metric("📊 Avg P&L", formatted_avg, delta=None)  # Título más corto

    with col8:
        st.metric("✅ Win/Loss", f"{winning_trades}/{losing_trades}", delta=None)

    # Métricas avanzadas - Tercera fila (solo si hay datos suficientes)
    if total_trades > 0:
        st.markdown('<hr style="margin: 0.3rem 0; border-top: 1px solid rgba(0,0,0,0.1);">', unsafe_allow_html=True)
        st.subheader("📊 Métricas Avanzadas")
        
        # Extraer datos avanzados con valores por defecto
        avg_win_pnl = strategy_data.get('avg_win_pnl', 0.0)
        avg_loss_pnl = strategy_data.get('avg_loss_pnl', 0.0)
        largest_win = strategy_data.get('largest_win', 0.0)
        largest_loss = strategy_data.get('largest_loss', 0.0)
        
        # Crear un contenedor separado para estas métricas
        metrics_row3 = st.container()
        col9, col10, col11, col12 = metrics_row3.columns([1.1, 1.1, 1.1, 1.1])  # Columnas uniformes para métricas avanzadas
        
        with col9:
            # Formato más compacto para ganancias promedio
            if abs(avg_win_pnl) >= 1000:
                formatted_win = f"${avg_win_pnl/1000:.1f}K"
            else:
                formatted_win = f"${avg_win_pnl:.1f}"  # Menos decimales
            st.metric("💚 Avg Win", formatted_win, delta=None)

        with col10:
            # Formato más compacto para pérdidas promedio
            if abs(avg_loss_pnl) >= 1000:
                formatted_loss = f"${avg_loss_pnl/1000:.1f}K"
            else:
                formatted_loss = f"${avg_loss_pnl:.1f}"  # Menos decimales
            st.metric("💔 Avg Loss", formatted_loss, delta=None)

        with col11:
            # Formato más compacto para mayor ganancia
            if abs(largest_win) >= 1000:
                formatted_max_win = f"${largest_win/1000:.1f}K"
            else:
                formatted_max_win = f"${largest_win:.1f}"  # Menos decimales
            st.metric("🏆 Max Win", formatted_max_win, delta=None)  # Título más corto

        with col12:
            # Formato más compacto para mayor pérdida
            if abs(largest_loss) >= 1000:
                formatted_max_loss = f"${largest_loss/1000:.1f}K"
            else:
                formatted_max_loss = f"${largest_loss:.1f}"  # Menos decimales
            st.metric("⚠️ Max Loss", formatted_max_loss, delta=None)  # Título más corto
            
        # Añadir información adicional sobre porcentajes (si están disponibles)
        if 'avg_trade_pct' in strategy_data:
            st.markdown('<hr style="margin: 0.3rem 0; border-top: 1px solid rgba(0,0,0,0.1);">', unsafe_allow_html=True)
            st.subheader("🔄 Métricas Porcentuales")
            
            metrics_row4 = st.container()
            col13, col14, col15, col16 = metrics_row4.columns([1, 1, 1, 1])  # Columnas uniformes para métricas porcentuales
            
            avg_trade_pct = strategy_data.get('avg_trade_pct', 0.0)
            with col13:
                st.metric("📊 Avg Trade %", f"{avg_trade_pct:.2f}%", delta=None)
                
            with col14:
                # Si hay datos de volatilidad, mostrarlos
                if 'volatility' in strategy_data:
                    volatility = strategy_data['volatility'] * 100  # Convertir a porcentaje
                    st.metric("📏 Volatilidad", f"{volatility:.2f}%", delta=None)
                    
            with col15:
                # Si hay datos de CAGR, mostrarlos
                if 'cagr' in strategy_data:
                    cagr = strategy_data['cagr']
                    st.metric("📈 CAGR", f"{cagr:.2f}%", delta=None)
                    
            with col16:
                # Si hay datos de risk_of_ruin, mostrarlos
                if 'risk_of_ruin' in strategy_data:
                    risk_of_ruin = strategy_data['risk_of_ruin'] * 100  # Convertir a porcentaje
                    st.metric("⚠️ Riesgo de Ruina", f"{risk_of_ruin:.2f}%", delta=None)

        # Métricas de compensación si están disponibles
        compensation_trades = strategy_data['compensated_trades']
        if compensation_trades > 0:
            st.markdown("**🔄 Métricas de Compensación**")
            col13, col14, col15, col16 = st.columns(4)
            with col13:
                st.metric("🔄 Compensaciones", f"{compensation_trades}", delta=None)
            with col14:
                comp_success_rate = strategy_data['compensation_success_rate']
                st.metric("✅ % Éxito Comp.", f"{comp_success_rate:.1f}%", delta=None)
            with col15:
                total_comp_pnl = strategy_data['total_compensation_pnl']
                st.metric("💰 P&L Comp.", f"${total_comp_pnl:.2f}", delta=None)
            with col16:
                comp_ratio = strategy_data['compensation_ratio']
                st.metric("📈 Ratio Comp.", f"{comp_ratio:.1f}%", delta=None)

    # Gráficos principales
    st.header("📈 Análisis Visual")

    # Curva de equity
    st.subheader("Curva de Capital y Drawdown")
    
    # Usar curva de equity del backtester (no generar datos sintéticos)
    equity_curve = strategy_data.get('equity_curve', [])
    if not equity_curve and strategy_data.get('trades'):
        # Generar curva de equity sintética si faltaba
        equity_curve = [initial_capital]
        running = initial_capital
        for t in strategy_data.get('trades', []):
            running += t.get('pnl', 0)
            equity_curve.append(running)
    if not equity_curve:
        st.info("No hay curva de equity en este resultado (sin trades).")
        equity_fig = plot_equity_curve([], selected_symbol, selected_strategy)
    else:
        equity_fig = plot_equity_curve(equity_curve, selected_symbol, selected_strategy)
    st.plotly_chart(equity_fig, width='stretch', key="equity_chart")

    # Distribución P&L
    st.subheader("Distribución de P&L")
    pnl_fig = plot_pnl_distribution(strategy_data.get('trades', []), selected_strategy)
    st.plotly_chart(pnl_fig, width='stretch', key="pnl_chart")

    # Análisis de traders ganadores vs perdedores
    st.subheader("🔍 Análisis: Traders Ganadores vs Perdedores")
    winners_fig = plot_winners_vs_losers(strategy_data.get('trades', []), selected_strategy)
    st.plotly_chart(winners_fig, width='stretch', key="winners_chart")

    # Comparación entre estrategias (solo si hay múltiples estrategias)
    if len(available_strategies) > 1:
        st.header("⚖️ Comparación entre Estrategias")
        comparison_fig = plot_strategy_comparison(results, selected_symbol)
        st.plotly_chart(comparison_fig, width='stretch', key="comparison_chart")

    # Tabla detallada de trades
    st.header("📋 Detalles de Operaciones")

    trades_raw = strategy_data.get('trades', [])
    # Opción para limitar trades (rendimiento)
    show_all_trades = st.checkbox("Mostrar todos los trades", value=False, help="Desmarca para ver solo los primeros 500 si hay demasiados.")
    if not show_all_trades and isinstance(trades_raw, list) and len(trades_raw) > 500:
        trades_display = trades_raw[:500]
        st.info(f"Mostrando primeros 500 de {len(trades_raw)} trades. Marca 'Mostrar todos los trades' para verlos completos.")
    else:
        trades_display = trades_raw
    trades_df = pd.DataFrame(trades_display)
    if not trades_df.empty:
        # Agregar columna de resultado
        trades_df['Resultado'] = trades_df['pnl'].apply(lambda x: '✅ Ganador' if x > 0 else '❌ Perdedor')

        # Mostrar estadísticas rápidas
        total_winners = len(trades_df[trades_df['pnl'] > 0])
        total_losers = len(trades_df[trades_df['pnl'] <= 0])
        avg_win = trades_df[trades_df['pnl'] > 0]['pnl'].mean() if total_winners > 0 else 0
        avg_loss = trades_df[trades_df['pnl'] <= 0]['pnl'].mean() if total_losers > 0 else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Trades Ganadores", total_winners)
        col2.metric("Trades Perdedores", total_losers)
        col3.metric("P&L Promedio Ganador", f"${avg_win:.2f}")
        col4.metric("P&L Promedio Perdedor", f"${avg_loss:.2f}")

        # Tabla de trades
        st.dataframe(trades_df, width='stretch')
    else:
        st.info("No hay operaciones registradas para esta estrategia.")

    # Información adicional
    st.sidebar.markdown("---")
    st.sidebar.subheader("ℹ️ Información del Sistema")
    st.sidebar.markdown("**Sistema Modular:** ✅ Activo")
    st.sidebar.markdown("**Carga Dinámica:** ✅ Funcional")
    st.sidebar.markdown(f"**Estrategias Activas:** {len(available_strategies)}")


if __name__ == "__main__":
    main()
