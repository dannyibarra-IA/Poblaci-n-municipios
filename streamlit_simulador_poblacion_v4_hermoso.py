
import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Simulador de Proyección Poblacional", layout="wide")

st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .css-18e3th9 {
        padding-top: 2rem;
    }
    .stDataFrame div {
        white-space: nowrap;
    }
</style>
""", unsafe_allow_html=True)

st.title("📈 Simulador de Proyección de Población")
st.write("Simule el crecimiento poblacional de múltiples municipios, compare métodos y, si desea, explore escenarios con tasas variables.")

# Control de escenarios
activar_escenario = st.checkbox("¿Desea activar simulación de escenarios por tramos?", value=False)
escenario_info = "Si activa esta opción, podrá definir diferentes tasas de crecimiento para dos periodos: 0 a la mitad del horizonte, y de la mitad al final."

# Entradas generales
col1, col2 = st.columns([1, 2])
with col1:
    num_municipios = st.number_input("Número de municipios", min_value=1, max_value=5, value=2)
with col2:
    t_horizonte = st.slider("Horizonte de proyección (años)", min_value=5, max_value=50, value=20)

t = np.arange(0, t_horizonte + 1)

# Cálculo y visualización
fig, ax = plt.subplots(figsize=(10, 5))
df_total = pd.DataFrame()

# Procesar cada municipio
for i in range(num_municipios):
    with st.expander(f"📍 Municipio {i+1}", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input(f"Nombre del municipio", f"Municipio_{i+1}", key=f"nombre_{i}")
            P0 = st.number_input("Población inicial", min_value=1000, value=100000, key=f"P0_{i}")
        with col2:
            metodos = st.multiselect("Métodos de proyección", ["Aritmético", "Geométrico", "Exponencial", "Wappaus"], default=["Aritmético", "Geométrico"], key=f"metodo_{i}")

        if activar_escenario:
            col1, col2 = st.columns(2)
            with col1:
                tasa1 = st.number_input("Tasa (%) para los primeros años", value=3.0, step=0.1, key=f"tasa1_{i}") / 100
            with col2:
                tasa2 = st.number_input("Tasa (%) para los años finales", value=1.5, step=0.1, key=f"tasa2_{i}") / 100
            t_split = t_horizonte // 2
        else:
            tasa = st.number_input("Tasa de crecimiento anual (%)", min_value=0.0, value=2.5, step=0.1, key=f"tasa_{i}") / 100

        # Inicializar DataFrame por municipio
        resultados = pd.DataFrame({"Año": t})

        # Cálculos por método
        for metodo in metodos:
            if activar_escenario:
                tasa_segmentada = np.concatenate([
                    np.full(t_split + 1, tasa1),
                    np.full(t_horizonte - t_split, tasa2)
                ])
                if metodo == "Aritmético":
                    incremento = P0 * tasa_segmentada
                    P = P0 + np.cumsum(incremento)
                elif metodo == "Geométrico":
                    P = [P0]
                    for i in range(1, len(t)):
                        P.append(P[i-1] * (1 + tasa_segmentada[i]))
                elif metodo == "Exponencial":
                    P = P0 * np.exp(np.cumsum(tasa_segmentada))
                elif metodo == "Wappaus":
                    Pn = P0 * (1 + np.mean(tasa_segmentada))**t_horizonte
                    P = P0 + ((Pn - P0)/t_horizonte) * t + ((Pn - P0)/(2 * t_horizonte**2)) * t**2
                P = np.array(P)
            else:
                if metodo == "Aritmético":
                    incremento = P0 * tasa
                    P = P0 + incremento * t
                elif metodo == "Geométrico":
                    P = P0 * (1 + tasa)**t
                elif metodo == "Exponencial":
                    P = P0 * np.exp(tasa * t)
                elif metodo == "Wappaus":
                    Pn = P0 * (1 + tasa)**t_horizonte
                    P = P0 + ((Pn - P0)/t_horizonte) * t + ((Pn - P0)/(2 * t_horizonte**2)) * t**2

            resultados[metodo] = P.astype(int)
            ax.plot(t, P, label=f"{nombre} - {metodo}")
            df_temp = pd.DataFrame({
                "Municipio": nombre,
                "Método": metodo,
                "Año": t,
                "Población proyectada": P.astype(int)
            })
            df_total = pd.concat([df_total, df_temp], ignore_index=True)

        # Mostrar tabla individual
        st.markdown(f"### 📊 Tabla de resultados para {nombre}")
        st.dataframe(resultados)

# Mostrar gráfico y tabla completa
st.subheader("📈 Comparación gráfica entre municipios y métodos")
ax.set_xlabel("Años")
ax.set_ylabel("Población")
ax.grid(True)
ax.legend()
st.pyplot(fig)

st.subheader("📋 Tabla consolidada de todos los municipios")
st.dataframe(df_total)

# Botón de descarga
csv = df_total.to_csv(index=False).encode('utf-8')
st.download_button("📥 Descargar tabla completa en Excel (CSV)", data=csv, file_name="proyeccion_comparada.csv", mime="text/csv")
