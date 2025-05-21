
import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Simulador de Proyección Poblacional", layout="centered")

st.title("Simulador de Proyección de Población")
st.write("Proyecte la población de varios municipios y compare métodos.")

# Entradas múltiples
num_municipios = st.number_input("¿Cuántos municipios quiere simular?", min_value=1, max_value=5, value=2, step=1)

municipios = []
for i in range(num_municipios):
    with st.expander(f"Municipio {i+1}"):
        nombre = st.text_input(f"Nombre del municipio {i+1}", f"Municipio_{i+1}")
        P0 = st.number_input(f"Población inicial de {nombre}", min_value=0, value=100000, key=f"P0_{i}")
        tasa = st.number_input(f"Tasa de crecimiento anual (%) de {nombre}", min_value=0.0, value=3.0, step=0.1, key=f"tasa_{i}")
        metodos = st.multiselect(f"Métodos a comparar para {nombre}", ["Aritmético", "Geométrico", "Exponencial", "Wappaus"], default=["Aritmético", "Geométrico"], key=f"metodos_{i}")
        municipios.append({
            "nombre": nombre,
            "P0": P0,
            "tasa": tasa / 100,
            "metodos": metodos
        })

t_horizonte = st.slider("Horizonte de proyección (años)", min_value=5, max_value=50, value=20)
t = np.arange(0, t_horizonte + 1)

# Inicializar dataframe para resultados globales
resultados_globales = []

# Cálculo y visualización
st.subheader("Gráfica comparativa")
fig, ax = plt.subplots(figsize=(10, 6))

for m in municipios:
    for metodo in m["metodos"]:
        if metodo == "Aritmético":
            incremento = m["P0"] * m["tasa"]
            P = m["P0"] + incremento * t
        elif metodo == "Geométrico":
            P = m["P0"] * (1 + m["tasa"])**t
        elif metodo == "Exponencial":
            P = m["P0"] * np.exp(m["tasa"] * t)
        elif metodo == "Wappaus":
            n = t_horizonte
            Pn = m["P0"] * (1 + m["tasa"])**n
            P = m["P0"] + ((Pn - m["P0"])/n) * t + ((Pn - m["P0"])/(2 * n**2)) * t**2
        ax.plot(t, P, label=f"{m['nombre']} - {metodo}")
        for i in range(len(t)):
            resultados_globales.append({
                "Municipio": m["nombre"],
                "Método": metodo,
                "Año": t[i],
                "Población proyectada": int(P[i])
            })

ax.set_title("Proyección de Población por Municipio y Método")
ax.set_xlabel("Años desde el inicio")
ax.set_ylabel("Población proyectada")
ax.grid(True)
ax.legend()
st.pyplot(fig)

# Tabla de resultados
df_resultados = pd.DataFrame(resultados_globales)
st.subheader("Tabla de resultados")
st.dataframe(df_resultados)

# Botón de descarga
csv = df_resultados.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Descargar resultados en Excel (CSV)",
    data=csv,
    file_name="proyeccion_municipios.csv",
    mime="text/csv"
)
