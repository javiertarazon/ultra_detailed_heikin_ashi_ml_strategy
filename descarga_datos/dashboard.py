import streamlit as st
import pandas as pd
import json
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

st.set_page_config(layout="wide", page_title="Dashboard de Backtesting Avanzado", page_icon="🤖")


@st.cache_data
def load_results():
    """
    Carga archivos JSON de resultados por símbolo y el resumen global.
    """
    base = Path(__file__).parent / "data" / "dashboard_results"
    results, global_summary = {}, {}
    if not base.exists():
        return {}, {}

    # Cargar archivos de símbolo
    for f in sorted(base.glob("*_results.json")):
        if f.name == 'global_summary.json':
            continue
        with open(f, 'r', encoding='utf-8') as fh:
            d = json.load(fh)
        sym = d.get('symbol', f.stem.replace('_results', ''))
        # Compatibilidad con JSONs antiguos sin 'strategies'
        if 'strategies' not in d:
            d = {'symbol': sym, 'strategies': {'Default': d}}
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
    return (max_drawdown / (total_pnl + max_drawdown)) * 100


def plot_equity_curve(equity_curve, symbol, strategy_name):
    """Genera la figura de la curva de equity con análisis detallado."""
    if not equity_curve:
        return go.Figure()

    df = pd.DataFrame({'Equity': equity_curve})
    df['Trade'] = df.index
    df['Drawdown'] = df['Equity'] - df['Equity'].cummax()

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                       subplot_titles=[f"Curva de Capital - {symbol} ({strategy_name})", "Drawdown"],
                       vertical_spacing=0.1)

    # Curva de equity
    fig.add_trace(go.Scatter(x=df['Trade'], y=df['Equity'], mode='lines',
                            name='Capital', line=dict(color='blue', width=2)), row=1, col=1)

    # Drawdown
    fig.add_trace(go.Scatter(x=df['Trade'], y=df['Drawdown'], mode='lines',
                            name='Drawdown', fill='tozeroy', line=dict(color='red')), row=2, col=1)

    fig.update_layout(height=600, template="plotly_white")
    fig.update_yaxes(title_text="Capital ($)", row=1, col=1)
    fig.update_yaxes(title_text="Drawdown ($)", row=2, col=1)
    fig.update_xaxes(title_text="Número de Trade", row=2, col=1)

    return fig


def plot_pnl_distribution(trades, strategy_name):
    """Genera análisis detallado de distribución de P&L."""
    if not trades:
        return go.Figure()

    pnl_values = [t.get('pnl', 0) for t in trades]
    pnl_percent = [t.get('pnl_percent', 0) for t in trades]

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
    fig.add_trace(go.Bar(x=strategy_names, y=win_rates, name='Win Rate (%)',
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
        st.info("Ejecuta `python run_backtesting_batches.py` para generar resultados.")
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
    selected_strategy = st.sidebar.selectbox(
        "🎯 Seleccionar Estrategia",
        available_strategies,
        key="strategy_selector"
    )

    # Botón de refresco para forzar recarga de datos
    if st.sidebar.button("🔄 Refrescar Datos", key="refresh_button"):
        st.cache_data.clear()
        st.rerun()

    # Debug info (temporal)
    with st.sidebar.expander("🐛 Debug Info"):
        st.write(f"**Símbolo seleccionado:** {selected_symbol}")
        st.write(f"**Estrategia seleccionada:** {selected_strategy}")
        st.write(f"**Estrategias disponibles:** {available_strategies}")
        if selected_strategy in symbol_data.get('strategies', {}):
            debug_data = symbol_data['strategies'][selected_strategy]
            st.write(f"**P&L de estrategia:** ${debug_data.get('total_pnl', 0):,.2f}")
            st.write(f"**Trades de estrategia:** {debug_data.get('total_trades', 0)}")

    # Obtener datos de la estrategia seleccionada
    strategy_data = symbol_data['strategies'][selected_strategy]

    # Métricas principales en cards
    st.header(f"📊 Métricas - {selected_symbol} | {selected_strategy}")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        pnl_total = strategy_data.get('total_pnl', 0)
        st.metric("💰 P&L Total", f"${pnl_total:,.2f}", delta=None)

    with col2:
        win_rate = strategy_data.get('win_rate', 0)
        st.metric("🎯 Win Rate", f"{win_rate:.1%}", delta=None)

    with col3:
        total_trades = strategy_data.get('total_trades', 0)
        st.metric("📊 Total Trades", f"{total_trades:,}", delta=None)

    with col4:
        max_dd_abs = strategy_data.get('max_drawdown', 0)
        max_dd_pct = calculate_drawdown_percentage(max_dd_abs, pnl_total)
        st.metric("📉 Max Drawdown", f"{max_dd_pct:.2f}%", delta=None)

    # Métricas adicionales
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        sharpe = strategy_data.get('sharpe_ratio', 0)
        st.metric("📈 Sharpe Ratio", f"{sharpe:.2f}", delta=None)

    with col6:
        profit_factor = strategy_data.get('profit_factor', 0)
        st.metric("⚡ Profit Factor", f"{profit_factor:.2f}", delta=None)

    with col7:
        avg_trade = strategy_data.get('avg_trade_pnl', 0)
        st.metric("📊 Avg Trade P&L", f"${avg_trade:.2f}", delta=None)

    with col8:
        winning_trades = strategy_data.get('winning_trades', 0)
        losing_trades = strategy_data.get('losing_trades', 0)
        st.metric("✅ Win/Loss", f"{winning_trades}/{losing_trades}", delta=None)

    # Gráficos principales
    st.header("📈 Análisis Visual")

    # Curva de equity
    st.subheader("Curva de Capital y Drawdown")
    equity_fig = plot_equity_curve(
        strategy_data.get('equity_curve', []),
        selected_symbol,
        selected_strategy
    )
    st.plotly_chart(equity_fig, use_container_width=True)

    # Distribución P&L
    st.subheader("Distribución de P&L")
    pnl_fig = plot_pnl_distribution(strategy_data.get('trades', []), selected_strategy)
    st.plotly_chart(pnl_fig, use_container_width=True)

    # Análisis de traders ganadores vs perdedores
    st.subheader("🔍 Análisis: Traders Ganadores vs Perdedores")
    winners_fig = plot_winners_vs_losers(strategy_data.get('trades', []), selected_strategy)
    st.plotly_chart(winners_fig, use_container_width=True)

    # Comparación entre estrategias (solo si hay múltiples estrategias)
    if len(available_strategies) > 1:
        st.header("⚖️ Comparación entre Estrategias")
        comparison_fig = plot_strategy_comparison(results, selected_symbol)
        st.plotly_chart(comparison_fig, use_container_width=True)

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
        col3.metric("P&L Promedio Ganador", ".2f")
        col4.metric("P&L Promedio Perdedor", ".2f")

        # Tabla de trades
        st.dataframe(trades_df, use_container_width=True)
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
