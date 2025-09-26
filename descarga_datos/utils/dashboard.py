import streamlit as st
import pandas as pd
import json
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

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


@st.cache_data
def load_results():
    """
    Carga archivos JSON de resultados por símbolo y el resumen global.
    """
    base = Path(__file__).parent.parent / "data" / "dashboard_results"
    results, global_summary = {}, {}
    if not base.exists():
        return {}, {}

    # Cargar archivos de símbolo
    for f in sorted(base.glob("*_results.json")):
        if f.name == 'global_summary.json':
            continue
        # Excluir archivos con datos simulados para mantener consistencia
        if 'realistic' in f.name:
            continue
        with open(f, 'r', encoding='utf-8') as fh:
            d = json.load(fh)
        
        # Extraer símbolo del nombre del archivo
        sym = f.stem.replace('_results', '').replace('_', '/')
        
        # Compatibilidad con diferentes formatos JSON
        if 'strategies' not in d and 'symbol' not in d:
            # Nuevo formato: {"Solana4HTrailing": {...}, "Solana4HOptimizedTrailing": {...}}
            # Verificar que todas las keys son nombres de estrategias (contienen datos dict con métricas)
            all_strategies = True
            for key, value in d.items():
                if not isinstance(value, dict) or 'total_trades' not in value:
                    all_strategies = False
                    break
            
            if all_strategies:
                # Es el nuevo formato de múltiples estrategias
                d = {'symbol': sym, 'strategies': d}
            else:
                # Formato antiguo donde d es una sola estrategia
                d = {'symbol': sym, 'strategies': {'Default': d}}
        elif 'strategies' not in d and 'symbol' in d:
            # Formato con símbolo pero sin strategies wrapper
            d = {'symbol': sym, 'strategies': {'Default': d}}
        elif 'strategies' not in d:
            # Formato legacy - key principal es símbolo
            symbol_key = list(d.keys())[0]
            strategies_data = d[symbol_key]
            d = {'symbol': symbol_key, 'strategies': strategies_data}
        
        results[sym] = d

    # Cargar resumen global
    gs = base / 'global_summary.json'
    if gs.exists():
        with open(gs, 'r', encoding='utf-8') as fh:
            global_summary = json.load(fh)

    return results, global_summary


def calculate_drawdown_percentage(max_drawdown, total_pnl):
    """
    Calcula el drawdown como porcentaje del capital total.
    """
    if total_pnl <= 0:
        return 0.0
    # Si max_drawdown es negativo, convertirlo a positivo
    max_dd_abs = abs(max_drawdown)
    initial_capital = 10000  # Capital inicial estándar
    return (max_dd_abs / initial_capital) * 100


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
    df['Drawdown'] = df['Equity'] - df['Equity'].cummax()

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
    fig.update_yaxes(title_text="Drawdown ($)", row=2, col=1)
    fig.update_xaxes(title_text="Número de Trade", row=2, col=1)

    # Añadir estadísticas como anotaciones
    max_equity = df['Equity'].max()
    min_drawdown = df['Drawdown'].min()
    final_equity = df['Equity'].iloc[-1]
    
    fig.add_annotation(
        text=f"Capital Final: ${final_equity:,.0f}<br>Máximo: ${max_equity:,.0f}<br>Max DD: ${min_drawdown:,.0f}",
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
        pnl_values.append(data.get('total_pnl', 0))
        win_rates.append(data.get('win_rate', 0) * 100)
        total_trades.append(data.get('total_trades', 0))
        max_dd = data.get('max_drawdown', 0)
        total_pnl = data.get('total_pnl', 0)
        max_drawdowns.append(calculate_drawdown_percentage(max_dd, total_pnl))

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

    # Cargar datos
    results, global_summary = load_results()

    if not results:
        st.error("❌ No se encontraron resultados de backtesting.")
        st.info("Ejecuta `python main.py` para generar resultados.")
        return

    # Información del período y configuración
    period_info = global_summary.get('period', {})
    if period_info:
        st.info(f"📅 **Período Analizado:** {period_info.get('start_date', 'N/A')} → {period_info.get('end_date', 'N/A')} | "
               f"⏱️ **Temporalidad:** {period_info.get('timeframe', 'N/A')} | "
               f"📊 **Total Símbolos:** {global_summary.get('total_symbols', 0)}")

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
    available_strategies = list(symbol_data.get('strategies', {}).keys())
    
    # Verificar si hay estrategias disponibles
    if not available_strategies:
        st.error(f"⚠️ No hay estrategias disponibles para {selected_symbol}. Por favor, ejecute un backtesting primero.")
        st.stop()
        
    selected_strategy = st.sidebar.selectbox(
        "🎯 Seleccionar Estrategia",
        available_strategies,
        key="strategy_selector"
    )

    # Botón de refresco para forzar recarga de datos
    if st.sidebar.button("🔄 Refrescar Datos", key="refresh_button"):
        st.cache_data.clear()
        st.rerun()

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
        st.error(f"⚠️ La estrategia '{selected_strategy}' no existe en los datos para {selected_symbol}. Por favor, seleccione otra estrategia o ejecute un backtesting con esta estrategia.")
        st.stop()
        
    raw_strategy_data = symbol_data['strategies'][selected_strategy]
    strategy_data = validate_and_clean_metrics(raw_strategy_data)

    # Métricas principales en cards
    st.header(f"📊 Métricas - {selected_symbol} | {selected_strategy}")

    # Extraer datos ya validados (ya están normalizados por validate_and_clean_metrics)
    total_pnl = strategy_data.get('total_pnl', 0.0)
    win_rate = strategy_data.get('win_rate', 0.0)  # Ya está normalizado (0-1)
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
        # Calcular drawdown como porcentaje del capital inicial
        initial_capital = 10000.0  # Capital inicial por defecto
        dd_pct = (max_drawdown / initial_capital) * 100 if max_drawdown > 0 else 0
        # Formato más compacto para el drawdown
        formatted_dd = f"${max_drawdown/1000:.1f}K" if max_drawdown >= 1000 else f"${max_drawdown:.0f}"
        st.metric("📉 Max DD", f"{formatted_dd} ({dd_pct:.1f}%)", delta=None)  # Título más corto

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
    
    # Generar curva de equity si no existe
    equity_curve = strategy_data.get('equity_curve', [])
    if not equity_curve and 'trades' in strategy_data:
        equity_curve = generate_equity_curve_from_trades(strategy_data['trades'])
    
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

    trades_df = pd.DataFrame(strategy_data.get('trades', []))
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
