import streamlit as st
from app.pages.dashboard import show_dashboard
from app.components.ui_elements import render_header

# Configuración de la página debe ser la primera instrucción de Streamlit
st.set_page_config(
    page_title="BPMN Analyzer App",
    page_icon="🔄",
    layout="wide"
)

def main():
    # Renderizar encabezado común
    render_header()
    
    # Cargar la vista del dashboard
    show_dashboard()

if __name__ == "__main__":
    main()