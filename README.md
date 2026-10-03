# Radar de Mercado

Aplicación en español para investigación educativa de productos de dropshipping y activos financieros. Incluye registros privados por cuenta, simulación manual y análisis opcional de imágenes con IA. No ejecuta órdenes, no vigila mercados en segundo plano, no verifica por sí sola la demanda de un producto y no ofrece recomendaciones financieras personalizadas.

## Arquitectura de datos y cuentas

- **Supabase Auth** gestiona registro, inicio de sesión y verificación de correo.
- **Supabase PostgreSQL** guarda productos, preferencias, alertas, carteras simuladas, progreso y resultados de imágenes.
- Cada fila tiene un `user_id`; Row Level Security (RLS) limita cada operación a la cuenta autenticada. El servicio usa la clave publicable junto con la sesión de Auth; no requiere la clave `service_role`.
- La app no ofrece cuentas anónimas. Si faltan las credenciales de Supabase, muestra la pantalla de configuración y no abre datos compartidos.
- Las fotos originales se procesan en memoria, se optimizan y se envían a OpenAI solo al pulsar **Analizar imagen**. Radar guarda el texto del análisis y el nombre del archivo, no la imagen.

## Configuración para publicar

1. Crea un proyecto en Supabase y ejecuta `database/schema.sql` completo en **SQL Editor**. El archivo crea las tablas y políticas RLS usadas por la app.
2. En la configuración API del proyecto, obtén la **Project URL** y su clave publicable (`anon`/publishable). No uses la clave `service_role`.
3. En **Authentication → Providers**, habilita correo y contraseña. Mantén activa la verificación de correo. En URL Configuration, establece la URL de Radar como `Site URL` y añade esa misma dirección a las URL permitidas para redirección.
4. En Streamlit Community Cloud, abre **Manage app → Settings → Secrets** y guarda:

   ```toml
   SUPABASE_URL = "https://tu-proyecto.supabase.co"
   SUPABASE_ANON_KEY = "tu-clave-publicable"
   OPENAI_API_KEY = "tu-clave-de-openai"
   OPENAI_MODEL = "gpt-5"
   OPENAI_VISION_MODEL = "gpt-5"
   ALPHAVANTAGE_API_KEY = ""
   COINGECKO_API_KEY = ""
   ```

   `OPENAI_API_KEY` habilita tanto el asistente como el análisis visual. Alpha Vantage y CoinGecko son opcionales. No copies secretos al repositorio ni los compartas en el chat.
5. Reinicia la app. Cada persona crea su cuenta con su correo, confirma el mensaje recibido e inicia sesión.

Para ejecutar localmente, instala las dependencias de `requirements.txt`, copia `.env.example` a `.env`, rellena las claves de prueba y ejecuta `python -m streamlit run app.py`. Nunca subas `.env`.

## Analizar una imagen

En **Analizar imágenes**, elige **Dropshipping** o **Trading**, sube una imagen JPG, PNG o WebP de hasta 8 MB y confirma el envío a OpenAI.

- **Dropshipping:** describe atributos visibles y propone qué validar con una muestra, proveedor, costes, entregas, devoluciones, demanda documentada y competencia. Una foto no demuestra ventas, demanda, precio, autenticidad ni derechos de uso.
- **Trading:** resume solo lo que resulte legible en una captura de gráfico y señala qué datos faltan. La captura puede estar desactualizada o incompleta; el análisis no predice el precio ni indica comprar o vender.

La búsqueda web es opcional y puede aumentar el coste de OpenAI. Cada cuenta tiene un límite de cinco intentos por periodo móvil de 24 horas; para controlar el gasto total, configura también alertas o límites de uso en la cuenta de API del administrador.

El archivo se convierte a una imagen JPEG optimizada y se descartan metadatos de orientación antes del envío. La imagen no se guarda; Radar conserva el resultado con un nombre genérico en tu cuenta y puedes borrarlo desde el historial. No subas identificaciones, datos personales, material privado ni imágenes que no tengas permiso para utilizar. El proveedor de IA procesa la imagen conforme a las condiciones de la cuenta de API configurada.

## Funciones y límites

- **Productos:** altas y edición manual, favoritos, comparación, CSV, histórico de anotaciones y cálculo aproximado de margen. No hay catálogo de proveedores, verificación automatizada de tendencias ni datos de ventas.
- **Activos:** acciones y ETF mediante Alpha Vantage y criptomonedas mediante CoinGecko, si las claves y planes respectivos permiten la consulta. La frecuencia es manual y los datos pueden venir retrasados o limitados.
- **Cartera virtual:** registros simulados manualmente; no hay conexión a un bróker ni órdenes reales.
- **Alertas:** se revisan al consultar datos o pulsar la acción correspondiente; no hay vigilancia continua ni avisos en segundo plano.
- **Asistente:** las preguntas y el contexto elegido se envían a OpenAI cuando se consulta. Las respuestas pueden equivocarse; comprueba las fuentes y fechas.
- **Imágenes:** el análisis visual es orientativo. La demanda, los precios, los indicadores y las condiciones del proveedor requieren evidencia actual por separado.

Antes de abrir el servicio a clientes o cobrar por él, completa una política de privacidad y condiciones de uso adecuadas a tu actividad, verifica los costes y límites de Supabase/OpenAI y prueba el alta, la verificación de correo y la separación de cuentas con dos usuarios distintos. La plantilla técnica no sustituye una revisión legal ni una auditoría de seguridad independiente.

## Protección de secretos

`.env`, `data/*.db`, `.streamlit/secrets.toml` y archivos temporales están excluidos por `.gitignore`. El acceso a la base se realiza con la clave publicable y el token de la cuenta autenticada; las políticas RLS del esquema son obligatorias para la privacidad.
