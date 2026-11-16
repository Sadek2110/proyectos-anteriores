---
name: sdd-development-loop
description: >-
  Metodología Specification-Driven Development (SDD) en bucle para diseñar,
  testear, implementar y verificar cada requisito funcional del widget hasta alcanzar
  el 100% de cobertura funcional sin regresiones.
---

# Skill: SDD (Specification-Driven Development) en Bucle

## Cuándo usar esta skill
Activar durante todo el ciclo de construcción y validación del proyecto tras la aprobación de los requisitos funcionales.

## Flujo del Bucle SDD
Para cada módulo o requisito funcional (`RF-01` a `RF-10` en `REQUISITOS_FUNCIONALES.md`):

1. **Verificación de Especificación**:
   - Revisar entradas, salidas, estados de error y criterios de aceptación en `REQUISITOS_FUNCIONALES.md`.
2. **Diseño de Pruebas (Test-First / Contract)**:
   - Escribir pruebas unitarias y de integración en `tests/` que validen exactamente los criterios de aceptación del requisito.
3. **Implementación Modular**:
   - Implementar el código en `src/` cumpliendo el contrato sin efectos secundarios indeseados.
4. **Ejecución y Diagnóstico Automático**:
   - Ejecutar `QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v` (o `pytest`).
   - Si algún test falla, analizar la traza, corregir el código y repetir el paso 4 inmediatamente.
5. **Prueba de Integración End-to-End**:
   - Verificar que el widget arranca, carga noticias reales de las fuentes de IA, anima el carrusel, redimensiona correctamente y guarda en SQLite sin errores.
