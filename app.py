import io
from typing import Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(
    page_title="Explorador automático de datos",
    page_icon="📊",
    layout="wide",
)


# -----------------------------
# Configuración y utilidades
# -----------------------------
TIPOS_ANALITICOS = ["Numérica", "Categórica", "Texto", "Booleana", "Fecha/hora"]


def clasificar_variable(serie: pd.Series) -> str:
    """Clasifica una variable para fines analíticos sin alterar la serie original."""
    if pd.api.types.is_bool_dtype(serie):
        return "Booleana"
    if pd.api.types.is_datetime64_any_dtype(serie):
        return "Fecha/hora"
    if pd.api.types.is_numeric_dtype(serie):
        return "Numérica"
    if pd.api.types.is_string_dtype(serie) or pd.api.types.is_object_dtype(serie):
        # Objetos con pocos valores distintos se consideran categóricos.
        no_nulos = serie.dropna()
        if len(no_nulos) > 0 and no_nulos.nunique(dropna=True) <= min(30, max(10, int(len(no_nulos) * 0.05))):
            return "Categórica"
        return "Texto"
    if pd.api.types.is_categorical_dtype(serie):
        return "Categórica"
    return "Texto"


def normalizar_nombres_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Elimina espacios innecesarios de los nombres, preservando el contenido de las celdas."""
    resultado = df.copy()
    resultado.columns = [str(col).strip() for col in resultado.columns]
    return resultado


def intentar_convertir_fechas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Intenta reconocer fechas únicamente en columnas cuyo nombre sugiere una fecha.
    No convierte silenciosamente columnas que no cumplan ese criterio.
    """
    resultado = df.copy()
    palabras_fecha = ("fecha", "date")

    for columna in resultado.columns:
        nombre = str(columna).strip().lower()
        if any(palabra in nombre for palabra in palabras_fecha):
            if pd.api.types.is_datetime64_any_dtype(resultado[columna]):
                continue

            original = resultado[columna]
            try:
                convertido = pd.to_datetime(original, errors="coerce")
                no_nulos_originales = original.notna().sum()

                if no_nulos_originales == 0:
                    continue

                proporción_convertida = convertido.notna().sum() / no_nulos_originales
                if proporción_convertida >= 0.80:
                    resultado[columna] = convertido
            except (ValueError, TypeError, OverflowError):
                continue

    return resultado


@st.cache_data(show_spinner=False)
def leer_dataset(contenido: bytes, nombre_archivo: str) -> pd.DataFrame:
    """Lee CSV, XLSX o XLS desde memoria."""
    extension = nombre_archivo.lower().rsplit(".", 1)[-1]

    if extension == "csv":
        # utf-8-sig permite abrir CSV con BOM y latin-1 funciona como respaldo.
        try:
            df = pd.read_csv(io.BytesIO(contenido), low_memory=False)
        except UnicodeDecodeError:
            df = pd.read_csv(io.BytesIO(contenido), encoding="latin-1", low_memory=False)
    elif extension == "xlsx":
        df = pd.read_excel(io.BytesIO(contenido), engine="openpyxl")
    elif extension == "xls":
        df = pd.read_excel(io.BytesIO(contenido), engine="xlrd")
    else:
        raise ValueError("Formato no soportado. Utiliza CSV, XLSX o XLS.")

    if not isinstance(df, pd.DataFrame):
        raise ValueError("El archivo no produjo una tabla de datos válida.")

    df = normalizar_nombres_columnas(df)
    df = intentar_convertir_fechas(df)
    return df


def csv_bytes(df: pd.DataFrame) -> bytes:
    """Genera CSV UTF-8 con BOM directamente en memoria."""
    return df.to_csv(index=False).encode("utf-8-sig")


def columnas_por_tipo(df: pd.DataFrame, tipo: str) -> list[str]:
    return [col for col in df.columns if clasificar_variable(df[col]) == tipo]


def construir_resumen_tipos(df: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for col in df.columns:
        serie = df[col]
        filas.append(
            {
                "Variable": col,
                "Tipo Pandas": str(serie.dtype),
                "Tipo analítico": clasificar_variable(serie),
                "Valores no nulos": int(serie.notna().sum()),
                "Valores únicos": int(serie.nunique(dropna=True)),
            }
        )
    return pd.DataFrame(filas)


def aplicar_filtros(
    df: pd.DataFrame,
    columnas_fecha: list[str],
    columnas_categoricas: list[str],
    columnas_numericas: list[str],
) -> pd.DataFrame:
    """Aplica filtros manteniendo los faltantes en filtros de fecha y numéricos."""
    filtrado = df.copy()

    # Filtros de fecha
    for col in columnas_fecha:
        if col not in filtrado.columns:
            continue

        serie = filtrado[col]
        fechas_validas = serie.dropna()
        if fechas_validas.empty:
            continue

        minimo = fechas_validas.min().date()
        maximo = fechas_validas.max().date()

        inicio = st.sidebar.date_input(
            f"Fecha inicial — {col}",
            value=minimo,
            min_value=minimo,
            max_value=maximo,
            key=f"fecha_inicio_{col}",
        )
        fin = st.sidebar.date_input(
            f"Fecha final — {col}",
            value=maximo,
            min_value=minimo,
            max_value=maximo,
            key=f"fecha_fin_{col}",
        )

        if inicio > fin:
            st.sidebar.error(f"La fecha inicial de «{col}» no puede ser posterior a la final.")
            return filtrado.iloc[0:0]

        mascara = serie.isna() | serie.dt.date.between(inicio, fin)
        filtrado = filtrado[mascara]

    # Filtros categóricos
    for col in columnas_categoricas:
        if col not in filtrado.columns:
            continue

        opciones = filtrado[col].dropna().astype(str).unique().tolist()
        opciones = sorted(opciones, key=lambda x: x.lower())

        if not opciones:
            continue

        seleccionadas = st.sidebar.multiselect(
            f"Categorías — {col}",
            options=opciones,
            default=[],
            key=f"categoria_{col}",
        )

        if seleccionadas:
            mascara = filtrado[col].isna() | filtrado[col].astype(str).isin(seleccionadas)
            filtrado = filtrado[mascara]

    # Filtros numéricos
    for col in columnas_numericas:
        if col not in filtrado.columns:
            continue

        valores = pd.to_numeric(filtrado[col], errors="coerce").dropna()
        if valores.empty:
            continue

        minimo = float(valores.min())
        maximo = float(valores.max())

        rango = st.sidebar.slider(
            f"Rango — {col}",
            min_value=minimo,
            max_value=maximo,
            value=(minimo, maximo),
            key=f"numerico_{col}",
        )

        mascara = filtrado[col].isna() | filtrado[col].between(rango[0], rango[1])
        filtrado = filtrado[mascara]

    return filtrado


def detectar_atipicos(df: pd.DataFrame, variables: list[str], factor: float) -> pd.DataFrame:
    """Detecta atípicos por variable usando el rango intercuartílico."""
    resultados = []

    for variable in variables:
        serie = pd.to_numeric(df[variable], errors="coerce")
        valida = serie.dropna()

        if valida.empty:
            continue

        q1 = valida.quantile(0.25)
        q3 = valida.quantile(0.75)
        iqr = q3 - q1
        limite_inferior = q1 - factor * iqr
        limite_superior = q3 + factor * iqr

        mascara = (serie < limite_inferior) | (serie > limite_superior)
        indices = df.index[mascara.fillna(False)]

        for idx in indices:
            registro = df.loc[idx].to_dict()
            registro["Fila original"] = idx
            registro["Variable"] = variable
            registro["Valor atípico"] = serie.loc[idx]
            registro["Límite inferior"] = limite_inferior
            registro["Límite superior"] = limite_superior
            resultados.append(registro)

    if not resultados:
        return pd.DataFrame(
            columns=list(df.columns)
            + ["Fila original", "Variable", "Valor atípico", "Límite inferior", "Límite superior"]
        )

    columnas_finales = (
        list(df.columns)
        + ["Fila original", "Variable", "Valor atípico", "Límite inferior", "Límite superior"]
    )
    return pd.DataFrame(resultados)[columnas_finales]


def mostrar_bienvenida() -> None:
    st.title("Explorador automático de datos")
    st.write(
        "Carga un archivo CSV, XLSX o XLS y realiza automáticamente un análisis "
        "exploratorio, de calidad y distribución de los datos."
    )

    st.info(
        "Para comenzar, utiliza el cargador de archivos de la barra lateral. "
        "La aplicación no utiliza datasets de ejemplo ni rutas de archivos predeterminadas."
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("1. Cargar")
        st.write("Selecciona tu dataset desde el computador.")
    with col2:
        st.subheader("2. Explorar")
        st.write("Revisa estructura, calidad, estadísticas, distribuciones y correlaciones.")
    with col3:
        st.subheader("3. Descargar")
        st.write("Descarga los datos filtrados y los valores atípicos detectados.")

    st.subheader("Análisis disponibles")
    st.markdown(
        """
        - Resumen y tipos de variables
        - Registros duplicados
        - Valores faltantes
        - Estadísticas descriptivas
        - Distribuciones numéricas y categóricas
        - Correlaciones Pearson, Spearman y Kendall
        - Detección de valores atípicos mediante IQR
        - Filtros interactivos
        - Tabla de datos ordenable
        - Descarga de resultados en CSV
        """
    )

    st.caption(
        "Privacidad: los datos se procesan durante la sesión. Evita cargar información "
        "personal, confidencial o sensible."
    )


# -----------------------------
# Carga del archivo
# -----------------------------
st.title("Explorador automático de datos")
st.caption(
    "Carga un dataset y obtén una exploración automática de estructura, calidad, "
    "estadística, distribución, correlación y valores atípicos."
)

st.sidebar.header("Carga del dataset")
archivo = st.sidebar.file_uploader(
    "Selecciona un archivo",
    type=["csv", "xlsx", "xls"],
    help="Formatos admitidos: CSV, XLSX y XLS.",
)

if archivo is None:
    mostrar_bienvenida()
    st.stop()

st.sidebar.success(f"Archivo cargado: {archivo.name}")

try:
    contenido = archivo.getvalue()
    if not contenido:
        st.warning("El archivo está vacío. Carga un archivo que contenga datos.")
        st.stop()

    df = leer_dataset(contenido, archivo.name)

except Exception as error:
    st.error(
        "No fue posible procesar el archivo. Verifica que el formato sea válido, "
        "que no esté dañado y que corresponda a CSV, XLSX o XLS."
    )
    with st.expander("Detalle técnico"):
        st.write(str(error))
    st.stop()

if df.empty:
    st.warning("El archivo no contiene registros.")
    st.stop()

if len(df.columns) == 0:
    st.warning("El archivo no contiene columnas.")
    st.stop()

# Índice técnico para conservar la posición original sin alterar las columnas.
df["_fila_original_explorador"] = np.arange(len(df))

# -----------------------------
# Filtros
# -----------------------------
st.sidebar.divider()
st.sidebar.header("Filtros interactivos")

tipos = {col: clasificar_variable(df[col]) for col in df.columns if col != "_fila_original_explorador"}

fecha_cols = [c for c, t in tipos.items() if t == "Fecha/hora"]
categoricas = [c for c, t in tipos.items() if t == "Categórica"]
numericas = [c for c, t in tipos.items() if t == "Numérica"]

with st.sidebar.expander("Seleccionar filtros", expanded=True):
    fecha_filtros = st.multiselect(
        "Variables de fecha",
        options=fecha_cols,
        default=[],
        help="Los registros con fecha faltante se conservan.",
    )
    cat_filtros = st.multiselect(
        "Variables categóricas",
        options=categoricas,
        default=[],
    )
    num_filtros = st.multiselect(
        "Variables numéricas",
        options=numericas,
        default=[],
    )

df_filtrado = aplicar_filtros(df, fecha_filtros, cat_filtros, num_filtros)

if df_filtrado.empty:
    st.warning(
        "Los filtros actuales no producen registros. Ajusta los filtros para continuar."
    )
    st.stop()

# Columnas visibles sin la columna técnica.
columnas_datos = [c for c in df.columns if c != "_fila_original_explorador"]

st.sidebar.divider()
st.sidebar.metric("Registros después de filtros", f"{len(df_filtrado):,}")

# -----------------------------
# Indicadores generales
# -----------------------------
st.subheader("Indicadores generales")
m1, m2, m3, m4 = st.columns(4)

duplicados = int(df_filtrado.duplicated().sum())
faltantes = int(df_filtrado[columnas_datos].isna().sum().sum())

m1.metric("Número de filas", f"{len(df_filtrado):,}")
m2.metric("Número de columnas", f"{len(columnas_datos):,}")
m3.metric("Duplicados completos", f"{duplicados:,}")
m4.metric("Celdas faltantes", f"{faltantes:,}")

st.caption(
    f"Archivo: **{archivo.name}** · Filas: **{df_filtrado.shape[0]:,}** · "
    f"Columnas: **{df_filtrado.shape[1] - 1:,}**"
)

# -----------------------------
# Pestañas
# -----------------------------
tabs = st.tabs(
    [
        "Resumen y tipos",
        "Calidad de datos",
        "Estadísticas",
        "Distribuciones",
        "Correlaciones",
        "Valores atípicos",
        "Tabla ordenable",
    ]
)

# TAB 1
with tabs[0]:
    st.header("Resumen y tipos")
    resumen = construir_resumen_tipos(df_filtrado[columnas_datos])
    st.dataframe(resumen, use_container_width=True, hide_index=True)

    st.subheader("Dimensiones")
    st.write(
        f"El dataset filtrado contiene **{df_filtrado.shape[0]:,} filas** y "
        f"**{df_filtrado.shape[1] - 1:,} columnas**."
    )

# TAB 2
with tabs[1]:
    st.header("Calidad de datos")

    st.subheader("Registros duplicados")
    duplicados_df = df_filtrado[df_filtrado[columnas_datos].duplicated(keep=False)]

    if duplicados_df.empty:
        st.success("No existen registros completamente duplicados en el dataset filtrado.")
    else:
        st.warning(
            f"Se encontraron {duplicados:,} filas duplicadas completas. "
            "No se eliminan automáticamente."
        )
        st.dataframe(duplicados_df[columnas_datos], use_container_width=True, hide_index=True)

    st.subheader("Valores faltantes")
    faltantes_df = pd.DataFrame(
        {
            "Variable": columnas_datos,
            "Valores faltantes": df_filtrado[columnas_datos].isna().sum().values,
        }
    )
    faltantes_df["Porcentaje faltante"] = (
        faltantes_df["Valores faltantes"] / len(df_filtrado) * 100
    )
    faltantes_df = faltantes_df.sort_values(
        "Valores faltantes", ascending=False
    ).reset_index(drop=True)

    st.dataframe(
        faltantes_df.style.format({"Porcentaje faltante": "{:.2f}%"}),
        use_container_width=True,
        hide_index=True,
    )

    fig_missing = px.bar(
        faltantes_df,
        x="Variable",
        y="Porcentaje faltante",
        title="Porcentaje de valores faltantes por variable",
        labels={"Porcentaje faltante": "% faltante", "Variable": "Variable"},
    )
    fig_missing.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_missing, use_container_width=True)

# TAB 3
with tabs[2]:
    st.header("Estadísticas descriptivas")

    opcion_estadisticas = st.radio(
        "Selecciona el tipo de variables",
        ["Todas las variables", "Solo variables numéricas", "Solo variables categóricas"],
        horizontal=True,
    )

    try:
        if opcion_estadisticas == "Solo variables numéricas":
            seleccion = [c for c in columnas_datos if tipos.get(c) == "Numérica"]
            if not seleccion:
                raise ValueError("No hay variables numéricas.")

            estadisticas_num = df_filtrado[seleccion].describe().T.reset_index()
            estadisticas_num = estadisticas_num.rename(columns={"index": "Variable"})
            st.dataframe(
                estadisticas_num.style.format(
                    {c: "{:,.4f}" for c in estadisticas_num.columns if c != "Variable"}
                ),
                use_container_width=True,
                hide_index=True,
            )

        elif opcion_estadisticas == "Solo variables categóricas":
            seleccion = [c for c in columnas_datos if tipos.get(c) == "Categórica"]
            if not seleccion:
                raise ValueError("No hay variables categóricas.")

            filas = []
            for col in seleccion:
                serie = df_filtrado[col]
                conteo = int(serie.notna().sum())
                unicos = int(serie.nunique(dropna=True))
                if serie.dropna().empty:
                    dominante = np.nan
                    frecuencia = 0
                else:
                    frecuencias = serie.value_counts(dropna=True)
                    dominante = frecuencias.index[0]
                    frecuencia = int(frecuencias.iloc[0])

                filas.append(
                    {
                        "Variable": col,
                        "Conteo": conteo,
                        "Valores únicos": unicos,
                        "Categoría más frecuente": dominante,
                        "Frecuencia dominante": frecuencia,
                    }
                )

            st.dataframe(
                pd.DataFrame(filas),
                use_container_width=True,
                hide_index=True,
            )

        else:
            seleccion_num = [c for c in columnas_datos if tipos.get(c) == "Numérica"]
            seleccion_cat = [c for c in columnas_datos if tipos.get(c) == "Categórica"]

            if seleccion_num:
                st.subheader("Variables numéricas")
                tabla_num = df_filtrado[seleccion_num].describe().T.reset_index()
                tabla_num = tabla_num.rename(columns={"index": "Variable"})
                st.dataframe(tabla_num, use_container_width=True, hide_index=True)
            else:
                st.info("No existen variables numéricas.")

            if seleccion_cat:
                st.subheader("Variables categóricas")
                filas = []
                for col in seleccion_cat:
                    serie = df_filtrado[col]
                    frec = serie.value_counts(dropna=True)
                    filas.append(
                        {
                            "Variable": col,
                            "Conteo": int(serie.notna().sum()),
                            "Valores únicos": int(serie.nunique(dropna=True)),
                            "Categoría más frecuente": frec.index[0] if not frec.empty else np.nan,
                            "Frecuencia dominante": int(frec.iloc[0]) if not frec.empty else 0,
                        }
                    )
                st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)
            else:
                st.info("No existen variables categóricas.")

    except ValueError as error:
        st.info(str(error))
    except Exception as error:
        st.error(f"No fue posible calcular las estadísticas: {error}")

# TAB 4
with tabs[3]:
    st.header("Distribuciones")

    opciones_distribucion = columnas_datos
    if not opciones_distribucion:
        st.info("No existen variables para visualizar.")
    else:
        variable = st.selectbox("Selecciona una variable", opciones_distribucion)
        tipo_variable = clasificar_variable(df_filtrado[variable])

        if tipo_variable == "Numérica":
            col_a, col_b = st.columns(2)

            with col_a:
                bins = st.slider("Número de intervalos del histograma", 5, 100, 30)
                serie_num = pd.to_numeric(df_filtrado[variable], errors="coerce").dropna()
                fig_hist = px.histogram(
                    x=serie_num,
                    nbins=bins,
                    title=f"Histograma — {variable}",
                    labels={"x": variable, "y": "Frecuencia"},
                )
                st.plotly_chart(fig_hist, use_container_width=True)

            with col_b:
                categorias_box = [c for c in columnas_datos if clasificar_variable(df_filtrado[c]) == "Categórica"]
                opciones_box = ["Sin agrupación"] + categorias_box
                agrupador = st.selectbox("Agrupar diagrama de caja por", opciones_box)

                datos_box = df_filtrado[[variable]].copy()
                datos_box[variable] = pd.to_numeric(datos_box[variable], errors="coerce")

                if agrupador != "Sin agrupación":
                    datos_box[agrupador] = df_filtrado[agrupador].astype("object").fillna("(Faltante)")
                    fig_box = px.box(
                        datos_box,
                        x=agrupador,
                        y=variable,
                        points="outliers",
                        title=f"Diagrama de caja — {variable}",
                    )
                else:
                    fig_box = px.box(
                        datos_box,
                        y=variable,
                        points="outliers",
                        title=f"Diagrama de caja — {variable}",
                    )

                st.plotly_chart(fig_box, use_container_width=True)

        elif tipo_variable in ("Categórica", "Booleana", "Texto"):
            frecuencia = (
                df_filtrado[variable]
                .astype("object")
                .where(df_filtrado[variable].notna(), "(Faltante)")
                .astype(str)
                .value_counts()
                .reset_index()
            )
            frecuencia.columns = [variable, "Frecuencia"]

            if len(frecuencia) > 30:
                st.info("La variable tiene muchas categorías. Se muestran las 30 más frecuentes.")
                frecuencia = frecuencia.head(30)

            fig_bar = px.bar(
                frecuencia,
                x=variable,
                y="Frecuencia",
                title=f"Frecuencia por categoría — {variable}",
                labels={variable: "Categoría", "Frecuencia": "Frecuencia"},
            )
            fig_bar.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_bar, use_container_width=True)

            st.dataframe(frecuencia, use_container_width=True, hide_index=True)

        elif tipo_variable == "Fecha/hora":
            frecuencia = (
                df_filtrado[variable]
                .dropna()
                .dt.to_period("M")
                .astype(str)
                .value_counts()
                .sort_index()
                .reset_index()
            )
            frecuencia.columns = ["Periodo", "Frecuencia"]
            fig_fecha = px.bar(
                frecuencia,
                x="Periodo",
                y="Frecuencia",
                title=f"Registros por mes — {variable}",
            )
            st.plotly_chart(fig_fecha, use_container_width=True)

# TAB 5
with tabs[4]:
    st.header("Correlaciones")

    variables_numericas = [c for c in columnas_datos if tipos.get(c) == "Numérica"]

    if len(variables_numericas) < 2:
        st.info("Se requieren al menos dos variables numéricas para calcular correlaciones.")
    else:
        variables_corr = st.multiselect(
            "Selecciona las variables",
            options=variables_numericas,
            default=variables_numericas[: min(8, len(variables_numericas))],
        )

        metodo = st.selectbox(
            "Método de correlación",
            ["Pearson", "Spearman", "Kendall"],
        )

        if len(variables_corr) < 2:
            st.warning("Selecciona al menos dos variables.")
        else:
            mapa_metodos = {"Pearson": "pearson", "Spearman": "spearman", "Kendall": "kendall"}
            matriz = df_filtrado[variables_corr].corr(method=mapa_metodos[metodo])

            fig_corr = go.Figure(
                data=go.Heatmap(
                    z=matriz.values,
                    x=matriz.columns,
                    y=matriz.index,
                    zmin=-1,
                    zmax=1,
                    colorscale="RdBu",
                    text=np.round(matriz.values, 2),
                    texttemplate="%{text}",
                    hovertemplate="%{y} × %{x}<br>Correlación: %{z:.3f}<extra></extra>",
                    colorbar={"title": "Correlación"},
                )
            )
            fig_corr.update_layout(
                title=f"Matriz de correlación — {metodo}",
                xaxis_title="Variable",
                yaxis_title="Variable",
            )
            st.plotly_chart(fig_corr, use_container_width=True)

            st.subheader("Matriz como tabla")
            st.dataframe(
                matriz.style.format("{:.4f}"),
                use_container_width=True,
            )

# TAB 6
with tabs[5]:
    st.header("Valores atípicos")
    st.write(
        "Método utilizado: rango intercuartílico (IQR). "
        "IQR = Q3 − Q1; límite inferior = Q1 − factor × IQR; "
        "límite superior = Q3 + factor × IQR."
    )

    variables_atipicos = st.multiselect(
        "Selecciona una o varias variables numéricas",
        options=numericas,
        default=numericas[: min(3, len(numericas))],
    )
    factor = st.slider("Factor IQR", 1.0, 3.0, 1.5, 0.1)

    if not variables_atipicos:
        st.info("Selecciona al menos una variable numérica.")
        atipicos_df = pd.DataFrame()
    else:
        atipicos_df = detectar_atipicos(
            df_filtrado[columnas_datos],
            variables_atipicos,
            factor,
        )

        if atipicos_df.empty:
            st.success("No se detectaron valores atípicos con la configuración seleccionada.")
        else:
            conteos = (
                atipicos_df["Variable"]
                .value_counts()
                .rename_axis("Variable")
                .reset_index(name="Cantidad de atípicos")
            )

            st.subheader("Cantidad de detecciones")
            st.dataframe(conteos, use_container_width=True, hide_index=True)

            fig_out = px.bar(
                conteos,
                x="Variable",
                y="Cantidad de atípicos",
                title="Valores atípicos detectados por variable",
            )
            st.plotly_chart(fig_out, use_container_width=True)

            st.subheader("Registros detectados")
            st.dataframe(atipicos_df, use_container_width=True, hide_index=True)

            st.download_button(
                "Descargar valores atípicos",
                data=csv_bytes(atipicos_df),
                file_name="valores_atipicos.csv",
                mime="text/csv",
                use_container_width=True,
            )

# TAB 7
with tabs[6]:
    st.header("Tabla ordenable")

    columnas_seleccionadas = st.multiselect(
        "Columnas visibles",
        options=columnas_datos,
        default=columnas_datos,
        help="Selecciona las columnas que deseas visualizar.",
    )

    if not columnas_seleccionadas:
        st.info("No se ha seleccionado ninguna columna.")
    else:
        st.dataframe(
            df_filtrado[columnas_seleccionadas],
            use_container_width=True,
            hide_index=True,
        )

# -----------------------------
# Descarga general
# -----------------------------
st.divider()
st.subheader("Descarga de resultados")

d1, d2 = st.columns(2)

with d1:
    st.download_button(
        "Descargar datos filtrados",
        data=csv_bytes(df_filtrado[columnas_datos]),
        file_name="datos_filtrados.csv",
        mime="text/csv",
        use_container_width=True,
    )

with d2:
    if "atipicos_df" in locals() and not atipicos_df.empty:
        datos_atipicos_descarga = atipicos_df
    else:
        datos_atipicos_descarga = pd.DataFrame()

    st.download_button(
        "Descargar valores atípicos",
        data=csv_bytes(datos_atipicos_descarga),
        file_name="valores_atipicos.csv",
        mime="text/csv",
        use_container_width=True,
        disabled=datos_atipicos_descarga.empty,
    )

st.info(
    "Tratamiento responsable de los datos: los datos se procesan durante la sesión de la "
    "aplicación; evita cargar información personal, confidencial o sensible. Esta herramienta "
    "realiza análisis exploratorio y no reemplaza la interpretación experta. Una correlación "
    "no implica causalidad y un valor atípico no necesariamente representa un error."
)
