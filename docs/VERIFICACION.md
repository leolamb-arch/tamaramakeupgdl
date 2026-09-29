# Correcciones y verificación

Fecha: 29 de septiembre de 2026. Base: `f8cb1b0c984437800491216bef9784c9c1d782b5`. Rama: `fix/auditoria-y-limpieza`.

## Resultado comprobado

- 20 pruebas de servidor aprobadas con SQLite temporal: autenticación, CSRF, permisos, validación, publicación, versiones, restauración, imágenes, solicitudes, exportación y respaldos.
- Navegador Edge mediante Playwright, escritorio de 1440 × 1000 y móvil de 390 × 844: navegación, formulario, registro pendiente, login, edición, guardado, visualización pública y logout aprobados. Se probaron también Contenido, Ubicación, Cotización y Quiz, y Apariencia.
- Sin errores de consola en los recorridos automatizados.
- ESLint, Ruff, comprobación de formato y build aprobados. El build valida 129 archivos; utiliza módulos nativos y no recompila el panel de terceros.
- npm audit y pip-audit no encontraron vulnerabilidades conocidas en las dependencias declaradas consultadas. No cubren por completo las bibliotecas incrustadas en el panel compilado.
- Axe no detectó incumplimientos distintos de contraste en los recorridos con la paleta original. En las páginas comprobadas con las opciones de contraste activadas tampoco detectó incumplimientos de contraste. Esto no sustituye una evaluación manual completa WCAG.

## Hallazgos y resolución

| Hallazgo | Acción y estado |
| --- | --- |
| Tipos inválidos podían romper la portada; índice fraccionario de imagen | Esquemas estrictos y rechazo antes de publicar. Probado. |
| Una edición podía deshacer una restauración | Instantáneas coherentes del CMS y del panel, transacciones y pruebas de regresión. |
| Pruebas y documentación anunciadas pero ausentes | Suite de servidor y navegador, CI, README y guía de despliegue incorporados. CI remota pendiente de ejecución. |
| Formulario que solo mostraba un resumen | Envío explícito de solicitudes pendientes al panel, conforme a la decisión del propietario. Sin confirmación ni cobro automáticos. |
| Contenido sin controles de edición suficientes | Pestaña Textos y versiones, imágenes, SEO, vista previa privada y restauración. |
| Contraste insuficiente con la paleta original | Controles opcionales desde el panel, propuesta y vista previa antes de publicar; opción local para mejorar el propio panel. La apariencia inicial se conserva. |
| Campos del panel sin etiquetas accesibles | Asociación de etiquetas existentes y nombre accesible del cierre de sesión móvil. |
| Recursos y flujos defectuosos | Correcciones de favicon, fuentes en vista previa, MIME WebP, login por nombre, exportación ICS y contacto configurado. |
| Proxy y errores internos | Confianza por CIDR explícito, errores públicos genéricos y health check con consulta a base. |
| Código duplicado, archivos vacíos y herramientas ausentes | Limpieza de módulos sin referencias, formato del código propio, linters y exclusión de archivos sensibles. |
| Panel compilado sin sus fuentes originales | Se conserva y se extiende con módulos propios. Recuperar las fuentes originales sigue pendiente; no es posible reconstruirlas fielmente a partir del repositorio. |

## Límites y pasos de producción

No se modificaron las cuentas, solicitudes ni bases reales. No se desplegó esta rama ni se verificaron secretos, permisos PostgreSQL/Supabase, bucket, IP real del proxy o restauración de respaldos en Render. Esas comprobaciones necesitan acceso al entorno; el procedimiento está en DESPLIEGUE.md. No se realizó prueba de carga ni auditoría del historial Git completo.

GitHub Pages no ejecuta este backend Python: el servicio funcional debe desplegarse en Render u otro servidor compatible. No se implementaron pagos ni integración automática con Google Calendar. Se conserva la exportación manual y el comportamiento pendiente elegido por el propietario.

Los CSS, fuentes e imágenes originales no se modificaron. El administrador puede decidir publicar otros colores; las pruebas de contraste usaron exclusivamente datos temporales. Los resultados automatizados no justifican prometer ausencia absoluta de errores o certificar producción sin verificar el despliegue real.
