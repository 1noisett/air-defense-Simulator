# Simulación de Defensa Antiaérea

Este es un simulador educativo de sistemas de defensa contra misiles. El objetivo principal es la claridad pedagógica: cada decisión de diseño prioriza la comprensión matemática sobre el rendimiento.

> **Créditos:** Este proyecto fue diseñado e implementado íntegramente por **Claude Code** (Anthropic), actuando como agente de desarrollo principal bajo la dirección y supervisión del autor. Una demostración de ingeniería de software autónoma y modelado físico.

## ¿Cómo funciona?

El proyecto simula el ciclo completo de una interceptación:

1.  **Física y Trayectorias:** Utiliza un motor de física desde cero (sin bibliotecas externas) que implementa integración numérica **RK4** para una precisión máxima en misiles que realizan maniobras evasivas.
2.  **Detección y Rastreo:** Un modelo de Radar detecta amenazas en rango, y un sistema de rastreo (`ThreatTracker`) mantiene la identidad de los objetivos, incluso si se pierde la señal momentáneamente (coasting).
3.  **Guiado PN:** Los interceptores utilizan **Navegación Proporcional**, una técnica real de guiado que busca colisionar con el objetivo basándose en el cambio angular de la línea de visión.
4.  **Control de Batería:** Un controlador evalúa qué amenazas son más peligrosas para una "zona protegida" y asigna los interceptores disponibles de forma inteligente.

## Visualización
<img width="1512" height="827" alt="Screenshot 2026-05-28 at 6 55 57 PM" src="https://github.com/user-attachments/assets/e039f1cf-7653-4fc4-9a6b-46e14517ad42" />
<img width="1511" height="821" alt="Screenshot 2026-05-28 at 6 55 32 PM" src="https://github.com/user-attachments/assets/0d7c9f39-b1f0-4f59-8a13-157b5433622c" />


- **Modo Interactivo:** Una ventana de Matplotlib para ajustar parámetros y ver la física en tiempo real.
- **Interfaz Web:** Un frontend moderno que se conecta a una API en FastAPI para visualizar las trayectorias.

## Instalación y Uso

1. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
2. Ejecutar simulador de escritorio:
   ```bash
   python3 scripts/run_interactive.py
   ```
3. Ejecutar servidor web:
   ```bash
   python3 scripts/run_api.py
   ```

---
*Creado por 🤖 Claude Code.*
