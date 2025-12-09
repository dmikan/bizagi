import streamlit as st
import pandas as pd
from backend.services.bpmn_service import BPMNProcessor
from app.components.ui_elements import render_file_uploader, render_metrics

def show_dashboard():
    uploaded_file = render_file_uploader()

    if uploaded_file is not None:
        # Instanciar servicio y procesar
        processor = BPMNProcessor()
        
        # Spinner visual mientras procesa
        with st.spinner('Analizando estructura del grafo y aplicando desconexiones virtuales...'):
            df_result, error = processor.process_xml(uploaded_file)

        if error:
            st.error(f"Error: {error}")
        else:
            st.success("Archivo procesado exitosamente.")
            
            # Métricas
            render_metrics(df_result)
            
            # Tabs
            tab1, tab2 = st.tabs(["📋 Lista de Actividades", "⚙️ Configuración Avanzada (Futuro)"])
            
            with tab1:
                st.subheader("Reporte Secuencial Generado")
                st.markdown("A continuación se muestra el orden lógico de ejecución detectado:")
                
                # Dataframe interactivo
                st.dataframe(
                    df_result,
                    use_container_width=True,
                    hide_index=True
                )
                
                # Botón de descarga
                csv = df_result.to_csv(index=False, sep=';', encoding='utf-8-sig')
                st.download_button(
                    label="Descargar CSV",
                    data=csv,
                    file_name='reporte_actividades_bpmn.csv',
                    mime='text/csv',
                )
            
            with tab2:
                st.info("Este módulo está reservado para futuras funcionalidades (Visualización de grafos, simulación de tiempos, etc).")
                st.empty()
    else:
        st.info("Por favor, sube un archivo BPMN para comenzar el análisis.")