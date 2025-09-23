import streamlit as st
import pandas as pd

st.title("🧪 Dashboard de Prueba")

st.success("✅ Dashboard básico funcionando")

# Verificar que podemos cargar datos
try:
    from pathlib import Path
    base = Path(__file__).parent / "data" / "dashboard_results"
    if base.exists():
        st.info(f"📁 Datos encontrados en: {base}")
        files = list(base.glob("*_results.json"))
        st.info(f"📄 Archivos encontrados: {len(files)}")
        for f in files:
            if "SOL_USDT" in str(f):
                st.success(f"✅ Archivo principal encontrado: {f.name}")
    else:
        st.error(f"❌ Directorio de datos no encontrado: {base}")
except Exception as e:
    st.error(f"❌ Error al verificar datos: {e}")

st.write("🎯 Si ves este mensaje, Streamlit está funcionando correctamente")