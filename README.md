# Radar de Mercado

Aplicación educativa en español para investigar fichas de productos de dropshipping y estudiar activos financieros con cotizaciones e históricos consultados manualmente. Está creada con Python, Streamlit y SQLite. No ejecuta órdenes, no se conecta a brókeres y no promete resultados.

## Instalación

Requiere Python 3.11 o posterior.

En Windows, abre PowerShell en la carpeta del proyecto:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
streamlit run app.py
```

En macOS o Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

La aplicación se abrirá en la dirección local que Streamlit muestre en la terminal. Para detenerla, usa `Ctrl+C`.

## Configurar fuentes

Edita el archivo `.env` que has creado. Las claves solo se leen desde variables de entorno o ese archivo local; no se guardan en SQLite ni se muestran en la interfaz.

```text
ALPHAVANTAGE_API_KEY=tu_clave
COINGECKO_API_KEY=tu_clave_demo
OPENAI_API_KEY=tu_clave
OPENAI_MODEL=gpt-5
```

- **Alpha Vantage**: crea una clave y consulta [su documentación oficial](https://www.alphavantage.co/documentation/). Se usa para cotizaciones de acciones/ETF, históricos diarios, ficha fundamental y noticias. La cotización disponible depende del plan y puede ser diaria, retrasada o limitada; la aplicación muestra la fecha que devuelve el proveedor. Las consultas de fundamentales y noticias son opcionales. Respeta el plan y los términos de uso de tu cuenta.
- **CoinGecko**: crea una clave Demo y sigue [la documentación oficial](https://docs.coingecko.com/). Se usa para precio, capitalización, volumen e histórico de criptoactivos. En el buscador se introduce el ID de CoinGecko, por ejemplo `bitcoin` o `ethereum`; la app envía la clave como encabezado HTTP y no la muestra.
- **OpenAI API**: crea una clave y sigue [la guía oficial](https://platform.openai.com/docs/quickstart). El asistente envía la pregunta y el contexto visible de la app cuando tú la envías. Se solicita `store=False`; revisa la configuración y condiciones de tu cuenta antes de usar datos sensibles. Si no hay clave, funciona un modo de demostración explícito con explicaciones predefinidas, sin precios ni búsqueda en Internet.

Reinicia Streamlit después de editar `.env`. En **Configuración** puedes ver qué credenciales se detectaron, el estado de las últimas consultas y la hora de la última respuesta correcta. La app no comprueba la validez de una clave hasta que consultas el servicio.

## Funciones que usan datos reales

Con una fuente y credencial configuradas, una consulta manual puede traer:

- Acciones y ETF: cotización de Alpha Vantage, hasta 100 observaciones diarias, volumen histórico y, si lo solicitas, fundamentals y noticias con enlaces y fecha.
- Criptoactivos: precio, variación, capitalización, volumen e histórico de CoinGecko.
- Alertas de activo: se evalúan cuando consultas la cotización o pulsas **Revisar alertas de activos en seguimiento**. Las alertas de noticias se revisan cuando se consulta esa fuente.
- Asistente conectado: explica los datos que se pasan desde la pantalla. Puede equivocarse; conserva los enlaces originales para verificarlos.

El botón de consulta es manual. La aplicación no ofrece datos de alta frecuencia, no programa tareas en segundo plano ni envía notificaciones fuera de la sesión. Límites, cobertura y retraso dependen de la cuenta y de los términos de cada fuente.

## Funciones locales o manuales

- **Productos**: alta, edición, favoritos, comparación, importación CSV, puntuación ajustable y calculadora de margen. Costes, demanda, competencia, calidad y plazo se consideran datos introducidos por ti o importados; no hay catálogo de proveedores, Google Trends, comparador de precios ni estimación automática de demanda conectados. Añade el enlace y la fecha de cada evidencia.
- **Cálculo económico**: resta coste de producto, envío, comisión porcentual, impuesto estimado, reserva por devoluciones y publicidad por pedido. Ventas de equilibrio = presupuesto fijo de campaña dividido por la contribución por pedido antes de ese presupuesto. Es una aproximación: solo incluye los conceptos que introduzcas.
- **Puntuación de producto**: ordena fichas con los pesos visibles de margen, demanda documentada, saturación anotada y entrega. Omite los factores sin datos y aplica penalizaciones visibles por fragilidad o riesgo de marca. No estima ventas.
- **Evolución manual de producto**: cada vez que guardas cambios se registra precio, margen, señal de demanda, competencia y costes. Los gráficos muestran tus anotaciones; no detectan tendencias ni estacionalidad del mercado automáticamente.
- **Cartera virtual**: saldo ficticio, compras y ventas manuales simuladas, valoración manual o consulta de precios compatibles. Una moneda diferente no se convierte automáticamente. La referencia SPY solo se obtiene automáticamente para cartera USD; también se puede aportar una marca manual. La comparación no ajusta por efectivo, riesgo, fiscalidad ni dividendos.
- **Estrategia histórica**: cruce de medias rápidas/lentas aplicado desde la sesión siguiente a la señal; usa hasta 100 sesiones diarias de Alpha Vantage o un CSV aportado. No incluye dividendos, deslizamiento, impacto de mercado, impuestos ni ejecución parcial. Resultados pasados no predicen resultados futuros.
- **Aprendizaje**: lecciones, cuestionarios y progreso guardados localmente.
- **Bonos**: no hay integración de precios de bonos en esta versión; se señala en la pantalla.

## CSV de productos

En **Productos → Importar CSV** puedes descargar una plantilla. La columna `name` es obligatoria. Las columnas disponibles son `name`, `category`, `country`, `currency`, `provider`, `provider_url`, `source_url`, `product_cost`, `shipping_cost`, `ad_cost`, `platform_fee_pct`, `tax_pct`, `refund_pct`, `sale_price`, `launch_budget`, `delivery_days`, `supplier_quality`, `demand_score`, `demand_source`, `demand_updated`, `competition_score`, `fragile`, `brand_risk` y `notes`.

Para el histórico de estrategia, carga CSV con columnas `date` y `close`; se aceptan columnas adicionales, que no se usan en este cálculo.

## Datos locales y privacidad

Las fichas, preferencias, carteras, historial simulado, alertas y avance se guardan en `data/radar.db` (SQLite) dentro del proyecto. Ese archivo se crea al iniciar la app y está excluido del control de versiones por `.gitignore`. No se sincroniza automáticamente con otros dispositivos. **Configuración → Borrar datos locales** elimina los registros de la app; no borra `.env`.

No guardes información personal innecesaria, claves, contraseñas ni datos financieros identificables. Si activas OpenAI, la pregunta y el resumen de datos visibles se envían a la API cuando consultas el asistente.

El idioma preferido se guarda como configuración, pero la fuente de noticias configurada no expone un filtro de idioma en este conector.

## Estructura

```text
app.py
radar/
  config.py
  db.py
  scoring.py
  alerts.py
  assistant.py
  lessons.py
  sources/
    alpha_vantage.py
    coingecko.py
  views/
    home.py
    products.py
    investments.py
    simulator.py
    alerts.py
    learning.py
    assistant.py
    settings.py
data/              # se crea al iniciar; SQLite local
.env.example       # plantilla sin credenciales reales
requirements.txt
```

## Límites educativos

El análisis muestra datos disponibles, supuestos y campos ausentes. Una cotización, métrica histórica, índice de revisión o alerta no es una señal de compra o venta. Revisa las condiciones del servicio, comisiones, impuestos y normativa aplicables a tu país antes de tomar decisiones.
