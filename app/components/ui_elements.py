import streamlit as st

def render_header():
    """Renderiza el encabezado común."""
    st.title("⚙️ Procesador de BPMN")
    st.markdown("""
    Esta aplicación analiza archivos BPMN y genera un reporte secuencial de actividades.
    """)
    st.divider()

def render_file_uploader():
    """Renderiza el cargador de archivos."""
    uploaded_file = st.file_uploader("Carga tu archivo .bpmn", type=['bpmn', 'xml'])
    return uploaded_file

def render_metrics(df):
    """Muestra métricas rápidas del proceso."""
    if df is not None and not df.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Actividades", len(df))
        with col2:
            roles_count = df['Rol (Responsable)'].nunique()
            st.metric("Roles Involucrados", roles_count)
        with col3:
            # Check si hay subprocesos o nombres de proceso distintos
            proc_count = df['Proceso Principal'].nunique()
            st.metric("Procesos Detectados", proc_count)