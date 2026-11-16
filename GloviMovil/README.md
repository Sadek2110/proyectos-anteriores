# GLOVI · Ceuta (Aplicación Android Nativa)

Aplicación móvil nativa para Android del piloto turístico y cultural de Ceuta, reescrita en **Kotlin** con **Jetpack Compose** y **Material Design 3**.

La app conserva todas las características, lógica de negocio y contenidos verificados del proyecto original: sistema multilingüe (Español, English, Français, العربية), itinerario histórico guiado con geolocalización y síntesis de voz (TTS), asistente inteligente híbrido (determinista + Gemini AI), motor de reservas con idempotencia y aforo, directorio de emergencias 112 y panel de operación para el piloto.

---

## Características Implementadas

1. **Pantalla Principal (Inicio / Home):**
   - Encabezado editorial con imágenes de Ceuta (*Entre murallas y mar*).
   - Acceso rápido a las rutas, asistente y reservas.
   - Panel de personalización en tiempo real: intereses (Historia, Arquitectura, Gastronomía) y consentimientos (Ubicación GPS e IA Gemini).

2. **Rutas Históricas (Ceuta Histórica):**
   - Recorrido monumental de 3 paradas: *Murallas Reales*, *Plaza de África* y *Casa de los Dragones*.
   - Medición de proximidad por GPS (umbral de 100 m) y simulación interactiva de llegada para pruebas.
   - Audioguía mediante el motor nativo de Android `TextToSpeech` en el idioma seleccionado.
   - Navegación a pie integrada con Google Maps y fuentes oficiales.
   - Seguimiento del progreso del tour (*0 / 3 · En curso*).

3. **Asistente GLOVI:**
   - Detección determinista de intenciones: emergencias (112), reservas, gastronomía y eSIM.
   - Respuestas contextualizadas según el idioma e intereses del usuario.
   - Modo Gemini AI disponible cuando el usuario otorga su consentimiento.
   - Historial de conversación (hasta 40 mensajes) y enlaces a fuentes verificadas.

4. **Motor de Reservas:**
   - Servicios de demostración (*Restaurante de demostración* y *Paseo cultural de demostración*) y turnos generados.
   - Selección de plazas (1 a 12 comensales), validación de datos y clave de idempotencia.
   - Control de aforo disponible en tiempo real.
   - Consulta del historial de solicitudes y cancelación de reservas activas.

5. **Emergencias (SOS 112):**
   - Botón directo de marcación telefónica al **112**.
   - Protocolo de actuación paso a paso localizado en los 4 idiomas.
   - Directorio de centros de atención (Hospital Universitario de Ceuta, Policía Nacional y consulados) con apertura directa en mapas.

6. **Privacidad y RGPD:**
   - Explicación clara sobre el tratamiento de datos (sin guardado de coordenadas GPS).
   - Exportación de los datos de la sesión en formato JSON mediante el menú compartir de Android.
   - Borrado completo de la sesión con liberación de plazas reservadas.

7. **Operación del Piloto (Admin):**
   - Acceso autenticado mediante token de administración.
   - Revisión de solicitudes de reserva entrantes (confirmar / rechazar).
   - Creación de nuevos servicios turísticos y nuevos turnos horarios.

---

## Arquitectura y Tecnologías

- **Lenguaje:** Kotlin 2.0
- **UI Toolkit:** Jetpack Compose + Material Design 3 (M3)
- **Patrón:** MVVM (Model-View-ViewModel) con `StateFlow`
- **Audio:** Android `android.speech.tts.TextToSpeech`
- **Ubicación:** Android Location APIs y cálculo geodésico Haversine
- **Iconografía:** Material Icons Extended + Icono adaptable personalizado
- **Recursos Gráficos:** Imágenes WebP nativas y paleta de colores mediterránea (*Terracota, Azul Marino, Pergamino*)

---

## Estructura del Proyecto

```
app/
├── src/main/
│   ├── AndroidManifest.xml
│   ├── java/com/example/
│   │   ├── MainActivity.kt
│   │   ├── model/
│   │   │   └── Models.kt
│   │   ├── data/
│   │   │   ├── CatalogRepository.kt
│   │   │   ├── AssistantEngine.kt
│   │   │   └── I18n.kt
│   │   ├── viewmodel/
│   │   │   └── GloviViewModel.kt
│   │   └── ui/
│   │       ├── GloviApp.kt
│   │       ├── theme/
│   │       │   ├── Color.kt
│   │       │   ├── Type.kt
│   │       │   └── Theme.kt
│   │       └── screens/
│   │           ├── HomeScreen.kt
│   │           ├── RoutesScreen.kt
│   │           ├── AssistantScreen.kt
│   │           ├── BookingsScreen.kt
│   │           ├── EmergencyScreen.kt
│   │           ├── PrivacyScreen.kt
│   │           └── AdminScreen.kt
│   └── res/
│       ├── drawable/
│       │   ├── ceuta_portada.webp
│       │   ├── ceuta_calle.webp
│       │   ├── ceuta_mar.webp
│       │   ├── ic_launcher_background.xml
│       │   └── ic_launcher_foreground.xml
│       ├── mipmap-*/
│       └── values/
│           ├── strings.xml
│           ├── colors.xml
│           └── themes.xml
```

---

## Licencia y Procedencia

Piloto desarrollado para la promoción turística y cultural de Ceuta. Las fuentes del catálogo y las normas del MVP se encuentran detalladas en la carpeta `docs/`.
