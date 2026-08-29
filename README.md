# Explorador automático de datos

Aplicación web desarrollada con Python, Pandas, Plotly y Streamlit para realizar análisis exploratorio de datos (EDA) a partir de archivos cargados directamente por el usuario.

## Descripción

**Explorador automático de datos** permite cargar archivos CSV, XLSX y XLS sin depender de un dataset predeterminado ni de rutas locales. Después de la carga, la aplicación analiza el dataset filtrado y presenta información sobre estructura, tipos de variables, calidad de datos, estadísticas, distribuciones, correlaciones y valores atípicos.

Los archivos se procesan en memoria durante la sesión y no se incorpora ningún dataset de ejemplo al repositorio.

## Funcionalidades

- Carga de archivos CSV, XLSX y XLS.
- Lectura de CSV con Pandas.
- Lectura de XLSX mediante `openpyxl`.
- Lectura de XLS mediante `xlrd`.
- Detección orientativa de columnas de fecha a partir de nombres que contienen `fecha` o `date`.
- Eliminación de espacios innecesarios en nombres de columnas.
- Indicadores de filas, columnas, duplicados y valores faltantes.
- Clasificación analítica de variables:
  - Numérica
  - Categórica
  - Texto
  - Booleana
  - Fecha/hora
- Identificación de registros completamente duplicados sin eliminarlos.
- Análisis de valores faltantes.
- Histograma y diagrama de caja para variables numéricas.
- Agrupación del diagrama de caja por variable categórica.
- Frecuencia de categorías con representación de faltantes.
- Límite de 30 categorías en visualizaciones categóricas de alta cardinalidad.
- Correlaciones Pearson, Spearman y Kendall.
- Mapa de calor interactivo de correlaciones con escala de -1 a 1.
- Detección de valores atípicos mediante IQR.
- Factor IQR configurable entre 1.0 y 3.0, con 1.5 como valor inicial.
- Filtros interactivos por fecha, categoría y rango numérico.
- Conservación de valores faltantes en los filtros de fecha y numéricos.
- Tabla interactiva mediante `st.dataframe`.
- Selección de columnas visibles.
- Descarga de datos filtrados y valores atípicos en CSV UTF-8 con BOM.
- Interfaz organizada mediante pestañas.
- Preparación para despliegue en Streamlit Community Cloud.

## Formatos admitidos

| Formato | Extensión | Motor |
|---|---|---|
| CSV | `.csv` | Pandas |
| Excel moderno | `.xlsx` | openpyxl |
| Excel antiguo | `.xls` | xlrd |

## Estructura del repositorio

```text
explorador-automatico-datos/
├── app.py
├── requirements.txt
└── README.md
```

No se debe incluir ningún dataset dentro del proyecto.

## Instalación local

### 1. Crear y entrar al proyecto

```bash
mkdir explorador-automatico-datos
cd explorador-automatico-datos
```

Copia dentro de esta carpeta:

- `app.py`
- `requirements.txt`
- `README.md`

### 2. Crear un entorno virtual

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Ejecutar

```bash
streamlit run app.py
```

La terminal mostrará la dirección local de la aplicación. Normalmente será:

```text
http://localhost:8501
```

## Uso

1. Inicia la aplicación.
2. Utiliza el cargador ubicado en la barra lateral.
3. Selecciona un archivo CSV, XLSX o XLS.
4. Revisa los indicadores generales.
5. Aplica filtros si los necesitas.
6. Explora las siete pestañas.
7. Selecciona las variables necesarias para estadísticas, distribuciones, correlaciones y atípicos.
8. Descarga los resultados desde la sección correspondiente.

## Despliegue en Streamlit Community Cloud

### 1. Crear un repositorio en GitHub

Crea un repositorio, por ejemplo:

```text
explorador-automatico-datos
```

Sube únicamente:

```text
app.py
requirements.txt
README.md
```

No subas datasets reales.

### 2. Subir los archivos con Git

```bash
git init
git add app.py requirements.txt README.md
git commit -m "Crear explorador automático de datos"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/explorador-automatico-datos.git
git push -u origin main
```

Sustituye `TU_USUARIO` por tu usuario de GitHub.

### 3. Crear la aplicación en Streamlit Community Cloud

1. Ingresa a Streamlit Community Cloud.
2. Inicia sesión con GitHub.
3. Selecciona **Create app**.
4. Selecciona el repositorio.
5. Selecciona la rama `main`.
6. Como archivo principal indica:

```text
app.py
```

7. Despliega la aplicación.

Streamlit instalará las dependencias indicadas en `requirements.txt`.

## Privacidad de los datos

La aplicación está diseñada para procesar los archivos durante la sesión. Aun así, el usuario debe evitar cargar información personal, confidencial o sensible, especialmente cuando la aplicación se encuentre desplegada en un servicio en la nube.

El análisis exploratorio tampoco reemplaza las políticas internas de seguridad, gobierno de datos, anonimización o clasificación de información de una organización.

## Limitaciones conocidas

- La detección de fechas se realiza de manera conservadora y se activa principalmente cuando el nombre de la columna contiene `fecha` o `date`.
- La clasificación de variables categóricas frente a texto es heurística y depende de la cardinalidad observada.
- Los archivos extremadamente grandes pueden superar la memoria disponible de la sesión.
- El formato `.xls` requiere la dependencia `xlrd`.
- Los análisis de correlación requieren al menos dos variables numéricas.
- Kendall puede ser considerablemente más lento que Pearson en datasets grandes.
- La detección IQR depende del factor seleccionado y de la distribución de cada variable.
- Los valores faltantes y atípicos no se imputan, corrigen ni eliminan automáticamente.
- Un valor atípico no implica necesariamente un error.
- Una correlación no implica causalidad.

## Pruebas funcionales recomendadas

### Carga

- [ ] Abrir la aplicación sin cargar archivo.
- [ ] Verificar la pantalla de bienvenida.
- [ ] Verificar que se utiliza `st.stop()`.
- [ ] Cargar un CSV válido.
- [ ] Cargar un XLSX válido.
- [ ] Cargar un XLS válido.
- [ ] Intentar cargar un archivo incompatible.
- [ ] Intentar cargar un archivo vacío.
- [ ] Cargar un archivo con nombres de columnas con espacios.

### Estructura y calidad

- [ ] Validar filas y columnas.
- [ ] Validar duplicados completos.
- [ ] Verificar que los duplicados no se eliminen.
- [ ] Validar valores faltantes.
- [ ] Verificar el porcentaje de faltantes.
- [ ] Probar una columna completamente vacía.

### Tipos y estadísticas

- [ ] Dataset solo con texto.
- [ ] Dataset solo numérico.
- [ ] Dataset con variables categóricas.
- [ ] Dataset con booleanos.
- [ ] Dataset con fechas.
- [ ] Dataset con una sola columna.
- [ ] Dataset sin variables numéricas.
- [ ] Dataset sin variables categóricas.

### Visualizaciones

- [ ] Histograma numérico.
- [ ] Cambio de número de intervalos.
- [ ] Boxplot sin agrupación.
- [ ] Boxplot agrupado por categoría.
- [ ] Barras de variables categóricas.
- [ ] Variable con más de 30 categorías.
- [ ] Visualización de faltantes.

### Correlaciones

- [ ] Pearson.
- [ ] Spearman.
- [ ] Kendall.
- [ ] Seleccionar una sola variable.
- [ ] Seleccionar dos o más variables.

### Atípicos

- [ ] Factor 1.0.
- [ ] Factor 1.5.
- [ ] Factor 3.0.
- [ ] Varias variables.
- [ ] Registro atípico en más de una variable.
- [ ] Descarga `valores_atipicos.csv`.
- [ ] Verificar que se conserva la fila original.

### Filtros

- [ ] Filtro de fecha.
- [ ] Fecha inicial posterior a fecha final.
- [ ] Registros con fecha faltante.
- [ ] Filtro categórico.
- [ ] Selección múltiple de categorías.
- [ ] Filtro numérico.
- [ ] Valores numéricos faltantes.
- [ ] Filtros que dejan cero registros.

### Descargas

- [ ] Descargar datos filtrados.
- [ ] Descargar valores atípicos.
- [ ] Verificar ausencia del índice de Pandas.
- [ ] Abrir los CSV descargados en Excel.
- [ ] Verificar codificación UTF-8 con BOM.

## Posibles errores y soluciones

### `ModuleNotFoundError: No module named 'streamlit'`

Instala las dependencias:

```bash
pip install -r requirements.txt
```

### Error al abrir `.xls`

Comprueba que `xlrd` esté instalado:

```bash
pip install xlrd
```

### Error al abrir `.xlsx`

Comprueba que `openpyxl` esté instalado:

```bash
pip install openpyxl
```

### CSV con caracteres extraños

La aplicación intenta primero UTF-8 y después `latin-1`. Si el archivo utiliza una codificación diferente, puede ser necesario adaptar la lectura.

### La aplicación se queda sin memoria

Reduce el tamaño del dataset, utiliza una muestra para exploración inicial o despliega en una instancia con mayor memoria.

### No se reconoce una fecha

Comprueba que el nombre de la columna contenga una expresión como `fecha` o `date` y que los valores tengan un formato interpretable por Pandas.

### No aparecen correlaciones

La matriz requiere al menos dos variables clasificadas como numéricas.

### No aparecen valores atípicos

Comprueba que hayas seleccionado variables numéricas y que tengan suficientes valores no nulos y variabilidad.

## Licencia

Puedes adaptar este proyecto a tus necesidades. Si se utiliza en un entorno corporativo, incorpora las políticas de seguridad, privacidad y gobierno de datos correspondientes.
